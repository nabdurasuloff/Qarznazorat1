# -*- coding: utf-8 -*-
"""VAFOT ETGANLAR — vafot qayd etish, sug'urta xabarnomasi.

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

bp = Blueprint('vafot', __name__)


@bp.route('/api/vafot/royxat', methods=['GET'])
def vafot_royxat():
    royxat = db.get_vafot_etganlar_royxati()
    return jsonify({'royxat': royxat})


@bp.route('/api/vafot/excel', methods=['GET'])
def vafot_excel():
    import tempfile
    from flask import send_file
    import pandas as pd
    royxat = db.get_vafot_etganlar_royxati()
    if not royxat:
        return jsonify({'xato': "Hozircha vafot etgan mijoz qayd qilinmagan"}), 400
    rows = []
    for x in royxat:
        prow = db.get_portfel_by_id(x.get('portfel_id')) if x.get('portfel_id') else None
        if not prow:
            plist = db.get_portfel_by_anketa(x.get('anketa_raqami', ''))
            prow = plist[0] if plist else None
        prow = prow or {}
        muddati_otgan_asosiy = prow.get('asosiy_qarz') or 0
        muddati_otgan_foiz = prow.get('foiz_qarz') or 0
        muddati_otgan_jarima = prow.get('jarima') or 0
        rows.append({
            'Anketa raqami': x.get('anketa_raqami', ''),
            'F.I.Sh': x.get('mijoz_nomi', ''),
            'PINFL': prow.get('pinfl') or prow.get('stir') or '',
            "O'limlik kuni": x.get('vafot_sanasi', ''),
            'Kredit hisob raqami': prow.get('kredit_hisob_raqami', ''),
            'Jami olingan summasi': prow.get('jami_berilgan_summa') or 0,
            'Bugungi kundagi qoldiq': prow.get('jami_qarz') or 0,
            "Shundan muddati o'tgan jami qoldiq": muddati_otgan_asosiy + muddati_otgan_foiz + muddati_otgan_jarima,
            'Asosiy qarz': muddati_otgan_asosiy,
            'Foiz': muddati_otgan_foiz,
            'Penya': muddati_otgan_jarima,
            "Sug'urta nomi": x.get('sugurta_kompaniya', '') or '',
            'Shartnoma raqami': x.get('sugurta_polis_raqam', '') or '',
            'Amalda yoki tugagan': {'amalda': 'Amalda', 'muddati_otgan': 'Muddati tugagan',
                                     'tekshirilmagan': 'Tekshirilmagan'}.get(x.get('polis_holati', ''), x.get('polis_holati', '')),
            'Tarmoq kodi': prow.get('tarmoq', '') or '',
            'Kredit maqsadi': prow.get('tulov_maqsadi', '') or '',
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='vafot_etganlar.xlsx')


@bp.route('/api/vafot/qoshish', methods=['POST'])
def vafot_qoshish():
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami', '').strip()
    vafot_sanasi, sana_xato = util.sana_tekshir(
        data.get('vafot_sanasi', ''), 'Vafot sanasi', majburiy=True, kelajak_mumkinmi=False)
    if sana_xato:
        return jsonify({'xato': sana_xato}), 400
    if not anketa:
        return jsonify({'xato': 'anketa_raqami kerak'}), 400
    prow_list = db.get_portfel_by_anketa(anketa)
    mijoz_nomi = prow_list[0].get('mijoz_nomi', '') if prow_list else data.get('mijoz_nomi', '')
    conn = db.get_conn()
    conn.execute(
        "INSERT INTO vafot_etganlar (anketa_raqami, mijoz_nomi, vafot_sanasi, polis_holati) "
        "VALUES (?, ?, ?, 'amalda')", (anketa, mijoz_nomi, vafot_sanasi))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@bp.route('/api/vafot/fayl_yuklash', methods=['POST'])
def vafot_fayl_yuklash():
    """Vafot etgan mijoz uchun hujjat (o'limlik guvohnomasi / pasport / sug'urta
    polis) yuklaydi va uni ko'rish/yuklab olish mumkin bo'lgan holatda saqlaydi."""
    vafot_id = request.form.get('id')
    turi = request.form.get('turi')  # olimlik | pasport | sugurta_polis
    maydon_map = {
        'olimlik': 'olimlik_guvohnomasi_fayl',
        'pasport': 'pasport_fayl',
        'sugurta_polis': 'sugurta_polis_fayl',
    }
    if not vafot_id or turi not in maydon_map:
        return jsonify({'xato': "id va to'g'ri turi (olimlik/pasport/sugurta_polis) kerak"}), 400
    f = request.files.get('file')
    if not f or not f.filename:
        return jsonify({'xato': 'Fayl yuborilmadi'}), 400

    conn = db.get_conn()
    row = conn.execute('SELECT anketa_raqami FROM vafot_etganlar WHERE id=?', (vafot_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'xato': 'Yozuv topilmadi'}), 404
    anketa = row['anketa_raqami']
    out_dir = os.path.join(hujjatlar_papkasi(), 'vafot_etganlar', letters.safe_filename(anketa))
    os.makedirs(out_dir, exist_ok=True)
    fayl_yoli = os.path.join(out_dir, f"{turi}_{letters.safe_filename(f.filename)}")
    xato_natija = mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]

    ustun = maydon_map[turi]
    conn.execute(f'UPDATE vafot_etganlar SET {ustun}=? WHERE id=?', (fayl_yoli, vafot_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@bp.route('/api/vafot/yangilash', methods=['POST'])
def vafot_yangilash():
    data = request.get_json() or {}
    vafot_id = data.get('id')
    if not vafot_id:
        return jsonify({'xato': 'id kerak'}), 400
    ruxsat_etilgan = ['polis_holati', 'sugurta_kompaniya', 'sugurta_polis_raqam', 'xabarnoma_holati',
                       'xabarnoma_yuborilgan_sana', 'javob_kelgan_sana']
    updates = {k: v for k, v in data.items() if k in ruxsat_etilgan}
    if not updates:
        return jsonify({'xato': "Yangilanadigan maydon topilmadi"}), 400
    conn = db.get_conn()
    set_clause = ', '.join(f'{k}=?' for k in updates)
    conn.execute(f'UPDATE vafot_etganlar SET {set_clause} WHERE id=?', (*updates.values(), vafot_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@bp.route('/api/vafot/sugurta_kiritish', methods=['POST'])
def vafot_sugurta_kiritish():
    vafot_id = request.form.get('id')
    kompaniya = request.form.get('kompaniya', '')
    raqam = request.form.get('raqam', '')
    if not vafot_id:
        return jsonify({'xato': 'id kerak'}), 400
    v = db.get_vafot_etgan_by_id(vafot_id)
    if not v:
        return jsonify({'xato': 'Yozuv topilmadi'}), 404
    if v['polis_holati'] != 'amalda':
        return jsonify({'xato': "Sug'urta polisi amalda emas — sug'urta ma'lumoti kiritilmaydi."}), 400
    polis_dest = None
    f = request.files.get('polis_fayl')
    if f and f.filename:
        out_dir = os.path.join(hujjatlar_papkasi(), 'vafot_etganlar', letters.safe_filename(v['anketa_raqami']))
        os.makedirs(out_dir, exist_ok=True)
        polis_dest = os.path.join(out_dir, f"Polis_{letters.safe_filename(f.filename)}")
        xato_natija = mustahkam_fayl_saqlash(f, polis_dest, ozbek_kengaytma_tekshiruvi=False)
        if xato_natija:
            return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    db.update_sugurta_malumot(vafot_id, kompaniya, raqam, polis_dest)
    return jsonify({'ok': True})


@bp.route('/api/vafot/xabarnoma_tayyorlash', methods=['GET'])
def vafot_xabarnoma_tayyorlash():
    from flask import send_file
    vafot_id = request.args.get('id')
    v = db.get_vafot_etgan_by_id(vafot_id)
    if not v:
        return jsonify({'xato': 'Yozuv topilmadi'}), 404
    if v['polis_holati'] != 'amalda':
        return jsonify({'xato': "Sug'urta polisi amalda bo'lmagan mijoz uchun xabarnoma tayyorlanmaydi."}), 400
    if not v.get('sugurta_kompaniya'):
        return jsonify({'xato': "Avval sug'urta ma'lumotini kiriting."}), 400
    prow = db.get_portfel_by_id(v['portfel_id']) if v.get('portfel_id') else None
    if not prow:
        rows = db.get_portfel_by_anketa(v['anketa_raqami'])
        prow = rows[0] if rows else None
    if not prow:
        return jsonify({'xato': "Bog'liq portfel yozuvi topilmadi."}), 404
    turi_m, mijoz = util.resolve_mijoz(prow)
    settings = db.get_all_settings()
    out_dir = os.path.join(hujjatlar_papkasi(), 'vafot_etganlar', letters.safe_filename(v['anketa_raqami']))
    os.makedirs(out_dir, exist_ok=True)
    fname = f"Xabarnoma_{letters.safe_filename(v['anketa_raqami'])}_{letters.safe_filename(v['mijoz_nomi'])}.docx"
    out_path = os.path.join(out_dir, fname)
    try:
        letters.generate_sugurta_xabarnoma(out_path, v, prow, mijoz, settings)
    except Exception as e:
        return jsonify({'xato': f"Xabarnoma yaratishda xato: {e}"}), 400
    return send_file(out_path, as_attachment=True, download_name=fname)


@bp.route('/api/vafot/xabarnoma_yuborildi', methods=['POST'])
def vafot_xabarnoma_yuborildi():
    data = request.get_json() or {}
    vafot_id = data.get('id')
    sana = data.get('sana', '').strip()
    sana, sana_xato = util.sana_tekshir(sana, 'Xabarnoma yuborilgan sana', kelajak_mumkinmi=False)
    if sana_xato:
        return jsonify({'xato': sana_xato}), 400
    if not vafot_id or not sana:
        return jsonify({'xato': 'id va sana kerak'}), 400
    db.mark_xabarnoma_yuborildi(vafot_id, sana)
    return jsonify({'ok': True})


@bp.route('/api/vafot/javob_keldi', methods=['POST'])
def vafot_javob_keldi():
    vafot_id = request.form.get('id')
    sana = request.form.get('sana', '').strip()
    sana, sana_xato = util.sana_tekshir(sana, 'Javob kelgan sana', kelajak_mumkinmi=False)
    if sana_xato:
        return jsonify({'xato': sana_xato}), 400
    if not vafot_id or not sana:
        return jsonify({'xato': 'id va sana kerak'}), 400
    v = db.get_vafot_etgan_by_id(vafot_id)
    if not v:
        return jsonify({'xato': 'Yozuv topilmadi'}), 404
    if v['xabarnoma_holati'] != 'yuborildi':
        return jsonify({'xato': "Avval xabarnoma yuborilgani belgilanishi kerak."}), 400
    fayl_dest = None
    f = request.files.get('fayl')
    if f and f.filename:
        out_dir = os.path.join(hujjatlar_papkasi(), 'vafot_etganlar', letters.safe_filename(v['anketa_raqami']))
        os.makedirs(out_dir, exist_ok=True)
        fayl_dest = os.path.join(out_dir, f"Javob_{letters.safe_filename(f.filename)}")
        xato_natija = mustahkam_fayl_saqlash(f, fayl_dest, ozbek_kengaytma_tekshiruvi=False)
        if xato_natija:
            return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    db.mark_sugurta_javob_keldi(vafot_id, sana, fayl_dest)
    return jsonify({'ok': True})
