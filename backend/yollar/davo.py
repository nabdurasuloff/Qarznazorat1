# -*- coding: utf-8 -*-
"""DAVO ARIZA — ariza tayyorlash, SSP reestri, hisobotlar.

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

bp = Blueprint('davo', __name__)


@bp.route('/api/davo-ariza/turlari', methods=['GET'])
def davo_ariza_turlari():
    return jsonify({'turlari': letters.DAVO_ARIZA_NOMLARI})


@bp.route('/api/davo-ariza/royxat', methods=['GET'])
def davo_ariza_royxat():
    xatlar = db.get_xatlar_yuborilgan_davo_kerak()

    # Tezlik uchun: barcha ta'minot yozuvlarini BITTA so'rovda olamiz
    conn = db.get_conn()
    taminot_rows = conn.execute('SELECT * FROM davo_taminot').fetchall()
    conn.close()
    taminot_map = {r['anketa_raqami']: dict(r) for r in taminot_rows}

    settings = db.get_all_settings()
    muddat_kun = int(settings.get('davo_ariza_muddati_kun', 5))

    natija = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        if not prow:
            continue
        taminot = taminot_map.get(x['anketa_raqami'])
        tavsiya_kaliti = letters.tavsiya_ariza_turi(x['mijoz_turi'], taminot)
        tavsiya_nomi = letters.DAVO_ARIZA_NOMLARI.get(tavsiya_kaliti, '')

        jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
        has_davo = bool(x.get('davo_ariza_fayl_yoli'))
        olib_kelindi = x.get('davo_ariza_holati') == 'olib_kelindi'

        holat = 'yoq'
        holat_matni = '—'
        if x.get('mib_holati') == 'otkazildi':
            holat = 'olib_kelindi'
            holat_matni = "✓ MIBga o'tkazilgan" + (" (yakunlangan)" if x.get('mib_yakunlangan') else "")
        elif x.get('sud_holati') == 'topshirildi':
            holat, holat_matni = 'olib_kelindi', "✓ Sudga topshirilgan"
        elif olib_kelindi:
            holat, holat_matni = 'olib_kelindi', '✓ Olib kelindi'
        elif has_davo:
            try:
                davo_dt = datetime.datetime.fromisoformat(x['davo_ariza_sana'])
                qolgan = muddat_kun - (datetime.datetime.now() - davo_dt).days
                if qolgan < 0:
                    holat, holat_matni = 'otgan', f"⚠ {abs(qolgan)} kun o'tib ketdi"
                else:
                    holat, holat_matni = 'tayyor', f"Tayyor — {qolgan} kun qoldi"
            except Exception:
                holat, holat_matni = 'tayyor', 'Tayyor'

        davo_summasi = (x.get('davo_summasi_asosiy') or 0) + (x.get('davo_summasi_foiz') or 0) + \
            (x.get('davo_summasi_jarima') or 0) if has_davo else 0

        summa_farqi_matn = '—'
        qoshimcha_kerak = False
        if has_davo:
            farqi = db.get_davo_ariza_farqi(x, prow, settings=settings)
            if farqi['farq'] > 0:
                summa_farqi_matn = f"+{format(int(farqi['farq']), ',').replace(',', ' ')} so'm"
                qoshimcha_kerak = farqi['qoshimcha_kerak']
                if qoshimcha_kerak:
                    summa_farqi_matn += " ⚠ Qo'shimcha ariza kerak"

        tayyorlangan_sana = ''
        if has_davo and x.get('davo_ariza_sana'):
            try:
                tayyorlangan_sana = datetime.datetime.fromisoformat(x['davo_ariza_sana']).strftime('%d.%m.%Y')
            except Exception:
                tayyorlangan_sana = x.get('davo_ariza_sana', '')

        natija.append({
            'xat_id': x['id'],
            'anketa_raqami': x['anketa_raqami'],
            'mijoz_nomi': x['mijoz_nomi'],
            'turi': x['mijoz_turi'],
            'jami_qarz': jami,
            'davo_summasi': davo_summasi,
            'davo_ariza_turi': x.get('davo_ariza_turi'),
            'tavsiya_kaliti': tavsiya_kaliti,
            'tavsiya_nomi': tavsiya_nomi,
            'holat': holat,
            'holat_matni': holat_matni,
            'ish_raqami': x.get('davo_ariza_ish_raqami', ''),
            'taminot_bor': bool(taminot and taminot.get('taminot_turi') not in (None, '', 'yoq')),
            'summa_farqi_matn': summa_farqi_matn,
            'qoshimcha_kerak': qoshimcha_kerak,
            'tayyorlangan_sana': tayyorlangan_sana,
        })
    return jsonify({'royxat': natija})


@bp.route('/api/davo-ariza/yaratish', methods=['POST'])
def davo_ariza_yaratish():
    """Belgilangan anketalar uchun (har biriga o'z ta'minotiga qarab
    avtomatik to'g'ri tur tanlab) Davo ariza tayyorlaydi."""
    data = request.get_json() or {}
    anketalar = data.get('anketalar', [])
    settings = db.get_all_settings()

    yaratildi, otkazib_yuborildi, xatolar = 0, 0, []
    turlar_soni = {}
    for anketa in anketalar:
        if db.davo_ariza_mavjudmi(anketa):
            otkazib_yuborildi += 1
            continue
        xat = None
        conn = db.get_conn()
        row = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami=? AND holat='yuborildi'",
                            (anketa,)).fetchone()
        conn.close()
        xat = dict(row) if row else None
        if not xat:
            xatolar.append(f"{anketa}: xat topilmadi")
            continue
        prow = db.get_portfel_by_id(xat['portfel_id'])
        if not prow:
            xatolar.append(f"{anketa}: portfel topilmadi")
            continue
        try:
            mijoz_turi_calc, mijoz = util.resolve_mijoz(prow)
            taminot = db.get_taminot(anketa)
            turi = letters.tavsiya_ariza_turi(mijoz_turi_calc, taminot)
            turlar_soni[turi] = turlar_soni.get(turi, 0) + 1

            out_dir = bugungi_papka('Davo ariza')
            mijoz_ism = mijoz['ism'] if mijoz else xat['mijoz_nomi']
            fname = f"{letters.safe_filename(mijoz_ism)}_{letters.safe_filename(anketa)}_Davo_{turi}.docx"
            out_path = os.path.join(out_dir, fname)

            xat_sana = ''
            try:
                xat_sana = datetime.datetime.fromisoformat(xat['yaratilgan_sana']).strftime('%d.%m.%Y')
            except Exception:
                pass
            letters.generate_davo_ariza_v2(
                turi, out_path, prow, mijoz, taminot, settings, xat_sanasi=xat_sana,
                xat_turi_nomi=('Талабнома' if xat['xat_turi'] == 'Talabnoma' else 'Огохлантириш хати'),
            )
            db.mark_davo_ariza_yaratildi(xat['id'], out_path, turi=turi, portfel_row=prow)
            yaratildi += 1
        except Exception as e:
            xatolar.append(f"{anketa}: {e}")

    return jsonify({
        'yaratildi': yaratildi, 'otkazib_yuborildi': otkazib_yuborildi,
        'xatolar': xatolar, 'turlar_soni': turlar_soni,
    })


@bp.route('/api/davo-ariza/taminot', methods=['GET'])
def davo_ariza_taminot_get():
    anketa = request.args.get('anketa', '').strip()
    t = db.get_taminot(anketa) or {}
    return jsonify(t)


@bp.route('/api/davo-ariza/taminot', methods=['POST'])
def davo_ariza_taminot_save():
    data = request.get_json() or {}
    anketa = data.pop('anketa_raqami', None)
    if not anketa:
        return jsonify({'xato': 'anketa_raqami kerak'}), 400
    db.upsert_taminot(anketa, **data)
    return jsonify({'ok': True})


@bp.route('/api/davo-ariza/olib_kelindi', methods=['POST'])
def davo_ariza_olib_kelindi():
    anketa = request.form.get('anketa_raqami')
    ish_raqami = request.form.get('ish_raqami', '')
    sana = request.form.get('sana', '')
    # MUHIM: sana tekshirilmasa, noto'g'ri formatdagi sana jim qabul
    # qilinib, keyingi barcha muddat hisoblari shu ish uchun ishlamay qolardi.
    sana, sana_xato = util.sana_tekshir(sana, 'Imzo sanasi', kelajak_mumkinmi=False)
    if sana_xato:
        return jsonify({'xato': sana_xato}), 400
    f = request.files.get('skan')
    if not anketa or not ish_raqami or not sana:
        return jsonify({'xato': 'anketa_raqami, ish_raqami va sana kerak'}), 400
    if not f or not f.filename:
        return jsonify({'xato': "SSPdan olib kelingan hujjat skanini (PDF) yuklash majburiy"}), 400

    conn = db.get_conn()
    row = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami=? AND davo_ariza_fayl_yoli IS NOT NULL",
                        (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Davo arizasi tayyorlangan xat topilmadi'}), 404
    xat = dict(row)
    prow = db.get_portfel_by_id(xat['portfel_id'])
    settings = db.get_all_settings()

    # MUHIM: SSPdan olib kelingan (imzo/muhr bilan tasdiqlangan) rasmiy skan
    # Davo ariza faylining o'rniga saqlanadi — bu yig'ma jildga ham
    # avtomatik rasmiy nusxa tushishini ta'minlaydi.
    out_dir = bugungi_papka('SSP_tasdiqlangan')
    os.makedirs(out_dir, exist_ok=True)
    ext = os.path.splitext(f.filename)[1] or '.pdf'
    dest = os.path.join(out_dir, f"{letters.safe_filename(xat['mijoz_nomi'])}_{anketa}_SSP_tasdiqlangan{ext}")
    xato_natija = mustahkam_fayl_saqlash(f, dest, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    db.update_davo_ariza_fayl(xat['id'], dest)

    qoshimcha_kerak = db.mark_davo_ariza_olib_kelindi(xat['id'], ish_raqami, sana, portfel_row=prow, settings=settings)
    natija = {'ok': True}
    if qoshimcha_kerak:
        xat_yangi = db.get_xat_by_id(xat['id'])
        farqi = db.get_davo_ariza_farqi(xat_yangi, prow, settings)
        natija['ogohlantirish'] = (
            f"Davo ariza 'Olib kelindi' deb belgilandi. Diqqat: joriy qarzdorlik Davo ariza "
            f"yaratilgan paytdagi summadan {int(farqi['farq']):,} so'mga oshib ketgan — "
            f"qo'shimcha (yangi) SSP davo ariza kiritish talab qilinadi.".replace(',', ' ')
        )
    return jsonify(natija)


@bp.route('/api/davo-ariza/ochirish', methods=['POST'])
def davo_ariza_ochirish():
    data = request.get_json() or {}
    anketalar = data.get('anketalar', [])
    ochirildi, otkazib_yuborildi = 0, 0
    for anketa in anketalar:
        conn = db.get_conn()
        row = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami=? AND davo_ariza_fayl_yoli IS NOT NULL",
                            (anketa,)).fetchone()
        conn.close()
        if not row:
            otkazib_yuborildi += 1
            continue
        xat = dict(row)
        if xat.get('sud_holati') == 'topshirildi':
            otkazib_yuborildi += 1
            continue
        db.reset_davo_ariza(xat['id'])
        ochirildi += 1
    return jsonify({'ochirildi': ochirildi, 'otkazib_yuborildi': otkazib_yuborildi})


@bp.route('/api/davo-ariza/taminot_excel_eksport', methods=['POST'])
def davo_ariza_taminot_excel_eksport():
    import tempfile
    from flask import send_file
    data = request.get_json() or {}
    anketalar = data.get('anketalar', [])
    rows = []
    for anketa in anketalar:
        mijoz_nomi = anketa_mijoz_nomi(anketa)
        t = db.get_taminot(anketa) or {}
        rows.append({'anketa_raqami': anketa, 'mijoz_nomi': mijoz_nomi, **t})
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    importer.export_taminot_excel(rows, tmp_path)
    return send_file(tmp_path, as_attachment=True, download_name='taminot.xlsx')


@bp.route('/api/davo-ariza/taminot_excel_import', methods=['POST'])
def davo_ariza_taminot_excel_import():
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
        result = importer.import_taminot_excel(tmp_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({'xato': str(e)}), 400
    finally:
        os.remove(tmp_path)


@bp.route('/api/davo-ariza/imzodan_excel_eksport', methods=['POST'])
def davo_ariza_imzodan_excel_eksport():
    import tempfile
    from flask import send_file
    import pandas as pd
    royxat = db.get_olib_kelinganlar_royxati()
    if not royxat:
        return jsonify({'xato': "Hali Palatadan/imzodan qaytgan Davo arizalar yo'q."}), 400
    rows = []
    for item in royxat:
        xat = item['xat']
        rows.append({
            'Anketa raqami': xat['anketa_raqami'], 'Mijoz': xat['mijoz_nomi'],
            'PINFL/STIR': item.get('pinfl', ''),
            'Ish raqami': xat.get('davo_ariza_ish_raqami', '') or '',
            'Chiqqan sana': xat.get('davo_ariza_imzo_sana', '') or '',
            'Davo summasi (asosiy)': item['davo_summasi_asosiy'],
            'Davo summasi (foiz)': item['davo_summasi_foiz'],
            'Davo summasi (jarima)': item['davo_summasi_jarima'],
            'Jami davo summasi': item['davo_summasi'],
            'Joriy qarzdorlik': item['joriy_qarz'],
            'Farq': item['farq'],
            "Qo'shimcha ariza kerakmi": "✓ Ha" if item['qoshimcha_kerak'] else "Yo'q",
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='imzodan_kelganlar.xlsx')


@bp.route('/api/davo-ariza/sudga_topshirilganlar_excel', methods=['GET'])
def sudga_topshirilganlar_excel():
    import tempfile
    from flask import send_file
    import pandas as pd
    royxat = db.get_sudga_topshirilganlar_royxati()
    if not royxat:
        return jsonify({'xato': "Hozircha sudga topshirilgan ish yo'q"}), 400
    rows = []
    for item in royxat:
        xat = item['xat']
        prow = item['portfel']
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else xat.get('mijoz_turi')
        asosiy = xat.get('davo_summasi_asosiy') or 0
        foiz = xat.get('davo_summasi_foiz') or 0
        jarima = xat.get('davo_summasi_jarima') or 0
        rows.append({
            'Anketa raqami': xat['anketa_raqami'], 'Mijoz': xat['mijoz_nomi'], 'Turi': turi,
            'Davo summasi (jami)': asosiy + foiz + jarima,
            'Davo ariza tasdiqlangan (imzo) sanasi': xat.get('davo_ariza_imzo_sana', '') or '',
            "Sudga yuborishga ruxsat berilganmi": "Ha" if xat.get('sud_hujjatlar_ruxsat') else "Yo'q",
            'Sud ish raqami': xat.get('sud_ish_raqami', '') or '',
            'Sudga topshirilgan sana': xat.get('sud_topshirilgan_sana', '') or '',
            'Asosiy qarz': asosiy, 'Foiz': foiz, 'Penya (jarima)': jarima,
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='sudga_topshirilganlar.xlsx')


@bp.route('/api/davo-ariza/reestr', methods=['POST'])
def davo_ariza_reestr():
    import tempfile
    from flask import send_file
    data = request.get_json() or {}
    anketalar = data.get('anketalar', [])
    xat_raqami = data.get('xat_raqami', '')
    xat_sanasi = data.get('xat_sanasi', '')
    settings = db.get_all_settings()

    mijozlar_royxati = []
    for anketa in anketalar:
        conn = db.get_conn()
        row = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami=? AND davo_ariza_fayl_yoli IS NOT NULL",
                            (anketa,)).fetchone()
        conn.close()
        if not row:
            continue
        xat = dict(row)
        davo_summasi = (xat.get('davo_summasi_asosiy') or 0) + (xat.get('davo_summasi_foiz') or 0) + \
            (xat.get('davo_summasi_jarima') or 0)
        mijozlar_royxati.append({
            'anketa_raqami': anketa, 'mijoz_ism': xat['mijoz_nomi'], 'summa': davo_summasi,
        })
    if not mijozlar_royxati:
        return jsonify({'xato': "Davo arizasi tayyorlangan mijoz topilmadi"}), 400

    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
        tmp_path = tmp.name
    letters.generate_reestr_ssp(tmp_path, mijozlar_royxati, xat_raqami, xat_sanasi, settings)
    return send_file(tmp_path, as_attachment=True, download_name='Reestr_SSP.docx')


@bp.route('/api/davo-ariza/birlashtir', methods=['POST'])
def davo_ariza_birlashtir():
    import tempfile
    from flask import send_file
    data = request.get_json() or {}
    anketalar = data.get('anketalar', [])

    fayllar, turlari = [], []
    for anketa in anketalar:
        conn = db.get_conn()
        row = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami=? AND davo_ariza_fayl_yoli IS NOT NULL",
                            (anketa,)).fetchone()
        conn.close()
        if not row:
            continue
        xat = dict(row)
        if xat.get('davo_ariza_fayl_yoli') and os.path.exists(xat['davo_ariza_fayl_yoli']):
            fayllar.append(xat['davo_ariza_fayl_yoli'])
            turlari.append(xat.get('davo_ariza_turi'))

    if len(fayllar) < 2:
        return jsonify({'xato': "Birlashtirish uchun kamida 2 ta tayyorlangan Davo ariza kerak"}), 400

    bir_xil = len(set(turlari)) <= 1
    ext = '.docx' if bir_xil else '.pdf'
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp_path = tmp.name
    natija_yoli = letters.birlashtir_hujjatlar(fayllar, tmp_path, ariza_turlari=turlari)
    dl_name = 'Birlashgan_Davo_arizalar' + os.path.splitext(natija_yoli)[1]
    return send_file(natija_yoli, as_attachment=True, download_name=dl_name)


@bp.route('/api/davo-ariza/hisobot', methods=['GET'])
def davo_ariza_hisobot():
    muddat_kun = int(db.get_all_settings().get('davo_ariza_muddati_kun', 5))
    sabab_nomlari = {'qarz_yopilgan': "Qarz to'liq yopilgan", 'mijoz_arizasi': "Mijozning yozma arizasi asosida",
                      'xodim_iltimosi': "Bank xodimi iltimosiga asosan",
                      'dpd_kamaygan_avtomatik': "Avtomatik: DPD/qarz kamaygani sababli"}
    natija = []
    for x in db.get_davo_ariza_hisoboti():
        prow = db.get_portfel_by_id(x['portfel_id'])
        jami_joriy = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0) if prow else 0
        davo_asosiy = x.get('davo_summasi_asosiy') or 0
        davo_foiz = x.get('davo_summasi_foiz') or 0
        davo_jarima = x.get('davo_summasi_jarima') or 0

        olib_kelindi = x.get('davo_ariza_holati') == 'olib_kelindi'
        yaratilgan, davo_dt = '', None
        try:
            davo_dt = datetime.datetime.fromisoformat(x['davo_ariza_sana'])
            yaratilgan = davo_dt.strftime('%d.%m.%Y')
        except Exception:
            yaratilgan = x.get('davo_ariza_sana', '') or ''

        holat_pill = 'yoq'
        if olib_kelindi and davo_dt:
            try:
                imzo_dt = datetime.datetime.strptime(x['davo_ariza_imzo_sana'], '%d.%m.%Y')
                kutilgan_kun = max((imzo_dt.date() - davo_dt.date()).days, 0)
            except Exception:
                kutilgan_kun = ''
            holati = "✓ Olib kelindi"
            holat_pill = 'olib_kelindi'
        elif davo_dt:
            kutilgan_kun = (datetime.datetime.now() - davo_dt).days
            if kutilgan_kun > muddat_kun:
                holati = f"⚠ Muddati o'tgan ({kutilgan_kun} kun)"
                holat_pill = 'otgan'
            else:
                holati = f"Kutilmoqda ({muddat_kun - kutilgan_kun} kun qoldi)"
                holat_pill = 'tayyor'
        else:
            kutilgan_kun, holati = '', ''

        sud_topshirildi = x.get('sud_holati') == 'topshirildi'
        sud_kiritilmadi_sababi = x.get('sud_kiritilmadi_sababi')
        if sud_topshirildi:
            sud_holati_matn = "✓ Sudga kiritildi"
        elif sud_kiritilmadi_sababi:
            izoh_qoshimcha = ''
            if sud_kiritilmadi_sababi == 'xodim_iltimosi':
                izoh_qoshimcha = f" ({x.get('sud_kiritilmadi_xodim_ism', '')} — {x.get('sud_kiritilmadi_izoh', '')})"
            sud_holati_matn = f"✕ Sudga kiritilmadi: {sabab_nomlari.get(sud_kiritilmadi_sababi, sud_kiritilmadi_sababi)}{izoh_qoshimcha}"
        elif olib_kelindi:
            sud_holati_matn = "Sudga jo'natish kutilmoqda"
        else:
            sud_holati_matn = "—"

        # MUHIM: bitta, KONSOLIDATSIYALANGAN ustun — bu Davo ariza AYNAN
        # QAYSI bosqichgacha borganini (Xat -> Davo ariza -> SSPga
        # topshirilgan -> Sudga kiritilgan -> MIBga o'tkazilgan ->
        # Yakunlangan) darhol ko'rsatadi.
        if x.get('mib_yakunlangan'):
            joriy_bosqich = f"✓ Yakunlandi (MIB) — {x.get('mib_yakunlash_sababi', '')}"
        elif x.get('mib_holati') == 'otkazildi':
            joriy_bosqich = f"⚙ MIB jarayonida (ish №{x.get('mib_ish_raqami', '')})"
        elif sud_kiritilmadi_sababi:
            joriy_bosqich = f"✕ Sudga kiritilmadi: {sabab_nomlari.get(sud_kiritilmadi_sababi, sud_kiritilmadi_sababi)}"
        elif x.get('sud_qaror_natija') == 'rad_etildi':
            joriy_bosqich = "✕ Sud rad etdi"
        elif sud_topshirildi:
            joriy_bosqich = f"⚖ Sudga topshirilgan (ish №{x.get('sud_ish_raqami', '')})"
        elif olib_kelindi:
            joriy_bosqich = "📋 Portal tasdiqladi — sudga topshirish kutilmoqda"
        else:
            # MUHIM: Davo arizalar endi biznes-hamroh.uz portali orqali
            # yuboriladi. Shuning uchun hali sudga chiqmagan ishlarning
            # joriy bosqichi PORTAL holatidan olinadi — aks holda
            # portalga yuborilgan ish ham "tayyorlangan" bo'lib
            # ko'rinib, xodim uni qayta yuborishi mumkin edi.
            bh = db.bh_murojaat_olish(x['anketa_raqami']) or {}
            bh_holat = bh.get('holati')
            bh_raqam = bh.get('murojaat_raqami') or ''
            if bh_holat == 'rad_etildi':
                izoh = bh.get('natija_izoh') or ''
                joriy_bosqich = f"✕ Portal rad etdi{(' — ' + izoh) if izoh else ''}"
            elif bh_holat == 'javob_kutilmoqda':
                joriy_bosqich = f"⏳ Portalda javob kutilmoqda{(' (№' + bh_raqam + ')') if bh_raqam else ''}"
            elif bh_holat == 'yuborildi':
                joriy_bosqich = f"📤 Portalga yuborilgan{(' (№' + bh_raqam + ')') if bh_raqam else ''}"
            elif x.get('davo_ariza_ish_raqami'):
                joriy_bosqich = "📤 SSPga topshirilgan — javob kutilmoqda"
            else:
                joriy_bosqich = "📝 Davo ariza tayyorlangan — portalga yuborilishi kerak"

        natija.append({
            'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'], 'mijoz_turi': x['mijoz_turi'],
            'jami_qarz': jami_joriy,
            'davo_summasi_asosiy': davo_asosiy, 'davo_summasi_foiz': davo_foiz, 'davo_summasi_jarima': davo_jarima,
            'davo_summasi_jami': davo_asosiy + davo_foiz + davo_jarima,
            'yaratilgan': yaratilgan, 'kutilgan_kun': kutilgan_kun,
            'ish_raqami': x.get('davo_ariza_ish_raqami', '') or '', 'imzo_sana': x.get('davo_ariza_imzo_sana', '') or '',
            'holati': holati, 'holat_pill': holat_pill,
            'sud_ish_raqami': x.get('sud_ish_raqami', '') or '', 'sud_sana': x.get('sud_topshirilgan_sana', '') or '',
            'sud_holati': sud_holati_matn,
            'joriy_bosqich': joriy_bosqich,
        })
    return jsonify({'royxat': natija})


@bp.route('/api/davo-ariza/hisobot_excel', methods=['GET'])
def davo_ariza_hisobot_excel():
    import tempfile
    from flask import send_file
    import pandas as pd
    resp = davo_ariza_hisobot()
    rows = resp.get_json()['royxat']
    if not rows:
        return jsonify({'xato': "Hali birorta Davo ariza yaratilmagan"}), 400
    excel_qatorlar = []
    for r in rows:
        excel_qatorlar.append({
            'Anketa raqami': r['anketa_raqami'], 'Mijoz': r['mijoz_nomi'], 'Turi': r['mijoz_turi'],
            'Ish raqami': r['ish_raqami'], 'Tayyorlangan sanasi': r['yaratilgan'],
            'Davo summasi (asosiy)': r['davo_summasi_asosiy'], 'Davo summasi (foiz)': r['davo_summasi_foiz'],
            'Davo summasi (penya)': r['davo_summasi_jarima'], 'Davo summasi (jami)': r['davo_summasi_jami'],
            "Joriy qarzdorlik (bugun)": r['jami_qarz'],
            'Holati (Palata/SSP)': r['holati'],
            'Sud ish raqami': r['sud_ish_raqami'], 'Sudga topshirilgan sana': r['sud_sana'],
            'Sudga jo\'natish holati / izoh': r['sud_holati'],
            'Joriy bosqich (qaysi jarayongacha borgan)': r['joriy_bosqich'],
        })
    df = pd.DataFrame(excel_qatorlar)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='davo_ariza_hisoboti.xlsx')
