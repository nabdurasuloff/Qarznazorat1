# -*- coding: utf-8 -*-
"""PORTFEL va MIJOZLAR BAZASI — import, ro'yxat, qidiruv, fayl ko'rish.

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
    bugungi_papka, row_list, fayl_ruxsat_etilganmi,
)

bp = Blueprint('portfel', __name__)


@bp.route('/api/fayl_korish', methods=['GET'])
def fayl_korish():
    """Har qanday yaratilgan/yuklangan hujjatni (Word, PDF va h.k.) ko'rsatish
    yoki yuklab olish uchun umumiy endpoint."""
    from flask import send_file
    yol = request.args.get('yol', '')
    if not yol or not os.path.isfile(yol):
        return jsonify({'xato': 'Fayl topilmadi'}), 404

    # MUHIM XAVFSIZLIK: ilgari bu endpoint KOMPYUTERDAGI ISTALGAN faylni
    # berib yuborardi (server 0.0.0.0 da tinglagani uchun, bank tarmog'idagi
    # har kim bazaning o'zini ham, mijozlarning skanerlangan pasportlarini
    # ham yuklab olishi mumkin edi). Endi faqat dasturning O'Z papkalari
    # ichidagi fayllar beriladi.
    if not fayl_ruxsat_etilganmi(yol):
        return jsonify({'xato': "Bu fayl dastur papkalaridan tashqarida — ko'rsatib bo'lmaydi"}), 403
    return send_file(yol, as_attachment=request.args.get('yuklab_olish') == '1')


@bp.route('/api/portfel/import', methods=['POST'])
def portfel_import():
    import tempfile
    f = request.files.get('file')
    if not f:
        return jsonify({'xato': 'Fayl yuborilmadi'}), 400

    # MUHIM: f.save() o'rniga faylni to'liq xotiraga o'qib, aniq binary
    # rejimda, so'ng diskka mustahkam yozamiz (flush + fsync). Bu — ba'zi
    # Windows muhitlarida (masalan antivirus real-vaqt tekshiruvi fayl
    # yozilayotgan paytga to'g'ri kelib qolganda) faylning to'liq
    # yozilmasdan o'qilib qolishi ("incorrect header check" xatosi)
    # ehtimolini kamaytiradi.
    fayl_baytlari = f.read()
    if len(fayl_baytlari) < 100:
        return jsonify({'xato': "Yuklangan fayl juda kichik yoki bo'sh — qayta urinib ko'ring."}), 400
    # .xlsb (va .xlsx) fayllar aslida ZIP arxivi — to'g'ri fayl bo'lsa,
    # har doim 'PK' baytlari bilan boshlanishi kerak. Bu yerda xato
    # bo'lsa, foydalanuvchiga zlib'ning tushunarsiz xatosi o'rniga aniq,
    # tushunarli xabar ko'rsatamiz.
    if fayl_baytlari[:2] != b'PK':
        return jsonify({'xato': "Fayl to'liq yuklanmadi yoki buzilgan (ZIP formatiga mos emas). "
                                 "Iltimos, faylni qaytadan tanlab, qayta urinib ko'ring."}), 400

    with tempfile.NamedTemporaryFile(suffix='.xlsb', delete=False) as tmp:
        tmp.write(fayl_baytlari)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = tmp.name
    try:
        result = importer.import_portfel_xlsb(tmp_path)
        conn = db.get_conn()
        faol_soni = conn.execute("SELECT COUNT(*) c FROM portfel WHERE faol=1").fetchone()['c']
        faolsiz_soni = conn.execute("SELECT COUNT(*) c FROM portfel WHERE faol=0").fetchone()['c']
        conn.close()
        # MUHIM: portfel har yangilanganda shu kungi tahlil ko'rsatkichlari
        # avtomatik "suratga olinadi" — vaqt o'tishi bilan Tahlil bo'limida
        # haqiqiy tendensiya grafigini chizish uchun.
        try:
            db.tahlil_snapshot_saqlash()
        except Exception:
            pass  # Snapshot muvaffaqiyatsiz bo'lsa ham, import natijasi baribir qaytadi

        # MUHIM: portfel har yangilanganda, DPD chegarasidan pastga tushib
        # qolgan (lekin hali sudga chiqarilmagan) erta bosqich ishlarni
        # avtomatik tozalaymiz — shunda ular Chora ko'rishda noto'g'ri
        # ko'rinib qolmaydi, va DPD yana oshsa, toza holatdan boshlanadi.
        tozalangan_soni = 0
        try:
            tozalangan_soni = db.dpd_asosida_erta_bosqich_ishlarni_tozalash()
        except Exception:
            pass

        # MUHIM: Davo ariza tayyor (SSPdan qaytgan), lekin hali sudga
        # topshirilmagan ishlar uchun ham — DPD/qarz keskin kamaygan bo'lsa,
        # tizim ishni avtomatik yakunlaydi (asos hujjati bilan birga).
        sud_yakunlangan_soni = 0
        try:
            sud_yakunlangan_soni = db.dpd_asosida_sud_tayyor_ishlarni_yakunlash()
        except Exception:
            pass

        # MUHIM: avtomatik yopilgan ishlarni ham, DPD yana chegaradan
        # oshsa, avtomatik qayta ochamiz.
        qayta_ochilgan_soni = 0
        try:
            qayta_ochilgan_soni = db.dpd_asosida_sud_kiritilmagan_qayta_ochish()
        except Exception:
            pass

        # MUHIM: MIBda FAOL (hali yakunlanmagan) ishlar uchun ham — DPD
        # 'mib_toxtatish_dpd_chegara'dan (standart 30 kun) past bo'lib
        # qolgan, yoki qarz to'liq to'langan bo'lsa — tizim avtomatik
        # yakunlaydi (asos hujjati bilan birga).
        mib_avtomatik_yakunlangan = 0
        try:
            mib_avtomatik_yakunlangan = db.dpd_asosida_mib_avtomatik_yakunlash()
        except Exception:
            pass

        return jsonify({'jami_qator': result['jami_qator'], 'sheet': result.get('sheet', ''),
                         'faol_soni': faol_soni, 'faolsiz_soni': faolsiz_soni,
                         'avtomatik_tozalangan': tozalangan_soni,
                         'sud_avtomatik_yakunlangan': sud_yakunlangan_soni,
                         'sud_qayta_ochilgan': qayta_ochilgan_soni,
                         'mib_avtomatik_yakunlangan': mib_avtomatik_yakunlangan})
    except Exception as e:
        xabar = str(e)
        if 'decompress' in xabar.lower() or 'header check' in xabar.lower():
            xabar = ("Fayl o'qishda ichki xato: yuklangan .xlsb fayl to'liq yoki to'g'ri "
                     "yuklanmadi (buzilgan bo'lishi mumkin). Iltimos: 1) antivirusni vaqtincha "
                     "o'chirib yoki dastur papkasiga istisno qo'shib qayta urinib ko'ring, "
                     "2) faylni qayta saqlab (Excel'da 'Saqlash') qayta yuklang. "
                     f"(texnik tafsilot: {xabar})")
        return jsonify({'xato': xabar}), 400
    finally:
        os.remove(tmp_path)


@bp.route('/api/portfel/royxat', methods=['GET'])
def portfel_royxat():
    dpd_chegara = int(db.get_all_settings().get('dpd_chegara_kun', 45))
    rows = db.get_portfel_45_kun(dpd_chegara)
    natija = []
    for r in rows[:500]:
        # Bu ro'yxatda faqat mijoz TURI kerak — buni aniqlash uchun bazaga
        # murojaat qilish shart emas (ilgari har qator uchun 1-3 ta ulanish
        # ochilardi).
        turi = util.turi_kodidan(r.get('mijoz_turi_kodi'), r.get('mijoz_turi'))
        jami = (r.get('asosiy_qarz') or 0) + (r.get('foiz_qarz') or 0) + (r.get('jarima') or 0)
        natija.append({
            'anketa_raqami': r['anketa_raqami'], 'mijoz_nomi': r['mijoz_nomi'], 'turi': turi,
            'dpd': r.get('dpd_max', 0), 'jami_qarz': jami,
        })
    return jsonify({'royxat': natija, 'jami': len(rows)})


@bp.route('/api/mijozlar/stats', methods=['GET'])
def mijozlar_stats():
    conn = db.get_conn()
    jis = conn.execute("SELECT COUNT(*) c FROM mijozlar WHERE turi='jismoniy'").fetchone()['c']
    yur = conn.execute("SELECT COUNT(*) c FROM mijozlar WHERE turi='yuridik'").fetchone()['c']
    conn.close()
    return jsonify({'jismoniy': jis, 'yuridik': yur})


@bp.route('/api/mijozlar/import_txt', methods=['POST'])
def mijozlar_import_txt():
    import tempfile
    f = request.files.get('file')
    if not f:
        return jsonify({'xato': 'Fayl yuborilmadi'}), 400
    suffix = '.zip' if f.filename.lower().endswith('.zip') else '.txt'
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp_path = tmp.name
    # .txt fayllar ZIP tuzilishida bo'lmagani uchun, faqat .zip bo'lsa PK
    # header tekshiruvini yoqamiz.
    xato_natija = mustahkam_fayl_saqlash(f, tmp_path, ozbek_kengaytma_tekshiruvi=(suffix == '.zip'))
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    try:
        result = importer.import_clients_txt(tmp_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({'xato': str(e)}), 400
    finally:
        os.remove(tmp_path)


@bp.route('/api/mijozlar/excel_ustunlari', methods=['POST'])
def mijozlar_excel_ustunlari():
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
        cols, preview_df = importer.preview_mijozlar_columns(tmp_path)
        # Faylni vaqtincha saqlab qo'yamiz — keyingi (haqiqiy import) so'rovida qayta ishlatiladi
        doimiy_yol = os.path.join(hujjatlar_papkasi(), '_vaqtinchalik_mijozlar_excel.xlsx')
        os.makedirs(os.path.dirname(doimiy_yol), exist_ok=True)
        import shutil
        shutil.copy2(tmp_path, doimiy_yol)
        return jsonify({'ustunlar': cols, 'namuna': preview_df.fillna('').astype(str).values.tolist()})
    except Exception as e:
        return jsonify({'xato': str(e)}), 400
    finally:
        os.remove(tmp_path)


@bp.route('/api/mijozlar/excel_import', methods=['POST'])
def mijozlar_excel_import():
    data = request.get_json() or {}
    turi = data.get('turi')
    mapping = data.get('mapping', {})
    if not mapping.get('kalit') or not mapping.get('ism'):
        return jsonify({'xato': "Bog'lovchi ID va Ism ustunlari majburiy"}), 400
    fayl_yoli = os.path.join(hujjatlar_papkasi(), '_vaqtinchalik_mijozlar_excel.xlsx')
    if not os.path.exists(fayl_yoli):
        return jsonify({'xato': "Avval faylni yuklang (ustunlarni tanlash bosqichi)"}), 400
    try:
        result = importer.import_mijozlar_xlsx(fayl_yoli, turi, mapping)
        return jsonify(result)
    except Exception as e:
        return jsonify({'xato': str(e)}), 400
    finally:
        try:
            os.remove(fayl_yoli)
        except OSError:
            pass
