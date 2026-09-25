# -*- coding: utf-8 -*-
"""BOSH SAHIFA va REJA — umumiy ko'rsatkichlar, kunlik reja.

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
    bugungi_papka, row_list, AMAL_TURLARI_MAP,
)

bp = Blueprint('dashboard', __name__)


@bp.route('/api/dashboard/summary', methods=['GET'])
def dashboard_summary():
    conn = db.get_conn()
    portfel_soni = conn.execute("SELECT COUNT(*) c FROM portfel WHERE faol=1").fetchone()['c']
    conn.close()

    dpd_chegara = int(db.get_all_settings().get('dpd_chegara_kun', 45))
    kun45 = len(db.get_portfel_45_kun(dpd_chegara))
    yuborilmagan = len(db.get_xatlar('tayyor'))
    muddati_otgan = len(db.get_xatlar('muddati_otgan'))

    bugun = __import__('datetime').date.today().isoformat()
    conn = db.get_conn()
    bugun_yaratilgan = conn.execute(
        "SELECT COUNT(*) c FROM xatlar WHERE date(yaratilgan_sana)=?", (bugun,)).fetchone()['c']
    bugun_yuborilgan = conn.execute(
        "SELECT COUNT(*) c FROM xatlar WHERE date(yuborilgan_sana)=?", (bugun,)).fetchone()['c']
    conn.close()

    toliq = db.get_tarmoq_stage3_breakdown_toliq(limit=8)

    def xavfsiz(fn, standart=0):
        try:
            return fn()
        except Exception:
            return standart

    davo_muddati_otgan = xavfsiz(lambda: len(db.get_davo_ariza_muddati_otganlar()))
    sud_muddati_otgan = xavfsiz(lambda: len(db.get_sud_topshirish_muddati_otganlar()))
    mib_harakatsiz = xavfsiz(lambda: len(db.get_mib_harakatsizlar()))
    chora_soni = xavfsiz(lambda: len(db.get_chora_korish_royxati()))
    sugurta_kutilmoqda = xavfsiz(lambda: len(db.get_sugurta_javob_kutilayotganlar()))
    qayta_xat_kerak = xavfsiz(lambda: len(db.xat_qayta_yuborish_eslatmalari()))

    return jsonify({
        'portfeldagi_kreditlar': portfel_soni,
        'kun45_otgan': kun45,
        'yuborilmagan_xatlar': yuborilmagan,
        'muddati_otgan_xatlar': muddati_otgan,
        'bugun_yaratilgan': bugun_yaratilgan,
        'bugun_yuborilgan': bugun_yuborilgan,
        'davo_muddati_otgan': davo_muddati_otgan,
        'sud_muddati_otgan': sud_muddati_otgan,
        'mib_harakatsiz': mib_harakatsiz,
        'chora_soni': chora_soni,
        'sugurta_kutilmoqda': sugurta_kutilmoqda,
        'qayta_xat_kerak': qayta_xat_kerak,
        'tarmoq_jadval': toliq,
    })


@bp.route('/api/dashboard/qidirish', methods=['GET'])
def dashboard_qidirish():
    anketa = request.args.get('anketa', '').strip()
    natija = db.get_mijoz_holati_anketa_boyicha(anketa)
    if not natija:
        return jsonify({'topildi': False})
    natija_out = []
    for item in natija:
        prow = item['portfel']
        xat = item['xat']
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi'))
        jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
        bosqich = "Hali xat yaratilmagan"
        if xat:
            if xat.get('mib_holati') == 'otkazildi':
                bosqich = "✓ MIBga o'tkazilgan" + (" (yakunlangan)" if xat.get('mib_yakunlangan') else "")
            elif xat.get('sud_holati') == 'topshirildi':
                bosqich = "✓ Sudga topshirilgan"
            elif xat.get('sud_kiritilmadi_sababi'):
                sabab_nomlari = {'qarz_yopilgan': "Qarz to'liq yopilgan",
                                  'mijoz_arizasi': "Mijozning yozma arizasi asosida",
                                  'xodim_iltimosi': "Bank xodimi iltimosiga asosan",
                                  'dpd_kamaygan_avtomatik': "Avtomatik: DPD/qarz kamaygani sababli"}
                bosqich = ("✕ Sudga kiritilmadi: " +
                           sabab_nomlari.get(xat['sud_kiritilmadi_sababi'], xat['sud_kiritilmadi_sababi']))
            elif xat.get('davo_ariza_holati') == 'olib_kelindi':
                bosqich = "✓ Davo ariza (SSPdan olib kelingan)"
            elif xat.get('davo_ariza_fayl_yoli'):
                bosqich = "Davo ariza tayyorlangan"
            else:
                bosqich = {'tayyor': 'Xat tayyor (yuborilmagan)', 'yuborildi': '✓ Xat yuborilgan',
                           'muddati_otgan': "⚠ Xat muddati o'tgan"}.get(xat.get('holat'), xat.get('holat', ''))
        natija_out.append({
            'anketa_raqami': prow['anketa_raqami'], 'mijoz_nomi': prow.get('mijoz_nomi', ''),
            'turi': turi, 'jami_qarz': jami, 'bosqich': bosqich,
            'mib_ish_raqami': xat.get('mib_ish_raqami', '') if xat else '',
            'oxirgi_mib_amal': AMAL_TURLARI_MAP.get(item['oxirgi_mib_amal']['amal_turi'], '') if item.get('oxirgi_mib_amal') else '',
            'xat_fayl': xat.get('fayl_yoli', '') if xat else '',
            'davo_fayl': xat.get('davo_ariza_fayl_yoli', '') if xat else '',
            'sud_buyrugi_fayl': xat.get('sud_buyrugi_fayl', '') if xat else '',
            'ijro_varaqasi_fayl': xat.get('ijro_varaqasi_fayl', '') if xat else '',
            'yakunlash_fayl': xat.get('mib_yakunlash_hujjati_fayl', '') if xat else '',
            'yigma_jild_fayl': xat.get('yigma_jild_titul_fayl', '') if xat else '',
        })
    return jsonify({'topildi': True, 'natija': natija_out})


@bp.route('/api/dashboard/songgi_harakatlar', methods=['GET'])
def dashboard_songgi_harakatlar():
    xatlar = db.get_xatlar()[:15]
    status_labels = {'tayyor': 'Tayyor', 'yuborildi': "✓ Yuborildi", 'muddati_otgan': "⚠ Muddati o'tgan"}
    natija = []
    for r in xatlar:
        try:
            yaratilgan_sana = datetime.datetime.fromisoformat(r['yaratilgan_sana']).strftime('%d.%m.%Y %H:%M')
        except Exception:
            yaratilgan_sana = r.get('yaratilgan_sana', '') or ''

        # MUHIM: ko'rsatiladigan sana — mijozning ENG SO'NGGI (joriy)
        # bosqichiga tegishli sana bo'lishi kerak, doim xatning yaratilgan
        # sanasi emas — aks holda mijoz MIB bosqichiga o'tgan bo'lsa ham,
        # oyning boshidagi eski xat sanasi ko'rsatilib, chalkashlik
        # tug'dirardi.
        if r.get('mib_holati') == 'otkazildi':
            holat_matni = "✓ MIBga o'tkazilgan" + (" (yakunlangan)" if r.get('mib_yakunlangan') else "")
            sana = r.get('mib_otkazilgan_sana') or yaratilgan_sana
        elif r.get('sud_holati') == 'topshirildi':
            holat_matni = "✓ Sudga topshirilgan"
            sana = r.get('sud_topshirilgan_sana') or yaratilgan_sana
        elif r.get('sud_kiritilmadi_sababi'):
            holat_matni = "✕ Sudga kiritilmadi"
            sana = r.get('sud_kiritilmadi_sana') or yaratilgan_sana
        elif r.get('davo_ariza_holati') == 'olib_kelindi':
            holat_matni = "✓ Davo ariza (SSPdan olib kelingan)"
            sana = r.get('davo_ariza_imzo_sana') or yaratilgan_sana
        elif r.get('davo_ariza_fayl_yoli'):
            holat_matni = "Davo ariza tayyorlangan"
            sana = yaratilgan_sana
        else:
            holat_matni = status_labels.get(r['holat'], r['holat'])
            sana = yaratilgan_sana

        natija.append({
            'sana': sana, 'yaratilgan_sana': yaratilgan_sana,
            'anketa_raqami': r.get('anketa_raqami', ''), 'mijoz_nomi': r['mijoz_nomi'],
            'xat_turi': r['xat_turi'], 'holat_matni': holat_matni,
            # Mijozning BUTUN jarayoni davomida yaratilgan/yuklangan barcha
            # hujjatlar — nafaqat dastlabki xat, balki keyingi bosqichlar
            # (Sud buyrug'i, Ijro varaqasi, Yakunlash asosi) ham.
            'xat_fayl': r.get('fayl_yoli', ''),
            'davo_fayl': r.get('davo_ariza_fayl_yoli', ''),
            'sud_buyrugi_fayl': r.get('sud_buyrugi_fayl', ''),
            'ijro_varaqasi_fayl': r.get('ijro_varaqasi_fayl', ''),
            'yakunlash_fayl': r.get('mib_yakunlash_hujjati_fayl', ''),
        })
    return jsonify({'royxat': natija})


@bp.route('/api/reja/kunlik', methods=['GET'])
def reja_kunlik():
    return jsonify(db.get_ish_kuni_rejasi())


@bp.route('/api/reja/tarmoq', methods=['GET'])
def reja_tarmoq():
    conn = db.get_conn()
    rows = conn.execute('''
        SELECT COALESCE(NULLIF(TRIM(p.tarmoq), ''), "Noma'lum") AS tarmoq,
               COUNT(DISTINCT x.id) AS xat_soni,
               SUM(CASE WHEN x.holat IN ('yuborildi','muddati_otgan') THEN 1 ELSE 0 END) AS yuborilgan_soni,
               SUM(CASE WHEN x.davo_ariza_fayl_yoli IS NOT NULL THEN 1 ELSE 0 END) AS davo_soni,
               SUM(CASE WHEN x.sud_holati='topshirildi' THEN 1 ELSE 0 END) AS sud_soni,
               SUM(CASE WHEN x.mib_holati='otkazildi' THEN 1 ELSE 0 END) AS mib_soni
        FROM xatlar x
        LEFT JOIN portfel p ON p.id = x.portfel_id
        GROUP BY tarmoq ORDER BY xat_soni DESC
    ''').fetchall()
    conn.close()
    return jsonify({'tarmoq': [dict(r) for r in rows]})
