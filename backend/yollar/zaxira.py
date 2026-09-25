# -*- coding: utf-8 -*-
"""ZAXIRA NUSXALAR — bazani nusxalash, tiklash, yuklab olish.

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

bp = Blueprint('zaxira', __name__)


@bp.route('/api/zaxira/royxat', methods=['GET'])
def zaxira_royxat():
    royxat = db.zaxira_royxati()
    return jsonify({
        'royxat': royxat,
        'papka': db.zaxira_papkasi(),
        'saqlash_kun': db.ZAXIRA_SAQLASH_KUN,
        'oxirgi_sana': db.get_setting('oxirgi_zaxira_sana', '') or '',
        'bugun_olinganmi': not db.zaxira_kerakmi(),
    })


@bp.route('/api/zaxira/yaratish', methods=['POST'])
def zaxira_yaratish_endpoint():
    """Foydalanuvchi so'raganda darhol zaxira nusxa oladi (masalan katta
    o'zgarishdan oldin)."""
    try:
        yol = db.zaxira_yaratish('qolda')
    except Exception as e:
        return jsonify({'xato': f"Zaxira olishda xato: {e}"}), 500
    if not yol:
        return jsonify({'xato': 'Baza fayli topilmadi'}), 404
    return jsonify({'ok': True, 'fayl': yol, 'nomi': os.path.basename(yol)})


@bp.route('/api/zaxira/tiklash', methods=['POST'])
def zaxira_tiklash_endpoint():
    """Bazani tanlangan zaxira nusxasidan tiklaydi.

    MUHIM: bu amal joriy ma'lumotlarni ALMASHTIRADI. Shu sabab tiklashdan
    oldin joriy baza ham avtomatik nusxalanadi va foydalanuvchidan
    tasdiq so'raladi (frontendda)."""
    data = request.get_json() or {}
    yol = (data.get('yoli') or '').strip()
    if not yol:
        return jsonify({'xato': 'Zaxira faylini tanlang'}), 400
    # Faqat zaxira papkasi ichidagi fayllarga ruxsat — tashqaridan
    # ixtiyoriy fayl yo'lini yuborib bo'lmasin.
    papka = os.path.abspath(db.zaxira_papkasi())
    if not os.path.abspath(yol).startswith(papka):
        return jsonify({'xato': "Faqat zaxira papkasidagi fayl tanlanishi mumkin"}), 400
    try:
        db.zaxiradan_tiklash(yol)
    except Exception as e:
        return jsonify({'xato': f"Tiklashda xato: {e}"}), 500
    return jsonify({'ok': True})


@bp.route('/api/zaxira/yuklab_olish', methods=['GET'])
def zaxira_yuklab_olish():
    """Zaxira nusxani kompyuterga (yoki telefonga) yuklab olish —
    boshqa joyda ham saqlab qo'yish uchun."""
    from flask import send_file
    yol = (request.args.get('yoli') or '').strip()
    papka = os.path.abspath(db.zaxira_papkasi())
    if not yol or not os.path.abspath(yol).startswith(papka) or not os.path.exists(yol):
        return jsonify({'xato': 'Fayl topilmadi'}), 404
    return send_file(yol, as_attachment=True, download_name=os.path.basename(yol))


@bp.route('/api/zaxira/ochirish', methods=['POST'])
def zaxira_ochirish():
    data = request.get_json() or {}
    yol = (data.get('yoli') or '').strip()
    papka = os.path.abspath(db.zaxira_papkasi())
    if not yol or not os.path.abspath(yol).startswith(papka):
        return jsonify({'xato': "Faqat zaxira papkasidagi fayl o'chirilishi mumkin"}), 400
    try:
        os.remove(yol)
    except OSError as e:
        return jsonify({'xato': f"O'chirishda xato: {e}"}), 500
    return jsonify({'ok': True})
