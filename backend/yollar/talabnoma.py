# -*- coding: utf-8 -*-
"""TALABNOMA — ogohlantirish xatlarini tayyorlash va yuborish.

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

bp = Blueprint('talabnoma', __name__)


@bp.route('/api/talabnoma/qayta_xat_eslatmalari', methods=['GET'])
def talabnoma_qayta_xat_eslatmalari():
    """To'lov muddati o'tgan, LEKIN hech qanday chora (Davo ariza)
    ko'rilmagan mijozlar ro'yxati — yangi xat tayyorlab yuborish
    TAVSIYA etiladi (avtomatik yaratilmaydi)."""
    return jsonify({'royxat': db.xat_qayta_yuborish_eslatmalari()})


@bp.route('/api/talabnoma/royxat', methods=['GET'])
def talabnoma_royxat():
    """DPD chegarasidan (Sozlamalar -> Talabnoma -> 'Tahlil uchun DPD
    chegarasi') yuqori, xat yaratilmagan/muddati o'tgan mijozlar ro'yxati."""
    only_new = request.args.get('only_new', 'true') == 'true'
    dpd_chegara = int(db.get_all_settings().get('dpd_chegara_kun', 45))
    rows = db.get_portfel_45_kun(dpd_chegara)

    # MUHIM (tezlik): har bir anketa uchun ALOHIDA baza so'rovi (6000+
    # marta) qilish o'rniga — mavjud barcha anketalarni BITTA so'rovda
    # olib, xotirada (Python to'plami) tekshiramiz. Bu ro'yxatni
    # sekundlardan millisekundlargacha tezlashtiradi.
    conn = db.get_conn()
    mavjud_anketalar = {r['anketa_raqami'] for r in
                         conn.execute('SELECT DISTINCT anketa_raqami FROM xatlar').fetchall()}
    conn.close()

    # MUHIM (tezlik): bu ro'yxatda mijozning FAQAT topilgan-topilmagani
    # kerak, uning to'liq ma'lumoti emas. Ilgari har bir qator uchun
    # `util.resolve_mijoz()` chaqirilib, u 1-3 marta yangi baza ulanishini
    # ochardi — 6 000 qatorda bu 20 000 gacha ulanish va ~5 sekund demakdi.
    # Endi mijoz kalitlari bir marta o'qib olinadi.
    mijoz_kalitlari = db.mijoz_kalitlari_toplami()

    natija = []
    for r in rows:
        turi = util.turi_kodidan(r.get('mijoz_turi_kodi'), r.get('mijoz_turi'))
        mijoz = any((turi, k) in mijoz_kalitlari for k in util.kalit_candidates(r))
        mavjud = r['anketa_raqami'] in mavjud_anketalar
        if only_new and mavjud:
            continue
        jami = (r.get('asosiy_qarz') or 0) + (r.get('foiz_qarz') or 0) + (r.get('jarima') or 0)
        natija.append({
            'id': r['id'],
            'anketa_raqami': r['anketa_raqami'],
            'mijoz_nomi': r['mijoz_nomi'],
            'turi': turi,
            'dpd': r.get('dpd_max', 0),
            'jami_qarz': jami,
            'mijoz_topildi': bool(mijoz),
            'xat_mavjud': mavjud,
        })
    return jsonify({'royxat': natija, 'jami': len(rows)})


@bp.route('/api/talabnoma/xat_yaratish', methods=['POST'])
def talabnoma_xat_yaratish():
    """Belgilangan anketa(lar) uchun xat(lar) yaratadi — 'Tayyor' holatida qoladi."""
    data = request.get_json() or {}
    anketalar = data.get('anketalar', [])
    fayl_format = data.get('format', 'docx')  # 'docx' | 'pdf'
    settings = db.get_all_settings()

    yaratildi, otkazib_yuborildi, xatolar = 0, 0, []
    for anketa in anketalar:
        if not db.xat_qayta_yuborish_mumkinmi(anketa):
            otkazib_yuborildi += 1
            continue
        prow_list = db.get_portfel_by_anketa(anketa)
        if not prow_list:
            xatolar.append(f"{anketa}: portfelda topilmadi")
            continue
        prow = prow_list[0]
        try:
            turi, mijoz = util.resolve_mijoz(prow)
            xat_turi = 'Talabnoma' if turi in ('yuridik', 'yatt') else 'Ogohlantirish'
            mijoz_ism = mijoz['ism'] if mijoz else prow.get('mijoz_nomi', '')
            mijoz_manzil = mijoz['manzil'] if mijoz else ''
            rahbar_ism = mijoz.get('rahbar_ism') if mijoz else ''
            mijoz_ism_rasmiy = util.mijoz_ism_hujjat_uchun(mijoz_ism, turi)

            out_dir = bugungi_papka('Xat')
            fname = f"{letters.safe_filename(mijoz_ism)}_{letters.safe_filename(anketa)}_{xat_turi}.docx"
            out_path = os.path.join(out_dir, fname)

            letters.generate_letter(
                output_path=out_path, xat_turi=xat_turi, mijoz_ism=mijoz_ism_rasmiy,
                mijoz_manzil=mijoz_manzil, portfel_row=prow, settings=settings,
                anketa_raqami=anketa, rahbar_ism=rahbar_ism,
            )

            # MUHIM: agar foydalanuvchi PDF formatini tanlagan bo'lsa,
            # Word hujjatini PDF'ga aylantiramiz (Windows + MS Word talab
            # qilinadi) va asl xat yozuvida ANIQ PDF fayl yo'li saqlanadi.
            if fayl_format == 'pdf':
                try:
                    pdf_path = out_path[:-5] + '.pdf'
                    letters.convert_docx_to_pdf(out_path, pdf_path, delete_docx=True)
                    out_path = pdf_path
                except Exception as e:
                    xatolar.append(f"{anketa}: PDF'ga aylantirishda xato — {e}. Word (.docx) sifatida saqlandi.")

            muddat_kun = int(settings.get('eslatma_muddati_kun', 3))
            db.create_xat(
                portfel_id=prow['id'], anketa_raqami=anketa, mijoz_nomi=mijoz_ism, mijoz_turi=turi,
                xat_turi=xat_turi, fayl_yoli=out_path, muddat_kun=muddat_kun,
            )
            yaratildi += 1
        except Exception as e:
            xatolar.append(f"{anketa}: {e}")

    return jsonify({'yaratildi': yaratildi, 'otkazib_yuborildi': otkazib_yuborildi, 'xatolar': xatolar})


@bp.route('/api/talabnoma/xatlar_hisoboti', methods=['GET'])
def talabnoma_xatlar_hisoboti():
    """Yuborilgan barcha xatlar tarixi ('so'nggi qilingan ishlar')."""
    xatlar = db.get_xatlar()
    natija = []
    for x in xatlar[:500]:
        natija.append({
            'id': x['id'], 'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'],
            'mijoz_turi': x['mijoz_turi'], 'xat_turi': x['xat_turi'], 'holat': x['holat'],
            'yaratilgan_sana': x.get('yaratilgan_sana', ''), 'yuborilgan_sana': x.get('yuborilgan_sana', ''),
            'fayl_yoli': x.get('fayl_yoli', ''),
        })
    return jsonify({'royxat': natija, 'jami': len(xatlar)})


@bp.route('/api/talabnoma/xat_qidirish', methods=['GET'])
def talabnoma_xat_qidirish():
    anketa = request.args.get('anketa', '').strip()
    conn = db.get_conn()
    rows = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami LIKE ?", (f'%{anketa}%',)).fetchall()
    conn.close()
    return jsonify({'ids': [r['id'] for r in rows]})


@bp.route('/api/talabnoma/xat_yuborildi_belgilash_ommaviy', methods=['POST'])
def talabnoma_xat_yuborildi_belgilash_ommaviy():
    data = request.get_json() or {}
    ids = data.get('ids', [])
    for xat_id in ids:
        db.mark_xat_yuborildi(xat_id)
    return jsonify({'ok': True, 'yangilandi': len(ids)})


@bp.route('/api/talabnoma/xat_ochirish', methods=['POST'])
def talabnoma_xat_ochirish():
    data = request.get_json() or {}
    ids = data.get('ids', [])
    conn = db.get_conn()
    rows = conn.execute(f"SELECT id, holat FROM xatlar WHERE id IN ({','.join('?' * len(ids))})", ids).fetchall() if ids else []
    conn.close()
    yuborilgan = [r['id'] for r in rows if r['holat'] == 'yuborildi']
    ochiriladigan = [r['id'] for r in rows if r['holat'] != 'yuborildi']
    n = db.delete_xatlar(ochiriladigan) if ochiriladigan else 0
    return jsonify({'ochirildi': n, 'otkazib_yuborildi': len(yuborilgan)})


@bp.route('/api/talabnoma/barcha_tayyor_ochirish', methods=['POST'])
def talabnoma_barcha_tayyor_ochirish():
    ids = db.get_xatlar_ids_by_holat('tayyor') + db.get_xatlar_ids_by_holat('muddati_otgan')
    if not ids:
        return jsonify({'ochirildi': 0})
    n = db.delete_xatlar(ids)
    return jsonify({'ochirildi': n})


@bp.route('/api/talabnoma/dublikatlarni_tozalash', methods=['POST'])
def talabnoma_dublikatlarni_tozalash():
    dup = db.get_duplicate_xat_anketalar()
    if not dup:
        return jsonify({'topildi': 0, 'ochirildi': 0})
    n = db.tozala_duplikat_xatlar()
    return jsonify({'topildi': len(dup), 'ochirildi': n})


@bp.route('/api/talabnoma/qidirish', methods=['GET'])
def talabnoma_qidirish():
    anketa = request.args.get('anketa', '').strip()
    if not anketa:
        return jsonify({'royxat': []})
    rows = db.get_portfel_by_anketa(anketa)
    natija = []
    for r in rows:
        turi, mijoz = util.resolve_mijoz(r)
        mavjud = db.xat_mavjudmi(r['anketa_raqami'])
        jami = (r.get('asosiy_qarz') or 0) + (r.get('foiz_qarz') or 0) + (r.get('jarima') or 0)
        natija.append({
            'id': r['id'], 'anketa_raqami': r['anketa_raqami'], 'mijoz_nomi': r['mijoz_nomi'],
            'turi': turi, 'dpd': r.get('dpd_max', 0), 'jami_qarz': jami,
            'mijoz_topildi': bool(mijoz), 'xat_mavjud': mavjud,
        })
    return jsonify({'royxat': natija})


@bp.route('/api/talabnoma/excel_eksport', methods=['POST'])
def talabnoma_excel_eksport():
    from flask import send_file
    import io
    data = request.get_json() or {}
    anketalar = data.get('anketalar', [])
    rows = []
    for anketa in anketalar:
        prow_list = db.get_portfel_by_anketa(anketa)
        if not prow_list:
            continue
        prow = prow_list[0]
        turi, mijoz = util.resolve_mijoz(prow)
        xat_turi = 'Talabnoma' if turi in ('yuridik', 'yatt') else 'Ogohlantirish'
        jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
        rows.append({
            'anketa_raqami': anketa, 'mijoz_nomi': prow.get('mijoz_nomi', ''), 'turi': turi,
            'manzil': mijoz.get('manzil', '') if mijoz else '', 'telefon': mijoz.get('telefon', '') if mijoz else '',
            'dpd_max': prow.get('dpd_max', 0), 'jami_qarz': jami,
            'jami_berilgan_summa': prow.get('jami_berilgan_summa', ''), 'xat_turi': xat_turi,
        })
    buf = io.BytesIO()
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    importer.export_tahlil_excel(rows, tmp_path)
    return send_file(tmp_path, as_attachment=True, download_name='talabnoma_royxati.xlsx')


@bp.route('/api/talabnoma/excel_import', methods=['POST'])
def talabnoma_excel_import():
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
        result = importer.import_manzil_updates(tmp_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({'xato': str(e)}), 400
    finally:
        os.remove(tmp_path)
