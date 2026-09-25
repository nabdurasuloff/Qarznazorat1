# -*- coding: utf-8 -*-
"""BIZNES-HAMROH.UZ — davo arizalarni portal orqali elektron yuborish.

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

bp = Blueprint('bh', __name__)


def _bh_sana(qiymat):
    """ISO sanani (2026-09-17T17:12:55) kun.oy.yil ko'rinishiga keltiradi."""
    if not qiymat:
        return ''
    s = str(qiymat)
    try:
        return datetime.datetime.fromisoformat(s).strftime('%d.%m.%Y')
    except Exception:
        return s[:10]


def bh_portal_malumotlari(anketa, xat, prow):
    """Portalning "Ариза маълумотлари" shakli uchun BARCHA maydonlarni,
    aynan portaldagi tartib va nomlar bilan tayyorlaydi. Qiymatlar
    portfel, ta'minot va Sozlamalardan AVTOMATIK olinadi; xodim
    portalga faqat nusxalab qo'yadi."""
    settings = db.get_all_settings()
    taminot = db.get_taminot(anketa) or {}
    murojaat = db.bh_murojaat_olish(anketa) or {}
    turi, mijoz = util.resolve_mijoz(prow) if prow else (xat.get('mijoz_turi'), None)

    def q(maydon, zaxira=''):
        """Avval xodim qo'lda kiritgan qiymat, bo'lmasa avtomatik qiymat."""
        return murojaat.get(maydon) if murojaat.get(maydon) not in (None, '') else zaxira

    def valyuta_nomi(kod):
        """Portfelda valyuta ISO-4217 RAQAMLI kod sifatida saqlanadi
        (masalan '840.0'), portal esa harfli kodni ('USD') kutadi."""
        try:
            k = str(int(float(kod or 0)))
        except Exception:
            return 'UZS'
        return {'860': 'UZS', '840': 'USD', '978': 'EUR', '643': 'RUB',
                '156': 'CNY', '392': 'JPY', '826': 'GBP', '0': 'UZS'}.get(k, 'UZS')

    sana_formati = _bh_sana

    davo_asosiy = xat.get('davo_summasi_asosiy') or 0
    davo_foiz = xat.get('davo_summasi_foiz') or 0
    davo_jarima = xat.get('davo_summasi_jarima') or 0

    sud_nomi = "Iqtisodiy sud" if turi in ('yuridik', 'yatt') else "Fuqarolik sudi"
    sud_toliq = settings.get('sud_iqtisodiy_nomi', '') if turi in ('yuridik', 'yatt') \
        else settings.get('sud_fuqarolik_nomi', '')

    return {
        'yuborilgan_bolim': {
            'Yuborilgan hudud': q('yuborilgan_tashkilot', settings.get('bh_hududiy_boshqarma', '')),
            'Sud': q('sud_nomi', sud_toliq or sud_nomi),
        },
        'davogar': {
            'Arizachi STIR/JSHSHIR': settings.get('bank_stir', ''),
            'Arizachi nomi': settings.get('bank_nomi', ''),
            'Arizachi mas\'ul xodimi': settings.get('bh_masul_xodim', '') or settings.get('rahbar_ism', ''),
            'Arizachi turi': settings.get('bh_arizachi_turi', 'Yuridik shaxs'),
            'Arizachi telefon raqami': settings.get('bh_masul_tel', '') or settings.get('filial_tel', ''),
            'Arizachi MFOsi': settings.get('bh_mfo', ''),
            'Arizachi hisob raqami': settings.get('bank_hisob_raqami_filial', ''),
            'Arizachi manzili': settings.get('bank_rasmiy_manzil_filial', ''),
        },
        'javobgar': {
            'STIR/JSHSHIR': (prow.get('pinfl') or prow.get('stir') or '') if prow else '',
            'Nomi/FISH': xat.get('mijoz_nomi', ''),
            'Manzil': (mijoz.get('manzil') if mijoz else '') or '',
            'Telefon raqami': (mijoz.get('tel') if mijoz else '') or '',
            'Ishtirok turi': q('javobgar_ishtirok_turi', 'Qarzdor'),
            'Asos (hujjat) turi': q('asos_hujjat_turi', 'Kredit shartnomasi'),
            'Asos (hujjat) sanasi': q('asos_hujjat_sanasi', (prow.get('shartnoma_sanasi') or '') if prow else ''),
            'Asos (hujjat) raqami': q('asos_hujjat_raqami', (prow.get('kredit_hisob_raqami') or '') if prow else ''),
        },
        'kredit_taminoti': {
            'Garov turi': {'kafillik': 'Kafillik', 'garov': 'Garov',
                            'kafillik_garov': 'Kafillik va garov'}.get(taminot.get('taminot_turi', ''), "Ta'minotsiz"),
            'Garov tavsifi': taminot.get('garov_tavsifi', '') or '',
            'Garov qiymati': taminot.get('garov_bahosi', '') or '',
        },
        'kredit_shartnoma': {
            # MUHIM: portal "Shartnoma raqami" maydoniga kredit ZAYAFKA
            # (ariza) raqami yoziladi — bu tizimda anketa raqamining
            # o'zi, kredit hisob raqami emas.
            'Shartnoma raqami': q('shartnoma_raqami', anketa),
            'Shartnoma sanasi': q('shartnoma_sanasi', (prow.get('shartnoma_sanasi') or '') if prow else ''),
            'Shartnoma foizi': q('shartnoma_foizi', (prow.get('yillik_foiz') or '') if prow else ''),
            'Shartnoma muddati': q('shartnoma_muddati', (prow.get('shartnoma_tugash_sanasi') or '') if prow else ''),
            'Valyuta': q('valyuta', valyuta_nomi(prow.get('valyuta')) if prow else 'UZS'),
            'Summasi': q('shartnoma_summasi', ''),
        },
        'qarz': {
            'Qarz hisoblangan sanasi': q('qarz_hisoblangan_sana', sana_formati(xat.get('davo_ariza_sana'))),
            'Davo summasi': q('davo_summasi', davo_asosiy + davo_foiz + davo_jarima),
            'Joriy davr uchun asosiy qarz': q('joriy_asosiy_qarz', (prow.get('asosiy_qarz') or 0) if prow else 0),
            'Joriy davr uchun hisoblangan foiz': q('joriy_hisoblangan_foiz', (prow.get('foiz_qarz') or 0) if prow else 0),
            'Asosiy qarz bo\'yicha muddati o\'tgan qarzdorlik': q('mo_asosiy_qarz', davo_asosiy),
            'Muddati o\'tgan asosiy qarzga hisoblangan foiz': q('mo_asosiy_foiz', davo_foiz),
            'Muddati o\'tgan foiz to\'lovi': q('mo_foiz_tolovi', davo_jarima),
        },
    }


def bh_sud_jildini_toldirish(anketa):
    """Portal murojaati QABUL QILINGANDA chaqiriladi: sud uchun kerakli
    barcha hujjatlarni tizim o'zi yig'adi —

      1) Sud yig'ma jild papkasini ochib, Titulni yaratadi;
      2) Xat va Davo arizani jildga jismonan nusxalaydi;
      3) Kredit hujjatlarini (joriy sikldan yoki doimiy arxivdan) topib
         qo'shadi;
      4) Portal ilovalarini va portal TASDIQ hujjatini ham jildga
         qo'shib qo'yadi.

    Shu bilan xodim "Shakillantirish" tugmasini bosmasa ham, jild
    to'liq tayyor bo'ladi."""
    import shutil
    conn = db.get_conn()
    row = conn.execute(
        "SELECT * FROM xatlar WHERE anketa_raqami=? AND (arxivlangan IS NULL OR arxivlangan=0) "
        "ORDER BY id DESC LIMIT 1", (anketa,)).fetchone()
    conn.close()
    if not row:
        return {'xato': 'Xat topilmadi'}
    xat = dict(row)
    prow = db.get_portfel_by_id(xat['portfel_id'])
    turi, mijoz = util.resolve_mijoz(prow) if prow else (xat.get('mijoz_turi'), None)
    settings = db.get_all_settings()

    sikl_sana_dt = None
    try:
        sikl_sana_dt = datetime.datetime.fromisoformat(xat.get('yaratilgan_sana'))
    except Exception:
        pass
    jild_papka = sud_hujjatlari_mijoz_papkasi(xat.get('mijoz_nomi', ''), sikl_sana_dt, anketa)

    # 1) Titul
    titul_path = os.path.join(jild_papka, '00_Titul.docx')
    letters.generate_sud_yigma_jild_titul(titul_path, xat, prow, mijoz, settings)
    db.sud_yigma_jild_yaratish(xat['id'], jild_papka, titul_path)

    qoshilgan = []
    nusxalangan_manbalar = set()

    def nusxala(manba, nomi):
        """MUHIM: bitta ASL fayl jildga faqat BIR MARTA tushadi — masalan
        Talabnoma xati ham "Xat" sifatida, ham portal ilovasi sifatida
        ro'yxatda bo'lsa, u takrorlanib ikki nusxa bo'lib qolmaydi."""
        if not manba or not os.path.exists(manba):
            return
        kalit = os.path.abspath(manba)
        if kalit in nusxalangan_manbalar:
            return
        maqsad = os.path.join(jild_papka, nomi)
        if os.path.exists(maqsad):
            nusxalangan_manbalar.add(kalit)
            return
        try:
            shutil.copy2(manba, maqsad)
            nusxalangan_manbalar.add(kalit)
            qoshilgan.append(nomi)
        except Exception:
            pass

    # 2) Xat va Davo ariza
    nusxala(xat.get('fayl_yoli'), f"98_Xat_{os.path.basename(xat.get('fayl_yoli') or 'xat')}")
    nusxala(xat.get('davo_ariza_fayl_yoli'),
            f"99_Davo_ariza_{os.path.basename(xat.get('davo_ariza_fayl_yoli') or 'davo')}")

    # 3) Kredit hujjatlari — joriy sikldan yoki doimiy arxivdan
    conn = db.get_conn()
    arxiv_row = conn.execute(
        'SELECT * FROM kredit_hujjatlar_arxiv WHERE anketa_raqami=?', (anketa,)).fetchone()
    conn.close()
    arxiv = dict(arxiv_row) if arxiv_row else {}
    kredit_moslik = [
        ('kredit_shartnoma_fayl', '02_Kredit_shartnoma'),
        ('kafillik_shartnoma_fayl', '03_Kafillik_shartnoma'),
        ('garov_shartnoma_fayl', '04_Garov_shartnoma'),
        ('bank_baholash_fayl', '05_Bank_baholash'),
    ]
    for maydon, prefiks in kredit_moslik:
        manba = xat.get(maydon) or arxiv.get(maydon)
        if manba and os.path.exists(manba):
            nusxala(manba, f"{prefiks}_{os.path.basename(manba)}")
            if not xat.get(maydon):
                db.sud_hujjat_saqlash(xat['id'], maydon, manba)

    # 4) Portal ilovalari va tasdiq hujjati
    murojaat = db.bh_murojaat_olish(anketa) or {}
    if murojaat.get('id'):
        for il in db.bh_ilovalar_royxati(murojaat['id']):
            nusxala(il.get('fayl_yoli'),
                    f"BH_{letters.safe_filename(il.get('ilova_turi', ''))[:40]}_{os.path.basename(il.get('fayl_yoli') or '')}")
    if murojaat.get('tasdiq_fayl'):
        nusxala(murojaat['tasdiq_fayl'],
                f"01_Portal_tasdigi_{os.path.basename(murojaat['tasdiq_fayl'])}")

    return {'papka': jild_papka, 'qoshilgan_soni': len(qoshilgan), 'qoshilgan': qoshilgan}


def bh_avtomatik_ilovalar(anketa, xat):
    """Tizimda allaqachon mavjud hujjatlarni portal ilovalariga
    AVTOMATIK biriktiradi — har biri portalning o'z ilova turi bilan.
    Kredit/garov hujjatlari joriy siklda bo'lmasa, DOIMIY arxivdan ham
    qidiriladi. Takror biriktirilmaydi (bir tur — bir marta)."""
    murojaat_id = db.bh_murojaat_saqlash(anketa, xat_id=xat.get('id'))
    mavjud_turlar = {il['ilova_turi'] for il in db.bh_ilovalar_royxati(murojaat_id)}

    conn = db.get_conn()
    arxiv_row = conn.execute(
        'SELECT * FROM kredit_hujjatlar_arxiv WHERE anketa_raqami=?', (anketa,)).fetchone()
    conn.close()
    arxiv = dict(arxiv_row) if arxiv_row else {}

    # (xatdagi maydon, portaldagi ilova turi)
    moslik = [
        ('fayl_yoli', "Talabnoma xatlari nusxasi."),
        ('kredit_shartnoma_fayl', "Kredit shartnomasi va unga 1-ilova nusxasi."),
        ('garov_shartnoma_fayl', "Garov shartnomasi nusxasi."),
        ('sud_malumotnoma_topshirishda_fayl', "Qarzdorlik bo'yicha ma'lumotnoma."),
    ]
    for maydon, ilova_turi in moslik:
        if ilova_turi in mavjud_turlar:
            continue
        manba = xat.get(maydon) or arxiv.get(maydon)
        if manba and os.path.exists(manba):
            db.bh_ilova_qoshish(murojaat_id, ilova_turi, manba)
    return murojaat_id


@bp.route('/api/bh/royxat', methods=['GET'])
def bh_royxat():
    """Biznes-hamroh.uz portaliga yuborilishi kerak bo'lgan (yoki
    yuborilgan) barcha ishlar, holati bilan birga."""
    natija = []
    for item in db.get_bh_royxati():
        x = item['xat']
        m = item['murojaat'] or {}
        prow = db.get_portfel_by_id(x['portfel_id'])
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
        asosiy = x.get('davo_summasi_asosiy') or 0
        foiz = x.get('davo_summasi_foiz') or 0
        jarima = x.get('davo_summasi_jarima') or 0
        holati = m.get('holati', 'tayyorlanmoqda')
        natija.append({
            'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'], 'turi': turi,
            'pinfl_stir': (prow.get('pinfl') or prow.get('stir') or '') if prow else '',
            'davo_summasi': asosiy + foiz + jarima,
            'davo_ariza_sana': _bh_sana(x.get('davo_ariza_sana')),
            'holati': holati, 'holat_nomi': db.BH_HOLAT_NOMLARI.get(holati, holati),
            'murojaat_raqami': m.get('murojaat_raqami', '') or '',
            'yuborilgan_sana': m.get('yuborilgan_sana', '') or '',
            'ijro_muddati': m.get('ijro_muddati', '') or '',
            'natija_izoh': m.get('natija_izoh', '') or '',
            'ilovalar_soni': len(db.bh_ilovalar_royxati(m['id'])) if m.get('id') else 0,
        })
    soni = {}
    for r in natija:
        soni[r['holati']] = soni.get(r['holati'], 0) + 1
    return jsonify({'royxat': natija, 'soni': soni, 'holat_nomlari': db.BH_HOLAT_NOMLARI})


@bp.route('/api/bh/malumot', methods=['GET'])
def bh_malumot():
    """Bitta mijoz uchun portalga kiritiladigan TO'LIQ ma'lumotlar
    to'plami (nusxalash uchun tayyor) va biriktirilgan ilovalar."""
    anketa = request.args.get('anketa', '').strip()
    if not anketa:
        return jsonify({'xato': 'Anketa raqami kerak'}), 400
    conn = db.get_conn()
    row = conn.execute(
        "SELECT * FROM xatlar WHERE anketa_raqami=? AND (arxivlangan IS NULL OR arxivlangan=0) "
        "ORDER BY id DESC LIMIT 1", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Xat topilmadi'}), 404
    xat = dict(row)
    prow = db.get_portfel_by_id(xat['portfel_id'])

    # MUHIM: tizimda ALLAQACHON mavjud bo'lgan hujjatlar (Talabnoma/
    # Ogohlantirish xati, Davo ariza, kredit/garov shartnomalari) portal
    # ilovalariga AVTOMATIK biriktiriladi — xodim ularni qayta qidirib,
    # qo'lda yuklab o'tirmasligi uchun.
    murojaat_id = bh_avtomatik_ilovalar(anketa, xat)

    murojaat = db.bh_murojaat_olish(anketa) or {}
    ilovalar = db.bh_ilovalar_royxati(murojaat_id) if murojaat_id else []
    return jsonify({
        'malumotlar': bh_portal_malumotlari(anketa, xat, prow),
        'murojaat': murojaat,
        'ilovalar': ilovalar,
        'ilova_turlari': db.BH_ILOVA_TURLARI,
        'ishtirok_turlari': db.BH_ISHTIROK_TURLARI,
        # Qaysi maydonni xodim QO'LDA o'zgartira oladi (ko'rinadigan nomi
        # -> bazadagi ustun nomi). Avtomatik qiymat faqat standart taklif;
        # portal boshqacha raqam talab qilsa, xodim uni tuzatib qo'yadi.
        'tahrir_maydonlari': {
            'Yuborilgan hudud': 'yuborilgan_tashkilot',
            'Sud': 'sud_nomi',
            'Ishtirok turi': 'javobgar_ishtirok_turi',
            'Asos (hujjat) turi': 'asos_hujjat_turi',
            'Asos (hujjat) sanasi': 'asos_hujjat_sanasi',
            'Asos (hujjat) raqami': 'asos_hujjat_raqami',
            'Shartnoma raqami': 'shartnoma_raqami',
            'Shartnoma sanasi': 'shartnoma_sanasi',
            'Shartnoma foizi': 'shartnoma_foizi',
            'Shartnoma muddati': 'shartnoma_muddati',
            'Valyuta': 'valyuta',
            'Summasi': 'shartnoma_summasi',
            'Qarz hisoblangan sanasi': 'qarz_hisoblangan_sana',
            'Davo summasi': 'davo_summasi',
            'Joriy davr uchun asosiy qarz': 'joriy_asosiy_qarz',
            'Joriy davr uchun hisoblangan foiz': 'joriy_hisoblangan_foiz',
            "Asosiy qarz bo'yicha muddati o'tgan qarzdorlik": 'mo_asosiy_qarz',
            "Muddati o'tgan asosiy qarzga hisoblangan foiz": 'mo_asosiy_foiz',
            "Muddati o'tgan foiz to'lovi": 'mo_foiz_tolovi',
        },
        'holat_nomlari': db.BH_HOLAT_NOMLARI,
    })


@bp.route('/api/bh/saqlash', methods=['POST'])
def bh_saqlash():
    """Portal maydonlarini (xodim qo'lda tuzatgan qiymatlarni) saqlaydi."""
    data = request.get_json() or {}
    anketa = (data.pop('anketa_raqami', '') or '').strip()
    if not anketa:
        return jsonify({'xato': 'Anketa raqami kerak'}), 400
    ruxsat_etilgan = {
        'murojaat_raqami', 'yuborilgan_sana', 'ijro_muddati', 'yuborilgan_tashkilot', 'sud_nomi',
        'javobgar_ishtirok_turi', 'asos_hujjat_turi', 'asos_hujjat_sanasi', 'asos_hujjat_raqami',
        'shartnoma_raqami', 'shartnoma_sanasi', 'shartnoma_foizi', 'shartnoma_muddati',
        'valyuta', 'shartnoma_summasi', 'qarz_hisoblangan_sana', 'davo_summasi',
        'joriy_asosiy_qarz', 'joriy_hisoblangan_foiz', 'mo_asosiy_qarz', 'mo_asosiy_foiz',
        'mo_foiz_tolovi',
    }
    fields = {k: v for k, v in data.items() if k in ruxsat_etilgan}
    conn = db.get_conn()
    xat_row = conn.execute(
        'SELECT id FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1', (anketa,)).fetchone()
    conn.close()
    db.bh_murojaat_saqlash(anketa, xat_id=xat_row['id'] if xat_row else None, **fields)
    return jsonify({'ok': True})


@bp.route('/api/bh/holat', methods=['POST'])
def bh_holat():
    """Murojaat holatini o'zgartiradi (Yuborildi / Javob kutilmoqda /
    Qabul qilindi / Rad etildi).

    MUHIM: "Qabul qilindi" holati uchun buni TASDIQLOVCHI PDF hujjat
    yuklash MAJBURIY — chunki bu holat ishni avtomatik ravishda Sud
    bosqichiga o'tkazib yuboradi, va bunday muhim qadam hujjat bilan
    asoslanishi kerak. Shu sabab bu holat `multipart/form-data` orqali
    (fayl bilan birga) yuboriladi."""
    if request.files.get('tasdiq_fayl') or request.form.get('holati'):
        data = request.form.to_dict()
    else:
        data = request.get_json() or {}
    anketa = (data.get('anketa_raqami') or '').strip()
    yangi_holat = data.get('holati', '')
    if not anketa or yangi_holat not in db.BH_HOLAT_NOMLARI:
        return jsonify({'xato': "Anketa raqami va to'g'ri holat kerak"}), 400

    qoshimcha = {}
    if yangi_holat == 'qabul_qilindi':
        mavjud = db.bh_murojaat_olish(anketa) or {}
        f = request.files.get('tasdiq_fayl')
        if not (f and f.filename) and not mavjud.get('tasdiq_fayl'):
            return jsonify({'xato': "Maqullanganini tasdiqlovchi hujjat (PDF) yuklash MAJBURIY"}), 400
        if f and f.filename:
            mijoz_nomi = anketa_mijoz_nomi(anketa)
            out_dir = bugungi_papka('Biznes-hamroh tasdiqlar')
            fayl_yoli = os.path.join(
                out_dir, f"{letters.safe_filename(mijoz_nomi)}_{anketa}_Portal_tasdigi_{letters.safe_filename(f.filename)}")
            xato_natija = mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
            if xato_natija:
                return jsonify({'xato': xato_natija[0]}), xato_natija[1]
            qoshimcha['tasdiq_fayl'] = fayl_yoli

    for k in ('murojaat_raqami', 'yuborilgan_sana', 'ijro_muddati'):
        if data.get(k):
            qoshimcha[k] = data[k]
    if qoshimcha:
        db.bh_murojaat_saqlash(anketa, **qoshimcha)
    db.bh_holat_ozgartirish(anketa, yangi_holat, data.get('izoh', ''))

    # MUHIM (integratsiya): portal SSP o'rnini egallagani uchun, murojaat
    # QABUL QILINGANDA — bu, avvalgi "Davo ariza SSPdan tasdiqlanib
    # qaytdi" bosqichining aynan o'zi. Shu sabab Davo arizani
    # 'olib_kelindi' deb belgilaymiz, va ish AVTOMATIK ravishda
    # "SSPdan o'tib sudga jo'natiladiganlar" ro'yxatiga tushadi.
    sudga_otdi = False
    if yangi_holat == 'qabul_qilindi':
        conn = db.get_conn()
        row = conn.execute(
            "SELECT * FROM xatlar WHERE anketa_raqami=? AND (arxivlangan IS NULL OR arxivlangan=0) "
            "ORDER BY id DESC LIMIT 1", (anketa,)).fetchone()
        conn.close()
        if row and dict(row).get('davo_ariza_holati') != 'olib_kelindi':
            xat = dict(row)
            murojaat = db.bh_murojaat_olish(anketa) or {}
            prow = db.get_portfel_by_id(xat['portfel_id'])
            db.mark_davo_ariza_olib_kelindi(
                xat['id'],
                murojaat.get('murojaat_raqami', '') or '',
                murojaat.get('holat_sana') or datetime.datetime.now().strftime('%d.%m.%Y'),
                portfel_row=prow, settings=db.get_all_settings())
            sudga_otdi = True

    # MUHIM: murojaat qabul qilingach, sud uchun kerakli BARCHA
    # hujjatlarni tizim O'ZI yig'ib, Sud yig'ma jildini yaratadi va
    # to'ldiradi — xodim qo'lda hech narsa ko'chirmasligi uchun.
    jild_natija = {}
    if yangi_holat == 'qabul_qilindi':
        try:
            jild_natija = bh_sud_jildini_toldirish(anketa)
        except Exception as e:
            jild_natija = {'xato': str(e)}

    return jsonify({'ok': True, 'sudga_otdi': sudga_otdi, 'jild': jild_natija})


@bp.route('/api/bh/ilova_yuklash', methods=['POST'])
def bh_ilova_yuklash():
    """Portalga yuklanadigan ilova hujjatini biriktiradi."""
    anketa = request.form.get('anketa_raqami', '').strip()
    ilova_turi = request.form.get('ilova_turi', '').strip()
    f = request.files.get('file')
    if not anketa or not ilova_turi or not f or not f.filename:
        return jsonify({'xato': "Anketa raqami, ilova turi va fayl kerak"}), 400
    mijoz_nomi = anketa_mijoz_nomi(anketa)
    out_dir = bugungi_papka('Biznes-hamroh ilovalari')
    fayl_yoli = os.path.join(
        out_dir, f"{letters.safe_filename(mijoz_nomi)}_{anketa}_{letters.safe_filename(ilova_turi)[:40]}_{letters.safe_filename(f.filename)}")
    xato_natija = mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    murojaat_id = db.bh_murojaat_saqlash(anketa)
    db.bh_ilova_qoshish(murojaat_id, ilova_turi, fayl_yoli)
    return jsonify({'ok': True})


@bp.route('/api/bh/ilova/<int:ilova_id>', methods=['DELETE'])
def bh_ilova_ochirish_endpoint(ilova_id):
    db.bh_ilova_ochirish(ilova_id)
    return jsonify({'ok': True})


@bp.route('/api/bh/excel', methods=['GET'])
def bh_excel():
    """Biznes-hamroh ro'yxatini Excel qilib chiqaradi."""
    import tempfile
    from flask import send_file
    import pandas as pd
    resp = bh_royxat()
    rows = resp.get_json()['royxat']
    if not rows:
        return jsonify({'xato': "Hozircha ro'yxat bo'sh"}), 400
    df = pd.DataFrame([{
        'Anketa raqami': r['anketa_raqami'], 'PINFL/STIR': r['pinfl_stir'],
        'Mijoz nomi': r['mijoz_nomi'], 'Turi': r['turi'],
        'Davo summasi': r['davo_summasi'], 'Davo ariza sanasi': r['davo_ariza_sana'],
        'Portal holati': r['holat_nomi'], 'Murojaat raqami': r['murojaat_raqami'],
        'Yuborilgan sana': r['yuborilgan_sana'], 'Ijro muddati': r['ijro_muddati'],
        'Ilovalar soni': r['ilovalar_soni'], 'Izoh': r['natija_izoh'],
    } for r in rows])
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='biznes_hamroh_royxati.xlsx')


# ══ SUG'URTADAN UNDIRISH ═══════════════════════════════════════════════
# Bo'limning asosiy mantig'i: MIB (Majburiy ijro byurosi) CHIQARGAN
# hujjat — masalan "undirib bo'lmaganligi to'g'risidagi dalolatnoma" yoki
# "ijro hujjatini qaytarish to'g'risidagi qaror" — sug'urta kompaniyasidan
# qarzni undirish uchun ASOS bo'ladi. Jarayon 3 bosqich:
#     Ariza yuborildi  →  To'landi  |  Rad etildi
