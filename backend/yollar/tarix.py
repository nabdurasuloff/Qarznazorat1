# -*- coding: utf-8 -*-
"""TARIX va TIZIMDAN OLDINGI HUJJATLAR — o'tmishdagi sikllarni ko'rish.

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

bp = Blueprint('tarix', __name__)


@bp.route('/api/tizimdan_oldin/qidirish', methods=['GET'])
def tizimdan_oldin_qidirish():
    """'Tizimdan oldin' papkasi ichida, ANKETA RAQAMI yoki MIJOZ NOMI
    matnini o'z ichiga olgan fayl nomlarini qidirib topadi — bu papkadagi
    hujjatlar avvalgi tizimda tartibsiz saqlangani uchun, aniq papka
    yo'lini bilmasdan ham qidirish orqali topish imkonini beradi."""
    soz = request.args.get('q', '').strip().lower()
    if not soz or len(soz) < 3:
        return jsonify({'xato': "Qidiruv so'zi kamida 3 ta belgidan iborat bo'lishi kerak"}), 400
    ildiz = tizimdan_oldingi_hujjatlar_papkasi()
    natija = []
    for root, dirs, files in os.walk(ildiz):
        for fayl in files:
            if soz in fayl.lower():
                toliq_yol = os.path.join(root, fayl)
                natija.append({
                    'fayl_nomi': fayl,
                    'papka': os.path.relpath(root, ildiz),
                    'toliq_yol': toliq_yol,
                })
        if len(natija) >= 200:
            break
    return jsonify({'natija': natija, 'papka_yoli': ildiz})


@bp.route('/api/anketa/tarix', methods=['GET'])
def anketa_tarix():
    """Berilgan anketa uchun BARCHA sikllar (xat yozuvlari) tarixini
    qaytaradi — har biri o'z Sud va MIB yig'ma jildi, va YAKUNIY natijasi
    (qanday tugagani) bilan birga. Bir necha marta sudga/MIBga
    chiqarilgan bo'lsa, barchasi shu yerda ko'rinadi."""
    anketa = request.args.get('anketa', '').strip()
    conn = db.get_conn()
    rows = conn.execute('SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id ASC', (anketa,)).fetchall()
    conn.close()

    natija = []
    for row in rows:
        x = dict(row)

        # Sud bosqichi holati va yakuniy natijasi
        if x.get('sud_qaror_natija') == 'bank_foydasiga':
            sud_natija = "✓ Bank foydasiga"
        elif x.get('sud_qaror_natija') == 'qisman':
            sud_natija = "≈ Qisman qondirildi"
        elif x.get('sud_qaror_natija') == 'rad_etildi':
            sud_natija = f"✕ Rad etildi ({x.get('sud_rad_sababi', '')})"
        elif x.get('sud_kiritilmadi_sababi'):
            sabab_nomlari = {'qarz_yopilgan': "Qarz to'liq yopilgan", 'mijoz_arizasi': "Mijozning yozma arizasi asosida",
                              'xodim_iltimosi': "Bank xodimi iltimosiga asosan",
                              'dpd_kamaygan_avtomatik': "Avtomatik: DPD/qarz kamaygani sababli"}
            sud_natija = f"✕ Sudga kiritilmadi ({sabab_nomlari.get(x['sud_kiritilmadi_sababi'], x['sud_kiritilmadi_sababi'])})"
        elif x.get('sud_holati') == 'topshirildi':
            sud_natija = "⏳ Sudga topshirilgan, qaror kutilmoqda"
        elif x.get('davo_ariza_holati') == 'olib_kelindi':
            sud_natija = "⏳ Sudga topshirilishi kutilmoqda"
        else:
            sud_natija = "—"

        # MIB bosqichi holati va yakuniy natijasi
        if x.get('mib_yakunlangan'):
            mib_natija = f"✓ Yakunlangan ({x.get('mib_yakunlash_sababi', '')})"
        elif x.get('mib_holati') == 'otkazildi':
            mib_natija = "⏳ Jarayonda"
        else:
            mib_natija = "—"

        natija.append({
            'xat_id': x['id'],
            'yaratilgan_sana': (x.get('yaratilgan_sana') or '')[:10],
            'xat_holati': x.get('holat'),
            'xat_fayl': x.get('fayl_yoli', ''),
            'davo_ariza_fayl': x.get('davo_ariza_fayl_yoli', ''),
            'davo_ariza_ish_raqami': x.get('davo_ariza_ish_raqami', ''),
            'sud_ish_raqami': x.get('sud_ish_raqami', ''),
            'sud_natija': sud_natija,
            'sud_yigma_jild_bor': bool(x.get('sud_yigma_jild_titul_fayl')),
            'mib_ish_raqami': x.get('mib_ish_raqami', ''),
            'mib_natija': mib_natija,
            'mib_yigma_jild_bor': bool(x.get('yigma_jild_titul_fayl')),
        })
    return jsonify({'tarix': natija})
