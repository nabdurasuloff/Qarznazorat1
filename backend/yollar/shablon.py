# -*- coding: utf-8 -*-
"""SHABLONLAR — Word shablonlarini ko'rish va yangilash.

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

bp = Blueprint('shablon', __name__)

# Shablon turlarining foydalanuvchiga tushunarli nomlari — xato
# xabarlarida "bu shablon aslida qaysi bo'limniki" deb aytish uchun.
SHABLON_NOMLARI = {
    'xat_shablon.docx': "Talabnoma → Xat shabloni",
    'sugurta_xabarnoma_shablon.docx': "Vafot etganlar → Sug'urta xabarnomasi",
    'yigma_jild_titul_shablon.docx': "MIB → Yig'ma jild tituli",
    'reestr_ssp_shablon.docx': "Davo ariza → SSPga reestr",
    'malumotnoma_topshirishda_shablon.docx': "Sud → Ma'lumotnoma (sudga topshirishda)",
    'malumotnoma_kun_shablon.docx': "Sud → Ma'lumotnoma (sud kuni)",
    'sud_yigma_jild_titul_shablon.docx': "Sud → Yig'ma jild tituli",
    'sugurta_tovon_ariza_shablon.docx': "Sug'urta → Tovon arizasi (MIB qarori)",
    'vafot_sugurta_tovon_shablon.docx': "Sug'urta → Tovon arizasi (vafot)",
    'sud_malumotnoma_qarzdorlik_shablon.docx': "Sud → MA'LUMOTNOMA (kredit qarzdorligi holati)",
    'sud_qoshimcha_malumotnoma_shablon.docx': "Sud → QO'SHIMCHA MA'LUMOTNOMA (qarz o'zgarishi)",
}


def _shablon_belgilarini_tekshir(vaqtinchalik_yol, fayl_nomi):
    """Yuklanayotgan shablon SHU bo'limga mos kelishini tekshiradi.

    MUHIM: ilgari istalgan shablonni istalgan bo'limga yuklash mumkin edi.
    Natijada hujjat yaratilganda, o'sha bo'lim generatori bilmagan belgilar
    {{...}} bo'lib qolar va yarmi to'ldirilmagan hujjat sudga ketishi
    mumkin edi. Endi bunday shablon QABUL QILINMAYDI va foydalanuvchiga
    uni QAYSI bo'limga yuklash kerakligi aytiladi."""
    yangi = letters.shablon_belgilari(vaqtinchalik_yol)
    if not yangi:
        return None  # belgisiz shablon (masalan bo'sh blanka) — ruxsat
    kutilgan = letters.standart_shablon_belgilari(fayl_nomi)
    if not kutilgan:
        return None  # standart shablon topilmadi — tekshirib bo'lmaydi
    notanish = sorted(yangi - kutilgan)
    if not notanish:
        return None

    mos_fayl, ball = letters.shablon_qaysi_bolimniki(yangi)
    izoh = ''
    if mos_fayl and mos_fayl != fayl_nomi and ball >= 0.5:
        izoh = ("\n\nBu shablon, ko'rinishidan, boshqa bo'limga tegishli: "
                + SHABLON_NOMLARI.get(mos_fayl, mos_fayl)
                + ". Iltimos, uni o'sha bo'limga yuklang.")
    return ("Bu shablon «" + SHABLON_NOMLARI.get(fayl_nomi, fayl_nomi) + "» bo'limiga mos kelmaydi.\n\n"
            "Undagi quyidagi belgilarni bu bo'lim to'ldira olmaydi — hujjatda "
            "{{...}} bo'lib qolib ketadi:\n• " + "\n• ".join(notanish[:12])
            + (f"\n• ... va yana {len(notanish) - 12} ta" if len(notanish) > 12 else '')
            + izoh)



def _shablon_maplanishi():
    return {
        'xat': (letters.TEMPLATE_PATH, 'xat_shablon.docx'),
        'sugurta': (letters.SUGURTA_XABARNOMA_TEMPLATE_PATH, 'sugurta_xabarnoma_shablon.docx'),
        'yigma_jild': (letters.YIGMA_JILD_TITUL_TEMPLATE_PATH, 'yigma_jild_titul_shablon.docx'),
        'reestr_ssp': (letters.REESTR_SSP_TEMPLATE_PATH, 'reestr_ssp_shablon.docx'),
        'malumotnoma_topshirishda': (letters.MALUMOTNOMA_TOPSHIRISHDA_TEMPLATE_PATH, 'malumotnoma_topshirishda_shablon.docx'),
        'malumotnoma_kun': (letters.MALUMOTNOMA_KUN_TEMPLATE_PATH, 'malumotnoma_kun_shablon.docx'),
        'sud_yigma_jild': (letters.SUD_YIGMA_JILD_TITUL_TEMPLATE_PATH, 'sud_yigma_jild_titul_shablon.docx'),
        'sugurta_tovon': (letters.SUGURTA_TOVON_TEMPLATE_PATH, 'sugurta_tovon_ariza_shablon.docx'),
        'vafot_sugurta_tovon': (letters.VAFOT_SUGURTA_TOVON_TEMPLATE_PATH, 'vafot_sugurta_tovon_shablon.docx'),
        # Sudga beriladigan rasmiy ma'lumotnomalar
        'sud_malumotnoma_qarzdorlik': (letters.SUD_MALUMOTNOMA_QARZDORLIK_TEMPLATE_PATH, 'sud_malumotnoma_qarzdorlik_shablon.docx'),
        'sud_qoshimcha_malumotnoma': (letters.SUD_QOSHIMCHA_MALUMOTNOMA_TEMPLATE_PATH, 'sud_qoshimcha_malumotnoma_shablon.docx'),
    }


@bp.route('/api/shablon/davo_turlari', methods=['GET'])
def shablon_davo_turlari():
    return jsonify({'turlari': letters.DAVO_ARIZA_NOMLARI})


@bp.route('/api/shablon/korish', methods=['GET'])
def shablon_korish():
    from flask import send_file
    turi = request.args.get('turi')
    davo_turi = request.args.get('davo_turi')
    if turi == 'davo' and davo_turi:
        fayl_nomi = letters.DAVO_ARIZA_TEMPLATES.get(davo_turi)
        if not fayl_nomi:
            return jsonify({'xato': "Noma'lum Davo ariza turi"}), 400
        standart = os.path.join(letters._base_dir(), 'templates', fayl_nomi)
    else:
        maplanish = _shablon_maplanishi()
        if turi not in maplanish:
            return jsonify({'xato': "Noma'lum shablon turi"}), 400
        standart, fayl_nomi = maplanish[turi]
    yol = letters._effektiv_shablon_yoli(standart, fayl_nomi)
    if not os.path.exists(yol):
        return jsonify({'xato': 'Shablon fayli topilmadi'}), 404
    return send_file(yol, as_attachment=True, download_name=fayl_nomi)


@bp.route('/api/shablon/yuklash', methods=['POST'])
def shablon_yuklash():
    turi = request.form.get('turi')
    davo_turi = request.form.get('davo_turi')
    f = request.files.get('file')
    if not f or not f.filename:
        return jsonify({'xato': 'Fayl yuborilmadi'}), 400
    if not f.filename.lower().endswith('.docx'):
        return jsonify({'xato': "Faqat .docx fayl qabul qilinadi"}), 400

    if turi == 'davo' and davo_turi:
        fayl_nomi = letters.DAVO_ARIZA_TEMPLATES.get(davo_turi)
        if not fayl_nomi:
            return jsonify({'xato': "Noma'lum Davo ariza turi"}), 400
    else:
        maplanish = _shablon_maplanishi()
        if turi not in maplanish:
            return jsonify({'xato': "Noma'lum shablon turi"}), 400
        _, fayl_nomi = maplanish[turi]

    # Shablon SHU bo'limga mos kelishini tekshiramiz (yuqoridagi izohga qarang).
    import tempfile as _tempfile
    baytlar = f.read()
    f.seek(0)
    with _tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as _tmp:
        _tmp.write(baytlar)
        _tekshiruv_yoli = _tmp.name
    try:
        mos_emas = _shablon_belgilarini_tekshir(_tekshiruv_yoli, fayl_nomi)
    except Exception:
        mos_emas = None  # fayl o'qilmasa, quyida mustahkam_fayl_saqlash xato beradi
    finally:
        try:
            os.remove(_tekshiruv_yoli)
        except Exception:
            pass
    if mos_emas and request.form.get('majburiy') != 'true':
        return jsonify({'xato': mos_emas, 'mos_emas': True}), 400

    papka = letters._shablon_papkasi()
    maqsad = os.path.join(papka, fayl_nomi)
    if os.path.exists(maqsad):
        zaxira = maqsad + '.' + datetime.datetime.now().strftime('%Y%m%d%H%M%S') + '.bak'
        import shutil
        shutil.copy2(maqsad, zaxira)
    try:
        xato_natija = mustahkam_fayl_saqlash(f, maqsad, ozbek_kengaytma_tekshiruvi=False)
        if xato_natija:
            return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    except Exception as e:
        return jsonify({'xato': f"Shablonni saqlashda xato: {e}. Papka: {papka}"}), 500

    # MUHIM: saqlangandan keyin, DARHOL qayta o'qib tasdiqlaymiz — shunda
    # "jimgina" muvaffaqiyatsiz yozish (masalan disk to'lib qolgan yoki
    # boshqa kutilmagan sabab) sodir bo'lsa ham, foydalanuvchi ANIQ
    # xato ko'radi, "muvaffaqiyatli" deb noto'g'ri o'ylab qolmaydi.
    if not os.path.exists(maqsad):
        return jsonify({'xato': f"Shablon saqlanmadi (fayl topilmadi): {maqsad}"}), 500
    return jsonify({'ok': True})


@bp.route('/api/shablon/qayta_tayyorlash', methods=['POST'])
def shablon_qayta_tayyorlash():
    """Yangi shablon yuklangandan keyin, hali yuborilmagan/olib kelinmagan
    hujjatlarni yangi shablon bilan qayta yaratadi."""
    data = request.get_json() or {}
    turi = data.get('turi')
    davo_turi = data.get('davo_turi')
    settings = db.get_all_settings()

    if turi == 'xat':
        pending = db.get_xatlar('tayyor')
        updated, xatolar = 0, []
        for xat in pending:
            try:
                prow = db.get_portfel_by_id(xat['portfel_id'])
                if not prow:
                    continue
                mijoz_turi_calc, mijoz = util.resolve_mijoz(prow)
                mijoz_ism = mijoz['ism'] if mijoz else prow.get('mijoz_nomi', '')
                mijoz_ism = util.mijoz_ism_hujjat_uchun(mijoz_ism, mijoz_turi_calc)
                mijoz_manzil = mijoz['manzil'] if mijoz else ''
                rahbar_ism = mijoz.get('rahbar_ism') if mijoz else ''
                letters.generate_letter(
                    output_path=xat['fayl_yoli'], xat_turi=xat['xat_turi'], mijoz_ism=mijoz_ism,
                    mijoz_manzil=mijoz_manzil, portfel_row=prow, settings=settings,
                    anketa_raqami=xat['anketa_raqami'], rahbar_ism=rahbar_ism,
                )
                updated += 1
            except Exception as e:
                xatolar.append(f"{xat.get('anketa_raqami')}: {e}")
        return jsonify({'yangilandi': updated, 'xatolar': xatolar})

    elif turi == 'davo' and davo_turi:
        pending = db.get_davo_ariza_pending_by_turi(davo_turi)
        updated, xatolar = 0, []
        for xat in pending:
            try:
                prow = db.get_portfel_by_id(xat['portfel_id'])
                if not prow:
                    continue
                mijoz_turi_calc, mijoz = util.resolve_mijoz(prow)
                taminot = db.get_taminot(xat['anketa_raqami'])
                try:
                    xat_sanasi = datetime.datetime.fromisoformat(xat['yaratilgan_sana']).strftime('%d.%m.%Y')
                except Exception:
                    xat_sanasi = ''
                letters.generate_davo_ariza_v2(
                    davo_turi, xat['davo_ariza_fayl_yoli'], prow, mijoz, taminot, settings,
                    xat_sanasi=xat_sanasi,
                    xat_turi_nomi=('Талабнома' if xat['xat_turi'] == 'Talabnoma' else 'Огохлантириш хати'),
                )
                updated += 1
            except Exception as e:
                xatolar.append(f"{xat.get('anketa_raqami')}: {e}")
        return jsonify({'yangilandi': updated, 'xatolar': xatolar})

    return jsonify({'xato': "Bu shablon turi uchun avtomatik qayta tayyorlash mavjud emas"}), 400
