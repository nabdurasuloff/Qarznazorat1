# -*- coding: utf-8 -*-
"""CHORA KO'RISH — DPD asosida keyingi chorani tavsiya qilish.

Bu modul ilgari server.py ichida edi. Kod o'zgarmadi — faqat alohida
faylga ko'chirildi va Flask Blueprint orqali ilovaga ulanadi.
"""
import os
import sys
import datetime

from flask import Blueprint, current_app, jsonify, request

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

# Chora bo'limi xat va davo arizani o'sha bo'limlarning
# o'z funksiyalari orqali yaratadi (kod takrorlanmasligi uchun).
from yollar.talabnoma import talabnoma_xat_yaratish
from yollar.davo import davo_ariza_yaratish

bp = Blueprint('chora', __name__)


@bp.route('/api/chora/royxat', methods=['GET'])
def chora_royxat():
    royxat = db.get_chora_korish_royxati()
    natija = []
    for i, r in enumerate(royxat):
        prow = r['portfel']
        jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
        natija.append({
            'i': i, 'anketa_raqami': prow['anketa_raqami'], 'mijoz_nomi': prow['mijoz_nomi'],
            'turi': r['turi'], 'dpd': r['dpd'], 'qarzdorlik': jami,
            'chora': r['chora'], 'chora_nomi': r['chora_nomi'], 'tafsilot': r['tafsilot'],
        })
    soni = {}
    for r in royxat:
        soni[r['chora']] = soni.get(r['chora'], 0) + 1
    return jsonify({'royxat': natija, 'soni': soni, 'chora_nomlari': db.CHORA_NOMLARI})


@bp.route('/api/chora/amal_bajarish', methods=['POST'])
def chora_amal_bajarish():
    """Chora ko'rishdan tanlangan anketalar uchun tavsiya etilgan choraga
    qarab avtomatik amal bajaradi: xat yuborish YOKI Davo ariza tayyorlash
    (ommaviy) — MIB harakati alohida (bittadan) MIB bo'limida bajariladi."""
    data = request.get_json() or {}
    anketalar = data.get('anketalar', [])
    royxat = db.get_chora_korish_royxati()
    royxat_map = {r['portfel']['anketa_raqami']: r for r in royxat}

    xat_kerak, davo_kerak, boshqa = [], [], 0
    for anketa in anketalar:
        r = royxat_map.get(anketa)
        if not r:
            continue
        if r['chora'] in ('xat_yuborish', 'xat_yuborish_keyingi_bosqich'):
            xat_kerak.append(anketa)
        elif r['chora'] == 'davo_ariza_tayyorlash':
            davo_kerak.append(anketa)
        else:
            boshqa += 1

    if xat_kerak and davo_kerak:
        return jsonify({'xato': "Tanlanganlar orasida ham xat, ham Davo ariza bosqichidagilar bor. "
                                 "Iltimos, faqat bitta turdagi bosqichni tanlang."}), 400

    if xat_kerak:
        # talabnoma_xat_yaratish endpoint mantig'ini qayta ishlatamiz.
        # MUHIM TUZATISH: bu yerda `app` ishlatilgan edi, lekin u shu
        # modulga UMUMAN import qilinmagan — natijada "Chora ko'rish"
        # bo'limidagi ommaviy amal tugmasi HAR DOIM ichki xato (500)
        # berardi. Flask'ning `current_app` obyekti aynan shu maqsad
        # uchun mo'ljallangan va so'rov ichida doimo mavjud bo'ladi.
        with current_app.test_request_context(json={'anketalar': xat_kerak}):
            resp = talabnoma_xat_yaratish()
        result = resp.get_json()
        return jsonify({'turi': 'xat', **result})

    if davo_kerak:
        with current_app.test_request_context(json={'anketalar': davo_kerak}):
            resp = davo_ariza_yaratish()
        result = resp.get_json()
        return jsonify({'turi': 'davo', **result})

    # Bitta mijoz, MIB yoki Sudga kiritish bosqichida bo'lsa — tegishli
    # bo'limga yo'naltirish kerakligini bildiramiz (bular ommaviy
    # avtomatlashtirilmagan, chunki qo'shimcha hujjat/tasdiqlash talab qiladi)
    if len(anketalar) == 1:
        r = royxat_map.get(anketalar[0])
        if r and r['chora'] == 'mib_harakat_boshlash':
            return jsonify({'xato': "Bu mijoz MIB bosqichida. MIB harakati qo'shish uchun "
                                     "'MIB ijro harakatlari' bo'limiga o'ting va u yerdan "
                                     "'+ Harakat' tugmasini bosing."}), 400
        if r and r['chora'] == 'sudga_kiritish_kerak':
            return jsonify({'xato': "Bu mijozning Davo arizasi SSPdan tasdiqlanib qaytgan. "
                                     "Sudga topshirish uchun 'SUD Ishlari' bo'limiga o'ting."}), 400
        if r and r['chora'] == 'jarayon_qaytadan_tiklash_kerak':
            return jsonify({'xato': "Bu mijozning Davo ariza muddati tugagan. Jarayonni noldan "
                                     "boshlash uchun 'MIB ijro harakatlari → Yakunlangan ishlar' "
                                     "bo'limida (agar u yerda ko'rinmasa, Sud Ishlari bo'limidan) "
                                     "'Nollashtirish' funksiyasidan foydalaning."}), 400

    return jsonify({'xato': "Tanlanganlar orasida xat yoki Davo ariza bosqichidagi mijoz topilmadi "
                             "(MIB harakati alohida, MIB bo'limida bajariladi)."}), 400


@bp.route('/api/chora/qidirish', methods=['GET'])
def chora_qidirish():
    anketa = request.args.get('anketa', '').strip()
    royxat = db.get_chora_korish_royxati()
    for i, r in enumerate(royxat):
        if r['portfel']['anketa_raqami'] == anketa:
            prow = r['portfel']
            jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
            return jsonify({'topildi': True, 'row': {
                'i': i, 'anketa_raqami': prow['anketa_raqami'], 'mijoz_nomi': prow['mijoz_nomi'],
                'turi': r['turi'], 'dpd': r['dpd'], 'qarzdorlik': jami,
                'chora': r['chora'], 'chora_nomi': r['chora_nomi'], 'tafsilot': r['tafsilot'],
            }})
    return jsonify({'topildi': False})


@bp.route('/api/chora/excel_eksport', methods=['GET'])
def chora_excel_eksport():
    import tempfile
    from flask import send_file
    import pandas as pd
    royxat = db.get_chora_korish_royxati()
    rows = []
    for r in royxat:
        prow = r['portfel']
        jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
        rows.append({
            'Anketa raqami': prow['anketa_raqami'], 'Mijoz': prow['mijoz_nomi'], 'Turi': r['turi'],
            'DPD': r['dpd'], 'Qarzdorlik': jami, 'Chora': r['chora_nomi'], 'Tafsilot': r['tafsilot'],
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='chora_korish.xlsx')
