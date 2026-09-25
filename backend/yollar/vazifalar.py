# -*- coding: utf-8 -*-
"""AQLLI YORDAMCHI — bugungi vazifalar ro'yxati.

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

bp = Blueprint('vazifalar', __name__)


@bp.route('/api/vazifalar/bugun', methods=['GET'])
def vazifalar_bugun():
    """AQLLI YORDAMCHI: barcha bosqichlarni ko'rib chiqib, bugun
    bajarilishi kerak bo'lgan ishlar ro'yxatini qaytaradi."""
    try:
        royxat = vzf.bugungi_vazifalar()
    except Exception as e:
        return jsonify({'xato': f"Vazifalarni hisoblashda xato: {e}"}), 500
    # Xulosa TO'LIQ ro'yxatdan hisoblanadi (filtrdan oldin) — aks holda
    # kartalardagi sonlar filtrga qarab o'zgarib ketardi.
    xulosa = vzf.vazifalar_xulosasi(royxat)
    filtr = (request.args.get('ustuvorlik') or '').strip()
    if filtr:
        royxat = [v for v in royxat if v['ustuvorlik'] == filtr]
    limit = request.args.get('limit')
    if limit:
        try:
            royxat = royxat[:int(limit)]
        except ValueError:
            pass
    return jsonify({'royxat': royxat, 'xulosa': xulosa})


@bp.route('/api/vazifalar/excel', methods=['GET'])
def vazifalar_excel():
    """Bugungi vazifalar ro'yxatini Excel qilib chiqaradi."""
    import tempfile
    from flask import send_file
    import pandas as pd
    royxat = vzf.bugungi_vazifalar()
    if not royxat:
        return jsonify({'xato': "Bugun bajariladigan vazifa yo'q"}), 400
    ustuvorlik_nomi = {'kechikkan': 'Kechikkan', 'bugun': 'Shoshilinch', 'rejali': 'Rejali'}
    df = pd.DataFrame([{
        'Ustuvorlik': ustuvorlik_nomi.get(v['ustuvorlik'], v['ustuvorlik']),
        'Anketa raqami': v['anketa_raqami'], 'PINFL/STIR': v['pinfl_stir'],
        'Mijoz nomi': v['mijoz_nomi'], 'Qarz summasi': v['qarz'],
        'Bosqich': v['bosqich'], 'Bajariladigan ish': v['vazifa'],
        'Izoh': v['izoh'],
        'Muddat (kun)': v['qolgan_kun'] if v['qolgan_kun'] is not None else '',
        "Bo'lim": v['bolim_nomi'],
    } for v in royxat])
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='bugungi_vazifalar.xlsx')
