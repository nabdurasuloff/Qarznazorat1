# -*- coding: utf-8 -*-
"""TAHLIL — portfel tahlili va huquqiy jarayon samaradorligi.

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

bp = Blueprint('tahlil', __name__)


@bp.route('/api/tahlil/jarayon', methods=['GET'])
def tahlil_jarayon_endpoint():
    """HUQUQIY JARAYON TAHLILI: voronka, bosqich davomiyligi, undirish
    samaradorligi, oylik dinamika va harakatlar samaradorligi."""
    try:
        return jsonify(tj.toliq_hisobot())
    except Exception as e:
        return jsonify({'xato': f"Tahlilni hisoblashda xato: {e}"}), 500


@bp.route('/api/tahlil/jarayon_excel', methods=['GET'])
def tahlil_jarayon_excel():
    """Jarayon tahlilini ko'p varaqli Excel hisoboti qilib chiqaradi."""
    import tempfile
    from flask import send_file
    import pandas as pd
    h = tj.toliq_hisobot()
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    with pd.ExcelWriter(tmp_path) as yozuvchi:
        pd.DataFrame([{'Bosqich': v['nomi'], 'Ishlar soni': v['soni'],
                       'Qarz summasi': v['summa']} for v in h['voronka']]
                     ).to_excel(yozuvchi, sheet_name='Voronka', index=False)
        pd.DataFrame([{"O'tish": d['nomi'], 'Ishlar soni': d['soni'],
                       "O'rtacha kun": d['ortacha'], 'Mediana kun': d['mediana'],
                       'Eng uzun kun': d['eng_uzun']} for d in h['davomiylik']]
                     ).to_excel(yozuvchi, sheet_name='Davomiylik', index=False)
        pd.DataFrame([{'Manba': m['nomi'], 'Summa': m['summa'], 'Ulush %': m['ulush']}
                      for m in h['undirish']['manbalar']]
                     ).to_excel(yozuvchi, sheet_name='Undirish', index=False)
        pd.DataFrame([{'Oy': d['oy'], 'Yuborilgan xatlar': d['xat'],
                       'Sudga kiritilgan': d['sud'], "MIBga o'tkazilgan": d['mib'],
                       'Undirilgan summa': d['undirilgan']} for d in h['dinamika']]
                     ).to_excel(yozuvchi, sheet_name='Oylik dinamika', index=False)
        if h['harakatlar']:
            pd.DataFrame([{'Harakat turi': a['amal_turi'], 'Soni': a['soni'],
                           'Jami summa': a['summa'], "O'rtacha": a['ortacha']}
                          for a in h['harakatlar']]
                         ).to_excel(yozuvchi, sheet_name='MIB harakatlari', index=False)
    return send_file(tmp_path, as_attachment=True,
                     download_name='huquqiy_jarayon_tahlili.xlsx')


@bp.route('/api/tahlil/umumiy', methods=['GET'])
def tahlil_umumiy():
    return jsonify(db.get_umumiy_tahlil())


@bp.route('/api/tahlil/tarix', methods=['GET'])
def tahlil_tarix():
    return jsonify({'tarix': db.get_tahlil_tarixi()})


@bp.route('/api/tahlil/tarmoq_mijozlari', methods=['GET'])
def tahlil_tarmoq_mijozlari():
    tarmoq = request.args.get('tarmoq', '').strip()
    conn = db.get_conn()
    if tarmoq == "Noma'lum":
        rows = conn.execute(
            "SELECT anketa_raqami, mijoz_nomi, mijoz_turi, ead, stage FROM portfel "
            "WHERE faol=1 AND (tarmoq IS NULL OR TRIM(tarmoq)='') ORDER BY ead DESC LIMIT 300").fetchall()
    else:
        rows = conn.execute(
            "SELECT anketa_raqami, mijoz_nomi, mijoz_turi, ead, stage FROM portfel "
            "WHERE faol=1 AND TRIM(tarmoq)=? ORDER BY ead DESC LIMIT 300", (tarmoq,)).fetchall()
    conn.close()
    return jsonify({'mijozlar': [dict(r) for r in rows]})


@bp.route('/api/tahlil/hisobot_yuklab_olish', methods=['GET'])
def tahlil_hisobot_yuklab_olish():
    import tempfile
    from flask import send_file
    tahlil = db.get_umumiy_tahlil()
    settings = db.get_all_settings()
    formatv = request.args.get('format', 'word')
    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
        tmp_path = tmp.name
    letters.generate_tahlil_hisoboti(tmp_path, tahlil, settings)
    if formatv == 'pdf':
        try:
            tmp_path = letters.convert_docx_to_pdf(tmp_path, delete_docx=True)
            return send_file(tmp_path, as_attachment=True, download_name='tahlil_hisoboti.pdf')
        except Exception as e:
            return jsonify({'xato': f"PDF'ga o'tkazishda xato (MS Word talab qilinadi): {e}"}), 400
    return send_file(tmp_path, as_attachment=True, download_name='tahlil_hisoboti.docx')
