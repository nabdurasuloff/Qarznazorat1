# -*- coding: utf-8 -*-
"""SOZLAMALAR, AUTENTIFIKATSIYA va FOYDALANUVCHILAR.

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

bp = Blueprint('sozlamalar', __name__)


@bp.route('/api/auth/status', methods=['GET'])
def auth_status():
    return jsonify({'parol_kerak': db.parol_ornatilganmi(), 'kop_foydalanuvchi': db.foydalanuvchilar_bormi()})


@bp.route('/api/auth/login', methods=['POST'])
def auth_login():
    data = request.get_json() or {}
    login = data.get('login', '')
    parol = data.get('parol', '')
    # Ko'p kompyuterli tarmoq rejimi: agar foydalanuvchilar yaratilgan
    # bo'lsa, login+parol orqali tekshiramiz.
    if db.foydalanuvchilar_bormi():
        foydalanuvchi = db.foydalanuvchi_login_tekshirish(login, parol)
        if foydalanuvchi:
            return jsonify({'ok': True, 'foydalanuvchi': foydalanuvchi})
        return jsonify({'ok': False})
    # Eski, yagona-parolli rejim (hali foydalanuvchi yaratilmagan bo'lsa)
    ok = db.parol_tekshirish(parol)
    return jsonify({'ok': ok})


@bp.route('/api/foydalanuvchilar', methods=['GET'])
def foydalanuvchilar_royxat():
    return jsonify({'royxat': db.foydalanuvchilar_royxati()})


@bp.route('/api/foydalanuvchilar', methods=['POST'])
def foydalanuvchilar_yangi():
    data = request.get_json() or {}
    login = data.get('login', '').strip()
    parol = data.get('parol', '').strip()
    toliq_ism = data.get('toliq_ism', '').strip()
    rol = data.get('rol', 'xodim')
    if not login or not parol:
        return jsonify({'xato': 'Login va parol kerak'}), 400
    if len(parol) < 4:
        return jsonify({'xato': "Parol kamida 4 ta belgidan iborat bo'lishi kerak"}), 400
    ok = db.foydalanuvchi_yaratish(login, parol, toliq_ism, rol)
    if not ok:
        return jsonify({'xato': "Bu login band — boshqa login tanlang"}), 400
    return jsonify({'ok': True})


@bp.route('/api/foydalanuvchilar/<int:user_id>', methods=['DELETE'])
def foydalanuvchilar_ochirish_endpoint(user_id):
    db.foydalanuvchi_ochirish(user_id)
    return jsonify({'ok': True})


@bp.route('/api/foydalanuvchilar/<int:user_id>/faollik', methods=['POST'])
def foydalanuvchilar_faollik_endpoint(user_id):
    data = request.get_json() or {}
    db.foydalanuvchi_faollik(user_id, data.get('faol', True))
    return jsonify({'ok': True})


@bp.route('/api/sozlamalar', methods=['GET'])
def sozlamalar_get():
    return jsonify(db.get_all_settings())


@bp.route('/api/sozlamalar', methods=['POST'])
def sozlamalar_save():
    """Sozlamalarni saqlaydi.

    MUHIM: raqamli sozlamalar (muddat kunlari, DPD chegarasi, BXM va h.k.)
    saqlashdan OLDIN tekshiriladi. Ilgari ular hech qanday tekshiruvsiz
    saqlanardi va noto'g'ri qiymat butun ekranlarni ishdan chiqarardi —
    endi foydalanuvchi darhol tushunarli xato oladi."""
    data = request.get_json() or {}
    xatolar = []
    for kalit, qiymat in data.items():
        if kalit in db.RAQAMLI_SOZLAMALAR:
            matn = str(qiymat if qiymat is not None else '').replace(' ', '').replace(',', '.').strip()
            if not matn:
                xatolar.append(f"«{kalit}» bo'sh qoldirilgan — raqam kiriting")
                continue
            try:
                son = float(matn)
            except ValueError:
                xatolar.append(f"«{kalit}» raqam bo'lishi kerak (kiritilgan: {qiymat})")
                continue
            if son < 0:
                xatolar.append(f"«{kalit}» manfiy bo'lishi mumkin emas")
                continue
            qiymat = str(int(son)) if son == int(son) else str(son)
        db.set_setting(kalit, qiymat)
    if xatolar:
        return jsonify({'xato': "Quyidagi sozlamalar saqlanmadi:\n• " + "\n• ".join(xatolar)}), 400
    return jsonify({'ok': True})


@bp.route('/api/sozlamalar/parol', methods=['POST'])
def sozlamalar_parol():
    data = request.get_json() or {}
    yangi_parol = data.get('yangi_parol', '').strip()
    if not yangi_parol:
        return jsonify({'xato': "Yangi parolni kiriting"}), 400
    db.parol_ornatish(yangi_parol)
    return jsonify({'ok': True})
