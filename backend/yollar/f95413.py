# -*- coding: utf-8 -*-
"""95413 — balansdan chiqarilgan kreditlar va ularning yig'ma jildi.

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

bp = Blueprint('f95413', __name__)


@bp.route('/api/95413/yigma_jild_holati', methods=['GET'])
def f95413_yigma_jild_holati():
    """95413 mijozi uchun yig'ma jild holati: Titul yaratilganmi, va
    foydalanuvchi o'zi nom berib qo'shgan barcha hujjatlar ro'yxati."""
    anketa = request.args.get('anketa', '').strip()
    if not anketa:
        return jsonify({'xato': 'Anketa raqami kerak'}), 400

    # MUHIM (tezlik tuzatishi): oldingi Sud/MIB hujjatlarini 95413 papkasiga
    # avtomatik nusxalash ilgari RO'YXAT ekranida, HAR BIR mijoz uchun
    # bajarilardi — ya'ni ro'yxatni ochish minglab papka yaratish va
    # o'qish amallarini keltirib chiqarardi (hujjatlar papkasi tarmoq
    # diskida bo'lsa — bir necha daqiqa). Endi bu ish faqat AYNAN SHU
    # mijozning jildi ochilganda, bir marta bajariladi — natija bir xil,
    # lekin ro'yxat bir zumda ochiladi.
    try:
        prow_list = db.get_portfel_by_anketa(anketa)
        if prow_list:
            prow = prow_list[0]
            mijoz_papka = f95413_mijoz_papkasi(prow['mijoz_nomi'], anketa)
            if not os.listdir(mijoz_papka):
                conn = db.get_conn()
                eng_songgi_xat = conn.execute(
                    'SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1',
                    (anketa,)).fetchone()
                conn.close()
                if eng_songgi_xat:
                    f95413_hujjatlarni_nusxalash(prow['mijoz_nomi'], dict(eng_songgi_xat), anketa)
    except Exception:
        pass  # nusxalash imkoni bo'lmasa ham, jild holati baribir ko'rsatiladi

    titul = db.f95413_titul_olish(anketa)
    hujjatlar = db.f95413_hujjatlar_royxati(anketa)
    return jsonify({
        'titul_bor': bool(titul and titul.get('titul_fayl') and os.path.exists(titul['titul_fayl'])),
        'titul_fayl': titul['titul_fayl'] if titul else '',
        'hujjatlar': hujjatlar,
    })


@bp.route('/api/95413/titul_yaratish', methods=['POST'])
def f95413_titul_yaratish():
    """95413 mijozi uchun Titul (muqova) hujjatini AVTOMATIK yaratadi —
    MIB yig'ma jildining titul shabloni bilan bir xil ko'rinishda."""
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami', '').strip()
    if not anketa:
        return jsonify({'xato': 'Anketa raqami kerak'}), 400
    prow_list = db.get_portfel_by_anketa(anketa)
    if not prow_list:
        return jsonify({'xato': 'Bu anketa portfelda topilmadi'}), 404
    settings = db.get_all_settings()
    conn = db.get_conn()
    xat_row = conn.execute('SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1', (anketa,)).fetchone()
    conn.close()
    # MUHIM: bitta anketa raqami ostida ikki xil mijoz bo'lishi mumkin
    # (anketa_mijoz_nomi izohiga qarang) — shuning uchun to'g'ri portfel
    # qatorini xat yozuvi orqali aniqlaymiz.
    prow = None
    if xat_row and dict(xat_row).get('portfel_id'):
        prow = db.get_portfel_by_id(dict(xat_row)['portfel_id'])
    if not prow:
        prow = sorted(prow_list, key=lambda r: (r.get('asosiy_qarz') or 0) + (r.get('foiz_qarz') or 0),
                      reverse=True)[0]
    turi, mijoz = util.resolve_mijoz(prow)
    xat = dict(xat_row) if xat_row else {'anketa_raqami': anketa, 'mijoz_nomi': prow.get('mijoz_nomi', ''), 'mijoz_turi': turi}

    jild_papka = f95413_mijoz_papkasi(prow.get('mijoz_nomi', ''), anketa)
    titul_path = os.path.join(jild_papka, '00_Titul.docx')
    letters.generate_yigma_jild_titul(titul_path, xat, prow, mijoz, settings)
    # MUHIM: titul qayta yaratilganda, shu bilan birga, hali nusxalanmagan
    # (masalan Titul birinchi marta yaratilgandan keyin Sud bosqichida
    # yangi yuklangan) Xat/Davo ariza/Sud/Ijro/kredit hujjatlarini ham
    # qayta qidirib, topilganlarini AVTOMATIK qo'shib qo'yamiz.
    f95413_hujjatlarni_nusxalash(prow.get('mijoz_nomi', ''), xat, anketa)
    db.f95413_titul_saqlash(anketa, titul_path)
    return jsonify({'ok': True})


@bp.route('/api/95413/hujjat_yuklash', methods=['POST'])
def f95413_hujjat_yuklash():
    """95413 yig'ma jildiga, foydalanuvchi O'ZI YOZGAN nom bilan
    istalgan hujjatni yuklaydi (qattiq belgilangan hujjat turlari
    emas — bu bo'limda hujjatlar turi oldindan belgilanmagan)."""
    anketa = request.form.get('anketa_raqami', '').strip()
    hujjat_nomi = request.form.get('hujjat_nomi', '').strip()
    f = request.files.get('file')
    if not anketa or not hujjat_nomi or not f or not f.filename:
        return jsonify({'xato': "Anketa raqami, hujjat nomi va fayl kerak"}), 400
    if not db.get_portfel_by_anketa(anketa):
        return jsonify({'xato': 'Bu anketa portfelda topilmadi'}), 404
    mijoz_nomi = anketa_mijoz_nomi(anketa)
    jild_papka = f95413_mijoz_papkasi(mijoz_nomi, anketa)
    fayl_nomi_toza = letters.safe_filename(hujjat_nomi)
    fayl_yoli = os.path.join(jild_papka, f"{fayl_nomi_toza}_{letters.safe_filename(f.filename)}")
    xato_natija = mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    db.f95413_hujjat_qoshish(anketa, hujjat_nomi, fayl_yoli)
    return jsonify({'ok': True})


@bp.route('/api/95413/hujjat/<int:hujjat_id>', methods=['DELETE'])
def f95413_hujjat_ochirish_endpoint(hujjat_id):
    db.f95413_hujjat_ochirish(hujjat_id)
    return jsonify({'ok': True})


@bp.route('/api/nazorat95413/royxat', methods=['GET'])
def nazorat95413_royxat():
    royxat = db.get_95413_royxati()
    natija = []
    for r in royxat:
        prow = r['portfel']
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi'))

        natija.append({
            'anketa_raqami': prow['anketa_raqami'], 'mijoz_nomi': prow['mijoz_nomi'], 'turi': turi,
            'balans_95413': prow.get('balans_95413') or 0,
            'bosqich': r['bosqich'], 'bosqich_nomi': db.BOSQICH_NOMLARI_95413.get(r['bosqich'], r['bosqich']),
            'tafsilot': r['tafsilot'],
        })
    soni = {}
    for r in royxat:
        soni[r['bosqich']] = soni.get(r['bosqich'], 0) + 1
    jami_balans = sum((r['portfel'].get('balans_95413') or 0) for r in royxat)
    return jsonify({'royxat': natija, 'soni': soni, 'jami': len(royxat), 'jami_balans': jami_balans,
                     'bosqich_nomlari': db.BOSQICH_NOMLARI_95413})


@bp.route('/api/nazorat95413/excel_eksport', methods=['GET'])
def nazorat95413_excel_eksport():
    import tempfile
    from flask import send_file
    import pandas as pd
    royxat = db.get_95413_royxati()
    rows = []
    for r in royxat:
        prow = r['portfel']
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi'))
        rows.append({
            'Anketa raqami': prow['anketa_raqami'], 'Mijoz': prow['mijoz_nomi'], 'Turi': turi,
            'Balans 95413': prow.get('balans_95413') or 0,
            'Bosqich': db.BOSQICH_NOMLARI_95413.get(r['bosqich'], r['bosqich']), 'Tafsilot': r['tafsilot'],
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='95413_nazorati.xlsx')


@bp.route('/api/nazorat95413/xat_yuborildi_belgilash', methods=['POST'])
def nazorat95413_xat_yuborildi_belgilash():
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami', '').strip()
    conn = db.get_conn()
    row = conn.execute("SELECT id FROM xatlar WHERE anketa_raqami=?", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Xat topilmadi'}), 404
    db.mark_xat_yuborildi(row['id'])
    return jsonify({'ok': True})


@bp.route('/api/nazorat95413/eski_ish_qidirish', methods=['GET'])
def nazorat95413_eski_ish_qidirish():
    anketa = request.args.get('anketa', '').strip()
    rows = db.get_portfel_by_anketa(anketa)
    if not rows:
        return jsonify({'topildi': False})
    prow = rows[0]
    turi, mijoz = util.resolve_mijoz(prow)
    jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
    return jsonify({'topildi': True, 'mijoz_nomi': prow.get('mijoz_nomi', ''), 'turi': turi,
                     'jami_qarz': jami, 'balans_95413': prow.get('balans_95413') or 0})


@bp.route('/api/nazorat95413/eski_ish_kiritish', methods=['POST'])
def nazorat95413_eski_ish_kiritish():
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami', '').strip()
    ish_raqami = data.get('ish_raqami', '').strip()
    sana = data.get('sana', '').strip()
    sana, sana_xato = util.sana_tekshir(sana, 'MIB ish sanasi', kelajak_mumkinmi=False)
    if sana_xato:
        return jsonify({'xato': sana_xato}), 400
    if not anketa or not ish_raqami or not sana:
        return jsonify({'xato': 'anketa_raqami, ish_raqami va sana kerak'}), 400
    rows = db.get_portfel_by_anketa(anketa)
    if not rows:
        return jsonify({'xato': 'Bu anketa portfelda topilmadi'}), 404
    prow = rows[0]
    mijoz_turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi'))
    qarz = data.get('qarzdorlik')
    qarz = float(qarz) if qarz else None

    xat_id = db.create_legacy_mib_xat(
        portfel_id=prow['id'], anketa_raqami=anketa, mijoz_nomi=prow.get('mijoz_nomi', ''),
        mijoz_turi=mijoz_turi, mib_ish_raqami=ish_raqami, mib_sana=sana,
        sud_ish_raqami=data.get('sud_ish_raqami') or None, joriy_qarzdorlik=qarz,
    )

    # MUHIM: 95413 uchun yig'ma jild ODDIY MIB jildlaridan ALOHIDA papkaga yoziladi —
    # bu kreditlar asosiy balansdan chiqarilgani uchun boshqa bo'limlarda ko'rinmasligi
    # mumkin, shu bois hujjatlari ham alohida saqlanadi.
    try:
        turi_m, mijoz = util.resolve_mijoz(prow)
        settings = db.get_all_settings()
        xat_yangilangan = db.get_xat_by_id(xat_id)
        jild_papka = f95413_mijoz_papkasi(prow.get('mijoz_nomi', ''), anketa)
        titul_path = os.path.join(jild_papka, '00_Titul.docx')
        letters.generate_yigma_jild_titul(titul_path, xat_yangilangan, prow, mijoz, settings)
        db.mark_yigma_jild_yaratildi(xat_id, jild_papka, titul_path)
    except Exception as e:
        return jsonify({'ok': True, 'ogohlantirish': f"Eski ish kiritildi, lekin yig'ma jild yaratishda xato: {e}"})

    db.add_mib_amal(xat_id, 'eski_ish_kiritildi', sana,
                     tavsif=f"95413 balansidagi eski ish (MIB ish raqami: {ish_raqami}) tizimga qo'lda kiritildi.")
    return jsonify({'ok': True})
