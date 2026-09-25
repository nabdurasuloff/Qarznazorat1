# -*- coding: utf-8 -*-
"""MIB IJRO HARAKATLARI — o'tkazish, harakatlar jurnali, to'lovlar, avtomashinalar.

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
    bugungi_papka, row_list, yigma_jild_javobi, AMAL_TURLARI_MAP,
)

bp = Blueprint('mib', __name__)


@bp.route('/api/mib/tayyor_jild', methods=['GET'])
def mib_tayyor_jild_endpoint():
    """MIB yig'ma jildidagi barcha hujjatlarni (Titul -> Ijro varaqasi ->
    Xat -> Davo ariza -> Sud buyrug'i -> Yakunlash asosi, qaysi biri
    mavjud bo'lsa) yagona PDF qilib birlashtiradi."""
    anketa = request.args.get('anketa', '')
    conn = db.get_conn()
    row = conn.execute('SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1', (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Xat topilmadi'}), 404
    xat = dict(row)
    fayllar = []
    for maydon in ['yigma_jild_titul_fayl', 'ijro_varaqasi_fayl', 'fayl_yoli',
                   'davo_ariza_fayl_yoli', 'sud_buyrugi_fayl', 'sud_qaror_fayl',
                   'mib_yakunlash_hujjati_fayl']:
        if xat.get(maydon) and os.path.exists(xat[maydon]):
            fayllar.append(xat[maydon])
    mijoz_fayl_nomi = letters.safe_filename(xat.get('mijoz_nomi', ''))
    output_path = os.path.join(mib_hujjatlar_papkasi(), f"{mijoz_fayl_nomi}_MIB_jildi_{letters.safe_filename(anketa)}.pdf")
    return yigma_jild_javobi(fayllar, output_path, f"{mijoz_fayl_nomi}_MIB_jildi_{anketa}.pdf")


@bp.route('/api/mib/otkazish_kerak', methods=['GET'])
def mib_otkazish_kerak():
    xatlar = db.get_mib_otkazish_kerak()
    natija = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
        asosiy = x.get('davo_summasi_asosiy') or 0
        foiz = x.get('davo_summasi_foiz') or 0
        jarima = x.get('davo_summasi_jarima') or 0
        natija.append({
            'xat_id': x['id'], 'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'], 'turi': turi,
            'jami': asosiy + foiz + jarima, 'sud_ish_raqami': x.get('sud_ish_raqami', ''),
            'sudga_topshirilgan': x.get('sud_topshirilgan_sana', ''),
            'sud_buyrugi_mavjud': bool(x.get('sud_qaror_fayl') or x.get('sud_buyrugi_fayl')),
        })
    return jsonify({'royxat': natija})


@bp.route('/api/mib/otkazish_kerak_excel', methods=['GET'])
def mib_otkazish_kerak_excel():
    import tempfile
    from flask import send_file
    import pandas as pd
    xatlar = db.get_mib_otkazish_kerak()
    if not xatlar:
        return jsonify({'xato': "Hozircha MIBga o'tkazish kerak bo'lgan ish yo'q"}), 400
    rows = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
        asosiy = x.get('davo_summasi_asosiy') or 0
        foiz = x.get('davo_summasi_foiz') or 0
        jarima = x.get('davo_summasi_jarima') or 0
        rows.append({
            'Anketa raqami': x['anketa_raqami'], 'Mijoz': x['mijoz_nomi'], 'Turi': turi,
            "Qarzdorlik (so'm)": asosiy + foiz + jarima,
            'Sud ish raqami': x.get('sud_ish_raqami', '') or '',
            'Sudga topshirilgan sana': x.get('sud_topshirilgan_sana', '') or '',
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='mibga_otkazish_kerak.xlsx')


@bp.route('/api/mib/otkazildi', methods=['POST'])
def mib_otkazildi():
    anketa = request.form.get('anketa_raqami')
    ish_raqami = request.form.get('ish_raqami', '')
    sana = request.form.get('sana', '')
    # MUHIM (soddalashtirilgan oqim): "Qaror kutilayotganlar" alohida
    # bosqich sifatida OLIB TASHLANDI — sud qarori natijasi endi shu
    # MIBga o'tkazish oynasining o'zida so'raladi (agar hali qayd
    # etilmagan bo'lsa).
    natija = request.form.get('natija', '')  # 'bank_foydasiga' | 'qisman' | 'rad_etildi'
    sana, sana_xato = util.sana_tekshir(sana, "MIBga o'tkazilgan sana", kelajak_mumkinmi=False)
    if sana_xato:
        return jsonify({'xato': sana_xato}), 400
    qaror_sana, sana_xato = util.sana_tekshir(
        request.form.get('qaror_sana', '') or sana, 'Sud qarori sanasi', kelajak_mumkinmi=False)
    if sana_xato:
        return jsonify({'xato': sana_xato}), 400

    conn = db.get_conn()
    row = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami=? AND sud_holati='topshirildi' ORDER BY id DESC LIMIT 1", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Mos xat topilmadi'}), 404
    xat = dict(row)
    prow = db.get_portfel_by_id(xat['portfel_id'])
    mijoz_nomi_fayl = letters.safe_filename(xat['mijoz_nomi'])

    qaror_f = request.files.get('qaror_fayl') or request.files.get('sud_buyrugi')

    # 1-QADAM: agar sud qarori HALI qayd etilmagan bo'lsa, shu yerda
    # qayd qilamiz (natija + PDF hujjat).
    if not xat.get('sud_qaror_natija'):
        if not natija:
            return jsonify({'xato': "Sud qarori natijasini tanlang (Bank foydasiga / Qisman / Rad etildi)"}), 400
        if not qaror_f or not qaror_f.filename:
            return jsonify({'xato': "Sud qarori (PDF) yuklash majburiy"}), 400
        qaror_out_dir = bugungi_papka('Sud qaror')
        qaror_fayl_yoli = os.path.join(qaror_out_dir, f"{mijoz_nomi_fayl}_{anketa}_Sud_qarori_" + letters.safe_filename(qaror_f.filename))
        xato_natija = mustahkam_fayl_saqlash(qaror_f, qaror_fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
        if xato_natija:
            return jsonify({'xato': xato_natija[0]}), xato_natija[1]
        qisman_kwargs = {}
        if natija == 'qisman':
            qisman_kwargs = {
                'qisman_asosiy': request.form.get('qisman_asosiy_farq') or 0,
                'qisman_foiz': request.form.get('qisman_foiz_farq') or 0,
                'qisman_penya': request.form.get('qisman_penya_farq') or 0,
                'davlat_boji_sherik': request.form.get('davlat_boji_sherik') == 'true',
            }
        if natija == 'rad_etildi':
            qisman_kwargs = {'rad_sababi': request.form.get('rad_sababi', '')}
        db.sud_qaror_saqlash(xat['id'], natija, qaror_fayl_yoli, qaror_sana, **qisman_kwargs)
        xat['sud_qaror_natija'] = natija
        xat['sud_qaror_fayl'] = qaror_fayl_yoli

    # Agar natija "Rad etildi" bo'lsa — MIBga UMUMAN o'tkazilmaydi, shu
    # yerda to'xtaymiz (qaror allaqachon yuqorida saqlandi).
    if xat.get('sud_qaror_natija') == 'rad_etildi':
        return jsonify({'ok': True, 'rad_etildi': True})

    # 2-QADAM: MIBga o'tkazish uchun Ijro varaqasi MAJBURIY.
    if not ish_raqami or not sana:
        return jsonify({'xato': 'ish_raqami va sana kerak'}), 400
    ijro_f = request.files.get('ijro_varaqasi')
    if not ijro_f or not ijro_f.filename:
        return jsonify({'xato': "Ijro varaqasi (PDF) yuklash majburiy"}), 400

    jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0) if prow else \
        (xat.get('davo_summasi_asosiy') or 0) + (xat.get('davo_summasi_foiz') or 0) + (xat.get('davo_summasi_jarima') or 0)

    out_dir = bugungi_papka('Ijro varaqalari')
    ijro_fayl_yoli = os.path.join(out_dir, f"{mijoz_nomi_fayl}_{anketa}_Ijro_varaqasi_" + letters.safe_filename(ijro_f.filename))
    # MUHIM: yuklash natijasi TEKSHIRILADI — aks holda bo'sh/buzuq fayl
    # yuklansa ham, tizim "Ijro varaqasi yuklandi" deb yozib qo'yardi va
    # jild MIBga ijro varaqasisiz ketardi.
    xato_natija = mustahkam_fayl_saqlash(ijro_f, ijro_fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]

    sud_fayl_yoli = xat.get('sud_qaror_fayl') or xat.get('sud_buyrugi_fayl')

    db.mark_mib_otkazildi(xat['id'], ish_raqami, sana, ijro_fayl_yoli, mib_ijro_summasi=jami,
                           sud_buyrugi_fayl=sud_fayl_yoli)

    # Yig'ma jild (ish dossiyesi) papkasini ochib, titul (muqova) hujjatini
    # yaratamiz, so'ng shu ishga tegishli AVVAL yaratilgan barcha hujjatlarni
    # (xat, Davo ariza, Sud buyrug'i, Ijro varaqasi) avtomatik jildga
    # nusxalaymiz — foydalanuvchi qo'lda hech narsa qo'shmasa ham, jild
    # to'liq bo'ladi.
    try:
        mijoz_turi_calc, mijoz = util.resolve_mijoz(prow) if prow else (None, None)
        settings = db.get_all_settings()
        xat_yangilangan = db.get_xat_by_id(xat['id'])

        # MUHIM (yangi tuzilma): Huquqiy choralar/MIB hujjatlari/[MIBga
        # o'tkazilgan sana]/[mijoz nomi]/ papkasida saqlanadi.
        jild_papka = mib_hujjatlari_mijoz_papkasi(xat['mijoz_nomi'], datetime.datetime.now(), anketa)
        titul_path = os.path.join(jild_papka, '00_Titul.docx')
        letters.generate_yigma_jild_titul(titul_path, xat_yangilangan, prow, mijoz, settings)
        db.mark_yigma_jild_yaratildi(xat['id'], jild_papka, titul_path)

        xat_toliq = db.get_xat_by_id(xat['id'])
        db.yigma_jild_toldirish(jild_papka, xat_toliq)
    except Exception as e:
        return jsonify({'ok': True, 'ogohlantirish': f"MIBga o'tkazildi, lekin yig'ma jild yaratishda xato: {e}"})

    # MUHIM: agar shu anketa uchun "kutilmoqda" holatidagi pochta xarajati
    # bo'lsa — MIBga o'tkazilishi bilanoq, xarajat summasiga teng YANGI
    # ijro ishi TIZIM TOMONIDAN O'ZI avtomatik ochiladi (qo'lda
    # "MIB ish ochish" bosish shart emas).
    try:
        conn = db.get_conn()
        kutilayotgan_xarajatlar = conn.execute(
            "SELECT id FROM sud_xarajatlar WHERE anketa_raqami=? AND holati='kutilmoqda'", (anketa,)).fetchall()
        conn.close()
        for x in kutilayotgan_xarajatlar:
            xarajat_ish_raqami = f"{ish_raqami}-XARAJAT"
            db.sud_xarajat_mib_ish_ochish(x['id'], xarajat_ish_raqami)
    except Exception:
        pass

    return jsonify({'ok': True})


@bp.route('/api/mib/faol', methods=['GET'])
def mib_faol():
    xatlar = db.get_mib_faol_royxat()
    settings = db.get_all_settings()
    natija = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
        jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0) if prow else 0
        amallar = db.get_mib_amallar(x['id'])
        songgi = amallar[-1] if amallar else None
        mib_summasi = x.get('mib_ijro_summasi') or jami
        farq = jami - mib_summasi
        nazorat_natija = None
        if prow:
            try:
                nazorat_natija = db.get_mib_monitoring_holati(x['id'], prow, xat=x, settings=settings)
            except Exception:
                nazorat_natija = None
        nazorat = nazorat_natija.get('holat') if nazorat_natija else None
        nazorat_matn = nazorat_natija.get('xabar', '—') if nazorat_natija and nazorat_natija.get('holat') else '—'
        tolangan_summa, _ = db.tolovlar_jami_va_royxat(x['anketa_raqami'])
        natija.append({
            'xat_id': x['id'], 'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'], 'turi': turi,
            'qarzdorlik': jami, 'mib_ish_raqami': x.get('mib_ish_raqami', ''),
            'songgi_harakat': AMAL_TURLARI_MAP.get(songgi['amal_turi'], songgi['amal_turi']) if songgi else '—',
            'songgi_harakat_sana': songgi['amal_sanasi'] if songgi else '',
            'harakatlar_soni': len(amallar), 'farq': farq, 'nazorat': nazorat, 'nazorat_matn': nazorat_matn,
            'yigma_jild_titul_fayl': x.get('yigma_jild_titul_fayl', ''),
            'yigma_jild_papka': x.get('yigma_jild_papka', ''),
            'yigma_jild_bor': x.get('yigma_jild_holati') == 'mavjud',
            'tolangan_summa': tolangan_summa,
        })
    return jsonify({'royxat': natija})


@bp.route('/api/mib/amal_qoshish', methods=['POST'])
def mib_amal_qoshish():
    """Yangi MIB harakatini qo'shadi. MUHIM: har bir harakat, uni
    tasdiqlovchi PDF hujjat bilan birga bo'lishi SHART — bu hujjat, avval
    o'zi (harakat sanasi bilan) saqlanadi, so'ng shu ishning Sud/MIB
    yig'ma jildiga ham AVTOMATIK qo'shib qo'yiladi."""
    anketa = request.form.get('anketa_raqami')
    amal_turi = request.form.get('amal_turi', '')
    amal_sanasi, sana_xato = util.sana_tekshir(
        request.form.get('amal_sanasi', ''), 'Harakat sanasi', kelajak_mumkinmi=False)
    if sana_xato:
        return jsonify({'xato': sana_xato}), 400
    tavsif = request.form.get('tavsif', '')
    undirilgan_summa = request.form.get('undirilgan_summa') or None
    f = request.files.get('tasdiqlovchi_hujjat')
    if not f or not f.filename:
        return jsonify({'xato': "Har bir harakat uchun tasdiqlovchi hujjat (PDF) yuklash SHART"}), 400

    conn = db.get_conn()
    row = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami=? AND mib_holati='otkazildi' ORDER BY id DESC LIMIT 1", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Mos MIB ishi topilmadi'}), 404
    xat = dict(row)

    out_dir = bugungi_papka('MIB harakat hujjatlari')
    fayl_nomi = f"{letters.safe_filename(xat['mijoz_nomi'])}_{anketa}_{letters.safe_filename(amal_turi)}_{letters.safe_filename(f.filename)}"
    fayl_yoli = os.path.join(out_dir, fayl_nomi)
    xato_natija = mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]

    db.add_mib_amal(xat['id'], amal_turi, amal_sanasi, tavsif,
                     undirilgan_summa=undirilgan_summa, dalolatnoma_fayl=fayl_yoli)

    # MUHIM: shu harakat hujjatini, ishning MIB yig'ma jild papkasiga
    # (agar allaqachon yaratilgan bo'lsa) ham nusxalab qo'yamiz — shunda
    # yig'ma jildning o'zida ham barcha harakatlar hujjati ko'rinadi.
    if xat.get('yigma_jild_papka') and os.path.isdir(xat['yigma_jild_papka']):
        try:
            import shutil
            nusxa_nomi = f"Harakat_{letters.safe_filename(amal_turi)}_{amal_sanasi.replace('.', '')}_{letters.safe_filename(f.filename)}"
            shutil.copy2(fayl_yoli, os.path.join(xat['yigma_jild_papka'], nusxa_nomi))
        except Exception:
            pass

    return jsonify({'ok': True})


@bp.route('/api/mib/harakat_turlari', methods=['GET'])
def mib_harakat_turlari_endpoint():
    return jsonify({'turlar': db.mib_harakat_turlari_royxati()})


@bp.route('/api/mib/harakat_turlari', methods=['POST'])
def mib_harakat_turi_qoshish_endpoint():
    data = request.get_json() or {}
    nomi = data.get('nomi', '').strip()
    if not nomi:
        return jsonify({'xato': "Harakat nomi kerak"}), 400
    db.mib_harakat_turi_qoshish(nomi)
    return jsonify({'ok': True})


@bp.route('/api/mib/harakat_turlari/<int:turi_id>', methods=['DELETE'])
def mib_harakat_turi_ochirish_endpoint(turi_id):
    db.mib_harakat_turi_ochirish(turi_id)
    return jsonify({'ok': True})


@bp.route('/api/mib/amallar_tarixi', methods=['GET'])
def mib_amallar_tarixi():
    anketa = request.args.get('anketa', '').strip()
    conn = db.get_conn()
    row = conn.execute("SELECT id FROM xatlar WHERE anketa_raqami=? AND mib_holati='otkazildi'", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'amallar': []})
    amallar = db.get_mib_amallar(row['id'])
    return jsonify({'amallar': amallar})


@bp.route('/api/mib/qidirish', methods=['GET'])
def mib_qidirish():
    anketa = request.args.get('anketa', '').strip()
    conn = db.get_conn()
    row = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami=? AND mib_holati='otkazildi'", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'topildi': False})
    x = dict(row)
    prow = db.get_portfel_by_id(x['portfel_id'])
    turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
    jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0) if prow else 0
    amallar = db.get_mib_amallar(x['id'])
    songgi = amallar[-1] if amallar else None
    return jsonify({'topildi': True, 'row': {
        'xat_id': x['id'], 'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'], 'turi': turi,
        'qarzdorlik': jami, 'mib_ish_raqami': x.get('mib_ish_raqami', ''),
        'songgi_harakat': songgi['amal_turi'] if songgi else '—',
        'songgi_harakat_sana': songgi['amal_sanasi'] if songgi else '',
        'harakatlar_soni': len(amallar),
        'yigma_jild_titul_fayl': x.get('yigma_jild_titul_fayl', ''),
        'yigma_jild_papka': x.get('yigma_jild_papka', ''),
        'yigma_jild_bor': x.get('yigma_jild_holati') == 'mavjud',
    }})


@bp.route('/api/mib/jild_fayllari', methods=['GET'])
def mib_jild_fayllari():
    anketa = request.args.get('anketa', '').strip()
    conn = db.get_conn()
    row = conn.execute("SELECT yigma_jild_papka FROM xatlar WHERE anketa_raqami=?", (anketa,)).fetchone()
    conn.close()
    papka = row['yigma_jild_papka'] if row else None
    if not papka or not os.path.isdir(papka):
        return jsonify({'fayllar': [], 'papka': papka or ''})
    fayllar = []
    for f in sorted(os.listdir(papka)):
        toliq = os.path.join(papka, f)
        if os.path.isfile(toliq):
            fayllar.append({'nomi': f, 'yoli': toliq})
    return jsonify({'fayllar': fayllar, 'papka': papka})


@bp.route('/api/mib/jarayondagilar_excel', methods=['GET'])
def mib_jarayondagilar_excel():
    import tempfile
    from flask import send_file
    import pandas as pd
    royxat = db.get_mib_faol_royxat_toliq()
    if not royxat:
        return jsonify({'xato': "MIBda jarayondagi hujjatlar yo'q"}), 400
    rows = []
    for item in royxat:
        xat = item['xat']
        amal = item['amal']
        amal_turi_nomi = AMAL_TURLARI_MAP.get(amal['amal_turi'], amal['amal_turi']) if amal else ''
        oylik = amal.get('undirilgan_summa', '') if amal and amal['amal_turi'] == 'oylik_ish_haqqi' else ''
        rows.append({
            'Anketa raqami': xat['anketa_raqami'], 'PINFL/STIR': item.get('pinfl') or item.get('stir', ''),
            "F.I.Sh / Nomi": xat['mijoz_nomi'], 'Turi': xat['mijoz_turi'],
            "Qarzdorlik (so'm)": item['jami_qarz'], 'MIB ish raqami': xat.get('mib_ish_raqami', ''),
            "MIBga o'tkazilgan sana": xat.get('mib_otkazilgan_sana', ''), 'Harakat turi': amal_turi_nomi,
            'Harakat sanasi': amal.get('amal_sanasi', '') if amal else '', 'Tavsif': amal.get('tavsif', '') if amal else '',
            "Oylik ish haqqidan undirilgan summa": oylik,
            "Undirilgan summa (umumiy)": amal.get('undirilgan_summa', '') if amal else '',
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='mib_jarayondagi_hujjatlar.xlsx')


@bp.route('/api/mib/eski_ish_qidirish', methods=['GET'])
def mib_eski_ish_qidirish():
    anketa = request.args.get('anketa', '').strip()
    rows = db.get_portfel_by_anketa(anketa)
    if not rows:
        return jsonify({'topildi': False})
    prow = rows[0]
    turi, mijoz = util.resolve_mijoz(prow)
    jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
    return jsonify({'topildi': True, 'mijoz_nomi': prow.get('mijoz_nomi', ''), 'turi': turi, 'jami_qarz': jami})


@bp.route('/api/mib/eski_ish_kiritish', methods=['POST'])
def mib_eski_ish_kiritish():
    anketa = request.form.get('anketa_raqami', '').strip()
    ish_raqami = request.form.get('ish_raqami', '').strip()
    sana = request.form.get('sana', '').strip()
    sana, sana_xato = util.sana_tekshir(sana, "MIBga o'tkazilgan sana", kelajak_mumkinmi=False)
    if sana_xato:
        return jsonify({'xato': sana_xato}), 400
    sud_ish_raqami = request.form.get('sud_ish_raqami', '').strip()
    qarzdorlik_qiymat = request.form.get('qarzdorlik', '')
    if not anketa or not ish_raqami or not sana:
        return jsonify({'xato': 'anketa_raqami, ish_raqami va sana kerak'}), 400

    ijro_f = request.files.get('ijro_varaqasi')
    if not ijro_f or not ijro_f.filename:
        return jsonify({'xato': "Ijro varaqasi (PDF) yuklash majburiy"}), 400

    rows = db.get_portfel_by_anketa(anketa)
    if not rows:
        return jsonify({'xato': 'Bu anketa portfelda topilmadi'}), 404
    prow = rows[0]
    turi, mijoz = util.resolve_mijoz(prow)
    jami = float(qarzdorlik_qiymat or 0) or (
        (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0))

    # MUHIM: hujjatlar, asl dasturdagi kabi, BUGUNGI SANA papkasi ichida
    # (masalan "09.09.2026/MIB/...") saqlanadi — to'g'ridan-to'g'ri asosiy
    # papkaga emas.
    out_dir = bugungi_papka('Ijro varaqalari')
    ijro_fayl_yoli = os.path.join(out_dir, f"{letters.safe_filename(prow.get('mijoz_nomi', ''))}_{letters.safe_filename(anketa)}_Ijro_varaqasi_{letters.safe_filename(ijro_f.filename)}")
    xato_natija = mustahkam_fayl_saqlash(ijro_f, ijro_fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]

    conn = db.get_conn()
    mavjud = conn.execute("SELECT id FROM xatlar WHERE anketa_raqami=?", (anketa,)).fetchone()
    if mavjud:
        xat_id = mavjud['id']
        conn.execute("UPDATE xatlar SET mib_holati='otkazildi', mib_ish_raqami=?, mib_otkazilgan_sana=?, "
                     "sud_ish_raqami=COALESCE(sud_ish_raqami, ?), sud_holati='topshirildi', "
                     "mib_ijro_summasi=?, ijro_varaqasi_fayl=? WHERE id=?",
                     (ish_raqami, sana, sud_ish_raqami, jami, ijro_fayl_yoli, xat_id))
    else:
        conn.execute(
            "INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi, holat, "
            "sud_holati, sud_ish_raqami, mib_holati, mib_ish_raqami, mib_otkazilgan_sana, "
            "mib_ijro_summasi, ijro_varaqasi_fayl) "
            "VALUES (?, ?, ?, ?, 'yuborildi', 'topshirildi', ?, 'otkazildi', ?, ?, ?, ?)",
            (prow['id'], anketa, prow.get('mijoz_nomi', ''), turi, sud_ish_raqami,
             ish_raqami, sana, jami, ijro_fayl_yoli))
        xat_id = conn.execute("SELECT id FROM xatlar WHERE anketa_raqami=?", (anketa,)).fetchone()['id']
    conn.commit()
    conn.close()
    db.add_mib_amal(xat_id, 'eski_ish_kiritildi', sana, "Eski ish sifatida bazaga kiritildi")

    # Yig'ma jild (ish dossiyesi) — yangi ishlar MIBga o'tkazilganda qanday
    # avtomatik yaratilsa, eski ish kiritilganda ham xuddi shunday
    # yaratiladi: muqova (titul) hujjati + mavjud barcha hujjatlar
    # (agar bo'lsa) avtomatik jildga yig'iladi.
    try:
        settings = db.get_all_settings()
        xat_toliq = db.get_xat_by_id(xat_id)
        jild_papka = mib_hujjatlari_mijoz_papkasi(prow.get('mijoz_nomi', ''), datetime.datetime.now(), anketa)
        titul_path = os.path.join(jild_papka, '00_Titul.docx')
        letters.generate_yigma_jild_titul(titul_path, xat_toliq, prow, mijoz, settings)
        db.mark_yigma_jild_yaratildi(xat_id, jild_papka, titul_path)
        xat_yangilangan = db.get_xat_by_id(xat_id)
        db.yigma_jild_toldirish(jild_papka, xat_yangilangan)
    except Exception as e:
        return jsonify({'ok': True, 'ogohlantirish': f"Ish kiritildi, lekin yig'ma jild yaratishda xato: {e}"})

    return jsonify({'ok': True})


@bp.route('/api/mib/avtomashinalar', methods=['GET'])
def mib_avtomashinalar():
    anketa = request.args.get('anketa', '').strip()
    conn = db.get_conn()
    row = conn.execute("SELECT id FROM xatlar WHERE anketa_raqami=?", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'mashinalar': []})
    return jsonify({'mashinalar': db.get_avtomashinalar(row['id'])})


@bp.route('/api/mib/avtomashina_qoshish', methods=['POST'])
def mib_avtomashina_qoshish():
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami', '').strip()
    conn = db.get_conn()
    row = conn.execute("SELECT id FROM xatlar WHERE anketa_raqami=?", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Mos MIB ishi topilmadi'}), 404
    db.add_avtomashina(row['id'], data.get('rusumi', ''), data.get('davlat_raqami', ''), data.get('pinfl', ''))
    return jsonify({'ok': True})


@bp.route('/api/mib/avtomashina_holati', methods=['POST'])
def mib_avtomashina_holati():
    mashina_id = request.form.get('id')
    holati = request.form.get('holati')
    modda = request.form.get('modda', '')
    if not mashina_id or not holati:
        return jsonify({'xato': 'id va holati kerak'}), 400
    fayl_yoli = None
    f = request.files.get('hujjat')
    if f and f.filename:
        out_dir = bugungi_papka('Avtomashina_hujjatlar')
        os.makedirs(out_dir, exist_ok=True)
        fayl_yoli = os.path.join(out_dir, f"{mashina_id}_{letters.safe_filename(f.filename)}")
        xato_natija = mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
        if xato_natija:
            return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    db.update_avtomashina_holati(mashina_id, holati, asoslovchi_hujjat_fayl=fayl_yoli, modda=modda or None)
    return jsonify({'ok': True})


@bp.route('/api/mib/avtomashinalar_import', methods=['POST'])
def mib_avtomashinalar_import():
    import tempfile
    f = request.files.get('file')
    if not f:
        return jsonify({'xato': 'Fayl yuborilmadi'}), 400
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:

        tmp_path = tmp.name

    xato_natija = mustahkam_fayl_saqlash(f, tmp_path)

    if xato_natija:

        return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    try:
        natija = importer.import_avtomashinalar_excel(tmp_path)
        return jsonify(natija)
    except Exception as e:
        return jsonify({'xato': str(e)}), 400
    finally:
        os.remove(tmp_path)


@bp.route('/api/mib/avtomashinalar_xatlanmagan_excel', methods=['GET'])
def mib_avtomashinalar_xatlanmagan_excel():
    import tempfile
    from flask import send_file
    import pandas as pd
    xatlanmagan = db.get_xatlanmagan_avtomashinalar()
    if not xatlanmagan:
        return jsonify({'xato': "Xatlanmagan avtomashinalar yo'q"}), 400
    rows = [{'Mashina rusumi': m['mashina_rusumi'], 'Davlat raqami': m['davlat_raqami'],
             'Mijoz PINFL': m.get('mijoz_pinfl', ''), 'Anketa raqami': m['anketa_raqami'],
             'Mijoz nomi': m['mijoz_nomi']} for m in xatlanmagan]
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='xatlanmagan_avtomashinalar.xlsx')


@bp.route('/api/mib/yakunlash', methods=['POST'])
def mib_yakunlash():
    anketa = request.form.get('anketa_raqami')
    sabab = request.form.get('sabab', '')
    sana = request.form.get('sana', '')
    sana, sana_xato = util.sana_tekshir(sana, 'Yakunlangan sana', kelajak_mumkinmi=False)
    if sana_xato:
        return jsonify({'xato': sana_xato}), 400
    if not anketa or not sabab:
        return jsonify({'xato': 'anketa_raqami va sabab kerak'}), 400
    f = request.files.get('asos_hujjat')
    if not f or not f.filename:
        return jsonify({'xato': "Yakunlash asosi hujjatini (PDF) yuklang — bu majburiy."}), 400
    conn = db.get_conn()
    row = conn.execute("SELECT id, mijoz_nomi FROM xatlar WHERE anketa_raqami=? AND mib_holati='otkazildi'", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Mos MIB ishi topilmadi'}), 404
    out_dir = os.path.join(mib_hujjatlar_papkasi(), letters.safe_filename(anketa))
    os.makedirs(out_dir, exist_ok=True)
    fayl_yoli = os.path.join(out_dir, f"{letters.safe_filename(row['mijoz_nomi'])}_{anketa}_Yakunlash_asosi_" + letters.safe_filename(f.filename))
    xato_natija = mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    db.mark_mib_yakunlandi(row['id'], sabab, sana or None)
    db.set_mib_yakunlash_hujjati(row['id'], fayl_yoli)

    # Yakunlash asosi hujjati ham yig'ma jildga avtomatik qo'shiladi.
    try:
        xat = db.get_xat_by_id(row['id'])
        if xat and xat.get('yigma_jild_papka'):
            db.yigma_jild_toldirish(xat['yigma_jild_papka'], xat)
    except Exception:
        pass

    return jsonify({'ok': True})


@bp.route('/api/mib/yakunlangan', methods=['GET'])
def mib_yakunlangan():
    xatlar = db.get_mib_yakunlangan_royxati()
    natija = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
        natija.append({
            'xat_id': x['id'], 'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'], 'turi': turi,
            'mib_ish_raqami': x.get('mib_ish_raqami', ''), 'yakunlangan_sana': x.get('mib_yakunlangan_sana', ''),
            'sabab': x.get('mib_yakunlash_sababi', ''),
        })
    return jsonify({'royxat': natija})


@bp.route('/api/mib/yakunlangan_excel', methods=['GET'])
def mib_yakunlangan_excel():
    """MIB'da yakunlangan (to'xtatilgan) barcha ishlarni Excel qilib
    chiqaradi: Anketa raqami, PINFL/STIR, Mijoz nomi, Turi, MIB ish
    raqami, Yakunlangan sana, Sabab."""
    import tempfile
    from flask import send_file
    import pandas as pd
    xatlar = db.get_mib_yakunlangan_royxati()
    if not xatlar:
        return jsonify({'xato': "Hozircha yakunlangan MIB ishi yo'q"}), 400
    rows = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
        pinfl_stir = (prow.get('pinfl') or prow.get('stir') or '') if prow else ''
        rows.append({
            'Anketa raqami': x['anketa_raqami'], 'PINFL/STIR': pinfl_stir, 'Mijoz nomi': x['mijoz_nomi'],
            'Turi': turi, 'MIB ish raqami': x.get('mib_ish_raqami', '') or '',
            'Yakunlangan sana': x.get('mib_yakunlangan_sana', '') or '',
            'Yakunlash sababi': x.get('mib_yakunlash_sababi', '') or '',
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='mib_yakunlangan_ishlar.xlsx')


@bp.route('/api/mib/qayta_ochish', methods=['POST'])
def mib_qayta_ochish():
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami')
    conn = db.get_conn()
    row = conn.execute("SELECT id FROM xatlar WHERE anketa_raqami=? AND mib_yakunlangan=1", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Topilmadi'}), 404
    db.mib_ishni_qayta_ochish(row['id'])
    return jsonify({'ok': True})


@bp.route('/api/mib/jarayonni_nollashtirish', methods=['POST'])
def mib_jarayonni_nollashtirish():
    """MUHIM, QAYTARILMAYDIGAN AMAL: anketaning butun xat/Davo ariza/Sud/MIB
    jarayoni tarixini o'chirib, uni "hech qanday harakat qilinmagan"
    holatiga qaytaradi. Faqat MIB yakunlangan (mib_yakunlangan=1) ishlar
    uchun ishlatilishi mumkin — tasodifan faol ishni o'chirib
    yubormaslik uchun."""
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami')
    tasdiq = data.get('tasdiqlayman')
    if not anketa:
        return jsonify({'xato': 'anketa_raqami kerak'}), 400
    if not tasdiq:
        return jsonify({'xato': "Bu amalni tasdiqlash kerak"}), 400
    conn = db.get_conn()
    row = conn.execute(
        "SELECT id FROM xatlar WHERE anketa_raqami=? AND (mib_yakunlangan=1 OR "
        "(sud_kiritilmadi_sababi IS NOT NULL AND sud_kiritilmadi_sababi != '') OR "
        "sud_qaror_natija='rad_etildi')",
        (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': "Bu anketa uchun yakunlangan MIB ishi, 'Sudga kiritilmadi' yoki "
                                 "sud tomonidan 'Rad etilgan' ish topilmadi. Nollashtirish faqat "
                                 "shunday holatlar uchun mumkin."}), 404
    db.anketa_jarayonini_nollashtirish(anketa)
    return jsonify({'ok': True})


@bp.route('/api/mib/harakatsizlar', methods=['GET'])
def mib_harakatsizlar():
    xatlar = db.get_mib_harakatsizlar()
    natija = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0) if prow else 0
        natija.append({
            'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'], 'turi': x['mijoz_turi'],
            'jami_qarz': jami, 'mib_ish_raqami': x.get('mib_ish_raqami', ''),
            'harakatsizlik_kun': x.get('harakatsizlik_kun', ''),
        })
    return jsonify({'royxat': natija})


def mib_tolov_asosida_avtomatik_yakunlashni_tekshirish(anketa_raqami):
    """Har safar bir to'lov biror anketaga 'tasdiqlangan' deb biriktirilganda
    chaqiriladi. Agar shu anketaning MIB ishi FAOL (otkazilgan, hali
    yakunlanmagan) bo'lsa va unga tasdiqlangan to'lovlar yig'indisi Davo
    (ijro) summasiga YETGAN yoki OSHGAN bo'lsa — MIB ishini AVTOMATIK
    yakunlaydi, asos sifatida to'lovlar ro'yxatini o'z ichiga olgan
    hujjatni (imkon bo'lsa PDF, aks holda Word) yaratib, yig'ma jildga
    qo'shadi."""
    conn = db.get_conn()
    xat_row = conn.execute(
        "SELECT * FROM xatlar WHERE anketa_raqami=? AND mib_holati='otkazildi' AND (mib_yakunlangan IS NULL OR mib_yakunlangan=0)",
        (anketa_raqami,)).fetchone()
    conn.close()
    if not xat_row:
        return False
    xat = dict(xat_row)

    davo_qarz = (xat.get('mib_ijro_summasi') or 0)
    if not davo_qarz:
        prow = db.get_portfel_by_id(xat['portfel_id'])
        davo_qarz = (prow.get('asosiy_qarz', 0) or 0) + (prow.get('foiz_qarz', 0) or 0) + \
            (prow.get('jarima', 0) or 0) if prow else 0
    if not davo_qarz or davo_qarz <= 0:
        return False

    jami_tolangan, tolovlar_royxati = db.tolovlar_jami_va_royxat(anketa_raqami)
    if jami_tolangan < davo_qarz:
        return False  # Hali yetarli emas — hech narsa qilmaymiz

    # Hujjatni yaratamiz (avval Word, imkon bo'lsa PDF'ga aylantiramiz)
    out_dir = bugungi_papka('MIB_avtomatik_yakunlash')
    docx_path = os.path.join(out_dir, f"yakunlash_{letters.safe_filename(anketa_raqami)}.docx")
    letters.generate_tolov_asosida_yakunlash_hujjati(
        docx_path, xat, xat.get('mijoz_nomi', ''), davo_qarz, tolovlar_royxati, jami_tolangan)

    yakuniy_fayl = docx_path
    try:
        yakuniy_fayl = letters.convert_docx_to_pdf(docx_path, delete_docx=True)
    except Exception:
        pass  # MS Word mavjud bo'lmasa, Word hujjati o'zi ham yetarli

    sabab = ("To'liq to'landi (tizim avtomatik) — to'langan: "
             f"{jami_tolangan:,.0f} so'm").replace(',', ' ')
    db.mark_mib_yakunlandi(xat['id'], sabab, datetime.datetime.now().strftime('%d.%m.%Y'))
    db.set_mib_yakunlash_hujjati(xat['id'], yakuniy_fayl)

    try:
        if xat.get('yigma_jild_papka'):
            xat_yangi = db.get_xat_by_id(xat['id'])
            db.yigma_jild_toldirish(xat['yigma_jild_papka'], xat_yangi)
    except Exception:
        pass

    return True


@bp.route('/api/mib/tolovlar_shablon', methods=['GET'])
def mib_tolovlar_shablon():
    """29801 (kunlik) yoki MIBdan kelgan to'lovlar uchun to'ldirish shablonini
    (bo'sh Excel, ustunlar bilan) beradi."""
    import tempfile
    from flask import send_file
    import pandas as pd
    manba = request.args.get('manba', 'kunlik_29801')
    if manba == 'mib':
        df = pd.DataFrame(columns=[
            'Sana (kun.oy.yil)', "To'lov maqsadi / Naznacheniye (PINFL shu yerda bo'lishi mumkin)",
            "F.I.Sh / Nomi (ixtiyoriy)", "Summa (so'm)",
            "Tranzaksiya raqami (bir xil kun/hisobga bir nechta tolov bolsa, dublikatni aniqlash uchun)"])
        nomi = 'mibdan_kelgan_tolovlar_shabloni.xlsx'
    else:
        df = pd.DataFrame(columns=[
            'Sana (kun.oy.yil)', 'Hisob raqami (yoki PINFL/STIR)',
            "F.I.Sh / Nomi (ixtiyoriy)", "Summa (so'm)",
            "Tranzaksiya raqami (bir xil kun/hisobga bir nechta tolov bolsa, dublikatni aniqlash uchun)"])
        nomi = 'kunlik_29801_tolovlar_shabloni.xlsx'
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name=nomi)


@bp.route('/api/mib/tolovlar_import', methods=['POST'])
def mib_tolovlar_import():
    """Kunlik (29801-hisobvaraq) yoki MIBdan kelgan to'lovlar Excel faylini
    yuklaydi. Har bir qator uchun, ustun nomidan qat'i nazar (hisob raqami,
    PINFL, STIR yoki erkin to'lov maqsadi matni bo'lishi mumkin), tizim
    KO'P BOSQICHLI usul bilan mos anketani aniqlashga harakat qiladi
    (batafsil: database.py -> tolov_qoshish)."""
    import tempfile
    import pandas as pd
    manba = request.form.get('manba', 'kunlik_29801')
    f = request.files.get('file')
    if not f:
        return jsonify({'xato': 'Fayl yuborilmadi'}), 400
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    xato_natija = mustahkam_fayl_saqlash(f, tmp_path)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    try:
        df = pd.read_excel(tmp_path)
    except Exception as e:
        return jsonify({'xato': str(e)}), 400
    finally:
        os.remove(tmp_path)

    sana_col = next((c for c in df.columns if str(c).startswith('Sana')), None)
    # Moslashuvchan: "Hisob raqami", "PINFL", "STIR", yoki "Naznacheniye" —
    # qaysi biri bo'lsa ham, xom matn sifatida qabul qilinadi va
    # tolov_qoshish() ichida ko'p bosqichli aniqlash ishga tushadi.
    xom_col = next((c for c in df.columns if any(
        k in str(c).upper() for k in ['HISOB', 'PINFL', 'STIR', 'NAZNACHENIYE', 'MAQSAD'])), None)
    summa_col = next((c for c in df.columns if 'Summa' in str(c)), None)
    ism_col = next((c for c in df.columns if 'F.I.Sh' in str(c) or 'Nomi' in str(c)), None)
    tranzaksiya_col = next((c for c in df.columns if 'Tranzaksiya' in str(c)), None)
    if not sana_col or not xom_col or not summa_col:
        return jsonify({'xato': (
            "Fayl tuzilmasi tanilmadi — 'Sana', 'Hisob raqami/PINFL/STIR/Naznacheniye' "
            "va 'Summa' ustunlari kerak.")}), 400

    tasdiqlangan, aniqlash_kerak, mos_kelmadi, dublikat, xatolar = 0, 0, 0, 0, []
    for i, row in df.iterrows():
        try:
            xom_qiymat = row[xom_col]
            # MUHIM: Excel/pandas uzun raqamli qiymatlarni ba'zan sonli
            # qiymat (masalan 42701766360013.0) sifatida o'qib, oxiriga
            # ".0" qo'shib qo'yishi yoki oldindagi nollarni yo'qotishi
            # mumkin. Shu sabab, matn ko'rinishini to'g'ri tiklaymiz.
            if isinstance(xom_qiymat, float):
                xom_matn = str(int(xom_qiymat))
            else:
                xom_matn = str(xom_qiymat).strip()
                if xom_matn.endswith('.0'):
                    xom_matn = xom_matn[:-2]
            if not xom_matn or xom_matn.lower() == 'nan':
                continue
            summa = float(row[summa_col])
            sana_qiymat = row[sana_col]
            sana = sana_qiymat.strftime('%d.%m.%Y') if hasattr(sana_qiymat, 'strftime') else str(sana_qiymat)
            ism = str(row[ism_col]).strip() if ism_col and str(row[ism_col]).strip().lower() != 'nan' else None
            tranzaksiya = None
            if tranzaksiya_col:
                tval = row[tranzaksiya_col]
                if isinstance(tval, float) and not (tval != tval):  # NaN tekshiruvi
                    tranzaksiya = str(int(tval)) if tval == int(tval) else str(tval)
                elif tval is not None and str(tval).strip().lower() != 'nan':
                    tranzaksiya = str(tval).strip()
            holati, tasdiqlangan_anketa = db.tolov_qoshish(
                manba, sana, summa, xom_matn, toliq_ism=ism, tranzaksiya_raqami=tranzaksiya)
            if holati == 'tasdiqlangan':
                tasdiqlangan += 1
                try:
                    mib_tolov_asosida_avtomatik_yakunlashni_tekshirish(tasdiqlangan_anketa)
                except Exception:
                    pass
            elif holati == 'aniqlash_kerak':
                aniqlash_kerak += 1
            elif holati == 'dublikat':
                dublikat += 1
            else:
                mos_kelmadi += 1
        except Exception as e:
            xatolar.append(f"{i + 2}-qator: {e}")

    return jsonify({
        'tasdiqlangan': tasdiqlangan, 'aniqlash_kerak': aniqlash_kerak,
        'mos_kelmadi': mos_kelmadi, 'dublikat': dublikat, 'xatolar': xatolar,
    })


@bp.route('/api/mib/tolovlar_royxat', methods=['GET'])
def mib_tolovlar_royxat():
    manba = request.args.get('manba')
    holati = request.args.get('holati')
    royxat = db.get_tolovlar_royxati(manba=manba, holati=holati)
    return jsonify({'royxat': royxat})


@bp.route('/api/mib/anketa_tolovlari', methods=['GET'])
def mib_anketa_tolovlari():
    """Bitta anketaga tegishli (tasdiqlangan) barcha to'lovlarni ko'rsatadi
    — 'Jarayondagi hujjatlar' jadvalidagi 'To'langan summa' ustuniga
    bosilganda tafsilotni ko'rish uchun."""
    anketa = request.args.get('anketa', '').strip()
    jami, royxat = db.tolovlar_jami_va_royxat(anketa)
    return jsonify({'jami': jami, 'royxat': royxat})


@bp.route('/api/mib/tolov_nomzodlar', methods=['GET'])
def mib_tolov_nomzodlar():
    """Bitta to'lov uchun, uning saqlangan identifikatoriga (PINFL/STIR
    YOKI 'unikal' kodi bo'lishi mumkin — manbaga qarab) mos barcha
    anketalarni qaytaradi — foydalanuvchi qaysi birini tanlashini bilish
    uchun. Avval PINFL/STIR bo'yicha, topilmasa 'unikal' bo'yicha ham
    qidiriladi (chunki "29801..." hisob raqamlari asosida aniqlangan
    to'lovlarda identifikator aslida unikal kod bo'ladi)."""
    pinfl = request.args.get('pinfl', '')
    nomzodlar = db.tolov_uchun_anketalarni_topish(pinfl)
    if not nomzodlar:
        conn = db.get_conn()
        rows = conn.execute('''
            SELECT anketa_raqami, mijoz_nomi, asosiy_qarz, foiz_qarz, jarima
            FROM portfel WHERE faol=1 AND unikal=?
        ''', (pinfl,)).fetchall()
        conn.close()
        nomzodlar = [dict(r) for r in rows]
    natija = []
    for n in nomzodlar:
        jami = (n.get('asosiy_qarz') or 0) + (n.get('foiz_qarz') or 0) + (n.get('jarima') or 0)
        natija.append({'anketa_raqami': n['anketa_raqami'], 'mijoz_nomi': n['mijoz_nomi'], 'jami_qarz': jami})
    return jsonify({'nomzodlar': natija})


@bp.route('/api/mib/tolov_anketa_tanlash', methods=['POST'])
def mib_tolov_anketa_tanlash():
    data = request.get_json() or {}
    tolov_id = data.get('tolov_id')
    anketa = data.get('anketa_raqami')
    if not tolov_id or not anketa:
        return jsonify({'xato': 'tolov_id va anketa_raqami kerak'}), 400
    db.tolov_anketa_biriktirish(tolov_id, anketa)
    try:
        mib_tolov_asosida_avtomatik_yakunlashni_tekshirish(anketa)
    except Exception:
        pass
    return jsonify({'ok': True})


@bp.route('/api/mib/tolov_qidirish', methods=['GET'])
def mib_tolov_qidirish():
    """Avtomatik aniqlash umuman ishlamagan ('mos_kelmadi') to'lovlar uchun
    — anketa raqami yoki mijoz nomi bo'yicha QO'LDA qidirib topish."""
    q = request.args.get('q', '')
    natija = db.tolov_qidirib_biriktirish(q)
    for n in natija:
        n['jami_qarz'] = (n.pop('asosiy_qarz', 0) or 0) + (n.pop('foiz_qarz', 0) or 0) + (n.pop('jarima', 0) or 0)
    return jsonify({'natija': natija})


@bp.route('/api/mib/harakatsizlar_excel', methods=['GET'])
def mib_harakatsizlar_excel():
    import tempfile
    from flask import send_file
    import pandas as pd
    xatlar = db.get_mib_harakatsizlar()
    if not xatlar:
        return jsonify({'xato': "Hozircha harakatsiz qolgan MIB ishi yo'q"}), 400
    rows = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0) if prow else 0
        rows.append({
            'Anketa raqami': x['anketa_raqami'], 'Mijoz': x['mijoz_nomi'], 'Turi': x['mijoz_turi'],
            "Qarzdorlik (so'm)": jami, 'MIB ish raqami': x.get('mib_ish_raqami', '') or '',
            'Necha kun harakatsiz': x.get('harakatsizlik_kun', ''),
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='mib_harakatsiz_qolganlar.xlsx')


# ══ BIZNES-HAMROH.UZ ═══════════════════════════════════════════════════
