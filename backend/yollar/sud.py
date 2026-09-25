# -*- coding: utf-8 -*-
"""SUD ISHLARI — sudga topshirish, yig'ma jild, sud kunlari, xarajatlar.

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
    bugungi_papka, row_list, yigma_jild_javobi,
)

bp = Blueprint('sud', __name__)


def _sana_dt(qiymat):
    """Turli ko'rinishdagi sanani (kk.oo.yyyy yoki ISO) date obyektiga
    aylantiradi. O'qib bo'lmasa None qaytaradi."""
    if not qiymat:
        return None
    matn = str(qiymat).strip()
    for shakl in ('%d.%m.%Y', '%Y-%m-%d', '%d-%m-%Y', '%d/%m/%Y'):
        try:
            return datetime.datetime.strptime(matn[:10], shakl).date()
        except ValueError:
            continue
    try:
        return datetime.datetime.fromisoformat(matn).date()
    except Exception:
        return None


@bp.route('/api/sud/topshirish_kerak', methods=['GET'])
def sud_topshirish_kerak():
    xatlar = db.get_sud_topshirish_kerak()
    natija = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
        sud_nomi = "Iqtisodiy sud" if turi in ('yuridik', 'yatt') else "Fuqarolik sudi"
        asosiy = x.get('davo_summasi_asosiy') or 0
        foiz = x.get('davo_summasi_foiz') or 0
        jarima = x.get('davo_summasi_jarima') or 0
        natija.append({
            'xat_id': x['id'], 'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'],
            'turi': turi, 'sud_nomi': sud_nomi, 'jami': asosiy + foiz + jarima,
            'asosiy': asosiy, 'foiz': foiz, 'jarima': jarima,
            'imzo_sana': x.get('davo_ariza_imzo_sana', ''),
            'yigma_jild_bor': bool(x.get('sud_yigma_jild_titul_fayl')),
            'ruxsat_berilgan': bool(x.get('sud_hujjatlar_ruxsat')),
        })
    return jsonify({'royxat': natija})


@bp.route('/api/sud/topshirish_kerak_excel', methods=['GET'])
def sud_topshirish_kerak_excel():
    """'SSPdan o'tib sudga jo'natiladiganlar' ro'yxatini, jumladan
    'Ruxsat berilganmi' ustuni bilan, Excel qilib chiqaradi."""
    import tempfile
    from flask import send_file
    import pandas as pd
    xatlar = db.get_sud_topshirish_kerak()
    if not xatlar:
        return jsonify({'xato': "Hozircha ro'yxat bo'sh"}), 400
    rows = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
        pinfl_stir = (prow.get('pinfl') or prow.get('stir') or '') if prow else ''
        asosiy = x.get('davo_summasi_asosiy') or 0
        foiz = x.get('davo_summasi_foiz') or 0
        jarima = x.get('davo_summasi_jarima') or 0
        rows.append({
            'Anketa raqami': x['anketa_raqami'], 'PINFL/STIR': pinfl_stir, 'Mijoz nomi': x['mijoz_nomi'],
            'Turi': turi, 'Jami qarzdorlik': asosiy + foiz + jarima,
            'Palatadan kelgan sana': x.get('davo_ariza_imzo_sana', '') or '',
            'Yig\'ma jild yaratilganmi': "Ha" if x.get('sud_yigma_jild_titul_fayl') else "Yo'q",
            'Sudga yuborishga ruxsat berilganmi': "Ha" if x.get('sud_hujjatlar_ruxsat') else "Yo'q",
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='sudga_jonatiladiganlar.xlsx')


@bp.route('/api/sud/ruxsat_berilganlar_excel', methods=['GET'])
def sud_ruxsat_berilganlar_excel():
    """Ruxsat berilgan BARCHA mijozlar ro'yxati — sudga ALLAQACHON
    topshirilganmi yoki hali topshirilishni kutayotganmi, farqi yo'q.
    Bu, 'SSPdan o'tib sudga jo'natiladiganlar' ro'yxatidan farqli
    o'laroq, sudga topshirilgach ham ro'yxatdan chiqib ketmaydi."""
    import tempfile
    from flask import send_file
    import pandas as pd
    conn = db.get_conn()
    rows = conn.execute('''
        SELECT * FROM xatlar WHERE sud_hujjatlar_ruxsat=1
          AND (arxivlangan IS NULL OR arxivlangan=0)
        ORDER BY id DESC
    ''').fetchall()
    conn.close()
    if not rows:
        return jsonify({'xato': "Hozircha ruxsat berilgan ish yo'q"}), 400
    data_rows = []
    for row in rows:
        x = dict(row)
        prow = db.get_portfel_by_id(x['portfel_id'])
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
        pinfl_stir = (prow.get('pinfl') or prow.get('stir') or '') if prow else ''
        if x.get('sud_holati') == 'topshirildi':
            holat = f"✓ Sudga topshirilgan (ish №{x.get('sud_ish_raqami', '')}, {x.get('sud_topshirilgan_sana', '')})"
        else:
            holat = "⏳ Sudga topshirilishi kutilmoqda"

        # MUHIM: mijozning ta'minoti (kafillik/garov) haqida ma'lumot —
        # "Davo ariza" bo'limida kiritilgan davo_taminot jadvalidan olinadi.
        taminot = db.get_taminot(x['anketa_raqami']) or {}
        taminot_turi_nomi = {'yoq': "Ta'minotsiz", 'kafillik': 'Kafillik', 'garov': 'Garov',
                              'kafillik_garov': 'Kafillik + Garov'}.get(taminot.get('taminot_turi', ''), '—')
        taminot_tafsilot_qismlar = []
        if taminot.get('kafil_ism'):
            taminot_tafsilot_qismlar.append(f"Kafil: {taminot['kafil_ism']}")
        if taminot.get('garov_tavsifi'):
            taminot_tafsilot_qismlar.append(f"Garov: {taminot['garov_tavsifi']}")
        taminot_tafsilot = "; ".join(taminot_tafsilot_qismlar) or '—'

        data_rows.append({
            'Anketa raqami': x['anketa_raqami'], 'PINFL/STIR': pinfl_stir, 'Mijoz nomi': x['mijoz_nomi'],
            'Turi': turi, 'Ruxsat berilgan sana': x.get('sud_hujjatlar_ruxsat_sana', '') or '',
            'Holati': holat,
            "Davo ariza raqami": x.get('davo_ariza_ish_raqami', '') or '',
            "Ta'minot turi": taminot_turi_nomi, "Ta'minot / Kafillik tafsiloti": taminot_tafsilot,
        })
    df = pd.DataFrame(data_rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='ruxsat_berilganlar.xlsx')


@bp.route('/api/sud/kiritilmadi', methods=['POST'])
def sud_kiritilmadi():
    """Tasdiqlangan Davo arizani sudga topshirmaslik sababini qayd qiladi.
    'Qarz yopilgan' sababi tanlansa, bu tizim tomonidan HAQIQATAN
    tekshiriladi — agar joriy qarzdorlik hali mavjud bo'lsa, bu sabab
    RAD ETILADI (chunki noto'g'ri ma'lumot bo'lishi mumkin)."""
    anketa = request.form.get('anketa_raqami')
    sababi = request.form.get('sababi')
    sana = request.form.get('sana', '')
    sana, sana_xato = util.sana_tekshir(sana, 'Sana', kelajak_mumkinmi=False)
    if sana_xato:
        return jsonify({'xato': sana_xato}), 400
    xodim_ism = request.form.get('xodim_ism', '')
    izoh = request.form.get('izoh', '')

    if not anketa or not sababi or not sana:
        return jsonify({'xato': 'anketa_raqami, sababi va sana kerak'}), 400
    if sababi not in ('qarz_yopilgan', 'mijoz_arizasi', 'xodim_iltimosi'):
        return jsonify({'xato': "Noma'lum sabab turi"}), 400

    conn = db.get_conn()
    row = conn.execute(
        "SELECT * FROM xatlar WHERE anketa_raqami=? AND davo_ariza_holati='olib_kelindi'", (anketa,)
    ).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Mos xat topilmadi'}), 404
    xat = dict(row)

    pdf_fayl = None

    if sababi == 'qarz_yopilgan':
        # MUHIM: bu sababni tizim o'zi tekshiradi — agar portfelda hali
        # qarzdorlik ko'rinsa, xodim yoki mijoz noto'g'ri ma'lumot berayotgan
        # bo'lishi mumkin, shuning uchun bu sabab qat'iyan rad etiladi.
        prow = db.get_portfel_by_id(xat['portfel_id'])
        joriy_qarz = 0
        if prow:
            joriy_qarz = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
        if joriy_qarz > 1:  # 1 so'mgacha yumaloqlash xatosi sifatida e'tiborga olinmaydi
            return jsonify({'xato': (
                f"Bu sabab qabul qilinmadi: tizim ma'lumotlariga ko'ra, mijozning joriy qarzdorligi "
                f"hali {int(joriy_qarz):,} so'm (yopilmagan). Agar bu noto'g'ri bo'lsa, avval Portfelni "
                f"yangilang yoki boshqa sababni tanlang."
            ).replace(',', ' ')}), 400

    elif sababi == 'mijoz_arizasi':
        f = request.files.get('mijoz_arizasi_pdf')
        if not f or not f.filename:
            return jsonify({'xato': "Mijozning yozma arizasi (PDF) yuklash majburiy"}), 400
        out_dir = bugungi_papka('Sudga_kiritilmadi_arizalar')
        os.makedirs(out_dir, exist_ok=True)
        ext = os.path.splitext(f.filename)[1] or '.pdf'
        pdf_fayl = os.path.join(out_dir, f"{letters.safe_filename(xat['mijoz_nomi'])}_{anketa}_Mijoz_arizasi{ext}")
        xato_natija = mustahkam_fayl_saqlash(f, pdf_fayl, ozbek_kengaytma_tekshiruvi=False)
        if xato_natija:
            return jsonify({'xato': xato_natija[0]}), xato_natija[1]

    elif sababi == 'xodim_iltimosi':
        if not xodim_ism.strip():
            return jsonify({'xato': "Bank xodimining F.I.Sh kiritish majburiy"}), 400
        if not izoh.strip():
            return jsonify({'xato': "Qoldirish sababini kiritish majburiy"}), 400

    db.mark_sud_kiritilmadi(xat['id'], sababi, sana, pdf_fayl=pdf_fayl,
                             xodim_ism=xodim_ism or None, izoh=izoh or None)
    return jsonify({'ok': True})


@bp.route('/api/sud/kiritilmagan_royxat', methods=['GET'])
def sud_kiritilmagan_royxat():
    xatlar = db.get_sud_kiritilmagan_royxati()
    sabab_nomlari = {'qarz_yopilgan': "Qarz to'liq yopilgan", 'mijoz_arizasi': "Mijozning yozma arizasi asosida",
                      'xodim_iltimosi': "Bank xodimi iltimosiga asosan",
                      'dpd_kamaygan_avtomatik': "Avtomatik: DPD/qarz kamaygani sababli"}
    natija = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
        natija.append({
            'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'], 'turi': turi,
            'sababi': x.get('sud_kiritilmadi_sababi'),
            'sababi_nomi': sabab_nomlari.get(x.get('sud_kiritilmadi_sababi'), ''),
            'sana': x.get('sud_kiritilmadi_sana', ''),
            'mijoz_arizasi_pdf': x.get('sud_kiritilmadi_pdf', ''),
            'xodim_ism': x.get('sud_kiritilmadi_xodim_ism', ''),
            'izoh': x.get('sud_kiritilmadi_izoh', ''),
        })
    return jsonify({'royxat': natija})


def sud_hujjatlar_papkasi():
    sozlama = db.get_all_settings().get('hujjatlar_papkasi', '').strip()
    papka = os.path.join(sozlama, 'sud_hujjatlar') if sozlama else os.path.join(db._app_dir(), 'sud_hujjatlar')
    os.makedirs(papka, exist_ok=True)
    return papka


@bp.route('/api/sud/yigma_jild_holati', methods=['GET'])
def sud_yigma_jild_holati():
    """Berilgan anketa uchun Sud harakatlari yig'ma jildida qaysi
    hujjatlar bor, qaysilari yetishmayotganini ko'rsatadi."""
    anketa = request.args.get('anketa', '')
    conn = db.get_conn()
    row = conn.execute('SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1', (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Xat topilmadi'}), 404
    xat = dict(row)
    # MUHIM: iqtisodiy sudga (yuridik shaxs / YaTT) topshiriladigan ishlarda
    # ro'yxatga "Davo ariza taraflarga yuborilgani" va "Talabnoma taraflarga
    # yuborilgani" tasdiqnomalari ham MAJBURIY hujjat sifatida qo'shiladi.
    kerakli = db.sud_majburiy_hujjatlar_royxati(xat)
    natija = []
    for maydon, nomi in kerakli:
        satr = {'maydon': maydon, 'nomi': nomi, 'mavjud': bool(xat.get(maydon)),
                'fayl': xat.get(maydon) or '', 'majburiy': True}
        sana_maydoni = db.TARAFLARGA_SANA_MAYDONI.get(maydon)
        if sana_maydoni:
            satr['sana'] = xat.get(sana_maydoni) or ''
            satr['sana_soraladi'] = True
        natija.append(satr)
    natija.append({'maydon': 'sud_yigma_jild_titul_fayl', 'nomi': 'Titul', 'mavjud': bool(xat.get('sud_yigma_jild_titul_fayl')),
                    'fayl': xat.get('sud_yigma_jild_titul_fayl') or '', 'majburiy': True})
    # MUHIM: Ma'lumotnoma — IXTIYORIY hujjat, shuning uchun u
    # "yetishmayapti" ro'yxatida ko'rinmasligi kerak (aks holda xodim
    # uni ham majburiy deb o'ylab, behuda izlab yurardi).
    natija.append({'maydon': 'sud_malumotnoma_topshirishda_fayl', 'nomi': "Ma'lumotnoma (ixtiyoriy)",
                    'mavjud': bool(xat.get('sud_malumotnoma_topshirishda_fayl')),
                    'fayl': xat.get('sud_malumotnoma_topshirishda_fayl') or '', 'majburiy': False})
    # Sudga beriladigan RASMIY ma'lumotnomalar — tizim o'zi tayyorlaydi,
    # shuning uchun "majburiy" emas (lekin sudga berilishi tavsiya etiladi).
    natija.append({'maydon': 'sud_malumotnoma_qarzdorlik_fayl',
                    'nomi': "Ma'lumotnoma — kredit qarzdorligi holati",
                    'mavjud': bool(xat.get('sud_malumotnoma_qarzdorlik_fayl')),
                    'fayl': xat.get('sud_malumotnoma_qarzdorlik_fayl') or '',
                    'majburiy': False, 'tizim_yaratadi': 'qarzdorlik'})
    natija.append({'maydon': 'sud_qoshimcha_malumotnoma_fayl',
                    'nomi': "Qo'shimcha ma'lumotnoma — qarz o'zgarishi",
                    'mavjud': bool(xat.get('sud_qoshimcha_malumotnoma_fayl')),
                    'fayl': xat.get('sud_qoshimcha_malumotnoma_fayl') or '',
                    'majburiy': False, 'tizim_yaratadi': 'qoshimcha'})
    natija.append({'maydon': 'davo_ariza_fayl_yoli', 'nomi': 'Davo ariza', 'mavjud': bool(xat.get('davo_ariza_fayl_yoli')),
                    'fayl': xat.get('davo_ariza_fayl_yoli') or '', 'majburiy': True})
    natija.append({'maydon': 'fayl_yoli', 'nomi': 'Xat', 'mavjud': bool(xat.get('fayl_yoli')),
                    'fayl': xat.get('fayl_yoli') or '', 'majburiy': True})
    toliqmi = db.sud_hujjatlar_toliqmi(xat)
    qoshimcha_hujjatlar = db.sud_qoshimcha_hujjatlar_royxati(xat['id'])
    return jsonify({'hujjatlar': natija, 'toliqmi': toliqmi, 'ruxsat_berilgan': bool(xat.get('sud_hujjatlar_ruxsat')),
                     'qoshimcha_hujjatlar': qoshimcha_hujjatlar,
                     'iqtisodiy_sud': db.iqtisodiy_sudmi(xat.get('mijoz_turi'))})


@bp.route('/api/sud/yigma_jild_yaratish', methods=['POST'])
def sud_yigma_jild_yaratish_endpoint():
    """Anketa uchun Sud harakatlari yig'ma jildi papkasi va titulini
    yaratadi (yoki, agar allaqachon bo'lsa, titulni qayta yangilaydi).
    MUHIM: agar bir necha marta sikl bo'lgan bo'lsa (masalan ilgari MIB
    orqali yakunlangan, endi qarzdorlik qaytadan boshlangan), har doim
    ENG SO'NGGI (joriy) xat yozuvi bilan ishlaydi."""
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami')
    conn = db.get_conn()
    row = conn.execute('SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1', (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Xat topilmadi'}), 404
    xat = dict(row)
    prow = db.get_portfel_by_id(xat['portfel_id'])
    turi, mijoz = util.resolve_mijoz(prow) if prow else (xat.get('mijoz_turi'), None)
    settings = db.get_all_settings()

    # MUHIM (yangi tuzilma): Huquqiy choralar/Sud hujjatlari/[sikl boshlangan
    # sana]/[mijoz nomi]/ papkasida saqlanadi.
    sikl_sana_dt = None
    try:
        sikl_sana_dt = datetime.datetime.fromisoformat(xat.get('yaratilgan_sana'))
    except Exception:
        pass
    jild_papka = sud_hujjatlari_mijoz_papkasi(xat.get('mijoz_nomi', ''), sikl_sana_dt, anketa)
    titul_path = os.path.join(jild_papka, '00_Titul.docx')
    letters.generate_sud_yigma_jild_titul(titul_path, xat, prow, mijoz, settings)
    db.sud_yigma_jild_yaratish(xat['id'], jild_papka, titul_path)

    # MUHIM: Xat va Davo arizaning O'ZI ham (ular boshqa, "Huquqiy
    # choralar/Xat/..." va ".../Davo ariza/..." papkalarida yaratilgan
    # bo'lsa-da) — tizimda "mavjud" ko'rinishi bilan bir qatorda, ULARNING
    # NUSXASI shu Sud yig'ma jild papkasining O'ZIGA HAM jismonan
    # nusxalanadi — shunda kimdir Explorer orqali shu bitta papkani ochsa,
    # BARCHA hujjatlarni (Xat, Davo ariza va boshqalar) shu yerning
    # o'zida, jismonan ko'radi.
    import shutil as _shutil
    for maydon, prefiks in [('fayl_yoli', '98_Xat'), ('davo_ariza_fayl_yoli', '99_Davo_ariza')]:
        manba = xat.get(maydon)
        if manba and os.path.exists(manba):
            allaqachon_bor = any(f.startswith(prefiks) for f in os.listdir(jild_papka))
            if not allaqachon_bor:
                ext = os.path.splitext(manba)[1]
                dest = os.path.join(jild_papka, f"{prefiks}_{os.path.basename(manba)}")
                try:
                    _shutil.copy2(manba, dest)
                except Exception:
                    pass

    # MUHIM: agar shu anketa uchun OLDINGI sikl(lar)da kredit hujjatlari
    # (kredit shartnoma, kafillik, garov, bank baholash) allaqachon
    # yuklangan bo'lsa — bu, odatda, o'zgarmaydigan hujjatlar bo'lgani
    # uchun, tizim ularni AVTOMATIK topib, yangi jildga ham nusxalab
    # qo'yadi (qayta yuklash shart bo'lmaydi). Davo ariza, Xat va
    # Ma'lumotnoma esa — har doimgidek, YANGI sikl uchun ALOHIDA, yangidan
    # yaratiladi (chunki bular joriy sana/summaga bog'liq).
    kredit_maydonlar = ['kredit_shartnoma_fayl', 'kafillik_shartnoma_fayl', 'garov_shartnoma_fayl', 'bank_baholash_fayl']
    nusxalangan = []
    conn = db.get_conn()
    oldingi_yozuvlar = conn.execute('''
        SELECT * FROM xatlar WHERE anketa_raqami=? AND id != ? ORDER BY id DESC
    ''', (anketa, xat['id'])).fetchall()
    # MUHIM: agar "Nollashtirish" orqali eski xat yozuvlari BUTUNLAY
    # o'chirilgan bo'lsa (jarayon noldan qayta boshlangan bo'lsa), yuqoridagi
    # 'oldingi_yozuvlar' bo'sh chiqishi mumkin — shu sabab, DOIMIY arxiv
    # jadvalini ham ZAXIRA manba sifatida tekshiramiz.
    arxiv_row = conn.execute('SELECT * FROM kredit_hujjatlar_arxiv WHERE anketa_raqami=?', (anketa,)).fetchone()
    arxiv = dict(arxiv_row) if arxiv_row else {}
    for maydon in kredit_maydonlar:
        if xat.get(maydon):
            continue  # joriy siklda allaqachon bor — tegilmaymiz
        manba_fayl = None
        for eski in oldingi_yozuvlar:
            eski = dict(eski)
            if eski.get(maydon) and os.path.exists(eski[maydon]):
                manba_fayl = eski[maydon]
                break
        if not manba_fayl and arxiv.get(maydon) and os.path.exists(arxiv[maydon]):
            manba_fayl = arxiv[maydon]
        if manba_fayl:
            import shutil
            yangi_nomi = os.path.basename(manba_fayl)
            yangi_yoli = os.path.join(jild_papka, f"nusxa_{yangi_nomi}")
            shutil.copy2(manba_fayl, yangi_yoli)
            db.sud_hujjat_saqlash(xat['id'], maydon, yangi_yoli)
            nusxalangan.append(maydon)
    conn.close()
    return jsonify({'ok': True, 'eski_hujjatlardan_nusxalangan': nusxalangan})


@bp.route('/api/sud/malumotnoma_yaratish', methods=['POST'])
def sud_malumotnoma_yaratish_endpoint():
    """Sudga topshirishdagi ma'lumotnomani (Davo summasiga teng bo'lishi
    kerak bo'lgan) avtomatik yaratadi va yig'ma jildga saqlaydi."""
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami')
    conn = db.get_conn()
    row = conn.execute('SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1', (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Xat topilmadi'}), 404
    xat = dict(row)
    if not xat.get('sud_yigma_jild_papka'):
        return jsonify({'xato': "Avval yig'ma jild (Titul) yaratilishi kerak"}), 400
    prow = db.get_portfel_by_id(xat['portfel_id'])
    turi, mijoz = util.resolve_mijoz(prow) if prow else (xat.get('mijoz_turi'), None)
    settings = db.get_all_settings()
    fayl_yoli = os.path.join(xat['sud_yigma_jild_papka'], '01_Malumotnoma_topshirishda.docx')
    letters.generate_malumotnoma_topshirishda(fayl_yoli, xat, prow, mijoz, settings)
    db.sud_hujjat_saqlash(xat['id'], 'sud_malumotnoma_topshirishda_fayl', fayl_yoli)
    return jsonify({'ok': True})


@bp.route('/api/sud/rasmiy_malumotnoma_yaratish', methods=['POST'])
def sud_rasmiy_malumotnoma_yaratish():
    """Sudga beriladigan RASMIY ma'lumotnomalarni tayyorlaydi:

      turi='qarzdorlik'  -> «Kredit qarzdorligi holati to'g'risida»
                            MA'LUMOTNOMA (da'vo arizasi bilan beriladi);
      turi='qoshimcha'   -> «QO'SHIMCHA MA'LUMOTNOMA — qarzdorlik
                            summasining o'zgarishi to'g'risida» (ish sudda
                            ko'rilayotganda qarz o'zgarsa beriladi).

    Ikkalasi ham tizimdagi ma'lumotlardan AVTOMATIK to'ldiriladi va
    Sud yig'ma jildiga qo'shiladi."""
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami')
    turi = data.get('turi', 'qarzdorlik')
    if turi not in ('qarzdorlik', 'qoshimcha'):
        return jsonify({'xato': "Noto'g'ri ma'lumotnoma turi"}), 400

    conn = db.get_conn()
    row = conn.execute('SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1',
                       (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Xat topilmadi'}), 404
    xat = dict(row)
    if not xat.get('sud_yigma_jild_papka'):
        return jsonify({'xato': "Avval yig'ma jild (Titul) yaratilishi kerak"}), 400

    prow = db.get_portfel_by_id(xat['portfel_id'])
    _turi, mijoz = util.resolve_mijoz(prow) if prow else (xat.get('mijoz_turi'), None)
    settings = db.get_all_settings()
    xat_raqami = (data.get('xat_raqami') or '').strip()

    try:
        if turi == 'qarzdorlik':
            taminot = db.get_taminot(anketa)
            # Oxirgi to'lov sanasi — tizimga tushgan tasdiqlangan to'lovlardan.
            # MUHIM: hujjat qaysi sanadagi holatni ko'rsatsa, to'lov ham shu
            # sanagacha bo'lishi kerak — aks holda "25 avgust holatiga" deb
            # yozilgan hujjatda "oxirgi to'lov 18 sentabrda" degan zid
            # ma'lumot chiqib qolardi.
            _jami, tlar = db.tolovlar_jami_va_royxat(anketa)
            holat_chegara = _sana_dt(xat.get('sud_topshirilgan_sana')
                                     or xat.get('davo_ariza_sana')) or datetime.date.today()
            mos_tolovlar = [t for t in tlar
                            if (_sana_dt(t.get('sana')) or datetime.date.min) <= holat_chegara]
            oxirgi_tolov = mos_tolovlar[-1].get('sana') if mos_tolovlar else None
            fayl_yoli = os.path.join(xat['sud_yigma_jild_papka'],
                                     '06_Malumotnoma_kredit_qarzdorlik.docx')
            letters.generate_sud_malumotnoma_qarzdorlik(
                fayl_yoli, xat, prow, mijoz, settings, taminot=taminot,
                xat_raqami=xat_raqami, oxirgi_tolov_sanasi=oxirgi_tolov)
            maydon = 'sud_malumotnoma_qarzdorlik_fayl'
        else:
            # Davo ariza sudga topshirilgandan KEYINGI to'lovlar
            _jami, tolovlar = db.tolovlar_jami_va_royxat(anketa)
            chegara = xat.get('sud_topshirilgan_sana') or xat.get('davo_ariza_sana')
            chegara_dt = _sana_dt(chegara)
            if chegara_dt:
                # Faqat sudga topshirilgandan KEYIN tushgan to'lovlar —
                # qo'shimcha ma'lumotnoma aynan shu davrdagi o'zgarishni
                # ko'rsatadi.
                tolovlar = [t for t in tolovlar
                            if (_sana_dt(t.get('sana')) or chegara_dt) >= chegara_dt]
            fayl_yoli = os.path.join(xat['sud_yigma_jild_papka'],
                                     '07_Qoshimcha_malumotnoma_ozgarish.docx')
            letters.generate_sud_qoshimcha_malumotnoma(
                fayl_yoli, xat, prow, mijoz, settings, tolovlar=tolovlar,
                xat_raqami=xat_raqami,
                avvalgi_malumotnoma_raqami=(data.get('avvalgi_raqam') or '').strip())
            maydon = 'sud_qoshimcha_malumotnoma_fayl'
    except FileNotFoundError as e:
        return jsonify({'xato': str(e)}), 400
    except Exception as e:
        return jsonify({'xato': f"Ma'lumotnoma tayyorlashda xato: {e}"}), 500

    db.sud_hujjat_saqlash(xat['id'], maydon, fayl_yoli)

    # MUHIM: hujjatda to'ldirilmay qolgan {{BELGI}} bo'lsa — foydalanuvchi
    # buni BILISHI shart, aks holda yarmi bo'sh hujjat sudga ketishi mumkin.
    # Bunday holat odatda shablon noto'g'ri bo'limga yuklangani sababli
    # yuz beradi.
    qolgan = letters.toldirilmagan_belgilar(fayl_yoli)
    if qolgan:
        return jsonify({
            'ok': True, 'fayl': fayl_yoli,
            'ogohlantirish': ("Hujjat tayyor, LEKIN quyidagi joylar to'ldirilmadi:\n• "
                              + "\n• ".join(qolgan[:12])
                              + (f"\n• ... va yana {len(qolgan) - 12} ta" if len(qolgan) > 12 else '')
                              + "\n\nSabab: shablon boshqa bo'limga yuklangan bo'lishi mumkin. "
                                "Sozlamalar → Sud bo'limida shablonni to'g'ri qatorga yuklang.")})
    return jsonify({'ok': True, 'fayl': fayl_yoli})


@bp.route('/api/sud/hujjat_yuklash', methods=['POST'])
def sud_hujjat_yuklash():
    """Sud yig'ma jildi uchun kredit hujjatlaridan birini (kredit
    shartnoma, kafillik, garov, bank baholash) PDF sifatida yuklaydi."""
    anketa = request.form.get('anketa_raqami')
    maydon = request.form.get('maydon')
    f = request.files.get('file')
    if not anketa or not maydon or not f or not f.filename:
        return jsonify({'xato': 'anketa_raqami, maydon va fayl kerak'}), 400
    if maydon not in db.SUD_YUKLANADIGAN_HUJJATLAR:
        return jsonify({'xato': f"Noto'g'ri hujjat turi: {maydon}"}), 400
    conn = db.get_conn()
    row = conn.execute('SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1', (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Xat topilmadi'}), 404
    xat = dict(row)
    if not xat.get('sud_yigma_jild_papka'):
        return jsonify({'xato': "Avval yig'ma jild (Titul) yaratilishi kerak"}), 400
    nomlar = {'kredit_shartnoma_fayl': '02_Kredit_shartnoma', 'kafillik_shartnoma_fayl': '03_Kafillik_shartnoma',
              'garov_shartnoma_fayl': '04_Garov_shartnoma', 'bank_baholash_fayl': '05_Bank_baholash',
              'davo_ariza_taraflarga_tasdiq_fayl': '06_Davo_ariza_taraflarga_yuborilgani',
              'talabnoma_taraflarga_tasdiq_fayl': '07_Talabnoma_taraflarga_yuborilgani'}
    prefiks = nomlar.get(maydon, maydon)

    # Taraflarga yuborilgani tasdig'i uchun — yuborilgan (kvitansiya) sanasi
    yuborilgan_sana = None
    if maydon in db.TARAFLARGA_SANA_MAYDONI:
        yuborilgan_sana, sana_xato = util.sana_tekshir(
            request.form.get('yuborilgan_sana', ''), 'Taraflarga yuborilgan sana',
            majburiy=True, kelajak_mumkinmi=False)
        if sana_xato:
            return jsonify({'xato': sana_xato}), 400

    fayl_yoli = os.path.join(xat['sud_yigma_jild_papka'], f"{prefiks}_{letters.safe_filename(f.filename)}")
    xato_natija = mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    db.sud_hujjat_saqlash(xat['id'], maydon, fayl_yoli, yuborilgan_sana=yuborilgan_sana)
    return jsonify({'ok': True})


@bp.route('/api/sud/qoshimcha_hujjat_yuklash', methods=['POST'])
def sud_qoshimcha_hujjat_yuklash():
    """Sud yig'ma jildiga, standart ro'yxatdagilardan tashqari, IXTIYORIY
    (foydalanuvchi o'zi nom bergan) qo'shimcha hujjat yuklaydi — masalan
    boshqa turdagi dalil, ariza yoki maxsus holatga oid hujjat."""
    anketa = request.form.get('anketa_raqami')
    hujjat_nomi = request.form.get('hujjat_nomi', '').strip()
    f = request.files.get('file')
    if not anketa or not hujjat_nomi or not f or not f.filename:
        return jsonify({'xato': "Anketa raqami, hujjat nomi va fayl kerak"}), 400
    conn = db.get_conn()
    row = conn.execute('SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1', (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Xat topilmadi'}), 404
    xat = dict(row)
    if not xat.get('sud_yigma_jild_papka'):
        return jsonify({'xato': "Avval yig'ma jild (Titul) yaratilishi kerak"}), 400
    fayl_nomi_toza = letters.safe_filename(hujjat_nomi)
    fayl_yoli = os.path.join(xat['sud_yigma_jild_papka'], f"Qoshimcha_{fayl_nomi_toza}_{letters.safe_filename(f.filename)}")
    xato_natija = mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    db.sud_qoshimcha_hujjat_qoshish(xat['id'], hujjat_nomi, fayl_yoli)
    return jsonify({'ok': True})


@bp.route('/api/sud/qoshimcha_hujjat/<int:hujjat_id>', methods=['DELETE'])
def sud_qoshimcha_hujjat_ochirish_endpoint(hujjat_id):
    db.sud_qoshimcha_hujjat_ochirish(hujjat_id)
    return jsonify({'ok': True})


@bp.route('/api/sud/ruxsat_berish', methods=['POST'])
def sud_ruxsat_berish_endpoint():
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami')
    conn = db.get_conn()
    row = conn.execute('SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1', (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Xat topilmadi'}), 404
    xat = dict(row)
    if not db.sud_hujjatlar_toliqmi(xat):
        # MUHIM: umumiy "to'liq emas" xabari o'rniga AYNAN qaysi hujjat
        # yetishmayotganini aytamiz — iqtisodiy sudda taraflarga yuborilganlik
        # tasdig'i yangi majburiy hujjat bo'lgani uchun, buni bilmasdan
        # foydalanuvchi nima kamligini topa olmasdi.
        yetishmayotgan = [nomi for maydon, nomi in db.sud_majburiy_hujjatlar_royxati(xat)
                          if not xat.get(maydon)]
        for maydon, nomi in (('sud_yigma_jild_titul_fayl', 'Titul'),
                             ('davo_ariza_fayl_yoli', 'Davo ariza'),
                             ('fayl_yoli', 'Xat')):
            if not xat.get(maydon):
                yetishmayotgan.append(nomi)
        return jsonify({'xato': "Quyidagi majburiy hujjatlar yuklanmagan:\n• " +
                                "\n• ".join(yetishmayotgan)}), 400
    db.sud_hujjatlar_ruxsat_berish(xat['id'])
    return jsonify({'ok': True})


@bp.route('/api/sud/tayyor_jild', methods=['GET'])
def sud_tayyor_jild_endpoint():
    """Belgilangan tartibda (Titul -> Ma'lumotnoma -> Davo ariza -> Xat ->
    Kredit hujjatlari) barcha hujjatlarni yagona PDF qilib birlashtiradi."""
    anketa = request.args.get('anketa', '')
    conn = db.get_conn()
    row = conn.execute('SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1', (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Xat topilmadi'}), 404
    xat = dict(row)
    fayllar = []
    for maydon in ['sud_yigma_jild_titul_fayl', 'sud_malumotnoma_topshirishda_fayl',
                   'sud_malumotnoma_qarzdorlik_fayl', 'sud_qoshimcha_malumotnoma_fayl',
                   'davo_ariza_fayl_yoli', 'davo_ariza_taraflarga_tasdiq_fayl',
                   'fayl_yoli', 'talabnoma_taraflarga_tasdiq_fayl',
                   'kredit_shartnoma_fayl', 'kafillik_shartnoma_fayl', 'garov_shartnoma_fayl', 'bank_baholash_fayl']:
        if xat.get(maydon) and os.path.exists(xat[maydon]):
            fayllar.append(xat[maydon])
    # MUHIM: standart ro'yxatdan tashqari, qo'lda qo'shilgan IXTIYORIY
    # qo'shimcha hujjatlar ham (oxirida) jildga qo'shiladi.
    for qh in db.sud_qoshimcha_hujjatlar_royxati(xat['id']):
        if qh.get('fayl_yoli') and os.path.exists(qh['fayl_yoli']):
            fayllar.append(qh['fayl_yoli'])
    mijoz_fayl_nomi = letters.safe_filename(xat.get('mijoz_nomi', ''))
    output_path = os.path.join(sud_hujjatlar_papkasi(), f"{mijoz_fayl_nomi}_Sud_jildi_{letters.safe_filename(anketa)}.pdf")
    return yigma_jild_javobi(fayllar, output_path, f"{mijoz_fayl_nomi}_Sud_jildi_{anketa}.pdf")


@bp.route('/api/sud/kiritilmagan_excel', methods=['GET'])
def sud_kiritilmagan_excel():
    import tempfile
    from flask import send_file
    import pandas as pd
    resp = sud_kiritilmagan_royxat()
    rows = resp.get_json()['royxat']
    if not rows:
        return jsonify({'xato': "Hozircha 'Sudga kiritilmadi' deb belgilangan ish yo'q"}), 400
    excel_qatorlar = [{
        'Anketa raqami': r['anketa_raqami'], 'Mijoz': r['mijoz_nomi'], 'Turi': r['turi'],
        'Sababi': r['sababi_nomi'], 'Sana': r['sana'],
        'Xodim F.I.Sh': r['xodim_ism'], 'Izoh': r['izoh'],
    } for r in rows]
    df = pd.DataFrame(excel_qatorlar)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='sudga_kiritilmaganlar.xlsx')


@bp.route('/api/sud/kiritilmadi_bekor_qilish', methods=['POST'])
def sud_kiritilmadi_bekor_qilish():
    """'Sudga kiritilmadi' deb noto'g'ri yoki muddatidan oldin belgilangan
    ishni bekor qiladi — ish qayta 'Sudga topshirish kerak' navbatiga qaytadi."""
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami')
    if not anketa:
        return jsonify({'xato': 'anketa_raqami kerak'}), 400
    conn = db.get_conn()
    row = conn.execute(
        "SELECT id FROM xatlar WHERE anketa_raqami=? AND sud_kiritilmadi_sababi IS NOT NULL "
        "AND sud_kiritilmadi_sababi != ''", (anketa,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'xato': "'Sudga kiritilmadi' deb belgilangan ish topilmadi"}), 404
    conn.execute(
        "UPDATE xatlar SET sud_kiritilmadi_sababi=NULL, sud_kiritilmadi_pdf=NULL, "
        "sud_kiritilmadi_xodim_ism=NULL, sud_kiritilmadi_izoh=NULL, sud_kiritilmadi_sana=NULL "
        "WHERE id=?", (row['id'],))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@bp.route('/api/sud/qaror_yuklash', methods=['POST'])
def sud_qaror_yuklash():
    """Sud qarorini (5/15 kunlik muddatda) yuklaydi. Natija:
      - 'bank_foydasiga' / 'qisman' -> sud ishi tugab, MIB uchun tayyor bo'ladi
      - 'rad_etildi' -> sud ishi (sabab bilan) tugaydi, keyinchalik
        "Nollashtirish" orqali qaytadan boshlanishi mumkin."""
    anketa = request.form.get('anketa_raqami')
    natija = request.form.get('natija')  # 'bank_foydasiga' | 'qisman' | 'rad_etildi'
    sana = request.form.get('sana', datetime.datetime.now().strftime('%d.%m.%Y'))
    sana, sana_xato = util.sana_tekshir(sana, 'Sud qarori sanasi', kelajak_mumkinmi=False)
    if sana_xato:
        return jsonify({'xato': sana_xato}), 400
    f = request.files.get('qaror_fayl')
    if not anketa or natija not in ('bank_foydasiga', 'qisman', 'rad_etildi'):
        return jsonify({'xato': "anketa_raqami va to'g'ri natija ('bank_foydasiga'/'qisman'/'rad_etildi') kerak"}), 400
    if not f or not f.filename:
        return jsonify({'xato': "Sud qarori (PDF) yuklash majburiy"}), 400

    conn = db.get_conn()
    row = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami=? AND sud_holati='topshirildi' ORDER BY id DESC LIMIT 1", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Mos sud ishi topilmadi'}), 404
    xat = dict(row)

    out_dir = bugungi_papka('Sud qaror')
    fayl_yoli = os.path.join(out_dir, f"{letters.safe_filename(xat['mijoz_nomi'])}_{anketa}_Sud_qarori_" + letters.safe_filename(f.filename))
    xato_natija = mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]

    # MUHIM: summalar "1 500 000" ko'rinishida kiritilishi odatiy hol —
    # ilgari bunday qiymat ichki xato (500) berardi va sud qarori
    # SAQLANMASDAN qolib ketardi (PDF esa allaqachon diskka yozilgan
    # bo'lardi). Endi tushunarli xabar qaytariladi.
    qisman_asosiy, s_xato = util.son_tekshir(request.form.get('qisman_asosiy_farq'), 'Asosiy qarz farqi')
    if s_xato:
        return jsonify({'xato': s_xato}), 400
    qisman_foiz, s_xato = util.son_tekshir(request.form.get('qisman_foiz_farq'), 'Foiz farqi')
    if s_xato:
        return jsonify({'xato': s_xato}), 400
    qisman_penya, s_xato = util.son_tekshir(request.form.get('qisman_penya_farq'), 'Penya farqi')
    if s_xato:
        return jsonify({'xato': s_xato}), 400
    davlat_boji_sherik = request.form.get('davlat_boji_sherik') == 'true'
    rad_sababi = request.form.get('rad_sababi', '')

    db.sud_qaror_saqlash(xat['id'], natija, fayl_yoli, sana, qisman_asosiy, qisman_foiz, qisman_penya,
                          davlat_boji_sherik, rad_sababi)

    if natija == 'rad_etildi':
        db.add_mib_amal(xat['id'], 'sud_rad_etildi', sana, f"Sud tomonidan rad etildi: {rad_sababi}")

    return jsonify({'ok': True})


@bp.route('/api/sud/qaror_kutilayotganlar', methods=['GET'])
def sud_qaror_kutilayotganlar_endpoint():
    """Sudga topshirilgan, qaror hali yuklanmagan ishlar — muddat holati
    (necha kun qoldi/o'tdi) bilan birga."""
    royxat = db.get_sud_qaror_kutilayotganlar()
    natija = []
    bugun = datetime.datetime.now().date()
    for x in royxat:
        muddat_kun = db.sud_qaror_muddati_kun(x.get('mijoz_turi'))
        kun_qoldi = None
        if x.get('sud_topshirilgan_sana'):
            try:
                topshirilgan = datetime.datetime.strptime(x['sud_topshirilgan_sana'], '%d.%m.%Y').date()
                otgan_kun = (bugun - topshirilgan).days
                kun_qoldi = muddat_kun - otgan_kun
            except Exception:
                pass
        natija.append({
            'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'], 'turi': x.get('mijoz_turi'),
            'sud_topshirilgan_sana': x.get('sud_topshirilgan_sana'), 'muddat_kun': muddat_kun,
            'kun_qoldi': kun_qoldi, 'muddati_otganmi': kun_qoldi is not None and kun_qoldi < 0,
        })
    return jsonify({'royxat': natija})


@bp.route('/api/sud/qaror_kutilayotganlar_excel', methods=['GET'])
def sud_qaror_kutilayotganlar_excel():
    """Qaror kutilayotganlar ro'yxatini Excel qilib chiqaradi: Anketa
    raqami, PINFL/STIR, Mijoz nomi, Sud ish raqami, Sudga topshirilgan
    sana."""
    import tempfile
    from flask import send_file
    import pandas as pd
    royxat = db.get_sud_qaror_kutilayotganlar()
    if not royxat:
        return jsonify({'xato': "Hozircha qaror kutilayotgan ish yo'q"}), 400
    rows = []
    for x in royxat:
        prow = db.get_portfel_by_id(x.get('portfel_id')) if x.get('portfel_id') else None
        pinfl_stir = (prow.get('pinfl') or prow.get('stir') or '') if prow else ''
        rows.append({
            'Anketa raqami': x['anketa_raqami'],
            'PINFL/STIR': pinfl_stir,
            'Mijoz nomi': x['mijoz_nomi'],
            'Ish raqami': x.get('sud_ish_raqami', '') or '',
            'Sudga berilgan kuni': x.get('sud_topshirilgan_sana', '') or '',
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='qaror_kutilayotganlar.xlsx')


@bp.route('/api/sud/topshirildi', methods=['POST'])
def sud_topshirildi():
    anketa = request.form.get('anketa_raqami')
    ish_raqami = request.form.get('ish_raqami', '')
    sana = request.form.get('sana', '')
    majburiy = request.form.get('majburiy_davom_ettirish') == 'true'
    # MUHIM: sana tekshirilmasa, "2026.09.15" kabi noto'g'ri format
    # jim qabul qilinardi va shu ish uchun sud qarori muddati ogohlantirishi
    # HECH QACHON ishlamay qolardi (sana o'qib bo'lmagani uchun).
    sana, sana_xato = util.sana_tekshir(sana, 'Sudga topshirilgan sana', kelajak_mumkinmi=False)
    if sana_xato:
        return jsonify({'xato': sana_xato}), 400
    if not anketa or not ish_raqami or not sana:
        return jsonify({'xato': 'anketa_raqami, ish_raqami va sana kerak'}), 400
    conn = db.get_conn()
    row = conn.execute(
        "SELECT * FROM xatlar WHERE anketa_raqami=? AND davo_ariza_holati='olib_kelindi' ORDER BY id DESC LIMIT 1",
        (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Mos xat topilmadi'}), 404
    xat = dict(row)

    # MUHIM: sudga topshirilganini tasdiqlashdan OLDIN, "Yig'ma jild"
    # oynasida "Sudga yuborishga ruxsat berish" bosilganligi TEKSHIRILADI —
    # aks holda, hujjatlar hali to'liq bo'lmagan holatda ish sudga
    # "topshirilgan" deb noto'g'ri belgilanib qolishining oldi olinadi.
    if not xat.get('sud_hujjatlar_ruxsat'):
        return jsonify({'xato': (
            "Bu ish uchun hali \"Sudga yuborishga ruxsat berish\" bosilmagan. "
            "Iltimos, avval \"Yig'ma jild\" oynasida barcha kerakli hujjatlarni "
            "yuklab, ruxsat bering, so'ng sudga topshirilganini tasdiqlang."
        )}), 400

    # MUHIM: sudga topshirishdan OLDIN, mijozning JORIY (bugungi) DPD va
    # qarzdorligini tekshiramiz — agar Davo ariza tayyorlangandan beri
    # holat sezilarli yaxshilangan bo'lsa (masalan to'lov qilingan
    # bo'lsa), operatorni OGOHLANTIRAMIZ va aniq tasdiqlashni so'raymiz
    # (avtomatik bloklamaymiz, chunki operatorda qo'shimcha ma'lumot
    # bo'lishi mumkin — lekin "bilmasdan" davom etib ketmasligi kerak).
    if not majburiy:
        prow = db.get_portfel_by_id(xat['portfel_id'])
        if prow:
            settings = db.get_all_settings()
            dpd_ogoh = int(settings.get('dpd_chegara_kun', settings.get('chora_ogohlantirish_dpd_kun', 45)))
            joriy_dpd = prow.get('dpd_max') or 0
            joriy_qarz = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
            eski_qarz = (xat.get('davo_summasi_asosiy') or 0) + (xat.get('davo_summasi_foiz') or 0) + (xat.get('davo_summasi_jarima') or 0)
            dpd_pasaygan = joriy_dpd < dpd_ogoh
            qarz_keskin_kamaygan = eski_qarz > 0 and joriy_qarz < (eski_qarz * 0.5)
            if dpd_pasaygan or qarz_keskin_kamaygan:
                return jsonify({
                    'ogohlantirish': True,
                    'xabar': (f"Diqqat: mijozning joriy DPD'si ({joriy_dpd} kun) yoki qarzdorligi "
                              f"({joriy_qarz:,.0f} so'm) Davo ariza tayyorlangandagi holatdan "
                              f"({eski_qarz:,.0f} so'm) sezilarli yaxshilangan. Baribir sudga "
                              "topshirishni davom ettirasizmi?").replace(',', ' '),
                }), 200

    sud_buyrugi_fayl = None
    f = request.files.get('sud_buyrugi')
    if f and f.filename:
        out_dir = bugungi_papka('Sud qaror')
        os.makedirs(out_dir, exist_ok=True)
        ext = os.path.splitext(f.filename)[1] or '.pdf'
        sud_buyrugi_fayl = os.path.join(out_dir, f"{letters.safe_filename(xat['mijoz_nomi'])}_{anketa}_Sud_buyrugi{ext}")
        xato_natija = mustahkam_fayl_saqlash(f, sud_buyrugi_fayl, ozbek_kengaytma_tekshiruvi=False)
        if xato_natija:
            return jsonify({'xato': xato_natija[0]}), xato_natija[1]

    db.mark_sud_topshirildi(xat['id'], ish_raqami, sana, buyruq_fayl=sud_buyrugi_fayl)
    return jsonify({'ok': True})


@bp.route('/api/sud/topshirish_shablon', methods=['POST'])
def sud_topshirish_shablon():
    import tempfile
    from flask import send_file
    import pandas as pd
    data = request.get_json() or {}
    anketalar = data.get('anketalar', [])
    xatlar = db.get_sud_topshirish_kerak()
    xat_map = {x['anketa_raqami']: x for x in xatlar}
    settings = db.get_all_settings()
    rows = []
    for anketa in anketalar:
        x = xat_map.get(anketa)
        if not x:
            continue
        prow = db.get_portfel_by_id(x['portfel_id'])
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
        sud_nomi = "Iqtisodiy sud" if turi in ('yuridik', 'yatt') else "Fuqarolik sudi"
        asosiy = x.get('davo_summasi_asosiy') or 0
        foiz = x.get('davo_summasi_foiz') or 0
        jarima = x.get('davo_summasi_jarima') or 0
        farqi = db.get_davo_ariza_farqi(x, prow, settings=settings) if prow else {'farq': 0, 'qoshimcha_kerak': False}
        pinfl_stir = (prow.get('pinfl') or prow.get('stir') or '') if prow else ''
        rows.append({
            'Anketa raqami': anketa, 'Mijoz': x['mijoz_nomi'], 'PINFL/STIR': pinfl_stir, 'Sud turi': sud_nomi,
            'Davo ariza ish raqami': x.get('davo_ariza_ish_raqami', '') or '',
            'Davo summasi (asosiy)': asosiy, 'Davo summasi (foiz)': foiz, 'Davo summasi (jarima)': jarima,
            'Jami qarzdorlik': asosiy + foiz + jarima,
            "Farq (bugungi qarz bilan)": farqi['farq'],
            "Qo'shimcha ariza kerakmi": "✓ Ha" if farqi['qoshimcha_kerak'] else "Yo'q",
            'Sud ish raqami': '', "Sanasi (kun.oy.yil, masalan 20.08.2026)": '',
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='sudga_topshirish_shabloni.xlsx')


@bp.route('/api/sud/topshirish_excel_import', methods=['POST'])
def sud_topshirish_excel_import():
    import tempfile
    import pandas as pd
    f = request.files.get('file')
    if not f:
        return jsonify({'xato': 'Fayl yuborilmadi'}), 400
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:

        tmp_path = tmp.name

    xato_natija = mustahkam_fayl_saqlash(f, tmp_path)

    if xato_natija:

        return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    try:
        df = pd.read_excel(tmp_path)
    except Exception as e:
        return jsonify({'xato': str(e)}), 400
    finally:
        os.remove(tmp_path)

    sana_col = None
    for c in df.columns:
        if str(c).startswith('Sanasi'):
            sana_col = c
            break
    if 'Anketa raqami' not in df.columns or 'Sud ish raqami' not in df.columns or not sana_col:
        return jsonify({'xato': "Excel ustunlari mos emas — asl shablonni o'zgartirmang"}), 400

    yangilandi, otkazib_yuborildi, topilmadi = 0, 0, 0
    for _, r in df.iterrows():
        anketa = r.get('Anketa raqami')
        if pd.isna(anketa):
            continue
        anketa = str(anketa).strip()
        ish_raqami = r.get('Sud ish raqami')
        sana = r.get(sana_col)
        if pd.isna(ish_raqami) or pd.isna(sana) or not str(ish_raqami).strip() or not str(sana).strip():
            otkazib_yuborildi += 1
            continue
        conn = db.get_conn()
        row = conn.execute(
            "SELECT id FROM xatlar WHERE anketa_raqami=? AND davo_ariza_holati='olib_kelindi' "
            "AND (sud_holati IS NULL OR sud_holati != 'topshirildi')", (anketa,)).fetchone()
        conn.close()
        if not row:
            topilmadi += 1
            continue
        sana_str = str(sana).strip()
        if hasattr(sana, 'strftime'):
            sana_str = sana.strftime('%d.%m.%Y')
        db.mark_sud_topshirildi(row['id'], str(ish_raqami).strip(), sana_str)
        yangilandi += 1
    return jsonify({'yangilandi': yangilandi, 'otkazib_yuborildi': otkazib_yuborildi, 'topilmadi': topilmadi})


@bp.route('/api/sud/royxat', methods=['GET'])
def sud_royxat():
    royxat = db.get_sudga_topshirilganlar_royxati()
    natija = []
    for item in royxat:
        xat = item['xat']
        prow = item['portfel']
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else xat.get('mijoz_turi')
        asosiy = xat.get('davo_summasi_asosiy') or 0
        foiz = xat.get('davo_summasi_foiz') or 0
        jarima = xat.get('davo_summasi_jarima') or 0
        natija.append({
            'anketa_raqami': xat['anketa_raqami'], 'mijoz_nomi': xat['mijoz_nomi'], 'turi': turi,
            'jami_sud_summasi': asosiy + foiz + jarima, 'asosiy': asosiy, 'foiz': foiz, 'jarima': jarima,
            'sud_ish_raqami': xat.get('sud_ish_raqami', ''), 'sudga_topshirilgan': xat.get('sud_topshirilgan_sana', ''),
            'mib_holati': "✓ O'tkazilgan" if xat.get('mib_holati') == 'otkazildi' else 'Kutilmoqda',
        })
    return jsonify({'royxat': natija})


@bp.route('/api/sud/qidirish', methods=['GET'])
def sud_qidirish():
    anketa = request.args.get('anketa', '').strip()
    xatlar = db.get_sud_topshirish_kerak()
    for x in xatlar:
        if x['anketa_raqami'] == anketa:
            prow = db.get_portfel_by_id(x['portfel_id'])
            turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
            sud_nomi = "Iqtisodiy sud" if turi in ('yuridik', 'yatt') else "Fuqarolik sudi"
            asosiy = x.get('davo_summasi_asosiy') or 0
            foiz = x.get('davo_summasi_foiz') or 0
            jarima = x.get('davo_summasi_jarima') or 0
            return jsonify({'topildi': True, 'row': {
                'xat_id': x['id'], 'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'],
                'turi': turi, 'sud_nomi': sud_nomi, 'jami': asosiy + foiz + jarima,
                'imzo_sana': x.get('davo_ariza_imzo_sana', ''),
            }})
    return jsonify({'topildi': False})


@bp.route('/api/sud/eski_ish_qidirish', methods=['GET'])
def sud_eski_ish_qidirish():
    anketa = request.args.get('anketa', '').strip()
    rows = db.get_portfel_by_anketa(anketa)
    if not rows:
        return jsonify({'topildi': False})
    prow = rows[0]
    turi, mijoz = util.resolve_mijoz(prow)
    jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
    conn = db.get_conn()
    mavjud = conn.execute("SELECT id FROM xatlar WHERE portfel_id=?", (prow['id'],)).fetchone()
    conn.close()
    return jsonify({'topildi': True, 'mijoz_nomi': prow.get('mijoz_nomi', ''), 'turi': turi,
                     'jami_qarz': jami, 'mavjud_yozuv_bor': bool(mavjud)})


@bp.route('/api/sud/eski_ish_kiritish', methods=['POST'])
def sud_eski_ish_kiritish():
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami', '').strip()
    ish_raqami = data.get('ish_raqami', '').strip()
    sana = data.get('sana', '').strip()
    sana, sana_xato = util.sana_tekshir(sana, 'Sud ishi sanasi', kelajak_mumkinmi=False)
    if sana_xato:
        return jsonify({'xato': sana_xato}), 400
    if not anketa or not ish_raqami or not sana:
        return jsonify({'xato': 'anketa_raqami, ish_raqami va sana kerak'}), 400
    rows = db.get_portfel_by_anketa(anketa)
    if not rows:
        return jsonify({'xato': 'Bu anketa portfelda topilmadi'}), 404
    prow = rows[0]
    mijoz_turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi'))
    db.create_legacy_sud_xat(
        portfel_id=prow['id'], anketa_raqami=anketa, mijoz_nomi=prow.get('mijoz_nomi', ''),
        mijoz_turi=mijoz_turi, sud_ish_raqami=ish_raqami, sud_sana=sana,
    )
    return jsonify({'ok': True})


@bp.route('/api/sud/kunlari', methods=['GET'])
def sud_kunlari_royxat_endpoint():
    return jsonify({'royxat': db.sud_kunlari_royxati()})


@bp.route('/api/sud/kunlari', methods=['POST'])
def sud_kuni_qoshish_endpoint():
    """Sud kunini qo'lda (anketa raqami bilan) qo'shadi. Agar sud ish
    raqami berilgan bo'lsa, u shu anketaning yig'ma jild tituli va boshqa
    tegishli joylariga AVTOMATIK to'ldiriladi."""
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami', '').strip()
    if not anketa:
        return jsonify({'xato': 'anketa_raqami kerak'}), 400
    sud_sanasi, sana_xato = util.sana_tekshir(
        data.get('sud_sanasi', ''), 'Sud sanasi', majburiy=True)
    if sana_xato:
        return jsonify({'xato': sana_xato}), 400
    rows = db.get_portfel_by_anketa(anketa)
    mijoz_nomi = rows[0]['mijoz_nomi'] if rows else data.get('mijoz_nomi', '')
    db.sud_kuni_qoshish(anketa, mijoz_nomi, sud_sanasi, data.get('sud_vaqti', ''),
                         data.get('sud_nomi', ''), data.get('sud_ish_raqami', ''))
    return jsonify({'ok': True})


@bp.route('/api/sud/kunlari/excel_yuklash', methods=['POST'])
def sud_kunlari_excel_yuklash():
    """Sud kunlarini Excel orqali ommaviy yuklaydi. Ustunlar: Anketa raqami,
    Sud sanasi, Sud vaqti, Sud nomi, Sud ish raqami."""
    import pandas as pd
    f = request.files.get('file')
    if not f:
        return jsonify({'xato': 'Fayl yuborilmadi'}), 400
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    xato_natija = mustahkam_fayl_saqlash(f, tmp_path)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    try:
        df = pd.read_excel(tmp_path)
    finally:
        os.remove(tmp_path)
    anketa_col = next((c for c in df.columns if 'anketa' in str(c).lower()), None)
    sana_col = next((c for c in df.columns if 'sana' in str(c).lower()), None)
    vaqt_col = next((c for c in df.columns if 'vaqt' in str(c).lower()), None)
    nomi_col = next((c for c in df.columns if 'nomi' in str(c).lower() and 'sud' in str(c).lower()), None)
    ish_col = next((c for c in df.columns if 'ish' in str(c).lower()), None)
    if not anketa_col or not sana_col:
        return jsonify({'xato': "Fayl tuzilmasi tanilmadi — 'Anketa raqami' va 'Sud sanasi' ustunlari kerak"}), 400
    qoshilgan, xatolar = 0, []
    for i, row in df.iterrows():
        try:
            anketa = str(row[anketa_col]).strip()
            if not anketa or anketa.lower() == 'nan':
                continue
            sana_qiymat = row[sana_col]
            sana = sana_qiymat.strftime('%d.%m.%Y') if hasattr(sana_qiymat, 'strftime') else str(sana_qiymat)
            vaqt = str(row[vaqt_col]) if vaqt_col and str(row[vaqt_col]).lower() != 'nan' else ''
            nomi = str(row[nomi_col]) if nomi_col and str(row[nomi_col]).lower() != 'nan' else ''
            ish_raqami = str(row[ish_col]) if ish_col and str(row[ish_col]).lower() != 'nan' else ''
            rows = db.get_portfel_by_anketa(anketa)
            mijoz_nomi = rows[0]['mijoz_nomi'] if rows else ''
            db.sud_kuni_qoshish(anketa, mijoz_nomi, sana, vaqt, nomi, ish_raqami)
            qoshilgan += 1
        except Exception as e:
            xatolar.append(f"{i + 2}-qator: {e}")
    return jsonify({'qoshilgan': qoshilgan, 'xatolar': xatolar})


@bp.route('/api/sud/kunlari/<int:sud_kuni_id>', methods=['DELETE'])
def sud_kuni_ochirish_endpoint(sud_kuni_id):
    db.sud_kuni_ochirish(sud_kuni_id)
    return jsonify({'ok': True})


@bp.route('/api/sud/kunlari/eslatmalar', methods=['GET'])
def sud_kunlari_eslatmalar_endpoint():
    """Ertaga sud bo'ladigan mijozlar ro'yxatini qaytaradi. MUHIM: shu bilan
    birga, ertangi sud kunlari uchun "Ma'lumotnoma (sud kuni)" hujjati
    hali yaratilmagan bo'lsa, TIZIM O'ZI AVTOMATIK yaratib qo'yadi — sud
    kunidan aynan 1 kun oldin, Davo summasi bilan HOZIRGI (joriy portfel)
    qarzdorlikni solishtirib."""
    natija = db.sud_kunlari_eslatmalari()
    for kun in natija['ertaga']:
        try:
            conn = db.get_conn()
            xat_row = conn.execute('SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1', (kun['anketa_raqami'],)).fetchone()
            conn.close()
            if not xat_row:
                continue
            xat = dict(xat_row)
            if xat.get('sud_malumotnoma_kun_fayl') and os.path.exists(xat['sud_malumotnoma_kun_fayl']):
                continue  # allaqachon yaratilgan — qayta yaratmaymiz
            if not xat.get('sud_yigma_jild_papka'):
                continue  # yig'ma jild hali yaratilmagan bo'lsa, joy yo'q
            prow = db.get_portfel_by_id(xat['portfel_id'])
            turi, mijoz = util.resolve_mijoz(prow) if prow else (xat.get('mijoz_turi'), None)
            settings = db.get_all_settings()
            fayl_yoli = os.path.join(xat['sud_yigma_jild_papka'], '01b_Malumotnoma_sud_kuni.docx')
            letters.generate_malumotnoma_sud_kuni(fayl_yoli, xat, prow, mijoz, settings)
            db.sud_hujjat_saqlash(xat['id'], 'sud_malumotnoma_kun_fayl', fayl_yoli)
            kun['malumotnoma_yaratildi'] = True
        except Exception as e:
            kun['malumotnoma_xato'] = str(e)
    return jsonify(natija)


@bp.route('/api/sud/xarajatlar', methods=['GET'])
def sud_xarajatlar_royxat_endpoint():
    db.sud_xarajatlar_tolov_moslashtirish_tekshirish()
    return jsonify({'royxat': db.sud_xarajatlar_royxati()})


@bp.route('/api/sud/xarajatlar', methods=['POST'])
def sud_xarajat_qoshish_endpoint():
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami', '').strip()
    summa = data.get('summa')
    if not anketa or not summa:
        return jsonify({'xato': 'anketa_raqami va summa kerak'}), 400
    rows = db.get_portfel_by_anketa(anketa)
    if not rows:
        return jsonify({'xato': 'Bu anketa portfelda topilmadi'}), 404
    prow = rows[0]
    conn = db.get_conn()
    xat_row = conn.execute('SELECT id FROM xatlar WHERE anketa_raqami=?', (anketa,)).fetchone()
    conn.close()
    pinfl_stir = prow.get('pinfl') or prow.get('stir') or ''
    db.sud_xarajat_qoshish(xat_row['id'] if xat_row else None, anketa, prow['mijoz_nomi'], pinfl_stir, float(summa))
    return jsonify({'ok': True})


@bp.route('/api/sud/xarajatlar_shablon', methods=['GET'])
def sud_xarajatlar_shablon():
    import tempfile
    from flask import send_file
    import pandas as pd
    df = pd.DataFrame(columns=['Anketa raqami', 'Mijoz nomi (ixtiyoriy)', 'PINFL/STIR (ixtiyoriy)', 'Xarajat summasi'])
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='sud_xarajatlar_shabloni.xlsx')


@bp.route('/api/sud/xarajatlar_excel_yuklash', methods=['POST'])
def sud_xarajatlar_excel_yuklash():
    """Sud pochta xarajatlarini Excel orqali ommaviy yuklaydi. Ustunlar:
    Anketa raqami, Mijoz nomi (ixtiyoriy), PINFL/STIR (ixtiyoriy), Xarajat summasi.
    Mijoz nomi/PINFL berilmasa, portfeldan avtomatik olinadi."""
    import pandas as pd
    f = request.files.get('file')
    if not f:
        return jsonify({'xato': 'Fayl yuborilmadi'}), 400
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    xato_natija = mustahkam_fayl_saqlash(f, tmp_path)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    try:
        df = pd.read_excel(tmp_path)
    finally:
        os.remove(tmp_path)

    anketa_col = next((c for c in df.columns if 'anketa' in str(c).lower()), None)
    summa_col = next((c for c in df.columns if 'summa' in str(c).lower()), None)
    ism_col = next((c for c in df.columns if 'mijoz' in str(c).lower() or 'nomi' in str(c).lower()), None)
    pinfl_col = next((c for c in df.columns if 'pinfl' in str(c).lower() or 'stir' in str(c).lower()), None)
    if not anketa_col or not summa_col:
        return jsonify({'xato': "Fayl tuzilmasi tanilmadi — 'Anketa raqami' va 'Xarajat summasi' ustunlari kerak"}), 400

    qoshilgan, xatolar = 0, []
    for i, row in df.iterrows():
        try:
            anketa_qiymat = row[anketa_col]
            if isinstance(anketa_qiymat, float):
                anketa = str(int(anketa_qiymat))
            else:
                anketa = str(anketa_qiymat).strip()
                if anketa.endswith('.0'):
                    anketa = anketa[:-2]
            if not anketa or anketa.lower() == 'nan':
                continue
            summa_qiymat = row[summa_col]
            if str(summa_qiymat).lower() == 'nan':
                continue
            summa = float(summa_qiymat)

            rows = db.get_portfel_by_anketa(anketa)
            prow = rows[0] if rows else None
            mijoz_nomi = str(row[ism_col]).strip() if ism_col and str(row[ism_col]).strip().lower() != 'nan' else None
            if not mijoz_nomi:
                mijoz_nomi = prow['mijoz_nomi'] if prow else ''
            pinfl_stir = str(row[pinfl_col]).strip() if pinfl_col and str(row[pinfl_col]).strip().lower() != 'nan' else None
            if not pinfl_stir:
                pinfl_stir = (prow.get('pinfl') or prow.get('stir') or '') if prow else ''

            conn = db.get_conn()
            xat_row = conn.execute('SELECT id FROM xatlar WHERE anketa_raqami=?', (anketa,)).fetchone()
            conn.close()
            db.sud_xarajat_qoshish(xat_row['id'] if xat_row else None, anketa, mijoz_nomi, pinfl_stir, summa)
            qoshilgan += 1
        except Exception as e:
            xatolar.append(f"{i + 2}-qator: {e}")

    return jsonify({'qoshilgan': qoshilgan, 'xatolar': xatolar})


@bp.route('/api/sud/xarajatlar/<int:xarajat_id>/mib_ochish', methods=['POST'])
def sud_xarajat_mib_ochish_endpoint(xarajat_id):
    """Mijozning sud qarori 'bank foydasiga' bo'lib, MIBga o'tkazilgach —
    pochta xarajati summasiga teng YANGI, ALOHIDA ijro ishi avtomatik
    ochiladi (o'sha sud ish raqami bilan bog'liq holda)."""
    data = request.get_json() or {}
    mib_ijro_ish_raqami = data.get('mib_ijro_ish_raqami', '')
    db.sud_xarajat_mib_ish_ochish(xarajat_id, mib_ijro_ish_raqami)
    return jsonify({'ok': True})
