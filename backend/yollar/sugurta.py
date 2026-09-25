# -*- coding: utf-8 -*-
"""SUG'URTADAN UNDIRISH — MIB qarori va vafot bo'yicha sug'urta tovoni.

Bu modul ilgari server.py ichida edi. Kod o'zgarmadi — faqat alohida
faylga ko'chirildi va Flask Blueprint orqali ilovaga ulanadi.
"""
import os
import sys
import datetime

from flask import Blueprint, jsonify, request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import database as db
import util
import letters
import importer
import vazifalar as vzf
import tahlil_jarayon as tj
from umumiy import (
    mustahkam_fayl_saqlash, hujjatlar_papkasi, tizimdan_oldingi_hujjatlar_papkasi,
    huquqiy_choralar_papkasi, hujjat_turi_sana_papkasi, sud_hujjatlari_mijoz_papkasi,
    mib_hujjatlari_mijoz_papkasi, f95413_mijoz_papkasi, f95413_hujjatlarni_nusxalash,
    anketa_mijoz_nomi, sugurta_hujjatlari_mijoz_papkasi, mib_hujjatlar_papkasi,
    bugungi_papka, row_list,
)

bp = Blueprint('sugurta', __name__)


def sugurta_avtomatik_hujjatlar(anketa, xat):
    """Sud va MIB bosqichlarida ALLAQACHON yuklangan hujjatlarni tizim
    O'ZI topib, sug'urta jildiga nusxalaydi va ro'yxatga qayd etadi.

    Shablondagi "Ilovalar" ro'yxati aynan shu hujjatlarni talab qiladi:
    polis, kredit shartnomasi, qarz ma'lumotnomasi, talabnomalar,
    da'vo arizasi va sud qarori, garov/kafillik shartnomalari, hamda
    MIB chiqargan hujjatlar. Xodim ularni qo'lda qayta qidirmasligi
    kerak.

    MUHIM: hujjat JORIY sikl xatida bo'lmasa, tizim uni 1) shu
    anketaning OLDINGI sikllaridan, 2) doimiy kredit hujjatlar
    arxividan ("Nollashtirish" qilingan bo'lsa ham saqlanadi) qidiradi.
    Qayta chaqirilganda takror nusxa yaratmaydi."""
    import shutil
    if not xat:
        return {'qoshildi': 0, 'nomlar': []}

    mijoz_nomi = anketa_mijoz_nomi(anketa, xat)
    jild = sugurta_hujjatlari_mijoz_papkasi(mijoz_nomi, anketa)
    undirish_id = db.sugurta_undirish_saqlash(anketa, xat_id=xat.get('id'))

    # Allaqachon qayd etilgan hujjatlar — takrorlanmasligi uchun.
    mavjud = db.sugurta_hujjatlar_royxati(undirish_id)
    mavjud_manbalar = {os.path.basename(h.get('fayl_yoli') or '') for h in mavjud}
    mavjud_nomlar = {h.get('hujjat_nomi') for h in mavjud}

    conn = db.get_conn()
    oldingi = [dict(r) for r in conn.execute(
        'SELECT * FROM xatlar WHERE anketa_raqami=? AND id != ? ORDER BY id DESC',
        (anketa, xat.get('id'))).fetchall()]
    arxiv_row = conn.execute(
        'SELECT * FROM kredit_hujjatlar_arxiv WHERE anketa_raqami=?', (anketa,)).fetchone()
    conn.close()
    arxiv = dict(arxiv_row) if arxiv_row else {}

    def topish(maydon):
        """Hujjatni joriy xatdan, oldingi sikllardan yoki arxivdan topadi."""
        manba = xat.get(maydon)
        if manba and os.path.exists(manba):
            return manba
        for eski in oldingi:
            if eski.get(maydon) and os.path.exists(eski[maydon]):
                return eski[maydon]
        if arxiv.get(maydon) and os.path.exists(arxiv[maydon]):
            return arxiv[maydon]
        return None

    # Shablondagi "Ilovalar" tartibi bilan bir xil raqamlaymiz.
    moslik = [
        ('kredit_shartnoma_fayl', '02', 'Kredit shartnomasi'),
        ('sud_malumotnoma_topshirishda_fayl', '03', "Qarzdorlik ma'lumotnomasi"),
        ('sud_malumotnoma_kun_fayl', '03', "Qarzdorlik ma'lumotnomasi (sud kuni)"),
        ('fayl_yoli', '04', 'Talabnoma (ogohlantirish) xati'),
        ('davo_ariza_fayl_yoli', '05', "Da'vo arizasi"),
        ('sud_qaror_fayl', '05', 'Sud hal qiluv qarori'),
        ('sud_buyrugi_fayl', '05', 'Sud buyrug\'i'),
        ('garov_shartnoma_fayl', '06', 'Garov shartnomasi'),
        ('kafillik_shartnoma_fayl', '06', 'Kafillik shartnomasi'),
        ('bank_baholash_fayl', '06', 'Bank baholashi'),
        ('ijro_varaqasi_fayl', '07', 'Ijro varaqasi'),
        ('mib_yakunlash_hujjati_fayl', '07', 'MIB ishini yakunlash hujjati'),
    ]

    qoshilgan = []
    nusxalangan = set()

    def qosh(manba, tartib, nomi):
        if not manba or not os.path.exists(manba):
            return
        kalit = os.path.abspath(manba)
        if kalit in nusxalangan or nomi in mavjud_nomlar:
            return
        fayl_nomi = f"{tartib}_{letters.safe_filename(nomi)}_{os.path.basename(manba)}"
        if fayl_nomi in mavjud_manbalar:
            nusxalangan.add(kalit)
            return
        maqsad = os.path.join(jild, fayl_nomi)
        try:
            if not os.path.exists(maqsad):
                shutil.copy2(manba, maqsad)
            db.sugurta_hujjat_qoshish(undirish_id, nomi, maqsad)
            nusxalangan.add(kalit)
            mavjud_nomlar.add(nomi)
            qoshilgan.append(nomi)
        except Exception:
            pass

    for maydon, tartib, nomi in moslik:
        qosh(topish(maydon), tartib, nomi)

    # MIB harakatlari bo'yicha tuzilgan dalolatnomalar — sug'urta uchun
    # eng muhim dalil hujjatlari (undirib bo'lmaganligi tasdig'i).
    for amal in db.get_mib_amallar(xat.get('id')):
        if amal.get('dalolatnoma_fayl'):
            nomi = f"MIB: {amal.get('amal_turi', '')} ({amal.get('amal_sanasi', '')})".strip()
            qosh(amal['dalolatnoma_fayl'], '07', nomi)

    return {'qoshildi': len(qoshilgan), 'nomlar': qoshilgan, 'jild': jild}


def sugurta_ish_konteksti(anketa, tur='mib'):
    """Sug'urta ishi uchun umumiy kontekst: mijoz nomi, bog'langan yozuv
    va hujjatlar papkasi. Ikkala tur (MIB qarori / vafot) uchun ham bir
    xil ishlaydi, shuning uchun hujjat yuklash va holat o'zgartirish
    endpointlari ikkalasiga baravar xizmat qiladi."""
    conn = db.get_conn()
    if tur == 'vafot':
        row = conn.execute(
            'SELECT * FROM vafot_etganlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1',
            (anketa,)).fetchone()
        conn.close()
        if not row:
            return None
        v = dict(row)
        prow = db.get_portfel_by_id(v.get('portfel_id')) or {}
        mijoz_nomi = v.get('mijoz_nomi') or prow.get('mijoz_nomi') or anketa_mijoz_nomi(anketa)
        return {'tur': 'vafot', 'vafot': v, 'xat': None, 'portfel': prow,
                'mijoz_nomi': mijoz_nomi,
                'jild': sugurta_hujjatlari_mijoz_papkasi(mijoz_nomi, anketa)}
    row = conn.execute(
        "SELECT * FROM xatlar WHERE anketa_raqami=? AND mib_holati='otkazildi' "
        "AND (arxivlangan IS NULL OR arxivlangan=0) ORDER BY id DESC LIMIT 1", (anketa,)).fetchone()
    conn.close()
    if not row:
        return None
    xat = dict(row)
    mijoz_nomi = anketa_mijoz_nomi(anketa, xat)
    return {'tur': 'mib', 'vafot': None, 'xat': xat,
            'portfel': db.get_portfel_by_id(xat['portfel_id']) or {},
            'mijoz_nomi': mijoz_nomi,
            'jild': sugurta_hujjatlari_mijoz_papkasi(mijoz_nomi, anketa)}


@bp.route('/api/sugurta_undirish/vafot_royxat', methods=['GET'])
def sugurta_undirish_vafot_royxat():
    """Vafot etgan mijozlar bo'yicha sug'urta jarayonlari ro'yxati.
    "Vafot etganlar" bo'limidagi BARCHA mijozlar bu yerda avtomatik
    ko'rinadi — sug'urtalangan shaxsning vafoti sug'urta hodisasidir."""
    try:
        muddat_kun = int(db.get_setting('sugurta_undirish_muddat_kun', 30))
    except Exception:
        muddat_kun = 30
    bugun = datetime.date.today()

    natija = []
    for item in db.get_sugurta_vafot_royxati():
        v = item['vafot']
        u = item['undirish'] or {}
        prow = db.get_portfel_by_id(v.get('portfel_id')) or {}
        asosiy = prow.get('asosiy_qarz') or 0
        foiz = prow.get('foiz_qarz') or 0
        holati = u.get('holati') or 'tayyorlanmoqda'

        kechikkan, kutilgan_kun = False, ''
        if holati == 'yuborildi' and u.get('ariza_sana'):
            try:
                a_dt = datetime.datetime.strptime(u['ariza_sana'], '%d.%m.%Y').date()
                kutilgan_kun = (bugun - a_dt).days
                kechikkan = kutilgan_kun > muddat_kun
            except Exception:
                pass

        undirish_id = u.get('id')
        natija.append({
            'anketa_raqami': v['anketa_raqami'], 'vafot_id': v['id'],
            'mijoz_nomi': v.get('mijoz_nomi', ''),
            'pinfl_stir': (prow.get('pinfl') or prow.get('stir') or ''),
            'vafot_sanasi': v.get('vafot_sanasi', '') or '',
            'polis_holati': v.get('polis_holati', '') or 'tekshirilmagan',
            'asosiy_qarz': asosiy, 'foiz_qarz': foiz, 'jami_qarz': asosiy + foiz,
            'sugurta_kompaniya': u.get('sugurta_kompaniya') or v.get('sugurta_kompaniya', '') or '',
            'polis_raqami': u.get('polis_raqami') or v.get('sugurta_polis_raqam', '') or '',
            'holati': holati,
            'holat_nomi': db.SUGURTA_HOLAT_NOMLARI.get(holati, holati),
            'ariza_raqami': u.get('ariza_raqami', '') or '',
            'ariza_sana': u.get('ariza_sana', '') or '',
            'ariza_bor': bool(u.get('ariza_fayl') and os.path.exists(u['ariza_fayl'])),
            'talab_summasi': u.get('talab_summasi') or 0,
            'tolangan_summa': u.get('tolangan_summa') or 0,
            'tolov_sana': u.get('tolov_sana', '') or '',
            'natija_izoh': u.get('natija_izoh', '') or '',
            'kechikkan': kechikkan, 'kutilgan_kun': kutilgan_kun,
            'hujjatlar_soni': len(db.sugurta_hujjatlar_royxati(undirish_id)) if undirish_id else 0,
        })

    soni = {}
    for r in natija:
        soni[r['holati']] = soni.get(r['holati'], 0) + 1
    return jsonify({'royxat': natija, 'soni': soni,
                    'holat_nomlari': db.SUGURTA_HOLAT_NOMLARI, 'muddat_kun': muddat_kun})


@bp.route('/api/sugurta_undirish/vafot_malumot', methods=['GET'])
def sugurta_undirish_vafot_malumot():
    """Vafot etgan mijoz bo'yicha sug'urta kartochkasi: vafot ma'lumotlari,
    qo'lda kiritiladigan maydonlar va biriktirilgan hujjatlar."""
    anketa = request.args.get('anketa', '').strip()
    if not anketa:
        return jsonify({'xato': 'Anketa raqami kerak'}), 400
    ktx = sugurta_ish_konteksti(anketa, 'vafot')
    if not ktx:
        return jsonify({'xato': "Bu anketa 'Vafot etganlar' ro'yxatida topilmadi"}), 404
    v, prow = ktx['vafot'], ktx['portfel']

    # Vafot bo'limida yuklangan hujjatlar (guvohnoma, pasport, polis)
    # avtomatik sug'urta jildiga qo'shiladi.
    try:
        avto = sugurta_vafot_avtomatik_hujjatlar(anketa, v)
    except Exception:
        avto = {'qoshildi': 0, 'nomlar': []}

    undirish = db.sugurta_undirish_olish(anketa, 'vafot') or {}
    undirish_id = undirish.get('id')
    asosiy = prow.get('asosiy_qarz') or 0
    foiz = prow.get('foiz_qarz') or 0

    return jsonify({
        'vafot': {
            'id': v['id'], 'anketa_raqami': anketa, 'mijoz_nomi': v.get('mijoz_nomi', ''),
            'vafot_sanasi': v.get('vafot_sanasi', '') or '',
            'polis_holati': v.get('polis_holati', '') or 'tekshirilmagan',
            'sugurta_kompaniya': v.get('sugurta_kompaniya', '') or '',
            'sugurta_polis_raqam': v.get('sugurta_polis_raqam', '') or '',
            'olimlik_guvohnomasi_fayl': v.get('olimlik_guvohnomasi_fayl', '') or '',
            'pasport_fayl': v.get('pasport_fayl', '') or '',
            'sugurta_polis_fayl': v.get('sugurta_polis_fayl', '') or '',
            'xabarnoma_holati': v.get('xabarnoma_holati', '') or '',
            'pinfl_stir': (prow.get('pinfl') or prow.get('stir') or ''),
            'shartnoma_sanasi': prow.get('shartnoma_sanasi', '') or '',
            'asosiy_qarz': asosiy, 'foiz_qarz': foiz, 'jami_qarz': asosiy + foiz,
        },
        'undirish': undirish,
        'hujjatlar': db.sugurta_hujjatlar_royxati(undirish_id) if undirish_id else [],
        'avto_qoshildi': avto.get('qoshildi', 0),
        'kompaniyalar': [k['nomi'] for k in db.sugurta_kompaniyalar_royxati()],
        'holat_nomlari': db.SUGURTA_HOLAT_NOMLARI,
    })


def sugurta_vafot_avtomatik_hujjatlar(anketa, vafot):
    """Vafot etganlar bo'limida allaqachon yuklangan hujjatlarni
    (o'lim guvohnomasi, pasport, sug'urta polisi, kompaniya javobi)
    sug'urta jildiga avtomatik nusxalaydi."""
    import shutil
    if not vafot:
        return {'qoshildi': 0, 'nomlar': []}
    ktx = sugurta_ish_konteksti(anketa, 'vafot')
    jild = ktx['jild'] if ktx else sugurta_hujjatlari_mijoz_papkasi(vafot.get('mijoz_nomi', ''), anketa)
    undirish_id = db.sugurta_undirish_saqlash(anketa, tur='vafot', vafot_id=vafot.get('id'))

    mavjud = db.sugurta_hujjatlar_royxati(undirish_id)
    mavjud_nomlar = {h.get('hujjat_nomi') for h in mavjud}

    moslik = [
        ('olimlik_guvohnomasi_fayl', '01', "Vafot to'g'risidagi guvohnoma (FHDYo)"),
        ('pasport_fayl', '03', 'Pasport nusxasi'),
        ('sugurta_polis_fayl', '04', "Sug'urta polisi"),
        ('javob_fayl', '09', "Sug'urta kompaniyasi javobi"),
    ]
    qoshilgan = []
    for maydon, tartib, nomi in moslik:
        manba = vafot.get(maydon)
        if not manba or not os.path.exists(manba) or nomi in mavjud_nomlar:
            continue
        maqsad = os.path.join(jild, f"{tartib}_{letters.safe_filename(nomi)}_{os.path.basename(manba)}")
        try:
            if not os.path.exists(maqsad):
                shutil.copy2(manba, maqsad)
            db.sugurta_hujjat_qoshish(undirish_id, nomi, maqsad)
            mavjud_nomlar.add(nomi)
            qoshilgan.append(nomi)
        except Exception:
            pass

    # Kredit shartnomasi — doimiy arxivdan ham qidiriladi.
    conn = db.get_conn()
    arxiv_row = conn.execute(
        'SELECT * FROM kredit_hujjatlar_arxiv WHERE anketa_raqami=?', (anketa,)).fetchone()
    xat_row = conn.execute(
        'SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1', (anketa,)).fetchone()
    conn.close()
    arxiv = dict(arxiv_row) if arxiv_row else {}
    xat = dict(xat_row) if xat_row else {}
    for maydon, tartib, nomi in [('kredit_shartnoma_fayl', '05', 'Kredit shartnomasi')]:
        manba = xat.get(maydon) or arxiv.get(maydon)
        if manba and os.path.exists(manba) and nomi not in mavjud_nomlar:
            maqsad = os.path.join(jild, f"{tartib}_{letters.safe_filename(nomi)}_{os.path.basename(manba)}")
            try:
                if not os.path.exists(maqsad):
                    shutil.copy2(manba, maqsad)
                db.sugurta_hujjat_qoshish(undirish_id, nomi, maqsad)
                qoshilgan.append(nomi)
            except Exception:
                pass

    return {'qoshildi': len(qoshilgan), 'nomlar': qoshilgan, 'jild': jild}


@bp.route('/api/sugurta_undirish/vafot_ariza_yaratish', methods=['POST'])
def sugurta_undirish_vafot_ariza_yaratish():
    """Sug'urtalangan shaxsning vafoti munosabati bilan sug'urta tovonini
    to'lash to'g'risidagi arizani shablon asosida tayyorlaydi."""
    data = request.get_json() or {}
    anketa = (data.get('anketa_raqami') or '').strip()
    if not anketa:
        return jsonify({'xato': 'Anketa raqami kerak'}), 400
    ktx = sugurta_ish_konteksti(anketa, 'vafot')
    if not ktx:
        return jsonify({'xato': "Bu anketa 'Vafot etganlar' ro'yxatida topilmadi"}), 404

    undirish = db.sugurta_undirish_olish(anketa, 'vafot') or {}
    kompaniya = (undirish.get('sugurta_kompaniya') or ktx['vafot'].get('sugurta_kompaniya') or '').strip()
    if not kompaniya:
        return jsonify({'xato': "Avval sug'urta kompaniyasi nomini kiriting va saqlang"}), 400

    prow = ktx['portfel']
    turi, mijoz = util.resolve_mijoz(prow) if prow else (None, None)
    fayl_yoli = os.path.join(
        ktx['jild'], f"Vafot_sugurta_arizasi_{letters.safe_filename(ktx['mijoz_nomi'])}_{anketa}.docx")
    try:
        letters.generate_vafot_sugurta_tovon_arizasi(
            fayl_yoli, ktx['vafot'], prow, undirish, mijoz, db.get_all_settings())
    except Exception as e:
        return jsonify({'xato': f"Arizani tayyorlashda xato: {e}"}), 500

    if (data.get('format') or '').lower() == 'pdf':
        try:
            pdf_yoli = letters.convert_docx_to_pdf(fayl_yoli)
            if pdf_yoli and os.path.exists(pdf_yoli):
                fayl_yoli = pdf_yoli
        except Exception:
            pass

    db.sugurta_undirish_saqlash(anketa, tur='vafot', vafot_id=ktx['vafot']['id'],
                                ariza_fayl=fayl_yoli)
    return jsonify({'ok': True, 'fayl': fayl_yoli})


@bp.route('/api/sugurta_undirish/royxat', methods=['GET'])
def sugurta_undirish_royxat():
    """MIBga o'tkazilgan BARCHA ishlar + ular bo'yicha sug'urtadan
    undirish holati."""
    try:
        muddat_kun = int(db.get_setting('sugurta_undirish_muddat_kun', 30))
    except Exception:
        muddat_kun = 30
    bugun = datetime.date.today()

    natija = []
    for item in db.get_sugurta_undirish_royxati():
        x = item['xat']
        u = item['undirish'] or {}
        prow = db.get_portfel_by_id(x['portfel_id'])
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
        jami_qarz = 0
        if prow:
            jami_qarz = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
        holati = u.get('holati') or 'tayyorlanmoqda'

        # Ariza yuborilgan, lekin belgilangan muddat ichida javob
        # kelmagan bo'lsa — ogohlantirish belgisi.
        kechikkan = False
        kutilgan_kun = ''
        if holati == 'yuborildi' and u.get('ariza_sana'):
            try:
                a_dt = datetime.datetime.strptime(u['ariza_sana'], '%d.%m.%Y').date()
                kutilgan_kun = (bugun - a_dt).days
                kechikkan = kutilgan_kun > muddat_kun
            except Exception:
                pass

        undirish_id = u.get('id')
        natija.append({
            'anketa_raqami': x['anketa_raqami'], 'xat_id': x['id'],
            'mijoz_nomi': x['mijoz_nomi'], 'turi': turi,
            'pinfl_stir': (prow.get('pinfl') or prow.get('stir') or '') if prow else '',
            'jami_qarz': jami_qarz,
            'mib_ish_raqami': x.get('mib_ish_raqami', '') or '',
            'mib_otkazilgan_sana': x.get('mib_otkazilgan_sana', '') or '',
            'mib_yakunlangan': bool(x.get('mib_yakunlangan')),
            'mib_yakunlash_sababi': x.get('mib_yakunlash_sababi', '') or '',
            # Qarzi qolmagan ish — sug'urtadan undiradigan narsa yo'q.
            # Ro'yxatda tarix sifatida qoladi, lekin alohida belgilanadi,
            # chunki unga ariza berish kerak emas.
            'qarz_yopilgan': jami_qarz <= 0,
            'holati': holati,
            'holat_nomi': db.SUGURTA_HOLAT_NOMLARI.get(holati, holati),
            'sugurta_kompaniya': u.get('sugurta_kompaniya', '') or '',
            'polis_raqami': u.get('polis_raqami', '') or '',
            'mib_asos_hujjat_nomi': u.get('mib_asos_hujjat_nomi', '') or '',
            'mib_asos_bor': bool(u.get('mib_asos_fayl') and os.path.exists(u['mib_asos_fayl'])),
            'ariza_raqami': u.get('ariza_raqami', '') or '',
            'ariza_sana': u.get('ariza_sana', '') or '',
            'talab_summasi': u.get('talab_summasi') or 0,
            'tolangan_summa': u.get('tolangan_summa') or 0,
            'tolov_sana': u.get('tolov_sana', '') or '',
            'natija_izoh': u.get('natija_izoh', '') or '',
            'kechikkan': kechikkan, 'kutilgan_kun': kutilgan_kun,
            'muddatidan_oldin': item.get('muddatidan_oldin', False),
            'ariza_bor': bool(u.get('ariza_fayl') and os.path.exists(u['ariza_fayl'])),
            'hujjatlar_soni': len(db.sugurta_hujjatlar_royxati(undirish_id)) if undirish_id else 0,
        })

    soni = {}
    for r in natija:
        soni[r['holati']] = soni.get(r['holati'], 0) + 1
    return jsonify({'royxat': natija, 'soni': soni,
                    'holat_nomlari': db.SUGURTA_HOLAT_NOMLARI,
                    'muddat_kun': muddat_kun})


@bp.route('/api/sugurta_undirish/malumot', methods=['GET'])
def sugurta_undirish_malumot():
    """Bitta mijoz uchun sug'urtadan undirish kartochkasi: MIB ma'lumotlari,
    sug'urta yozuvi, biriktirilgan hujjatlar."""
    anketa = request.args.get('anketa', '').strip()
    if not anketa:
        return jsonify({'xato': 'Anketa raqami kerak'}), 400
    conn = db.get_conn()
    row = conn.execute(
        "SELECT * FROM xatlar WHERE anketa_raqami=? AND mib_holati='otkazildi' "
        "AND (arxivlangan IS NULL OR arxivlangan=0) ORDER BY id DESC LIMIT 1", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Bu anketa bo\'yicha MIB ishi topilmadi'}), 404
    xat = dict(row)
    prow = db.get_portfel_by_id(xat['portfel_id'])

    # MUHIM: Sud va MIB bosqichida allaqachon yuklangan hujjatlar
    # (kredit shartnomasi, talabnoma, da'vo ariza, sud qarori, ijro
    # varaqasi, MIB dalolatnomalari) AVTOMATIK topilib, sug'urta
    # jildiga qo'shiladi — xodim ularni qayta qidirmaydi.
    try:
        avto = sugurta_avtomatik_hujjatlar(anketa, xat)
    except Exception:
        avto = {'qoshildi': 0, 'nomlar': []}

    undirish = db.sugurta_undirish_olish(anketa) or {}
    undirish_id = undirish.get('id')
    hujjatlar = db.sugurta_hujjatlar_royxati(undirish_id) if undirish_id else []

    # MIB bosqichida qilingan harakatlar — sug'urta arizasiga asos
    # bo'ladigan hujjatlarni xodim shu ro'yxatdan ko'rib tanlaydi.
    amallar = db.get_mib_amallar(xat['id'])
    mib_harakatlari = [{
        'id': a['id'], 'amal_turi': a.get('amal_turi', ''),
        'amal_sanasi': a.get('amal_sanasi', ''), 'tavsif': a.get('tavsif', '') or '',
        'dalolatnoma_fayl': a.get('dalolatnoma_fayl', '') or '',
    } for a in amallar]

    jami_qarz = 0
    if prow:
        jami_qarz = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
    undirilgan = db.get_mib_undirilgan_summa(xat['id'])

    return jsonify({
        'xat': {
            'id': xat['id'], 'anketa_raqami': anketa, 'mijoz_nomi': xat.get('mijoz_nomi', ''),
            'mib_ish_raqami': xat.get('mib_ish_raqami', '') or '',
            'mib_otkazilgan_sana': xat.get('mib_otkazilgan_sana', '') or '',
            'mib_yakunlangan': bool(xat.get('mib_yakunlangan')),
            'mib_yakunlangan_sana': xat.get('mib_yakunlangan_sana', '') or '',
            'mib_yakunlash_sababi': xat.get('mib_yakunlash_sababi', '') or '',
            'mib_yakunlash_hujjati_fayl': xat.get('mib_yakunlash_hujjati_fayl', '') or '',
            'ijro_varaqasi_fayl': xat.get('ijro_varaqasi_fayl', '') or '',
            'sud_qaror_fayl': xat.get('sud_qaror_fayl', '') or xat.get('sud_buyrugi_fayl', '') or '',
            'pinfl_stir': (prow.get('pinfl') or prow.get('stir') or '') if prow else '',
            'jami_qarz': jami_qarz, 'undirilgan_summa': undirilgan,
            'qoldiq': max(jami_qarz - undirilgan, 0),
        },
        'undirish': undirish,
        'hujjatlar': hujjatlar,
        'avto_qoshildi': avto.get('qoshildi', 0),
        'avto_nomlar': avto.get('nomlar', []),
        'mib_harakatlari': mib_harakatlari,
        'kompaniyalar': [k['nomi'] for k in db.sugurta_kompaniyalar_royxati()],
        'holat_nomlari': db.SUGURTA_HOLAT_NOMLARI,
    })


@bp.route('/api/sugurta_undirish/saqlash', methods=['POST'])
def sugurta_undirish_saqlash_endpoint():
    """Sug'urta polisi / MIB asos hujjati / ariza maydonlarini saqlaydi."""
    data = request.get_json() or {}
    anketa = (data.pop('anketa_raqami', '') or '').strip()
    if not anketa:
        return jsonify({'xato': 'Anketa raqami kerak'}), 400
    ish_turi = (data.pop('ish_turi', '') or 'mib').strip()
    ruxsat_etilgan = {
        'sugurta_kompaniya', 'polis_raqami', 'polis_sanasi',
        'mib_asos_hujjat_nomi', 'mib_asos_hujjat_sanasi', 'mib_asos_hujjat_raqami',
        'ariza_raqami', 'ariza_sana', 'talab_summasi',
        # Vafot arizasi uchun QO'LDA kiritiladigan maydonlar
        'pasport_seriya', 'pasport_raqam', 'guvohnoma_raqami', 'guvohnoma_sanasi',
        'vafot_sababi', 'shartnoma_bandi', 'sugurta_shartnoma_raqami',
        'sugurta_shartnoma_sanasi',
    }
    fields = {k: v for k, v in data.items() if k in ruxsat_etilgan}
    if 'talab_summasi' in fields:
        try:
            fields['talab_summasi'] = float(str(fields['talab_summasi']).replace(' ', '') or 0)
        except Exception:
            fields['talab_summasi'] = 0
    # Barcha sana maydonlarini tekshirib, kk.oo.yyyy ko'rinishiga keltiramiz —
    # xato terilgan sana jimgina saqlanib, keyin muddat hisobini buzmasin.
    sana_maydonlari = {
        'polis_sanasi': "Polis sanasi", 'ariza_sana': 'Ariza sanasi',
        'mib_asos_hujjat_sanasi': 'Asos hujjat sanasi',
        'guvohnoma_sanasi': 'Guvohnoma sanasi',
        'sugurta_shartnoma_sanasi': "Sug'urta shartnomasi sanasi",
    }
    for maydon, nomi in sana_maydonlari.items():
        if maydon in fields:
            toza, sana_xato = util.sana_tekshir(fields[maydon], nomi)
            if sana_xato:
                return jsonify({'xato': sana_xato}), 400
            fields[maydon] = toza
    # Yangi sug'urta kompaniyasi kiritilgan bo'lsa — ro'yxatga ham
    # qo'shib qo'yamiz (keyingi safar tanlash uchun tayyor bo'lsin).
    if fields.get('sugurta_kompaniya'):
        try:
            db.sugurta_kompaniya_qoshish(fields['sugurta_kompaniya'])
        except Exception:
            pass
    ktx = sugurta_ish_konteksti(anketa, ish_turi)
    if ish_turi == 'vafot':
        db.sugurta_undirish_saqlash(anketa, tur='vafot',
                                    vafot_id=(ktx['vafot']['id'] if ktx and ktx['vafot'] else None),
                                    **fields)
    else:
        db.sugurta_undirish_saqlash(anketa, tur='mib',
                                    xat_id=(ktx['xat']['id'] if ktx and ktx['xat'] else None),
                                    **fields)
    return jsonify({'ok': True})


@bp.route('/api/sugurta_undirish/hujjat_yuklash', methods=['POST'])
def sugurta_undirish_hujjat_yuklash():
    """Sug'urta ishiga hujjat biriktiradi.

    'tur' qiymatlari:
      mib_asos  — MIB chiqargan ASOS hujjat (dalolatnoma/qaror)
      polis     — sug'urta polisi
      ariza     — sug'urta kompaniyasiga yuborilgan ariza
      qoshimcha — xodim o'zi nom berib yuklagan istalgan hujjat
    """
    anketa = request.form.get('anketa_raqami', '').strip()
    tur = request.form.get('tur', 'qoshimcha').strip()
    ish_turi = (request.form.get('ish_turi') or 'mib').strip()
    hujjat_nomi = request.form.get('hujjat_nomi', '').strip()
    f = request.files.get('file')
    if not anketa or not f or not f.filename:
        return jsonify({'xato': 'Anketa raqami va fayl kerak'}), 400
    if tur == 'qoshimcha' and not hujjat_nomi:
        return jsonify({'xato': 'Hujjat nomini yozing'}), 400

    # MUHIM: mijoz nomi va papka ish turiga qarab aniqlanadi (bitta
    # anketa raqami ostida ikki xil mijoz bo'lishi mumkin).
    ktx = sugurta_ish_konteksti(anketa, ish_turi)
    if not ktx:
        return jsonify({'xato': 'Bu anketa bo\'yicha ish topilmadi'}), 404
    jild = ktx['jild']
    prefiks_nomlari = {'mib_asos': 'MIB_asos_hujjat', 'polis': 'Sugurta_polisi',
                       'ariza': 'Sugurta_arizasi', 'natija': 'Sugurta_javobi'}
    prefiks = prefiks_nomlari.get(tur) or letters.safe_filename(hujjat_nomi)[:40]
    fayl_yoli = os.path.join(jild, f"{prefiks}_{letters.safe_filename(f.filename)}")
    xato_natija = mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]

    bog = ({'vafot_id': ktx['vafot']['id']} if ish_turi == 'vafot' and ktx['vafot']
           else {'xat_id': ktx['xat']['id']} if ktx['xat'] else {})
    maydon = {'mib_asos': 'mib_asos_fayl', 'polis': 'polis_fayl',
              'ariza': 'ariza_fayl', 'natija': 'natija_fayl'}.get(tur)
    if maydon:
        saqlanadi = {maydon: fayl_yoli}
        # MIB asos hujjatining NOMI ham shu yerda saqlanadi — ro'yxatda
        # "qaysi hujjat asos bo'lgani" ko'rinib tursin.
        if tur == 'mib_asos' and hujjat_nomi:
            saqlanadi['mib_asos_hujjat_nomi'] = hujjat_nomi
        db.sugurta_undirish_saqlash(anketa, tur=ish_turi, **bog, **saqlanadi)
    else:
        undirish_id = db.sugurta_undirish_saqlash(anketa, tur=ish_turi, **bog)
        db.sugurta_hujjat_qoshish(undirish_id, hujjat_nomi, fayl_yoli)
    return jsonify({'ok': True, 'fayl': fayl_yoli})


@bp.route('/api/sugurta_undirish/hujjatlarni_yigish', methods=['POST'])
def sugurta_undirish_hujjatlarni_yigish():
    """Sud/MIB bosqichida yuklangan hujjatlarni QAYTA qidirib, sug'urta
    jildiga qo'shadi — masalan ish ochilgandan keyin yangi hujjat
    (sud qarori, dalolatnoma) yuklangan bo'lsa."""
    data = request.get_json() or {}
    anketa = (data.get('anketa_raqami') or '').strip()
    if not anketa:
        return jsonify({'xato': 'Anketa raqami kerak'}), 400
    conn = db.get_conn()
    row = conn.execute(
        "SELECT * FROM xatlar WHERE anketa_raqami=? AND mib_holati='otkazildi' "
        "AND (arxivlangan IS NULL OR arxivlangan=0) ORDER BY id DESC LIMIT 1", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': "Bu anketa bo'yicha MIB ishi topilmadi"}), 404
    natija = sugurta_avtomatik_hujjatlar(anketa, dict(row))
    return jsonify({'ok': True, **natija})


@bp.route('/api/sugurta_undirish/ariza_yaratish', methods=['POST'])
def sugurta_undirish_ariza_yaratish():
    """Sug'urta kompaniyasiga yuboriladigan "sug'urta tovonini to'lash
    to'g'risida"gi arizani shablon asosida AVTOMATIK tayyorlaydi.

    MUHIM: ariza faqat kredit qarzini MUDDATIDAN OLDIN undirish uchun
    chiqarilgan sud qarori bo'yicha beriladi — shablon matni aynan shu
    holatga (sug'urta shartnomasining 5.1/5.2-bandlari) asoslangan."""
    data = request.get_json() or {}
    anketa = (data.get('anketa_raqami') or '').strip()
    if not anketa:
        return jsonify({'xato': 'Anketa raqami kerak'}), 400

    conn = db.get_conn()
    row = conn.execute(
        "SELECT * FROM xatlar WHERE anketa_raqami=? AND mib_holati='otkazildi' "
        "AND (arxivlangan IS NULL OR arxivlangan=0) ORDER BY id DESC LIMIT 1", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': "Bu anketa bo'yicha MIB ishi topilmadi"}), 404
    xat = dict(row)

    undirish = db.sugurta_undirish_olish(anketa) or {}
    if not (undirish.get('sugurta_kompaniya') or '').strip():
        return jsonify({'xato': "Avval sug'urta kompaniyasi nomini kiriting va saqlang"}), 400

    prow = db.get_portfel_by_id(xat['portfel_id']) or {}
    settings = db.get_all_settings()
    mijoz_nomi = anketa_mijoz_nomi(anketa, xat)
    jild = sugurta_hujjatlari_mijoz_papkasi(mijoz_nomi, anketa)
    fayl_yoli = os.path.join(
        jild, f"Sugurta_arizasi_{letters.safe_filename(mijoz_nomi)}_{anketa}.docx")

    try:
        letters.generate_sugurta_tovon_arizasi(fayl_yoli, xat, prow, undirish, settings)
    except Exception as e:
        return jsonify({'xato': f"Arizani tayyorlashda xato: {e}"}), 500

    # Foydalanuvchi PDF so'ragan bo'lsa — konvertatsiya qilamiz.
    if (data.get('format') or '').lower() == 'pdf':
        try:
            pdf_yoli = letters.convert_docx_to_pdf(fayl_yoli)
            if pdf_yoli and os.path.exists(pdf_yoli):
                fayl_yoli = pdf_yoli
        except Exception:
            pass  # PDF bo'lmasa (Word o'rnatilmagan), .docx baribir tayyor

    db.sugurta_undirish_saqlash(anketa, xat_id=xat['id'], ariza_fayl=fayl_yoli)
    return jsonify({'ok': True, 'fayl': fayl_yoli})


@bp.route('/api/sugurta_undirish/hujjat/<int:hujjat_id>', methods=['DELETE'])
def sugurta_undirish_hujjat_ochirish(hujjat_id):
    db.sugurta_hujjat_ochirish(hujjat_id)
    return jsonify({'ok': True})


@bp.route('/api/sugurta_undirish/holat', methods=['POST'])
def sugurta_undirish_holat():
    """Sug'urta undirish holatini o'zgartiradi.

    MUHIM shartlar:
      • "Ariza yuborildi" — MIB ASOS hujjati biriktirilgan bo'lishi SHART
        (bo'limning butun mantig'i shu hujjatga asoslanadi) + sug'urta
        kompaniyasi nomi ko'rsatilishi kerak.
      • "To'landi" — to'langan summa ko'rsatilishi SHART.
      • "Rad etildi" — rad etish sababi (izoh) yozilishi SHART.
    Ikkala yakuniy holat uchun ham natijani tasdiqlovchi hujjat yuklash
    mumkin (majburiy emas)."""
    if request.files.get('natija_fayl') or request.form.get('holati'):
        data = request.form.to_dict()
    else:
        data = request.get_json() or {}
    anketa = (data.get('anketa_raqami') or '').strip()
    yangi_holat = data.get('holati', '')
    if not anketa or yangi_holat not in db.SUGURTA_HOLAT_NOMLARI:
        return jsonify({'xato': "Anketa raqami va to'g'ri holat kerak"}), 400

    ish_turi = (data.get('ish_turi') or 'mib').strip()
    mavjud = db.sugurta_undirish_olish(anketa, ish_turi) or {}
    qoshimcha = {}

    for k in ('sugurta_kompaniya', 'polis_raqami', 'ariza_raqami', 'ariza_sana'):
        if data.get(k):
            qoshimcha[k] = data[k]
    if qoshimcha.get('ariza_sana'):
        toza, sana_xato = util.sana_tekshir(qoshimcha['ariza_sana'], 'Ariza sanasi')
        if sana_xato:
            return jsonify({'xato': sana_xato}), 400
        qoshimcha['ariza_sana'] = toza
    if data.get('tolov_sana'):
        toza, sana_xato = util.sana_tekshir(
            data['tolov_sana'], "To'lov sanasi", kelajak_mumkinmi=False)
        if sana_xato:
            return jsonify({'xato': sana_xato}), 400
        data['tolov_sana'] = toza

    if yangi_holat == 'yuborildi':
        if ish_turi == 'vafot':
            # Vafot bo'yicha ASOS — o'lim guvohnomasi (FHDYo). U "Vafot
            # etganlar" bo'limida yuklanadi yoki shu yerda biriktiriladi.
            ktx = sugurta_ish_konteksti(anketa, 'vafot')
            guvohnoma = (ktx['vafot'].get('olimlik_guvohnomasi_fayl') if ktx and ktx['vafot'] else None)
            if not (guvohnoma and os.path.exists(guvohnoma)):
                return jsonify({'xato': "Vafot to'g'risidagi guvohnoma (FHDYo) yuklanishi "
                                        "SHART — sug'urta hodisasi aynan shu hujjat bilan "
                                        "tasdiqlanadi. Uni 'Vafot etganlar' bo'limida yuklang."}), 400
        else:
            asos_fayl = mavjud.get('mib_asos_fayl')
            if not (asos_fayl and os.path.exists(asos_fayl)):
                return jsonify({'xato': "MIB chiqargan ASOS hujjatni (dalolatnoma/qaror) "
                                        "yuklash MAJBURIY — sug'urtadan undirish aynan shu "
                                        "hujjatga asoslanadi"}), 400
        if not (qoshimcha.get('sugurta_kompaniya') or mavjud.get('sugurta_kompaniya')):
            return jsonify({'xato': "Sug'urta kompaniyasi nomini ko'rsating"}), 400
        qoshimcha.setdefault('ariza_sana', datetime.date.today().strftime('%d.%m.%Y'))

    if yangi_holat == 'tolandi':
        try:
            summa = float(str(data.get('tolangan_summa', '')).replace(' ', '') or 0)
        except Exception:
            summa = 0
        if summa <= 0:
            return jsonify({'xato': "To'langan summani kiriting"}), 400
        qoshimcha['tolangan_summa'] = summa
        qoshimcha['tolov_sana'] = data.get('tolov_sana') or datetime.date.today().strftime('%d.%m.%Y')

    if yangi_holat == 'rad_etildi' and not (data.get('izoh') or '').strip():
        return jsonify({'xato': "Rad etish sababini yozing"}), 400

    f = request.files.get('natija_fayl')
    if f and f.filename:
        ktx = sugurta_ish_konteksti(anketa, ish_turi)
        jild = ktx['jild'] if ktx else sugurta_hujjatlari_mijoz_papkasi(anketa_mijoz_nomi(anketa), anketa)
        fayl_yoli = os.path.join(jild, f"Sugurta_javobi_{letters.safe_filename(f.filename)}")
        xato_natija = mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
        if xato_natija:
            return jsonify({'xato': xato_natija[0]}), xato_natija[1]
        qoshimcha['natija_fayl'] = fayl_yoli

    db.sugurta_holat_ozgartirish(anketa, yangi_holat, data.get('izoh', ''),
                                 tur=ish_turi, **qoshimcha)
    return jsonify({'ok': True})


@bp.route('/api/sugurta_undirish/excel', methods=['GET'])
def sugurta_undirish_excel():
    """Sug'urtadan undirish ro'yxatini Excel qilib chiqaradi."""
    import tempfile
    from flask import send_file
    import pandas as pd
    resp = sugurta_undirish_royxat()
    rows = resp.get_json()['royxat']
    if not rows:
        return jsonify({'xato': "Hozircha ro'yxat bo'sh"}), 400
    df = pd.DataFrame([{
        'Anketa raqami': r['anketa_raqami'], 'PINFL/STIR': r['pinfl_stir'],
        'Mijoz nomi': r['mijoz_nomi'], 'Turi': r['turi'],
        'Jami qarz': r['jami_qarz'],
        'MIB ish raqami': r['mib_ish_raqami'],
        'MIBga o\'tkazilgan sana': r['mib_otkazilgan_sana'],
        'MIB holati': "Yakunlangan" if r['mib_yakunlangan'] else "Jarayonda",
        'MIB asos hujjati': r['mib_asos_hujjat_nomi'],
        "Sug'urta kompaniyasi": r['sugurta_kompaniya'],
        'Polis raqami': r['polis_raqami'],
        'Ariza raqami': r['ariza_raqami'], 'Ariza sanasi': r['ariza_sana'],
        'Talab summasi': r['talab_summasi'],
        'Holati': r['holat_nomi'],
        "To'langan summa": r['tolangan_summa'], "To'lov sanasi": r['tolov_sana'],
        'Izoh': r['natija_izoh'],
    } for r in rows])
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='sugurtadan_undirish.xlsx')


@bp.route('/api/sugurta_undirish/vafot_excel', methods=['GET'])
def sugurta_undirish_vafot_excel():
    """Vafot etganlar bo'yicha sug'urta jarayonlarini Excel qilib chiqaradi."""
    import tempfile
    from flask import send_file
    import pandas as pd
    rows = sugurta_undirish_vafot_royxat().get_json()['royxat']
    if not rows:
        return jsonify({'xato': "Hozircha ro'yxat bo'sh"}), 400
    polis_nomlari = {'tekshirilmagan': 'Tekshirilmagan', 'amalda': 'Amalda',
                     'muddati_otgan': "Muddati o'tgan"}
    df = pd.DataFrame([{
        'Anketa raqami': r['anketa_raqami'], 'PINFL/STIR': r['pinfl_stir'],
        'Mijoz nomi': r['mijoz_nomi'], 'Vafot sanasi': r['vafot_sanasi'],
        'Polis holati': polis_nomlari.get(r['polis_holati'], r['polis_holati']),
        'Asosiy qarz': r['asosiy_qarz'], 'Foiz qarzi': r['foiz_qarz'], 'Jami qarz': r['jami_qarz'],
        "Sug'urta kompaniyasi": r['sugurta_kompaniya'], 'Polis raqami': r['polis_raqami'],
        'Ariza raqami': r['ariza_raqami'], 'Ariza sanasi': r['ariza_sana'],
        'Talab summasi': r['talab_summasi'], 'Holati': r['holat_nomi'],
        "To'langan summa": r['tolangan_summa'], "To'lov sanasi": r['tolov_sana'],
        'Izoh': r['natija_izoh'],
    } for r in rows])
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True,
                     download_name='vafot_sugurta_jarayonlari.xlsx')


@bp.route('/api/sugurta_undirish/kompaniyalar', methods=['GET', 'POST', 'DELETE'])
def sugurta_undirish_kompaniyalar():
    """Sug'urta kompaniyalari ro'yxati — foydalanuvchi o'zi to'ldiradi."""
    if request.method == 'GET':
        return jsonify({'royxat': db.sugurta_kompaniyalar_royxati(faqat_faol=False)})
    if request.method == 'POST':
        nomi = (request.get_json() or {}).get('nomi', '').strip()
        if not nomi:
            return jsonify({'xato': 'Kompaniya nomini yozing'}), 400
        db.sugurta_kompaniya_qoshish(nomi)
        return jsonify({'ok': True})
    kompaniya_id = (request.get_json() or {}).get('id')
    if not kompaniya_id:
        return jsonify({'xato': 'ID kerak'}), 400
    db.sugurta_kompaniya_ochirish(int(kompaniya_id))
    return jsonify({'ok': True})
