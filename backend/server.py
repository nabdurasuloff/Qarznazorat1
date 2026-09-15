# -*- coding: utf-8 -*-
"""
Qarz Nazorat — Web/Electron versiyasi uchun API server.
Bu server mavjud database.py, letters.py, importer.py, util.py
modullarini o'zgartirmasdan qayta ishlatadi — faqat ularga HTTP
orqali kirish imkonini beradi.
"""
import os
import sys
import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database as db
import util
import letters
import importer

app = Flask(__name__)
CORS(app)

db.init_db()


def mustahkam_fayl_saqlash(f, tmp_path, ozbek_kengaytma_tekshiruvi=True):
    """Yuklangan faylni (Excel/Word) diskka MUSTAHKAM usulda yozadi: to'liq
    xotiraga o'qib, binary rejimda flush+fsync bilan saqlaydi. Bu ba'zi
    Windows muhitlarida (masalan antivirus fayl yozilayotgan paytda
    tekshirsa) faylning yarim yozilgan holda o'qilib qolishi ("incorrect
    header check" kabi tushunarsiz xatolar) ehtimolini kamaytiradi.
    Agar fayl .xlsx/.xlsb/.docx bo'lib, lekin ZIP tuzilishiga mos kelmasa
    (PK bilan boshlanmasa), tushunarli xato qaytaradi. ZIP-tekshiruvi
    yoqilmagan hollarda (masalan .txt, .pdf) hajm chegarasi qo'llanmaydi —
    kichik matn/hujjat fayllari ham haqiqiy va yaroqli bo'lishi mumkin.
    Muvaffaqiyatli bo'lsa None, aks holda (xabar, http_kod) qaytaradi."""
    baytlar = f.read()
    if len(baytlar) == 0:
        return ("Yuklangan fayl bo'sh — qayta urinib ko'ring.", 400)
    if ozbek_kengaytma_tekshiruvi:
        if len(baytlar) < 100:
            return ("Yuklangan fayl juda kichik — qayta urinib ko'ring.", 400)
        if baytlar[:2] != b'PK':
            return ("Fayl to'liq yuklanmadi yoki buzilgan (ZIP formatiga mos emas). "
                     "Iltimos, faylni qaytadan tanlab, qayta urinib ko'ring.", 400)
    with open(tmp_path, 'wb') as out:
        out.write(baytlar)
        out.flush()
        os.fsync(out.fileno())
    return None

AMAL_TURLARI_MAP = {
    'oylik_ish_haqqi': "Oylik ish haqqiga qaratildi",
    'avto_taqiq': "Avto transportga taqiq qo'yildi",
    'avto_qidiruv': "Avto transport qidiruvga berildi",
    'chetga_chiqish_taqiq': "Chetga chiqishga taqiq qo'yilgan",
    'majburiy_xatlov': "Majburiy xatlov o'tkazildi",
    'sotish_togridan': "To'g'ridan-to'g'ri sotildi",
    'sotish_auksion': "Auksion yo'li bilan sotildi",
    'kafil_ish': "Kafil bo'yicha ish qilindi",
    'garov_xatlov': "Garov mulkiga xatlov o'tkazildi",
    'garov_sotish': "Garov mulki sotildi",
    'eski_ish_kiritildi': "Eski ish sifatida bazaga kiritildi",
    'ish_haqiga_qaratish': "Oylik ish haqqiga qaratildi",
}


def hujjatlar_papkasi():
    """Yaratilgan hujjatlar (xat, Davo ariza, MIB, sug'urta) saqlanadigan asosiy
    papka. Sozlamalarda ko'rsatilgan bo'lsa o'sha joy, aks holda standart papka
    (dastur ishga tushirilgan joy) ishlatiladi. Shu bilan foydalanuvchi
    hujjatlarni istalgan diskda (masalan D:\\) saqlashi mumkin."""
    sozlama = db.get_all_settings().get('hujjatlar_papkasi', '').strip()
    papka = sozlama if sozlama else os.path.join(db._app_dir(), 'yaratilgan_xatlar')
    os.makedirs(papka, exist_ok=True)
    return papka


def tizimdan_oldingi_hujjatlar_papkasi():
    """Yangi tizim (papka tuzilmasi) joriy etilishidan OLDIN qilingan
    hujjatlar uchun — foydalanuvchi eski hujjatlarni qo'lda shu papkaga
    ko'chiradi (masalan avvalgi 'qarznazorati' papkasidan). Tizim bu
    papka ichidan anketa raqami yoki mijoz nomi bo'yicha QIDIRISH orqali
    eski hujjatlarni topib bera oladi — hatto ular tartibsiz saqlangan
    bo'lsa ham."""
    papka = os.path.join(hujjatlar_papkasi(), 'Tizimdan oldin')
    os.makedirs(papka, exist_ok=True)
    return papka


def huquqiy_choralar_papkasi():
    """MUHIM (yangi tuzilma): barcha huquqiy chora hujjatlari uchun YAGONA
    ota papka — 'Huquqiy choralar'. Shu papka ichida hujjat turiga (Xat,
    Davo ariza, Sud qaror, Ijro varaqalari) va alohida Sud/MIB hujjatlari
    tarkibiga ko'ra tartiblangan quyi papkalar joylashadi."""
    papka = os.path.join(hujjatlar_papkasi(), 'Huquqiy choralar')
    os.makedirs(papka, exist_ok=True)
    return papka


def hujjat_turi_sana_papkasi(hujjat_turi):
    """'Huquqiy choralar' ichida, HUJJAT TURIGA (masalan 'Xat', 'Davo ariza',
    'Sud qaror', 'Ijro varaqalari') qarab, va ICHIDA yaratilgan sanaga
    (kun.oy.yil) qarab tartiblangan papka yo'lini qaytaradi:
        Huquqiy choralar/[Hujjat turi]/[bugungi sana]/"""
    sana_papka = datetime.datetime.now().strftime('%d.%m.%Y')
    path = os.path.join(huquqiy_choralar_papkasi(), hujjat_turi, sana_papka)
    os.makedirs(path, exist_ok=True)
    return path


def sud_hujjatlari_mijoz_papkasi(mijoz_nomi, sana_dt=None, anketa_raqami=None):
    """Sud uchun yaratilgan BARCHA hujjatlar (yig'ma jild tarkibidagilar)
    joylashadigan papka: Huquqiy choralar/Sud hujjatlari/[sana]/[mijoz nomi]_[anketa]/
    MUHIM 1: 'sana_dt' — SIKL BOSHLANGAN sana (masalan xatning yaratilgan
    sanasi) bo'lishi kerak, 'bugungi kun' emas — aks holda bitta sikl
    hujjatlari, ular turli kunlarda yuklansa, turli papkalarga bo'linib
    ketardi.
    MUHIM 2: papka nomiga ANKETA RAQAMI ham albatta qo'shiladi — aks
    holda, agar BITTA mijozning bir necha (turli kredit bo'yicha) anketasi
    bo'lsa, ularning barchasi bitta papkaga tushib, hujjatlar bir-birini
    bosib yozib yuborishi mumkin edi."""
    sana_papka = (sana_dt or datetime.datetime.now()).strftime('%d.%m.%Y')
    papka_nomi = letters.safe_filename(mijoz_nomi)
    if anketa_raqami:
        papka_nomi = f"{papka_nomi}_{letters.safe_filename(anketa_raqami)}"
    path = os.path.join(huquqiy_choralar_papkasi(), 'Sud hujjatlari', sana_papka, papka_nomi)
    os.makedirs(path, exist_ok=True)
    return path


def mib_hujjatlari_mijoz_papkasi(mijoz_nomi, sana_dt=None, anketa_raqami=None):
    """MIB uchun yaratilgan BARCHA hujjatlar (yig'ma jild tarkibidagilar)
    joylashadigan papka: Huquqiy choralar/MIB hujjatlari/[sana]/[mijoz nomi]_[anketa]/
    MUHIM: yuqoridagi izohlarga qarang — sana SIKL sanasi, papka nomida
    ANKETA RAQAMI ham bo'lishi shart (bir mijozning bir necha anketasi
    aralashib ketmasligi uchun)."""
    sana_papka = (sana_dt or datetime.datetime.now()).strftime('%d.%m.%Y')
    papka_nomi = letters.safe_filename(mijoz_nomi)
    if anketa_raqami:
        papka_nomi = f"{papka_nomi}_{letters.safe_filename(anketa_raqami)}"
    path = os.path.join(huquqiy_choralar_papkasi(), 'MIB hujjatlari', sana_papka, papka_nomi)
    os.makedirs(path, exist_ok=True)
    return path


def f95413_mijoz_papkasi(mijoz_nomi, anketa_raqami=None):
    """'95413' (balansdan chiqarilgan kreditlar) papkasi ichida, HAR BIR
    mijoz (VA aniq anketa) uchun ALOHIDA papka: 95413/[mijoz nomi]_[anketa]/
    — bu yerga o'sha mijoz uchun qilingan barcha hujjatlar (Xat, Davo
    ariza, Sud qaror, Ijro varaqasi) nusxasi ham avtomatik saqlanadi.
    MUHIM: agar bitta mijozning bir necha (turli kredit bo'yicha) anketasi
    bo'lsa, ular ANKETA RAQAMI orqali ajratiladi — aks holda hujjatlar
    bir-birini bosib yozib yuborishi mumkin edi."""
    papka_nomi = letters.safe_filename(mijoz_nomi)
    if anketa_raqami:
        papka_nomi = f"{papka_nomi}_{letters.safe_filename(anketa_raqami)}"
    path = os.path.join(hujjatlar_papkasi(), '95413', papka_nomi)
    os.makedirs(path, exist_ok=True)
    return path


def f95413_hujjatlarni_nusxalash(mijoz_nomi, xat_dict, anketa_raqami=None):
    """Agar bir mijoz 95413 ro'yxatida ilk bor ko'rinsa (yoki har safar
    tekshirilganda) — uning ENG SO'NGGI Sud va MIB yig'ma jild hujjatlarini
    (agar mavjud bo'lsa) 95413/[mijoz]_[anketa]/ papkasiga avtomatik
    nusxalab qo'yadi, hujjat turi nomlari bilan (Xat_..., Davo_ariza_...,
    kabi)."""
    if not xat_dict:
        return
    maqsad = f95413_mijoz_papkasi(mijoz_nomi, anketa_raqami)
    nusxalar = [
        ('fayl_yoli', 'Xat'),
        ('davo_ariza_fayl_yoli', 'Davo_ariza'),
        ('sud_qaror_fayl', 'Sud_qaror'),
        ('sud_buyrugi_fayl', 'Sud_qaror'),
        ('ijro_varaqasi_fayl', 'Ijro_varaqasi'),
    ]
    nomlar_uzbekcha = {'Xat': 'Xat', 'Davo_ariza': 'Davo ariza', 'Sud_qaror': 'Sud qarori',
                       'Ijro_varaqasi': 'Ijro varaqasi'}
    for maydon, prefiks in nusxalar:
        manba = xat_dict.get(maydon)
        if manba and os.path.exists(manba):
            nomi = f"{prefiks}_{os.path.basename(manba)}"
            maqsad_fayl = os.path.join(maqsad, nomi)
            if not os.path.exists(maqsad_fayl):
                import shutil
                try:
                    shutil.copy2(manba, maqsad_fayl)
                    # MUHIM: fayl jismonan nusxalanishi bilan bir qatorda,
                    # "Yig'ma jild" oynasida ham ko'rinishi uchun, uni
                    # f95413_hujjatlar jadvaliga ham QAYD ETAMIZ — aks
                    # holda fayl papkada bo'lsa-da, tizim oynasida
                    # ko'rinmay qolar edi.
                    if anketa_raqami:
                        db.f95413_hujjat_qoshish(anketa_raqami, nomlar_uzbekcha.get(prefiks, prefiks), maqsad_fayl)
                except Exception:
                    pass

    # MUHIM (qo'shildi): KREDIT HUJJATLARI (Kredit shartnoma, Kafillik,
    # Garov, Bank baholash) ham — bular Sud bosqichida yuklangan bo'lsa,
    # DOIMIY arxiv jadvalidan (kredit_hujjatlar_arxiv — "Nollashtirish"
    # qilingan bo'lsa ham saqlanadi) avtomatik topilib, 95413 jildiga
    # ham nusxalanadi.
    kredit_nomlari = {
        'kredit_shartnoma_fayl': 'Kredit shartnomasi',
        'kafillik_shartnoma_fayl': 'Kafillik shartnomasi',
        'garov_shartnoma_fayl': 'Garov shartnomasi',
        'bank_baholash_fayl': 'Bank baholashi',
    }
    if anketa_raqami:
        conn = db.get_conn()
        arxiv_row = conn.execute(
            'SELECT * FROM kredit_hujjatlar_arxiv WHERE anketa_raqami=?', (anketa_raqami,)).fetchone()
        conn.close()
        arxiv = dict(arxiv_row) if arxiv_row else {}
        for maydon, nomi_uzb in kredit_nomlari.items():
            manba = xat_dict.get(maydon) or arxiv.get(maydon)
            if manba and os.path.exists(manba):
                nomi = f"{letters.safe_filename(nomi_uzb)}_{os.path.basename(manba)}"
                maqsad_fayl = os.path.join(maqsad, nomi)
                if not os.path.exists(maqsad_fayl):
                    import shutil
                    try:
                        shutil.copy2(manba, maqsad_fayl)
                        db.f95413_hujjat_qoshish(anketa_raqami, nomi_uzb, maqsad_fayl)
                    except Exception:
                        pass


def mib_hujjatlar_papkasi():
    sozlama = db.get_all_settings().get('hujjatlar_papkasi', '').strip()
    papka = os.path.join(sozlama, 'mib_hujjatlar') if sozlama else os.path.join(db._app_dir(), 'mib_hujjatlar')
    os.makedirs(papka, exist_ok=True)
    return papka


def bugungi_papka(tur=None):
    """MUHIM (yangilandi): endi barcha huquqiy chora hujjatlari (Xat, Davo
    ariza, Sud qaror, Ijro varaqalari) 'Huquqiy choralar' YAGONA ota papkasi
    ichida, tur bo'yicha va sanasi bo'yicha tartiblanadi:
        Huquqiy choralar/[tur]/[sana]/
    Eski chaqiruvchilar bilan moslik uchun funksiya nomi saqlab qolindi."""
    if tur:
        return hujjat_turi_sana_papkasi(tur)
    sana_papka = datetime.datetime.now().strftime('%d.%m.%Y')
    path = os.path.join(huquqiy_choralar_papkasi(), sana_papka)
    os.makedirs(path, exist_ok=True)
    return path


def row_list(rows):
    """sqlite3.Row ro'yxatini JSON-serializable dict ro'yxatiga aylantiradi."""
    return [dict(r) for r in rows] if rows else []


# ---------------------------------------------------------------------------
# AUTENTIFIKATSIYA
# ---------------------------------------------------------------------------
@app.route('/api/auth/status', methods=['GET'])
def auth_status():
    return jsonify({'parol_kerak': db.parol_ornatilganmi(), 'kop_foydalanuvchi': db.foydalanuvchilar_bormi()})


@app.route('/api/auth/login', methods=['POST'])
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


@app.route('/api/foydalanuvchilar', methods=['GET'])
def foydalanuvchilar_royxat():
    return jsonify({'royxat': db.foydalanuvchilar_royxati()})


@app.route('/api/foydalanuvchilar', methods=['POST'])
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


@app.route('/api/foydalanuvchilar/<int:user_id>', methods=['DELETE'])
def foydalanuvchilar_ochirish_endpoint(user_id):
    db.foydalanuvchi_ochirish(user_id)
    return jsonify({'ok': True})


@app.route('/api/foydalanuvchilar/<int:user_id>/faollik', methods=['POST'])
def foydalanuvchilar_faollik_endpoint(user_id):
    data = request.get_json() or {}
    db.foydalanuvchi_faollik(user_id, data.get('faol', True))
    return jsonify({'ok': True})


@app.route('/api/sozlamalar', methods=['GET'])
def sozlamalar_get():
    return jsonify(db.get_all_settings())


@app.route('/api/sozlamalar', methods=['POST'])
def sozlamalar_save():
    data = request.get_json() or {}
    for kalit, qiymat in data.items():
        db.set_setting(kalit, qiymat)
    return jsonify({'ok': True})


@app.route('/api/sozlamalar/parol', methods=['POST'])
def sozlamalar_parol():
    data = request.get_json() or {}
    yangi_parol = data.get('yangi_parol', '').strip()
    if not yangi_parol:
        return jsonify({'xato': "Yangi parolni kiriting"}), 400
    db.parol_ornatish(yangi_parol)
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# SHABLONLAR (Word) — ko'rish / yuklash / qayta tayyorlash
# ---------------------------------------------------------------------------
def _shablon_maplanishi():
    return {
        'xat': (letters.TEMPLATE_PATH, 'xat_shablon.docx'),
        'sugurta': (letters.SUGURTA_XABARNOMA_TEMPLATE_PATH, 'sugurta_xabarnoma_shablon.docx'),
        'yigma_jild': (letters.YIGMA_JILD_TITUL_TEMPLATE_PATH, 'yigma_jild_titul_shablon.docx'),
        'reestr_ssp': (letters.REESTR_SSP_TEMPLATE_PATH, 'reestr_ssp_shablon.docx'),
        'malumotnoma_topshirishda': (letters.MALUMOTNOMA_TOPSHIRISHDA_TEMPLATE_PATH, 'malumotnoma_topshirishda_shablon.docx'),
        'malumotnoma_kun': (letters.MALUMOTNOMA_KUN_TEMPLATE_PATH, 'malumotnoma_kun_shablon.docx'),
        'sud_yigma_jild': (letters.SUD_YIGMA_JILD_TITUL_TEMPLATE_PATH, 'sud_yigma_jild_titul_shablon.docx'),
    }


@app.route('/api/shablon/davo_turlari', methods=['GET'])
def shablon_davo_turlari():
    return jsonify({'turlari': letters.DAVO_ARIZA_NOMLARI})


@app.route('/api/shablon/korish', methods=['GET'])
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


@app.route('/api/shablon/yuklash', methods=['POST'])
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


@app.route('/api/shablon/qayta_tayyorlash', methods=['POST'])
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


# ---------------------------------------------------------------------------
# BOSH SAHIFA / DASHBOARD
# ---------------------------------------------------------------------------
@app.route('/api/talabnoma/qayta_xat_eslatmalari', methods=['GET'])
def talabnoma_qayta_xat_eslatmalari():
    """To'lov muddati o'tgan, LEKIN hech qanday chora (Davo ariza)
    ko'rilmagan mijozlar ro'yxati — yangi xat tayyorlab yuborish
    TAVSIYA etiladi (avtomatik yaratilmaydi)."""
    return jsonify({'royxat': db.xat_qayta_yuborish_eslatmalari()})


@app.route('/api/dashboard/summary', methods=['GET'])
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


@app.route('/api/dashboard/qidirish', methods=['GET'])
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


@app.route('/api/dashboard/songgi_harakatlar', methods=['GET'])
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


# ---------------------------------------------------------------------------
# TALABNOMA
# ---------------------------------------------------------------------------
@app.route('/api/talabnoma/royxat', methods=['GET'])
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

    natija = []
    for r in rows:
        turi, mijoz = util.resolve_mijoz(r)
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


@app.route('/api/talabnoma/xat_yaratish', methods=['POST'])
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


@app.route('/api/talabnoma/xatlar_hisoboti', methods=['GET'])
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


@app.route('/api/talabnoma/xat_qidirish', methods=['GET'])
def talabnoma_xat_qidirish():
    anketa = request.args.get('anketa', '').strip()
    conn = db.get_conn()
    rows = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami LIKE ?", (f'%{anketa}%',)).fetchall()
    conn.close()
    return jsonify({'ids': [r['id'] for r in rows]})


@app.route('/api/talabnoma/xat_yuborildi_belgilash_ommaviy', methods=['POST'])
def talabnoma_xat_yuborildi_belgilash_ommaviy():
    data = request.get_json() or {}
    ids = data.get('ids', [])
    for xat_id in ids:
        db.mark_xat_yuborildi(xat_id)
    return jsonify({'ok': True, 'yangilandi': len(ids)})


@app.route('/api/talabnoma/xat_ochirish', methods=['POST'])
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


@app.route('/api/talabnoma/barcha_tayyor_ochirish', methods=['POST'])
def talabnoma_barcha_tayyor_ochirish():
    ids = db.get_xatlar_ids_by_holat('tayyor') + db.get_xatlar_ids_by_holat('muddati_otgan')
    if not ids:
        return jsonify({'ochirildi': 0})
    n = db.delete_xatlar(ids)
    return jsonify({'ochirildi': n})


@app.route('/api/talabnoma/dublikatlarni_tozalash', methods=['POST'])
def talabnoma_dublikatlarni_tozalash():
    dup = db.get_duplicate_xat_anketalar()
    if not dup:
        return jsonify({'topildi': 0, 'ochirildi': 0})
    n = db.tozala_duplikat_xatlar()
    return jsonify({'topildi': len(dup), 'ochirildi': n})


@app.route('/api/talabnoma/qidirish', methods=['GET'])
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


@app.route('/api/talabnoma/excel_eksport', methods=['POST'])
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


@app.route('/api/talabnoma/excel_import', methods=['POST'])
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


# ---------------------------------------------------------------------------
# DAVO ARIZA
# ---------------------------------------------------------------------------
@app.route('/api/davo-ariza/turlari', methods=['GET'])
def davo_ariza_turlari():
    return jsonify({'turlari': letters.DAVO_ARIZA_NOMLARI})


@app.route('/api/davo-ariza/royxat', methods=['GET'])
def davo_ariza_royxat():
    xatlar = db.get_xatlar_yuborilgan_davo_kerak()

    # Tezlik uchun: barcha ta'minot yozuvlarini BITTA so'rovda olamiz
    conn = db.get_conn()
    taminot_rows = conn.execute('SELECT * FROM davo_taminot').fetchall()
    conn.close()
    taminot_map = {r['anketa_raqami']: dict(r) for r in taminot_rows}

    settings = db.get_all_settings()
    muddat_kun = int(settings.get('davo_ariza_muddati_kun', 5))

    natija = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        if not prow:
            continue
        taminot = taminot_map.get(x['anketa_raqami'])
        tavsiya_kaliti = letters.tavsiya_ariza_turi(x['mijoz_turi'], taminot)
        tavsiya_nomi = letters.DAVO_ARIZA_NOMLARI.get(tavsiya_kaliti, '')

        jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
        has_davo = bool(x.get('davo_ariza_fayl_yoli'))
        olib_kelindi = x.get('davo_ariza_holati') == 'olib_kelindi'

        holat = 'yoq'
        holat_matni = '—'
        if x.get('mib_holati') == 'otkazildi':
            holat = 'olib_kelindi'
            holat_matni = "✓ MIBga o'tkazilgan" + (" (yakunlangan)" if x.get('mib_yakunlangan') else "")
        elif x.get('sud_holati') == 'topshirildi':
            holat, holat_matni = 'olib_kelindi', "✓ Sudga topshirilgan"
        elif olib_kelindi:
            holat, holat_matni = 'olib_kelindi', '✓ Olib kelindi'
        elif has_davo:
            try:
                davo_dt = datetime.datetime.fromisoformat(x['davo_ariza_sana'])
                qolgan = muddat_kun - (datetime.datetime.now() - davo_dt).days
                if qolgan < 0:
                    holat, holat_matni = 'otgan', f"⚠ {abs(qolgan)} kun o'tib ketdi"
                else:
                    holat, holat_matni = 'tayyor', f"Tayyor — {qolgan} kun qoldi"
            except Exception:
                holat, holat_matni = 'tayyor', 'Tayyor'

        davo_summasi = (x.get('davo_summasi_asosiy') or 0) + (x.get('davo_summasi_foiz') or 0) + \
            (x.get('davo_summasi_jarima') or 0) if has_davo else 0

        summa_farqi_matn = '—'
        qoshimcha_kerak = False
        if has_davo:
            farqi = db.get_davo_ariza_farqi(x, prow, settings=settings)
            if farqi['farq'] > 0:
                summa_farqi_matn = f"+{format(int(farqi['farq']), ',').replace(',', ' ')} so'm"
                qoshimcha_kerak = farqi['qoshimcha_kerak']
                if qoshimcha_kerak:
                    summa_farqi_matn += " ⚠ Qo'shimcha ariza kerak"

        tayyorlangan_sana = ''
        if has_davo and x.get('davo_ariza_sana'):
            try:
                tayyorlangan_sana = datetime.datetime.fromisoformat(x['davo_ariza_sana']).strftime('%d.%m.%Y')
            except Exception:
                tayyorlangan_sana = x.get('davo_ariza_sana', '')

        natija.append({
            'xat_id': x['id'],
            'anketa_raqami': x['anketa_raqami'],
            'mijoz_nomi': x['mijoz_nomi'],
            'turi': x['mijoz_turi'],
            'jami_qarz': jami,
            'davo_summasi': davo_summasi,
            'davo_ariza_turi': x.get('davo_ariza_turi'),
            'tavsiya_kaliti': tavsiya_kaliti,
            'tavsiya_nomi': tavsiya_nomi,
            'holat': holat,
            'holat_matni': holat_matni,
            'ish_raqami': x.get('davo_ariza_ish_raqami', ''),
            'taminot_bor': bool(taminot and taminot.get('taminot_turi') not in (None, '', 'yoq')),
            'summa_farqi_matn': summa_farqi_matn,
            'qoshimcha_kerak': qoshimcha_kerak,
            'tayyorlangan_sana': tayyorlangan_sana,
        })
    return jsonify({'royxat': natija})


@app.route('/api/davo-ariza/yaratish', methods=['POST'])
def davo_ariza_yaratish():
    """Belgilangan anketalar uchun (har biriga o'z ta'minotiga qarab
    avtomatik to'g'ri tur tanlab) Davo ariza tayyorlaydi."""
    data = request.get_json() or {}
    anketalar = data.get('anketalar', [])
    settings = db.get_all_settings()

    yaratildi, otkazib_yuborildi, xatolar = 0, 0, []
    turlar_soni = {}
    for anketa in anketalar:
        if db.davo_ariza_mavjudmi(anketa):
            otkazib_yuborildi += 1
            continue
        xat = None
        conn = db.get_conn()
        row = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami=? AND holat='yuborildi'",
                            (anketa,)).fetchone()
        conn.close()
        xat = dict(row) if row else None
        if not xat:
            xatolar.append(f"{anketa}: xat topilmadi")
            continue
        prow = db.get_portfel_by_id(xat['portfel_id'])
        if not prow:
            xatolar.append(f"{anketa}: portfel topilmadi")
            continue
        try:
            mijoz_turi_calc, mijoz = util.resolve_mijoz(prow)
            taminot = db.get_taminot(anketa)
            turi = letters.tavsiya_ariza_turi(mijoz_turi_calc, taminot)
            turlar_soni[turi] = turlar_soni.get(turi, 0) + 1

            out_dir = bugungi_papka('Davo ariza')
            mijoz_ism = mijoz['ism'] if mijoz else xat['mijoz_nomi']
            fname = f"{letters.safe_filename(mijoz_ism)}_{letters.safe_filename(anketa)}_Davo_{turi}.docx"
            out_path = os.path.join(out_dir, fname)

            xat_sana = ''
            try:
                xat_sana = datetime.datetime.fromisoformat(xat['yaratilgan_sana']).strftime('%d.%m.%Y')
            except Exception:
                pass
            letters.generate_davo_ariza_v2(
                turi, out_path, prow, mijoz, taminot, settings, xat_sanasi=xat_sana,
                xat_turi_nomi=('Талабнома' if xat['xat_turi'] == 'Talabnoma' else 'Огохлантириш хати'),
            )
            db.mark_davo_ariza_yaratildi(xat['id'], out_path, turi=turi, portfel_row=prow)
            yaratildi += 1
        except Exception as e:
            xatolar.append(f"{anketa}: {e}")

    return jsonify({
        'yaratildi': yaratildi, 'otkazib_yuborildi': otkazib_yuborildi,
        'xatolar': xatolar, 'turlar_soni': turlar_soni,
    })


@app.route('/api/davo-ariza/taminot', methods=['GET'])
def davo_ariza_taminot_get():
    anketa = request.args.get('anketa', '').strip()
    t = db.get_taminot(anketa) or {}
    return jsonify(t)


@app.route('/api/davo-ariza/taminot', methods=['POST'])
def davo_ariza_taminot_save():
    data = request.get_json() or {}
    anketa = data.pop('anketa_raqami', None)
    if not anketa:
        return jsonify({'xato': 'anketa_raqami kerak'}), 400
    db.upsert_taminot(anketa, **data)
    return jsonify({'ok': True})


@app.route('/api/davo-ariza/olib_kelindi', methods=['POST'])
def davo_ariza_olib_kelindi():
    anketa = request.form.get('anketa_raqami')
    ish_raqami = request.form.get('ish_raqami', '')
    sana = request.form.get('sana', '')
    f = request.files.get('skan')
    if not anketa or not ish_raqami or not sana:
        return jsonify({'xato': 'anketa_raqami, ish_raqami va sana kerak'}), 400
    if not f or not f.filename:
        return jsonify({'xato': "SSPdan olib kelingan hujjat skanini (PDF) yuklash majburiy"}), 400

    conn = db.get_conn()
    row = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami=? AND davo_ariza_fayl_yoli IS NOT NULL",
                        (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Davo arizasi tayyorlangan xat topilmadi'}), 404
    xat = dict(row)
    prow = db.get_portfel_by_id(xat['portfel_id'])
    settings = db.get_all_settings()

    # MUHIM: SSPdan olib kelingan (imzo/muhr bilan tasdiqlangan) rasmiy skan
    # Davo ariza faylining o'rniga saqlanadi — bu yig'ma jildga ham
    # avtomatik rasmiy nusxa tushishini ta'minlaydi.
    out_dir = bugungi_papka('SSP_tasdiqlangan')
    os.makedirs(out_dir, exist_ok=True)
    ext = os.path.splitext(f.filename)[1] or '.pdf'
    dest = os.path.join(out_dir, f"{letters.safe_filename(xat['mijoz_nomi'])}_{anketa}_SSP_tasdiqlangan{ext}")
    xato_natija = mustahkam_fayl_saqlash(f, dest, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    db.update_davo_ariza_fayl(xat['id'], dest)

    qoshimcha_kerak = db.mark_davo_ariza_olib_kelindi(xat['id'], ish_raqami, sana, portfel_row=prow, settings=settings)
    natija = {'ok': True}
    if qoshimcha_kerak:
        xat_yangi = db.get_xat_by_id(xat['id'])
        farqi = db.get_davo_ariza_farqi(xat_yangi, prow, settings)
        natija['ogohlantirish'] = (
            f"Davo ariza 'Olib kelindi' deb belgilandi. Diqqat: joriy qarzdorlik Davo ariza "
            f"yaratilgan paytdagi summadan {int(farqi['farq']):,} so'mga oshib ketgan — "
            f"qo'shimcha (yangi) SSP davo ariza kiritish talab qilinadi.".replace(',', ' ')
        )
    return jsonify(natija)


@app.route('/api/davo-ariza/ochirish', methods=['POST'])
def davo_ariza_ochirish():
    data = request.get_json() or {}
    anketalar = data.get('anketalar', [])
    ochirildi, otkazib_yuborildi = 0, 0
    for anketa in anketalar:
        conn = db.get_conn()
        row = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami=? AND davo_ariza_fayl_yoli IS NOT NULL",
                            (anketa,)).fetchone()
        conn.close()
        if not row:
            otkazib_yuborildi += 1
            continue
        xat = dict(row)
        if xat.get('sud_holati') == 'topshirildi':
            otkazib_yuborildi += 1
            continue
        db.reset_davo_ariza(xat['id'])
        ochirildi += 1
    return jsonify({'ochirildi': ochirildi, 'otkazib_yuborildi': otkazib_yuborildi})


@app.route('/api/davo-ariza/taminot_excel_eksport', methods=['POST'])
def davo_ariza_taminot_excel_eksport():
    import tempfile
    from flask import send_file
    data = request.get_json() or {}
    anketalar = data.get('anketalar', [])
    rows = []
    for anketa in anketalar:
        prow_list = db.get_portfel_by_anketa(anketa)
        mijoz_nomi = prow_list[0].get('mijoz_nomi', '') if prow_list else ''
        t = db.get_taminot(anketa) or {}
        rows.append({'anketa_raqami': anketa, 'mijoz_nomi': mijoz_nomi, **t})
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    importer.export_taminot_excel(rows, tmp_path)
    return send_file(tmp_path, as_attachment=True, download_name='taminot.xlsx')


@app.route('/api/davo-ariza/taminot_excel_import', methods=['POST'])
def davo_ariza_taminot_excel_import():
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
        result = importer.import_taminot_excel(tmp_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({'xato': str(e)}), 400
    finally:
        os.remove(tmp_path)


@app.route('/api/davo-ariza/imzodan_excel_eksport', methods=['POST'])
def davo_ariza_imzodan_excel_eksport():
    import tempfile
    from flask import send_file
    import pandas as pd
    royxat = db.get_olib_kelinganlar_royxati()
    if not royxat:
        return jsonify({'xato': "Hali Palatadan/imzodan qaytgan Davo arizalar yo'q."}), 400
    rows = []
    for item in royxat:
        xat = item['xat']
        rows.append({
            'Anketa raqami': xat['anketa_raqami'], 'Mijoz': xat['mijoz_nomi'],
            'PINFL/STIR': item.get('pinfl', ''),
            'Ish raqami': xat.get('davo_ariza_ish_raqami', '') or '',
            'Chiqqan sana': xat.get('davo_ariza_imzo_sana', '') or '',
            'Davo summasi (asosiy)': item['davo_summasi_asosiy'],
            'Davo summasi (foiz)': item['davo_summasi_foiz'],
            'Davo summasi (jarima)': item['davo_summasi_jarima'],
            'Jami davo summasi': item['davo_summasi'],
            'Joriy qarzdorlik': item['joriy_qarz'],
            'Farq': item['farq'],
            "Qo'shimcha ariza kerakmi": "✓ Ha" if item['qoshimcha_kerak'] else "Yo'q",
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='imzodan_kelganlar.xlsx')


@app.route('/api/davo-ariza/sudga_topshirilganlar_excel', methods=['GET'])
def sudga_topshirilganlar_excel():
    import tempfile
    from flask import send_file
    import pandas as pd
    royxat = db.get_sudga_topshirilganlar_royxati()
    if not royxat:
        return jsonify({'xato': "Hozircha sudga topshirilgan ish yo'q"}), 400
    rows = []
    for item in royxat:
        xat = item['xat']
        prow = item['portfel']
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else xat.get('mijoz_turi')
        asosiy = xat.get('davo_summasi_asosiy') or 0
        foiz = xat.get('davo_summasi_foiz') or 0
        jarima = xat.get('davo_summasi_jarima') or 0
        rows.append({
            'Anketa raqami': xat['anketa_raqami'], 'Mijoz': xat['mijoz_nomi'], 'Turi': turi,
            'Davo summasi (jami)': asosiy + foiz + jarima,
            'Davo ariza tasdiqlangan (imzo) sanasi': xat.get('davo_ariza_imzo_sana', '') or '',
            "Sudga yuborishga ruxsat berilganmi": "Ha" if xat.get('sud_hujjatlar_ruxsat') else "Yo'q",
            'Sud ish raqami': xat.get('sud_ish_raqami', '') or '',
            'Sudga topshirilgan sana': xat.get('sud_topshirilgan_sana', '') or '',
            'Asosiy qarz': asosiy, 'Foiz': foiz, 'Penya (jarima)': jarima,
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='sudga_topshirilganlar.xlsx')


@app.route('/api/davo-ariza/reestr', methods=['POST'])
def davo_ariza_reestr():
    import tempfile
    from flask import send_file
    data = request.get_json() or {}
    anketalar = data.get('anketalar', [])
    xat_raqami = data.get('xat_raqami', '')
    xat_sanasi = data.get('xat_sanasi', '')
    settings = db.get_all_settings()

    mijozlar_royxati = []
    for anketa in anketalar:
        conn = db.get_conn()
        row = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami=? AND davo_ariza_fayl_yoli IS NOT NULL",
                            (anketa,)).fetchone()
        conn.close()
        if not row:
            continue
        xat = dict(row)
        davo_summasi = (xat.get('davo_summasi_asosiy') or 0) + (xat.get('davo_summasi_foiz') or 0) + \
            (xat.get('davo_summasi_jarima') or 0)
        mijozlar_royxati.append({
            'anketa_raqami': anketa, 'mijoz_ism': xat['mijoz_nomi'], 'summa': davo_summasi,
        })
    if not mijozlar_royxati:
        return jsonify({'xato': "Davo arizasi tayyorlangan mijoz topilmadi"}), 400

    with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp:
        tmp_path = tmp.name
    letters.generate_reestr_ssp(tmp_path, mijozlar_royxati, xat_raqami, xat_sanasi, settings)
    return send_file(tmp_path, as_attachment=True, download_name='Reestr_SSP.docx')


@app.route('/api/davo-ariza/birlashtir', methods=['POST'])
def davo_ariza_birlashtir():
    import tempfile
    from flask import send_file
    data = request.get_json() or {}
    anketalar = data.get('anketalar', [])

    fayllar, turlari = [], []
    for anketa in anketalar:
        conn = db.get_conn()
        row = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami=? AND davo_ariza_fayl_yoli IS NOT NULL",
                            (anketa,)).fetchone()
        conn.close()
        if not row:
            continue
        xat = dict(row)
        if xat.get('davo_ariza_fayl_yoli') and os.path.exists(xat['davo_ariza_fayl_yoli']):
            fayllar.append(xat['davo_ariza_fayl_yoli'])
            turlari.append(xat.get('davo_ariza_turi'))

    if len(fayllar) < 2:
        return jsonify({'xato': "Birlashtirish uchun kamida 2 ta tayyorlangan Davo ariza kerak"}), 400

    bir_xil = len(set(turlari)) <= 1
    ext = '.docx' if bir_xil else '.pdf'
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp_path = tmp.name
    natija_yoli = letters.birlashtir_hujjatlar(fayllar, tmp_path, ariza_turlari=turlari)
    dl_name = 'Birlashgan_Davo_arizalar' + os.path.splitext(natija_yoli)[1]
    return send_file(natija_yoli, as_attachment=True, download_name=dl_name)


# ---------------------------------------------------------------------------
# SUD ISHLARI
# ---------------------------------------------------------------------------
@app.route('/api/sud/topshirish_kerak', methods=['GET'])
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


@app.route('/api/sud/topshirish_kerak_excel', methods=['GET'])
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


@app.route('/api/sud/kiritilmadi', methods=['POST'])
def sud_kiritilmadi():
    """Tasdiqlangan Davo arizani sudga topshirmaslik sababini qayd qiladi.
    'Qarz yopilgan' sababi tanlansa, bu tizim tomonidan HAQIQATAN
    tekshiriladi — agar joriy qarzdorlik hali mavjud bo'lsa, bu sabab
    RAD ETILADI (chunki noto'g'ri ma'lumot bo'lishi mumkin)."""
    anketa = request.form.get('anketa_raqami')
    sababi = request.form.get('sababi')
    sana = request.form.get('sana', '')
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


@app.route('/api/sud/kiritilmagan_royxat', methods=['GET'])
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


@app.route('/api/sud/yigma_jild_holati', methods=['GET'])
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
    kerakli = db.sud_kredit_hujjatlar_royxati(xat.get('davo_ariza_turi'))
    natija = []
    for maydon, nomi in kerakli:
        natija.append({'maydon': maydon, 'nomi': nomi, 'mavjud': bool(xat.get(maydon)), 'fayl': xat.get(maydon) or ''})
    natija.append({'maydon': 'sud_yigma_jild_titul_fayl', 'nomi': 'Titul', 'mavjud': bool(xat.get('sud_yigma_jild_titul_fayl')),
                    'fayl': xat.get('sud_yigma_jild_titul_fayl') or ''})
    natija.append({'maydon': 'sud_malumotnoma_topshirishda_fayl', 'nomi': "Ma'lumotnoma (ixtiyoriy)",
                    'mavjud': bool(xat.get('sud_malumotnoma_topshirishda_fayl')), 'fayl': xat.get('sud_malumotnoma_topshirishda_fayl') or ''})
    natija.append({'maydon': 'davo_ariza_fayl_yoli', 'nomi': 'Davo ariza', 'mavjud': bool(xat.get('davo_ariza_fayl_yoli')),
                    'fayl': xat.get('davo_ariza_fayl_yoli') or ''})
    natija.append({'maydon': 'fayl_yoli', 'nomi': 'Xat', 'mavjud': bool(xat.get('fayl_yoli')),
                    'fayl': xat.get('fayl_yoli') or ''})
    toliqmi = db.sud_hujjatlar_toliqmi(xat)
    qoshimcha_hujjatlar = db.sud_qoshimcha_hujjatlar_royxati(xat['id'])
    return jsonify({'hujjatlar': natija, 'toliqmi': toliqmi, 'ruxsat_berilgan': bool(xat.get('sud_hujjatlar_ruxsat')),
                     'qoshimcha_hujjatlar': qoshimcha_hujjatlar})


@app.route('/api/sud/yigma_jild_yaratish', methods=['POST'])
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


@app.route('/api/sud/malumotnoma_yaratish', methods=['POST'])
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


@app.route('/api/sud/hujjat_yuklash', methods=['POST'])
def sud_hujjat_yuklash():
    """Sud yig'ma jildi uchun kredit hujjatlaridan birini (kredit
    shartnoma, kafillik, garov, bank baholash) PDF sifatida yuklaydi."""
    anketa = request.form.get('anketa_raqami')
    maydon = request.form.get('maydon')
    f = request.files.get('file')
    if not anketa or not maydon or not f or not f.filename:
        return jsonify({'xato': 'anketa_raqami, maydon va fayl kerak'}), 400
    conn = db.get_conn()
    row = conn.execute('SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1', (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Xat topilmadi'}), 404
    xat = dict(row)
    if not xat.get('sud_yigma_jild_papka'):
        return jsonify({'xato': "Avval yig'ma jild (Titul) yaratilishi kerak"}), 400
    nomlar = {'kredit_shartnoma_fayl': '02_Kredit_shartnoma', 'kafillik_shartnoma_fayl': '03_Kafillik_shartnoma',
              'garov_shartnoma_fayl': '04_Garov_shartnoma', 'bank_baholash_fayl': '05_Bank_baholash'}
    prefiks = nomlar.get(maydon, maydon)
    fayl_yoli = os.path.join(xat['sud_yigma_jild_papka'], f"{prefiks}_{f.filename}")
    xato_natija = mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    db.sud_hujjat_saqlash(xat['id'], maydon, fayl_yoli)
    return jsonify({'ok': True})


@app.route('/api/sud/qoshimcha_hujjat_yuklash', methods=['POST'])
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
    fayl_yoli = os.path.join(xat['sud_yigma_jild_papka'], f"Qoshimcha_{fayl_nomi_toza}_{f.filename}")
    xato_natija = mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    db.sud_qoshimcha_hujjat_qoshish(xat['id'], hujjat_nomi, fayl_yoli)
    return jsonify({'ok': True})


@app.route('/api/sud/qoshimcha_hujjat/<int:hujjat_id>', methods=['DELETE'])
def sud_qoshimcha_hujjat_ochirish_endpoint(hujjat_id):
    db.sud_qoshimcha_hujjat_ochirish(hujjat_id)
    return jsonify({'ok': True})


@app.route('/api/sud/ruxsat_berish', methods=['POST'])
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
        return jsonify({'xato': "Barcha kerakli hujjatlar hali to'liq yuklanmagan"}), 400
    db.sud_hujjatlar_ruxsat_berish(xat['id'])
    return jsonify({'ok': True})


@app.route('/api/mib/tayyor_jild', methods=['GET'])
def mib_tayyor_jild_endpoint():
    """MIB yig'ma jildidagi barcha hujjatlarni (Titul -> Ijro varaqasi ->
    Xat -> Davo ariza -> Sud buyrug'i -> Yakunlash asosi, qaysi biri
    mavjud bo'lsa) yagona PDF qilib birlashtiradi."""
    from flask import send_file
    anketa = request.args.get('anketa', '')
    conn = db.get_conn()
    row = conn.execute('SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1', (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Xat topilmadi'}), 404
    xat = dict(row)
    fayllar = []
    for maydon in ['yigma_jild_titul_fayl', 'ijro_varaqasi_fayl', 'fayl_yoli',
                   'davo_ariza_fayl_yoli', 'sud_buyrugi_fayl', 'mib_yakunlash_hujjati_fayl']:
        if xat.get(maydon) and os.path.exists(xat[maydon]):
            fayllar.append(xat[maydon])
    if not fayllar:
        return jsonify({'xato': "Hujjatlar topilmadi"}), 400
    mijoz_fayl_nomi = letters.safe_filename(xat.get('mijoz_nomi', ''))
    output_path = os.path.join(mib_hujjatlar_papkasi(), f"{mijoz_fayl_nomi}_MIB_jildi_{letters.safe_filename(anketa)}.pdf")
    try:
        letters._birlashtir_pdf(fayllar, output_path)
    except Exception as e:
        return jsonify({'xato': f"Birlashtirishda xato: {e}"}), 500
    return send_file(output_path, as_attachment=True, download_name=f"{mijoz_fayl_nomi}_MIB_jildi_{anketa}.pdf")


@app.route('/api/sud/tayyor_jild', methods=['GET'])
def sud_tayyor_jild_endpoint():
    """Belgilangan tartibda (Titul -> Ma'lumotnoma -> Davo ariza -> Xat ->
    Kredit hujjatlari) barcha hujjatlarni yagona PDF qilib birlashtiradi."""
    from flask import send_file
    anketa = request.args.get('anketa', '')
    conn = db.get_conn()
    row = conn.execute('SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1', (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Xat topilmadi'}), 404
    xat = dict(row)
    fayllar = []
    for maydon in ['sud_yigma_jild_titul_fayl', 'sud_malumotnoma_topshirishda_fayl',
                   'davo_ariza_fayl_yoli', 'fayl_yoli',
                   'kredit_shartnoma_fayl', 'kafillik_shartnoma_fayl', 'garov_shartnoma_fayl', 'bank_baholash_fayl']:
        if xat.get(maydon) and os.path.exists(xat[maydon]):
            fayllar.append(xat[maydon])
    # MUHIM: standart ro'yxatdan tashqari, qo'lda qo'shilgan IXTIYORIY
    # qo'shimcha hujjatlar ham (oxirida) jildga qo'shiladi.
    for qh in db.sud_qoshimcha_hujjatlar_royxati(xat['id']):
        if qh.get('fayl_yoli') and os.path.exists(qh['fayl_yoli']):
            fayllar.append(qh['fayl_yoli'])
    if not fayllar:
        return jsonify({'xato': "Hujjatlar topilmadi"}), 400
    mijoz_fayl_nomi = letters.safe_filename(xat.get('mijoz_nomi', ''))
    output_path = os.path.join(sud_hujjatlar_papkasi(), f"{mijoz_fayl_nomi}_Sud_jildi_{letters.safe_filename(anketa)}.pdf")
    try:
        letters._birlashtir_pdf(fayllar, output_path)
    except Exception as e:
        return jsonify({'xato': f"Birlashtirishda xato: {e}"}), 500
    return send_file(output_path, as_attachment=True, download_name=f"{mijoz_fayl_nomi}_Sud_jildi_{anketa}.pdf")


@app.route('/api/sud/kiritilmagan_excel', methods=['GET'])
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


@app.route('/api/sud/kiritilmadi_bekor_qilish', methods=['POST'])
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


@app.route('/api/sud/qaror_yuklash', methods=['POST'])
def sud_qaror_yuklash():
    """Sud qarorini (5/15 kunlik muddatda) yuklaydi. Natija:
      - 'bank_foydasiga' / 'qisman' -> sud ishi tugab, MIB uchun tayyor bo'ladi
      - 'rad_etildi' -> sud ishi (sabab bilan) tugaydi, keyinchalik
        "Nollashtirish" orqali qaytadan boshlanishi mumkin."""
    anketa = request.form.get('anketa_raqami')
    natija = request.form.get('natija')  # 'bank_foydasiga' | 'qisman' | 'rad_etildi'
    sana = request.form.get('sana', datetime.datetime.now().strftime('%d.%m.%Y'))
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
    fayl_yoli = os.path.join(out_dir, f"{letters.safe_filename(xat['mijoz_nomi'])}_{anketa}_Sud_qarori_" + f.filename)
    xato_natija = mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]

    qisman_asosiy = float(request.form.get('qisman_asosiy_farq', 0) or 0)
    qisman_foiz = float(request.form.get('qisman_foiz_farq', 0) or 0)
    qisman_penya = float(request.form.get('qisman_penya_farq', 0) or 0)
    davlat_boji_sherik = request.form.get('davlat_boji_sherik') == 'true'
    rad_sababi = request.form.get('rad_sababi', '')

    db.sud_qaror_saqlash(xat['id'], natija, fayl_yoli, sana, qisman_asosiy, qisman_foiz, qisman_penya,
                          davlat_boji_sherik, rad_sababi)

    if natija == 'rad_etildi':
        db.add_mib_amal(xat['id'], 'sud_rad_etildi', sana, f"Sud tomonidan rad etildi: {rad_sababi}")

    return jsonify({'ok': True})


@app.route('/api/sud/qaror_kutilayotganlar', methods=['GET'])
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


@app.route('/api/sud/qaror_kutilayotganlar_excel', methods=['GET'])
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


@app.route('/api/sud/topshirildi', methods=['POST'])
def sud_topshirildi():
    anketa = request.form.get('anketa_raqami')
    ish_raqami = request.form.get('ish_raqami', '')
    sana = request.form.get('sana', '')
    majburiy = request.form.get('majburiy_davom_ettirish') == 'true'
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
        mustahkam_fayl_saqlash(f, sud_buyrugi_fayl, ozbek_kengaytma_tekshiruvi=False)

    db.mark_sud_topshirildi(xat['id'], ish_raqami, sana, buyruq_fayl=sud_buyrugi_fayl)
    return jsonify({'ok': True})


@app.route('/api/sud/topshirish_shablon', methods=['POST'])
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


@app.route('/api/sud/topshirish_excel_import', methods=['POST'])
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


@app.route('/api/sud/royxat', methods=['GET'])
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


@app.route('/api/sud/qidirish', methods=['GET'])
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


@app.route('/api/sud/eski_ish_qidirish', methods=['GET'])
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


@app.route('/api/sud/eski_ish_kiritish', methods=['POST'])
def sud_eski_ish_kiritish():
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami', '').strip()
    ish_raqami = data.get('ish_raqami', '').strip()
    sana = data.get('sana', '').strip()
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
# ---------------------------------------------------------------------------
@app.route('/api/mib/otkazish_kerak', methods=['GET'])
def mib_otkazish_kerak():
    xatlar = db.get_mib_otkazish_kerak()
    natija = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
        asosiy = x.get('davo_summasi_asosiy') or 0
        foiz = x.get('davo_summasi_foiz') or 0
        jarima = x.get('davo_summasi_jarima') or 0
        natija.append({
            'xat_id': x['id'], 'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'], 'turi': turi,
            'jami': asosiy + foiz + jarima, 'sud_ish_raqami': x.get('sud_ish_raqami', ''),
            'sudga_topshirilgan': x.get('sud_topshirilgan_sana', ''),
            'sud_buyrugi_mavjud': bool(x.get('sud_qaror_fayl') or x.get('sud_buyrugi_fayl')),
        })
    return jsonify({'royxat': natija})


@app.route('/api/mib/otkazish_kerak_excel', methods=['GET'])
def mib_otkazish_kerak_excel():
    import tempfile
    from flask import send_file
    import pandas as pd
    xatlar = db.get_mib_otkazish_kerak()
    if not xatlar:
        return jsonify({'xato': "Hozircha MIBga o'tkazish kerak bo'lgan ish yo'q"}), 400
    rows = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
        asosiy = x.get('davo_summasi_asosiy') or 0
        foiz = x.get('davo_summasi_foiz') or 0
        jarima = x.get('davo_summasi_jarima') or 0
        rows.append({
            'Anketa raqami': x['anketa_raqami'], 'Mijoz': x['mijoz_nomi'], 'Turi': turi,
            "Qarzdorlik (so'm)": asosiy + foiz + jarima,
            'Sud ish raqami': x.get('sud_ish_raqami', '') or '',
            'Sudga topshirilgan sana': x.get('sud_topshirilgan_sana', '') or '',
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='mibga_otkazish_kerak.xlsx')


@app.route('/api/mib/otkazildi', methods=['POST'])
def mib_otkazildi():
    anketa = request.form.get('anketa_raqami')
    ish_raqami = request.form.get('ish_raqami', '')
    sana = request.form.get('sana', '')
    # MUHIM (soddalashtirilgan oqim): "Qaror kutilayotganlar" alohida
    # bosqich sifatida OLIB TASHLANDI — sud qarori natijasi endi shu
    # MIBga o'tkazish oynasining o'zida so'raladi (agar hali qayd
    # etilmagan bo'lsa).
    natija = request.form.get('natija', '')  # 'bank_foydasiga' | 'qisman' | 'rad_etildi'
    qaror_sana = request.form.get('qaror_sana', '') or sana

    conn = db.get_conn()
    row = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami=? AND sud_holati='topshirildi' ORDER BY id DESC LIMIT 1", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Mos xat topilmadi'}), 404
    xat = dict(row)
    prow = db.get_portfel_by_id(xat['portfel_id'])
    mijoz_nomi_fayl = letters.safe_filename(xat['mijoz_nomi'])

    qaror_f = request.files.get('qaror_fayl') or request.files.get('sud_buyrugi')

    # 1-QADAM: agar sud qarori HALI qayd etilmagan bo'lsa, shu yerda
    # qayd qilamiz (natija + PDF hujjat).
    if not xat.get('sud_qaror_natija'):
        if not natija:
            return jsonify({'xato': "Sud qarori natijasini tanlang (Bank foydasiga / Qisman / Rad etildi)"}), 400
        if not qaror_f or not qaror_f.filename:
            return jsonify({'xato': "Sud qarori (PDF) yuklash majburiy"}), 400
        qaror_out_dir = bugungi_papka('Sud qaror')
        qaror_fayl_yoli = os.path.join(qaror_out_dir, f"{mijoz_nomi_fayl}_{anketa}_Sud_qarori_" + qaror_f.filename)
        xato_natija = mustahkam_fayl_saqlash(qaror_f, qaror_fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
        if xato_natija:
            return jsonify({'xato': xato_natija[0]}), xato_natija[1]
        qisman_kwargs = {}
        if natija == 'qisman':
            qisman_kwargs = {
                'qisman_asosiy': request.form.get('qisman_asosiy_farq') or 0,
                'qisman_foiz': request.form.get('qisman_foiz_farq') or 0,
                'qisman_penya': request.form.get('qisman_penya_farq') or 0,
                'davlat_boji_sherik': request.form.get('davlat_boji_sherik') == 'true',
            }
        if natija == 'rad_etildi':
            qisman_kwargs = {'rad_sababi': request.form.get('rad_sababi', '')}
        db.sud_qaror_saqlash(xat['id'], natija, qaror_fayl_yoli, qaror_sana, **qisman_kwargs)
        xat['sud_qaror_natija'] = natija
        xat['sud_qaror_fayl'] = qaror_fayl_yoli

    # Agar natija "Rad etildi" bo'lsa — MIBga UMUMAN o'tkazilmaydi, shu
    # yerda to'xtaymiz (qaror allaqachon yuqorida saqlandi).
    if xat.get('sud_qaror_natija') == 'rad_etildi':
        return jsonify({'ok': True, 'rad_etildi': True})

    # 2-QADAM: MIBga o'tkazish uchun Ijro varaqasi MAJBURIY.
    if not ish_raqami or not sana:
        return jsonify({'xato': 'ish_raqami va sana kerak'}), 400
    ijro_f = request.files.get('ijro_varaqasi')
    if not ijro_f or not ijro_f.filename:
        return jsonify({'xato': "Ijro varaqasi (PDF) yuklash majburiy"}), 400

    jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0) if prow else \
        (xat.get('davo_summasi_asosiy') or 0) + (xat.get('davo_summasi_foiz') or 0) + (xat.get('davo_summasi_jarima') or 0)

    out_dir = bugungi_papka('Ijro varaqalari')
    ijro_fayl_yoli = os.path.join(out_dir, f"{mijoz_nomi_fayl}_{anketa}_Ijro_varaqasi_" + ijro_f.filename)
    mustahkam_fayl_saqlash(ijro_f, ijro_fayl_yoli, ozbek_kengaytma_tekshiruvi=False)

    sud_fayl_yoli = xat.get('sud_qaror_fayl') or xat.get('sud_buyrugi_fayl')

    db.mark_mib_otkazildi(xat['id'], ish_raqami, sana, ijro_fayl_yoli, mib_ijro_summasi=jami,
                           sud_buyrugi_fayl=sud_fayl_yoli)

    # Yig'ma jild (ish dossiyesi) papkasini ochib, titul (muqova) hujjatini
    # yaratamiz, so'ng shu ishga tegishli AVVAL yaratilgan barcha hujjatlarni
    # (xat, Davo ariza, Sud buyrug'i, Ijro varaqasi) avtomatik jildga
    # nusxalaymiz — foydalanuvchi qo'lda hech narsa qo'shmasa ham, jild
    # to'liq bo'ladi.
    try:
        mijoz_turi_calc, mijoz = util.resolve_mijoz(prow) if prow else (None, None)
        settings = db.get_all_settings()
        xat_yangilangan = db.get_xat_by_id(xat['id'])

        # MUHIM (yangi tuzilma): Huquqiy choralar/MIB hujjatlari/[MIBga
        # o'tkazilgan sana]/[mijoz nomi]/ papkasida saqlanadi.
        jild_papka = mib_hujjatlari_mijoz_papkasi(xat['mijoz_nomi'], datetime.datetime.now(), anketa)
        titul_path = os.path.join(jild_papka, '00_Titul.docx')
        letters.generate_yigma_jild_titul(titul_path, xat_yangilangan, prow, mijoz, settings)
        db.mark_yigma_jild_yaratildi(xat['id'], jild_papka, titul_path)

        xat_toliq = db.get_xat_by_id(xat['id'])
        db.yigma_jild_toldirish(jild_papka, xat_toliq)
    except Exception as e:
        return jsonify({'ok': True, 'ogohlantirish': f"MIBga o'tkazildi, lekin yig'ma jild yaratishda xato: {e}"})

    # MUHIM: agar shu anketa uchun "kutilmoqda" holatidagi pochta xarajati
    # bo'lsa — MIBga o'tkazilishi bilanoq, xarajat summasiga teng YANGI
    # ijro ishi TIZIM TOMONIDAN O'ZI avtomatik ochiladi (qo'lda
    # "MIB ish ochish" bosish shart emas).
    try:
        conn = db.get_conn()
        kutilayotgan_xarajatlar = conn.execute(
            "SELECT id FROM sud_xarajatlar WHERE anketa_raqami=? AND holati='kutilmoqda'", (anketa,)).fetchall()
        conn.close()
        for x in kutilayotgan_xarajatlar:
            xarajat_ish_raqami = f"{ish_raqami}-XARAJAT"
            db.sud_xarajat_mib_ish_ochish(x['id'], xarajat_ish_raqami)
    except Exception:
        pass

    return jsonify({'ok': True})


@app.route('/api/mib/faol', methods=['GET'])
def mib_faol():
    xatlar = db.get_mib_faol_royxat()
    settings = db.get_all_settings()
    natija = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
        jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0) if prow else 0
        amallar = db.get_mib_amallar(x['id'])
        songgi = amallar[-1] if amallar else None
        mib_summasi = x.get('mib_ijro_summasi') or jami
        farq = jami - mib_summasi
        nazorat_natija = None
        if prow:
            try:
                nazorat_natija = db.get_mib_monitoring_holati(x['id'], prow, xat=x, settings=settings)
            except Exception:
                nazorat_natija = None
        nazorat = nazorat_natija.get('holat') if nazorat_natija else None
        nazorat_matn = nazorat_natija.get('xabar', '—') if nazorat_natija and nazorat_natija.get('holat') else '—'
        tolangan_summa, _ = db.tolovlar_jami_va_royxat(x['anketa_raqami'])
        natija.append({
            'xat_id': x['id'], 'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'], 'turi': turi,
            'qarzdorlik': jami, 'mib_ish_raqami': x.get('mib_ish_raqami', ''),
            'songgi_harakat': AMAL_TURLARI_MAP.get(songgi['amal_turi'], songgi['amal_turi']) if songgi else '—',
            'songgi_harakat_sana': songgi['amal_sanasi'] if songgi else '',
            'harakatlar_soni': len(amallar), 'farq': farq, 'nazorat': nazorat, 'nazorat_matn': nazorat_matn,
            'yigma_jild_titul_fayl': x.get('yigma_jild_titul_fayl', ''),
            'yigma_jild_papka': x.get('yigma_jild_papka', ''),
            'yigma_jild_bor': x.get('yigma_jild_holati') == 'mavjud',
            'tolangan_summa': tolangan_summa,
        })
    return jsonify({'royxat': natija})


@app.route('/api/mib/amal_qoshish', methods=['POST'])
def mib_amal_qoshish():
    """Yangi MIB harakatini qo'shadi. MUHIM: har bir harakat, uni
    tasdiqlovchi PDF hujjat bilan birga bo'lishi SHART — bu hujjat, avval
    o'zi (harakat sanasi bilan) saqlanadi, so'ng shu ishning Sud/MIB
    yig'ma jildiga ham AVTOMATIK qo'shib qo'yiladi."""
    anketa = request.form.get('anketa_raqami')
    amal_turi = request.form.get('amal_turi', '')
    amal_sanasi = request.form.get('amal_sanasi', '')
    tavsif = request.form.get('tavsif', '')
    undirilgan_summa = request.form.get('undirilgan_summa') or None
    f = request.files.get('tasdiqlovchi_hujjat')
    if not f or not f.filename:
        return jsonify({'xato': "Har bir harakat uchun tasdiqlovchi hujjat (PDF) yuklash SHART"}), 400

    conn = db.get_conn()
    row = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami=? AND mib_holati='otkazildi' ORDER BY id DESC LIMIT 1", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Mos MIB ishi topilmadi'}), 404
    xat = dict(row)

    out_dir = bugungi_papka('MIB harakat hujjatlari')
    fayl_nomi = f"{letters.safe_filename(xat['mijoz_nomi'])}_{anketa}_{letters.safe_filename(amal_turi)}_{f.filename}"
    fayl_yoli = os.path.join(out_dir, fayl_nomi)
    xato_natija = mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]

    db.add_mib_amal(xat['id'], amal_turi, amal_sanasi, tavsif,
                     undirilgan_summa=undirilgan_summa, dalolatnoma_fayl=fayl_yoli)

    # MUHIM: shu harakat hujjatini, ishning MIB yig'ma jild papkasiga
    # (agar allaqachon yaratilgan bo'lsa) ham nusxalab qo'yamiz — shunda
    # yig'ma jildning o'zida ham barcha harakatlar hujjati ko'rinadi.
    if xat.get('yigma_jild_papka') and os.path.isdir(xat['yigma_jild_papka']):
        try:
            import shutil
            nusxa_nomi = f"Harakat_{letters.safe_filename(amal_turi)}_{amal_sanasi.replace('.', '')}_{f.filename}"
            shutil.copy2(fayl_yoli, os.path.join(xat['yigma_jild_papka'], nusxa_nomi))
        except Exception:
            pass

    return jsonify({'ok': True})


@app.route('/api/mib/harakat_turlari', methods=['GET'])
def mib_harakat_turlari_endpoint():
    return jsonify({'turlar': db.mib_harakat_turlari_royxati()})


@app.route('/api/mib/harakat_turlari', methods=['POST'])
def mib_harakat_turi_qoshish_endpoint():
    data = request.get_json() or {}
    nomi = data.get('nomi', '').strip()
    if not nomi:
        return jsonify({'xato': "Harakat nomi kerak"}), 400
    db.mib_harakat_turi_qoshish(nomi)
    return jsonify({'ok': True})


@app.route('/api/mib/harakat_turlari/<int:turi_id>', methods=['DELETE'])
def mib_harakat_turi_ochirish_endpoint(turi_id):
    db.mib_harakat_turi_ochirish(turi_id)
    return jsonify({'ok': True})


@app.route('/api/mib/amallar_tarixi', methods=['GET'])
def mib_amallar_tarixi():
    anketa = request.args.get('anketa', '').strip()
    conn = db.get_conn()
    row = conn.execute("SELECT id FROM xatlar WHERE anketa_raqami=? AND mib_holati='otkazildi'", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'amallar': []})
    amallar = db.get_mib_amallar(row['id'])
    return jsonify({'amallar': amallar})


@app.route('/api/tizimdan_oldin/qidirish', methods=['GET'])
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


@app.route('/api/anketa/tarix', methods=['GET'])
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


@app.route('/api/mib/qidirish', methods=['GET'])
def mib_qidirish():
    anketa = request.args.get('anketa', '').strip()
    conn = db.get_conn()
    row = conn.execute("SELECT * FROM xatlar WHERE anketa_raqami=? AND mib_holati='otkazildi'", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'topildi': False})
    x = dict(row)
    prow = db.get_portfel_by_id(x['portfel_id'])
    turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
    jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0) if prow else 0
    amallar = db.get_mib_amallar(x['id'])
    songgi = amallar[-1] if amallar else None
    return jsonify({'topildi': True, 'row': {
        'xat_id': x['id'], 'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'], 'turi': turi,
        'qarzdorlik': jami, 'mib_ish_raqami': x.get('mib_ish_raqami', ''),
        'songgi_harakat': songgi['amal_turi'] if songgi else '—',
        'songgi_harakat_sana': songgi['amal_sanasi'] if songgi else '',
        'harakatlar_soni': len(amallar),
        'yigma_jild_titul_fayl': x.get('yigma_jild_titul_fayl', ''),
        'yigma_jild_papka': x.get('yigma_jild_papka', ''),
        'yigma_jild_bor': x.get('yigma_jild_holati') == 'mavjud',
    }})


@app.route('/api/mib/jild_fayllari', methods=['GET'])
def mib_jild_fayllari():
    anketa = request.args.get('anketa', '').strip()
    conn = db.get_conn()
    row = conn.execute("SELECT yigma_jild_papka FROM xatlar WHERE anketa_raqami=?", (anketa,)).fetchone()
    conn.close()
    papka = row['yigma_jild_papka'] if row else None
    if not papka or not os.path.isdir(papka):
        return jsonify({'fayllar': [], 'papka': papka or ''})
    fayllar = []
    for f in sorted(os.listdir(papka)):
        toliq = os.path.join(papka, f)
        if os.path.isfile(toliq):
            fayllar.append({'nomi': f, 'yoli': toliq})
    return jsonify({'fayllar': fayllar, 'papka': papka})


@app.route('/api/mib/jarayondagilar_excel', methods=['GET'])
def mib_jarayondagilar_excel():
    import tempfile
    from flask import send_file
    import pandas as pd
    royxat = db.get_mib_faol_royxat_toliq()
    if not royxat:
        return jsonify({'xato': "MIBda jarayondagi hujjatlar yo'q"}), 400
    rows = []
    for item in royxat:
        xat = item['xat']
        amal = item['amal']
        amal_turi_nomi = AMAL_TURLARI_MAP.get(amal['amal_turi'], amal['amal_turi']) if amal else ''
        oylik = amal.get('undirilgan_summa', '') if amal and amal['amal_turi'] == 'oylik_ish_haqqi' else ''
        rows.append({
            'Anketa raqami': xat['anketa_raqami'], 'PINFL/STIR': item.get('pinfl') or item.get('stir', ''),
            "F.I.Sh / Nomi": xat['mijoz_nomi'], 'Turi': xat['mijoz_turi'],
            "Qarzdorlik (so'm)": item['jami_qarz'], 'MIB ish raqami': xat.get('mib_ish_raqami', ''),
            "MIBga o'tkazilgan sana": xat.get('mib_otkazilgan_sana', ''), 'Harakat turi': amal_turi_nomi,
            'Harakat sanasi': amal.get('amal_sanasi', '') if amal else '', 'Tavsif': amal.get('tavsif', '') if amal else '',
            "Oylik ish haqqidan undirilgan summa": oylik,
            "Undirilgan summa (umumiy)": amal.get('undirilgan_summa', '') if amal else '',
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='mib_jarayondagi_hujjatlar.xlsx')


@app.route('/api/mib/eski_ish_qidirish', methods=['GET'])
def mib_eski_ish_qidirish():
    anketa = request.args.get('anketa', '').strip()
    rows = db.get_portfel_by_anketa(anketa)
    if not rows:
        return jsonify({'topildi': False})
    prow = rows[0]
    turi, mijoz = util.resolve_mijoz(prow)
    jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
    return jsonify({'topildi': True, 'mijoz_nomi': prow.get('mijoz_nomi', ''), 'turi': turi, 'jami_qarz': jami})


@app.route('/api/mib/eski_ish_kiritish', methods=['POST'])
def mib_eski_ish_kiritish():
    anketa = request.form.get('anketa_raqami', '').strip()
    ish_raqami = request.form.get('ish_raqami', '').strip()
    sana = request.form.get('sana', '').strip()
    sud_ish_raqami = request.form.get('sud_ish_raqami', '').strip()
    qarzdorlik_qiymat = request.form.get('qarzdorlik', '')
    if not anketa or not ish_raqami or not sana:
        return jsonify({'xato': 'anketa_raqami, ish_raqami va sana kerak'}), 400

    ijro_f = request.files.get('ijro_varaqasi')
    if not ijro_f or not ijro_f.filename:
        return jsonify({'xato': "Ijro varaqasi (PDF) yuklash majburiy"}), 400

    rows = db.get_portfel_by_anketa(anketa)
    if not rows:
        return jsonify({'xato': 'Bu anketa portfelda topilmadi'}), 404
    prow = rows[0]
    turi, mijoz = util.resolve_mijoz(prow)
    jami = float(qarzdorlik_qiymat or 0) or (
        (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0))

    # MUHIM: hujjatlar, asl dasturdagi kabi, BUGUNGI SANA papkasi ichida
    # (masalan "09.09.2026/MIB/...") saqlanadi — to'g'ridan-to'g'ri asosiy
    # papkaga emas.
    out_dir = bugungi_papka('Ijro varaqalari')
    ijro_fayl_yoli = os.path.join(out_dir, f"{letters.safe_filename(prow.get('mijoz_nomi', ''))}_{letters.safe_filename(anketa)}_Ijro_varaqasi_{ijro_f.filename}")
    xato_natija = mustahkam_fayl_saqlash(ijro_f, ijro_fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]

    conn = db.get_conn()
    mavjud = conn.execute("SELECT id FROM xatlar WHERE anketa_raqami=?", (anketa,)).fetchone()
    if mavjud:
        xat_id = mavjud['id']
        conn.execute("UPDATE xatlar SET mib_holati='otkazildi', mib_ish_raqami=?, mib_otkazilgan_sana=?, "
                     "sud_ish_raqami=COALESCE(sud_ish_raqami, ?), sud_holati='topshirildi', "
                     "mib_ijro_summasi=?, ijro_varaqasi_fayl=? WHERE id=?",
                     (ish_raqami, sana, sud_ish_raqami, jami, ijro_fayl_yoli, xat_id))
    else:
        conn.execute(
            "INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi, holat, "
            "sud_holati, sud_ish_raqami, mib_holati, mib_ish_raqami, mib_otkazilgan_sana, "
            "mib_ijro_summasi, ijro_varaqasi_fayl) "
            "VALUES (?, ?, ?, ?, 'yuborildi', 'topshirildi', ?, 'otkazildi', ?, ?, ?, ?)",
            (prow['id'], anketa, prow.get('mijoz_nomi', ''), turi, sud_ish_raqami,
             ish_raqami, sana, jami, ijro_fayl_yoli))
        xat_id = conn.execute("SELECT id FROM xatlar WHERE anketa_raqami=?", (anketa,)).fetchone()['id']
    conn.commit()
    conn.close()
    db.add_mib_amal(xat_id, 'eski_ish_kiritildi', sana, "Eski ish sifatida bazaga kiritildi")

    # Yig'ma jild (ish dossiyesi) — yangi ishlar MIBga o'tkazilganda qanday
    # avtomatik yaratilsa, eski ish kiritilganda ham xuddi shunday
    # yaratiladi: muqova (titul) hujjati + mavjud barcha hujjatlar
    # (agar bo'lsa) avtomatik jildga yig'iladi.
    try:
        settings = db.get_all_settings()
        xat_toliq = db.get_xat_by_id(xat_id)
        jild_papka = mib_hujjatlari_mijoz_papkasi(prow.get('mijoz_nomi', ''), datetime.datetime.now(), anketa)
        titul_path = os.path.join(jild_papka, '00_Titul.docx')
        letters.generate_yigma_jild_titul(titul_path, xat_toliq, prow, mijoz, settings)
        db.mark_yigma_jild_yaratildi(xat_id, jild_papka, titul_path)
        xat_yangilangan = db.get_xat_by_id(xat_id)
        db.yigma_jild_toldirish(jild_papka, xat_yangilangan)
    except Exception as e:
        return jsonify({'ok': True, 'ogohlantirish': f"Ish kiritildi, lekin yig'ma jild yaratishda xato: {e}"})

    return jsonify({'ok': True})


@app.route('/api/mib/avtomashinalar', methods=['GET'])
def mib_avtomashinalar():
    anketa = request.args.get('anketa', '').strip()
    conn = db.get_conn()
    row = conn.execute("SELECT id FROM xatlar WHERE anketa_raqami=?", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'mashinalar': []})
    return jsonify({'mashinalar': db.get_avtomashinalar(row['id'])})


@app.route('/api/mib/avtomashina_qoshish', methods=['POST'])
def mib_avtomashina_qoshish():
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami', '').strip()
    conn = db.get_conn()
    row = conn.execute("SELECT id FROM xatlar WHERE anketa_raqami=?", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Mos MIB ishi topilmadi'}), 404
    db.add_avtomashina(row['id'], data.get('rusumi', ''), data.get('davlat_raqami', ''), data.get('pinfl', ''))
    return jsonify({'ok': True})


@app.route('/api/mib/avtomashina_holati', methods=['POST'])
def mib_avtomashina_holati():
    mashina_id = request.form.get('id')
    holati = request.form.get('holati')
    modda = request.form.get('modda', '')
    if not mashina_id or not holati:
        return jsonify({'xato': 'id va holati kerak'}), 400
    fayl_yoli = None
    f = request.files.get('hujjat')
    if f and f.filename:
        out_dir = bugungi_papka('Avtomashina_hujjatlar')
        os.makedirs(out_dir, exist_ok=True)
        fayl_yoli = os.path.join(out_dir, f"{mashina_id}_{f.filename}")
        mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    db.update_avtomashina_holati(mashina_id, holati, asoslovchi_hujjat_fayl=fayl_yoli, modda=modda or None)
    return jsonify({'ok': True})


@app.route('/api/mib/avtomashinalar_import', methods=['POST'])
def mib_avtomashinalar_import():
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
        natija = importer.import_avtomashinalar_excel(tmp_path)
        return jsonify(natija)
    except Exception as e:
        return jsonify({'xato': str(e)}), 400
    finally:
        os.remove(tmp_path)


@app.route('/api/mib/avtomashinalar_xatlanmagan_excel', methods=['GET'])
def mib_avtomashinalar_xatlanmagan_excel():
    import tempfile
    from flask import send_file
    import pandas as pd
    xatlanmagan = db.get_xatlanmagan_avtomashinalar()
    if not xatlanmagan:
        return jsonify({'xato': "Xatlanmagan avtomashinalar yo'q"}), 400
    rows = [{'Mashina rusumi': m['mashina_rusumi'], 'Davlat raqami': m['davlat_raqami'],
             'Mijoz PINFL': m.get('mijoz_pinfl', ''), 'Anketa raqami': m['anketa_raqami'],
             'Mijoz nomi': m['mijoz_nomi']} for m in xatlanmagan]
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='xatlanmagan_avtomashinalar.xlsx')


@app.route('/api/mib/yakunlash', methods=['POST'])
def mib_yakunlash():
    anketa = request.form.get('anketa_raqami')
    sabab = request.form.get('sabab', '')
    sana = request.form.get('sana', '')
    if not anketa or not sabab:
        return jsonify({'xato': 'anketa_raqami va sabab kerak'}), 400
    f = request.files.get('asos_hujjat')
    if not f or not f.filename:
        return jsonify({'xato': "Yakunlash asosi hujjatini (PDF) yuklang — bu majburiy."}), 400
    conn = db.get_conn()
    row = conn.execute("SELECT id, mijoz_nomi FROM xatlar WHERE anketa_raqami=? AND mib_holati='otkazildi'", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Mos MIB ishi topilmadi'}), 404
    out_dir = os.path.join(mib_hujjatlar_papkasi(), letters.safe_filename(anketa))
    os.makedirs(out_dir, exist_ok=True)
    fayl_yoli = os.path.join(out_dir, f"{letters.safe_filename(row['mijoz_nomi'])}_{anketa}_Yakunlash_asosi_" + f.filename)
    mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    db.mark_mib_yakunlandi(row['id'], sabab, sana or None)
    db.set_mib_yakunlash_hujjati(row['id'], fayl_yoli)

    # Yakunlash asosi hujjati ham yig'ma jildga avtomatik qo'shiladi.
    try:
        xat = db.get_xat_by_id(row['id'])
        if xat and xat.get('yigma_jild_papka'):
            db.yigma_jild_toldirish(xat['yigma_jild_papka'], xat)
    except Exception:
        pass

    return jsonify({'ok': True})
@app.route('/api/mib/yakunlangan', methods=['GET'])
def mib_yakunlangan():
    xatlar = db.get_mib_yakunlangan_royxati()
    natija = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
        natija.append({
            'xat_id': x['id'], 'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'], 'turi': turi,
            'mib_ish_raqami': x.get('mib_ish_raqami', ''), 'yakunlangan_sana': x.get('mib_yakunlangan_sana', ''),
            'sabab': x.get('mib_yakunlash_sababi', ''),
        })
    return jsonify({'royxat': natija})


@app.route('/api/mib/yakunlangan_excel', methods=['GET'])
def mib_yakunlangan_excel():
    """MIB'da yakunlangan (to'xtatilgan) barcha ishlarni Excel qilib
    chiqaradi: Anketa raqami, PINFL/STIR, Mijoz nomi, Turi, MIB ish
    raqami, Yakunlangan sana, Sabab."""
    import tempfile
    from flask import send_file
    import pandas as pd
    xatlar = db.get_mib_yakunlangan_royxati()
    if not xatlar:
        return jsonify({'xato': "Hozircha yakunlangan MIB ishi yo'q"}), 400
    rows = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi')) if prow else x.get('mijoz_turi')
        pinfl_stir = (prow.get('pinfl') or prow.get('stir') or '') if prow else ''
        rows.append({
            'Anketa raqami': x['anketa_raqami'], 'PINFL/STIR': pinfl_stir, 'Mijoz nomi': x['mijoz_nomi'],
            'Turi': turi, 'MIB ish raqami': x.get('mib_ish_raqami', '') or '',
            'Yakunlangan sana': x.get('mib_yakunlangan_sana', '') or '',
            'Yakunlash sababi': x.get('mib_yakunlash_sababi', '') or '',
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='mib_yakunlangan_ishlar.xlsx')


@app.route('/api/mib/qayta_ochish', methods=['POST'])
def mib_qayta_ochish():
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami')
    conn = db.get_conn()
    row = conn.execute("SELECT id FROM xatlar WHERE anketa_raqami=? AND mib_yakunlangan=1", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Topilmadi'}), 404
    db.mib_ishni_qayta_ochish(row['id'])
    return jsonify({'ok': True})


@app.route('/api/mib/jarayonni_nollashtirish', methods=['POST'])
def mib_jarayonni_nollashtirish():
    """MUHIM, QAYTARILMAYDIGAN AMAL: anketaning butun xat/Davo ariza/Sud/MIB
    jarayoni tarixini o'chirib, uni "hech qanday harakat qilinmagan"
    holatiga qaytaradi. Faqat MIB yakunlangan (mib_yakunlangan=1) ishlar
    uchun ishlatilishi mumkin — tasodifan faol ishni o'chirib
    yubormaslik uchun."""
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami')
    tasdiq = data.get('tasdiqlayman')
    if not anketa:
        return jsonify({'xato': 'anketa_raqami kerak'}), 400
    if not tasdiq:
        return jsonify({'xato': "Bu amalni tasdiqlash kerak"}), 400
    conn = db.get_conn()
    row = conn.execute(
        "SELECT id FROM xatlar WHERE anketa_raqami=? AND (mib_yakunlangan=1 OR "
        "(sud_kiritilmadi_sababi IS NOT NULL AND sud_kiritilmadi_sababi != '') OR "
        "sud_qaror_natija='rad_etildi')",
        (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': "Bu anketa uchun yakunlangan MIB ishi, 'Sudga kiritilmadi' yoki "
                                 "sud tomonidan 'Rad etilgan' ish topilmadi. Nollashtirish faqat "
                                 "shunday holatlar uchun mumkin."}), 404
    db.anketa_jarayonini_nollashtirish(anketa)
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# CHORA KO'RISH
# ---------------------------------------------------------------------------
@app.route('/api/chora/royxat', methods=['GET'])
def chora_royxat():
    royxat = db.get_chora_korish_royxati()
    natija = []
    for i, r in enumerate(royxat):
        prow = r['portfel']
        jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
        natija.append({
            'i': i, 'anketa_raqami': prow['anketa_raqami'], 'mijoz_nomi': prow['mijoz_nomi'],
            'turi': r['turi'], 'dpd': r['dpd'], 'qarzdorlik': jami,
            'chora': r['chora'], 'chora_nomi': r['chora_nomi'], 'tafsilot': r['tafsilot'],
        })
    soni = {}
    for r in royxat:
        soni[r['chora']] = soni.get(r['chora'], 0) + 1
    return jsonify({'royxat': natija, 'soni': soni, 'chora_nomlari': db.CHORA_NOMLARI})


@app.route('/api/chora/amal_bajarish', methods=['POST'])
def chora_amal_bajarish():
    """Chora ko'rishdan tanlangan anketalar uchun tavsiya etilgan choraga
    qarab avtomatik amal bajaradi: xat yuborish YOKI Davo ariza tayyorlash
    (ommaviy) — MIB harakati alohida (bittadan) MIB bo'limida bajariladi."""
    data = request.get_json() or {}
    anketalar = data.get('anketalar', [])
    royxat = db.get_chora_korish_royxati()
    royxat_map = {r['portfel']['anketa_raqami']: r for r in royxat}

    xat_kerak, davo_kerak, boshqa = [], [], 0
    for anketa in anketalar:
        r = royxat_map.get(anketa)
        if not r:
            continue
        if r['chora'] in ('xat_yuborish', 'xat_yuborish_keyingi_bosqich'):
            xat_kerak.append(anketa)
        elif r['chora'] == 'davo_ariza_tayyorlash':
            davo_kerak.append(anketa)
        else:
            boshqa += 1

    if xat_kerak and davo_kerak:
        return jsonify({'xato': "Tanlanganlar orasida ham xat, ham Davo ariza bosqichidagilar bor. "
                                 "Iltimos, faqat bitta turdagi bosqichni tanlang."}), 400

    if xat_kerak:
        # talabnoma_xat_yaratish endpoint mantig'ini qayta ishlatamiz
        with app.test_request_context(json={'anketalar': xat_kerak}):
            resp = talabnoma_xat_yaratish()
        result = resp.get_json()
        return jsonify({'turi': 'xat', **result})

    if davo_kerak:
        with app.test_request_context(json={'anketalar': davo_kerak}):
            resp = davo_ariza_yaratish()
        result = resp.get_json()
        return jsonify({'turi': 'davo', **result})

    # Bitta mijoz, MIB yoki Sudga kiritish bosqichida bo'lsa — tegishli
    # bo'limga yo'naltirish kerakligini bildiramiz (bular ommaviy
    # avtomatlashtirilmagan, chunki qo'shimcha hujjat/tasdiqlash talab qiladi)
    if len(anketalar) == 1:
        r = royxat_map.get(anketalar[0])
        if r and r['chora'] == 'mib_harakat_boshlash':
            return jsonify({'xato': "Bu mijoz MIB bosqichida. MIB harakati qo'shish uchun "
                                     "'MIB ijro harakatlari' bo'limiga o'ting va u yerdan "
                                     "'+ Harakat' tugmasini bosing."}), 400
        if r and r['chora'] == 'sudga_kiritish_kerak':
            return jsonify({'xato': "Bu mijozning Davo arizasi SSPdan tasdiqlanib qaytgan. "
                                     "Sudga topshirish uchun 'SUD Ishlari' bo'limiga o'ting."}), 400
        if r and r['chora'] == 'jarayon_qaytadan_tiklash_kerak':
            return jsonify({'xato': "Bu mijozning Davo ariza muddati tugagan. Jarayonni noldan "
                                     "boshlash uchun 'MIB ijro harakatlari → Yakunlangan ishlar' "
                                     "bo'limida (agar u yerda ko'rinmasa, Sud Ishlari bo'limidan) "
                                     "'Nollashtirish' funksiyasidan foydalaning."}), 400

    return jsonify({'xato': "Tanlanganlar orasida xat yoki Davo ariza bosqichidagi mijoz topilmadi "
                             "(MIB harakati alohida, MIB bo'limida bajariladi)."}), 400


@app.route('/api/chora/qidirish', methods=['GET'])
def chora_qidirish():
    anketa = request.args.get('anketa', '').strip()
    royxat = db.get_chora_korish_royxati()
    for i, r in enumerate(royxat):
        if r['portfel']['anketa_raqami'] == anketa:
            prow = r['portfel']
            jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
            return jsonify({'topildi': True, 'row': {
                'i': i, 'anketa_raqami': prow['anketa_raqami'], 'mijoz_nomi': prow['mijoz_nomi'],
                'turi': r['turi'], 'dpd': r['dpd'], 'qarzdorlik': jami,
                'chora': r['chora'], 'chora_nomi': r['chora_nomi'], 'tafsilot': r['tafsilot'],
            }})
    return jsonify({'topildi': False})


@app.route('/api/chora/excel_eksport', methods=['GET'])
def chora_excel_eksport():
    import tempfile
    from flask import send_file
    import pandas as pd
    royxat = db.get_chora_korish_royxati()
    rows = []
    for r in royxat:
        prow = r['portfel']
        jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
        rows.append({
            'Anketa raqami': prow['anketa_raqami'], 'Mijoz': prow['mijoz_nomi'], 'Turi': r['turi'],
            'DPD': r['dpd'], 'Qarzdorlik': jami, 'Chora': r['chora_nomi'], 'Tafsilot': r['tafsilot'],
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='chora_korish.xlsx')


# ---------------------------------------------------------------------------
# 95413
# ---------------------------------------------------------------------------
@app.route('/api/95413/yigma_jild_holati', methods=['GET'])
def f95413_yigma_jild_holati():
    """95413 mijozi uchun yig'ma jild holati: Titul yaratilganmi, va
    foydalanuvchi o'zi nom berib qo'shgan barcha hujjatlar ro'yxati."""
    anketa = request.args.get('anketa', '').strip()
    if not anketa:
        return jsonify({'xato': 'Anketa raqami kerak'}), 400
    titul = db.f95413_titul_olish(anketa)
    hujjatlar = db.f95413_hujjatlar_royxati(anketa)
    return jsonify({
        'titul_bor': bool(titul and titul.get('titul_fayl') and os.path.exists(titul['titul_fayl'])),
        'titul_fayl': titul['titul_fayl'] if titul else '',
        'hujjatlar': hujjatlar,
    })


@app.route('/api/95413/titul_yaratish', methods=['POST'])
def f95413_titul_yaratish():
    """95413 mijozi uchun Titul (muqova) hujjatini AVTOMATIK yaratadi —
    MIB yig'ma jildining titul shabloni bilan bir xil ko'rinishda."""
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami', '').strip()
    if not anketa:
        return jsonify({'xato': 'Anketa raqami kerak'}), 400
    prow_list = db.get_portfel_by_anketa(anketa)
    if not prow_list:
        return jsonify({'xato': 'Bu anketa portfelda topilmadi'}), 404
    prow = prow_list[0]
    turi, mijoz = util.resolve_mijoz(prow)
    settings = db.get_all_settings()
    conn = db.get_conn()
    xat_row = conn.execute('SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1', (anketa,)).fetchone()
    conn.close()
    xat = dict(xat_row) if xat_row else {'anketa_raqami': anketa, 'mijoz_nomi': prow.get('mijoz_nomi', ''), 'mijoz_turi': turi}

    jild_papka = f95413_mijoz_papkasi(prow.get('mijoz_nomi', ''), anketa)
    titul_path = os.path.join(jild_papka, '00_Titul.docx')
    letters.generate_yigma_jild_titul(titul_path, xat, prow, mijoz, settings)
    # MUHIM: titul qayta yaratilganda, shu bilan birga, hali nusxalanmagan
    # (masalan Titul birinchi marta yaratilgandan keyin Sud bosqichida
    # yangi yuklangan) Xat/Davo ariza/Sud/Ijro/kredit hujjatlarini ham
    # qayta qidirib, topilganlarini AVTOMATIK qo'shib qo'yamiz.
    f95413_hujjatlarni_nusxalash(prow.get('mijoz_nomi', ''), xat, anketa)
    db.f95413_titul_saqlash(anketa, titul_path)
    return jsonify({'ok': True})


@app.route('/api/95413/hujjat_yuklash', methods=['POST'])
def f95413_hujjat_yuklash():
    """95413 yig'ma jildiga, foydalanuvchi O'ZI YOZGAN nom bilan
    istalgan hujjatni yuklaydi (qattiq belgilangan hujjat turlari
    emas — bu bo'limda hujjatlar turi oldindan belgilanmagan)."""
    anketa = request.form.get('anketa_raqami', '').strip()
    hujjat_nomi = request.form.get('hujjat_nomi', '').strip()
    f = request.files.get('file')
    if not anketa or not hujjat_nomi or not f or not f.filename:
        return jsonify({'xato': "Anketa raqami, hujjat nomi va fayl kerak"}), 400
    prow_list = db.get_portfel_by_anketa(anketa)
    if not prow_list:
        return jsonify({'xato': 'Bu anketa portfelda topilmadi'}), 404
    mijoz_nomi = prow_list[0].get('mijoz_nomi', '')
    jild_papka = f95413_mijoz_papkasi(mijoz_nomi, anketa)
    fayl_nomi_toza = letters.safe_filename(hujjat_nomi)
    fayl_yoli = os.path.join(jild_papka, f"{fayl_nomi_toza}_{f.filename}")
    xato_natija = mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)
    if xato_natija:
        return jsonify({'xato': xato_natija[0]}), xato_natija[1]
    db.f95413_hujjat_qoshish(anketa, hujjat_nomi, fayl_yoli)
    return jsonify({'ok': True})


@app.route('/api/95413/hujjat/<int:hujjat_id>', methods=['DELETE'])
def f95413_hujjat_ochirish_endpoint(hujjat_id):
    db.f95413_hujjat_ochirish(hujjat_id)
    return jsonify({'ok': True})


@app.route('/api/nazorat95413/royxat', methods=['GET'])
def nazorat95413_royxat():
    royxat = db.get_95413_royxati()
    natija = []
    for r in royxat:
        prow = r['portfel']
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi'))

        # MUHIM: agar bu mijoz uchun 95413 papkasi HALI YARATILMAGAN bo'lsa
        # (ya'ni bu mijoz 95413 ro'yxatida BIRINCHI marta ko'rinayotgan
        # bo'lsa) — uning ENG SO'NGGI Sud/MIB hujjatlarini (agar mavjud
        # bo'lsa) avtomatik topib, 95413/[mijoz]/ papkasiga nusxalab
        # qo'yamiz.
        try:
            mijoz_papka = f95413_mijoz_papkasi(prow['mijoz_nomi'], prow['anketa_raqami'])
            if not os.listdir(mijoz_papka):
                conn = db.get_conn()
                eng_songgi_xat = conn.execute(
                    'SELECT * FROM xatlar WHERE anketa_raqami=? ORDER BY id DESC LIMIT 1',
                    (prow['anketa_raqami'],)).fetchone()
                conn.close()
                if eng_songgi_xat:
                    f95413_hujjatlarni_nusxalash(prow['mijoz_nomi'], dict(eng_songgi_xat), prow['anketa_raqami'])
        except Exception:
            pass

        natija.append({
            'anketa_raqami': prow['anketa_raqami'], 'mijoz_nomi': prow['mijoz_nomi'], 'turi': turi,
            'balans_95413': prow.get('balans_95413') or 0,
            'bosqich': r['bosqich'], 'bosqich_nomi': db.BOSQICH_NOMLARI_95413.get(r['bosqich'], r['bosqich']),
            'tafsilot': r['tafsilot'],
        })
    soni = {}
    for r in royxat:
        soni[r['bosqich']] = soni.get(r['bosqich'], 0) + 1
    jami_balans = sum((r['portfel'].get('balans_95413') or 0) for r in royxat)
    return jsonify({'royxat': natija, 'soni': soni, 'jami': len(royxat), 'jami_balans': jami_balans,
                     'bosqich_nomlari': db.BOSQICH_NOMLARI_95413})


@app.route('/api/nazorat95413/excel_eksport', methods=['GET'])
def nazorat95413_excel_eksport():
    import tempfile
    from flask import send_file
    import pandas as pd
    royxat = db.get_95413_royxati()
    rows = []
    for r in royxat:
        prow = r['portfel']
        turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi'))
        rows.append({
            'Anketa raqami': prow['anketa_raqami'], 'Mijoz': prow['mijoz_nomi'], 'Turi': turi,
            'Balans 95413': prow.get('balans_95413') or 0,
            'Bosqich': db.BOSQICH_NOMLARI_95413.get(r['bosqich'], r['bosqich']), 'Tafsilot': r['tafsilot'],
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='95413_nazorati.xlsx')


@app.route('/api/nazorat95413/xat_yuborildi_belgilash', methods=['POST'])
def nazorat95413_xat_yuborildi_belgilash():
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami', '').strip()
    conn = db.get_conn()
    row = conn.execute("SELECT id FROM xatlar WHERE anketa_raqami=?", (anketa,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'xato': 'Xat topilmadi'}), 404
    db.mark_xat_yuborildi(row['id'])
    return jsonify({'ok': True})


@app.route('/api/nazorat95413/eski_ish_qidirish', methods=['GET'])
def nazorat95413_eski_ish_qidirish():
    anketa = request.args.get('anketa', '').strip()
    rows = db.get_portfel_by_anketa(anketa)
    if not rows:
        return jsonify({'topildi': False})
    prow = rows[0]
    turi, mijoz = util.resolve_mijoz(prow)
    jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)
    return jsonify({'topildi': True, 'mijoz_nomi': prow.get('mijoz_nomi', ''), 'turi': turi,
                     'jami_qarz': jami, 'balans_95413': prow.get('balans_95413') or 0})


@app.route('/api/nazorat95413/eski_ish_kiritish', methods=['POST'])
def nazorat95413_eski_ish_kiritish():
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami', '').strip()
    ish_raqami = data.get('ish_raqami', '').strip()
    sana = data.get('sana', '').strip()
    if not anketa or not ish_raqami or not sana:
        return jsonify({'xato': 'anketa_raqami, ish_raqami va sana kerak'}), 400
    rows = db.get_portfel_by_anketa(anketa)
    if not rows:
        return jsonify({'xato': 'Bu anketa portfelda topilmadi'}), 404
    prow = rows[0]
    mijoz_turi = util.turi_kodidan(prow.get('mijoz_turi_kodi'), prow.get('mijoz_turi'))
    qarz = data.get('qarzdorlik')
    qarz = float(qarz) if qarz else None

    xat_id = db.create_legacy_mib_xat(
        portfel_id=prow['id'], anketa_raqami=anketa, mijoz_nomi=prow.get('mijoz_nomi', ''),
        mijoz_turi=mijoz_turi, mib_ish_raqami=ish_raqami, mib_sana=sana,
        sud_ish_raqami=data.get('sud_ish_raqami') or None, joriy_qarzdorlik=qarz,
    )

    # MUHIM: 95413 uchun yig'ma jild ODDIY MIB jildlaridan ALOHIDA papkaga yoziladi —
    # bu kreditlar asosiy balansdan chiqarilgani uchun boshqa bo'limlarda ko'rinmasligi
    # mumkin, shu bois hujjatlari ham alohida saqlanadi.
    try:
        turi_m, mijoz = util.resolve_mijoz(prow)
        settings = db.get_all_settings()
        xat_yangilangan = db.get_xat_by_id(xat_id)
        jild_papka = f95413_mijoz_papkasi(prow.get('mijoz_nomi', ''), anketa)
        titul_path = os.path.join(jild_papka, '00_Titul.docx')
        letters.generate_yigma_jild_titul(titul_path, xat_yangilangan, prow, mijoz, settings)
        db.mark_yigma_jild_yaratildi(xat_id, jild_papka, titul_path)
    except Exception as e:
        return jsonify({'ok': True, 'ogohlantirish': f"Eski ish kiritildi, lekin yig'ma jild yaratishda xato: {e}"})

    db.add_mib_amal(xat_id, 'eski_ish_kiritildi', sana,
                     tavsif=f"95413 balansidagi eski ish (MIB ish raqami: {ish_raqami}) tizimga qo'lda kiritildi.")
    return jsonify({'ok': True})


# ---------------------------------------------------------------------------
# TAHLIL
# ---------------------------------------------------------------------------
@app.route('/api/tahlil/umumiy', methods=['GET'])
def tahlil_umumiy():
    return jsonify(db.get_umumiy_tahlil())


@app.route('/api/tahlil/tarix', methods=['GET'])
def tahlil_tarix():
    return jsonify({'tarix': db.get_tahlil_tarixi()})


@app.route('/api/tahlil/tarmoq_mijozlari', methods=['GET'])
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


@app.route('/api/tahlil/hisobot_yuklab_olish', methods=['GET'])
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


@app.route('/api/mib/harakatsizlar', methods=['GET'])
def mib_harakatsizlar():
    xatlar = db.get_mib_harakatsizlar()
    natija = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0) if prow else 0
        natija.append({
            'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'], 'turi': x['mijoz_turi'],
            'jami_qarz': jami, 'mib_ish_raqami': x.get('mib_ish_raqami', ''),
            'harakatsizlik_kun': x.get('harakatsizlik_kun', ''),
        })
    return jsonify({'royxat': natija})


def mib_tolov_asosida_avtomatik_yakunlashni_tekshirish(anketa_raqami):
    """Har safar bir to'lov biror anketaga 'tasdiqlangan' deb biriktirilganda
    chaqiriladi. Agar shu anketaning MIB ishi FAOL (otkazilgan, hali
    yakunlanmagan) bo'lsa va unga tasdiqlangan to'lovlar yig'indisi Davo
    (ijro) summasiga YETGAN yoki OSHGAN bo'lsa — MIB ishini AVTOMATIK
    yakunlaydi, asos sifatida to'lovlar ro'yxatini o'z ichiga olgan
    hujjatni (imkon bo'lsa PDF, aks holda Word) yaratib, yig'ma jildga
    qo'shadi."""
    conn = db.get_conn()
    xat_row = conn.execute(
        "SELECT * FROM xatlar WHERE anketa_raqami=? AND mib_holati='otkazildi' AND (mib_yakunlangan IS NULL OR mib_yakunlangan=0)",
        (anketa_raqami,)).fetchone()
    conn.close()
    if not xat_row:
        return False
    xat = dict(xat_row)

    davo_qarz = (xat.get('mib_ijro_summasi') or 0)
    if not davo_qarz:
        prow = db.get_portfel_by_id(xat['portfel_id'])
        davo_qarz = (prow.get('asosiy_qarz', 0) or 0) + (prow.get('foiz_qarz', 0) or 0) + \
            (prow.get('jarima', 0) or 0) if prow else 0
    if not davo_qarz or davo_qarz <= 0:
        return False

    jami_tolangan, tolovlar_royxati = db.tolovlar_jami_va_royxat(anketa_raqami)
    if jami_tolangan < davo_qarz:
        return False  # Hali yetarli emas — hech narsa qilmaymiz

    # Hujjatni yaratamiz (avval Word, imkon bo'lsa PDF'ga aylantiramiz)
    out_dir = bugungi_papka('MIB_avtomatik_yakunlash')
    docx_path = os.path.join(out_dir, f"yakunlash_{letters.safe_filename(anketa_raqami)}.docx")
    letters.generate_tolov_asosida_yakunlash_hujjati(
        docx_path, xat, xat.get('mijoz_nomi', ''), davo_qarz, tolovlar_royxati, jami_tolangan)

    yakuniy_fayl = docx_path
    try:
        yakuniy_fayl = letters.convert_docx_to_pdf(docx_path, delete_docx=True)
    except Exception:
        pass  # MS Word mavjud bo'lmasa, Word hujjati o'zi ham yetarli

    sabab = ("To'liq to'landi (tizim avtomatik) — to'langan: "
             f"{jami_tolangan:,.0f} so'm").replace(',', ' ')
    db.mark_mib_yakunlandi(xat['id'], sabab, datetime.datetime.now().strftime('%d.%m.%Y'))
    db.set_mib_yakunlash_hujjati(xat['id'], yakuniy_fayl)

    try:
        if xat.get('yigma_jild_papka'):
            xat_yangi = db.get_xat_by_id(xat['id'])
            db.yigma_jild_toldirish(xat['yigma_jild_papka'], xat_yangi)
    except Exception:
        pass

    return True


@app.route('/api/mib/tolovlar_shablon', methods=['GET'])
def mib_tolovlar_shablon():
    """29801 (kunlik) yoki MIBdan kelgan to'lovlar uchun to'ldirish shablonini
    (bo'sh Excel, ustunlar bilan) beradi."""
    import tempfile
    from flask import send_file
    import pandas as pd
    manba = request.args.get('manba', 'kunlik_29801')
    if manba == 'mib':
        df = pd.DataFrame(columns=[
            'Sana (kun.oy.yil)', "To'lov maqsadi / Naznacheniye (PINFL shu yerda bo'lishi mumkin)",
            "F.I.Sh / Nomi (ixtiyoriy)", "Summa (so'm)",
            "Tranzaksiya raqami (bir xil kun/hisobga bir nechta tolov bolsa, dublikatni aniqlash uchun)"])
        nomi = 'mibdan_kelgan_tolovlar_shabloni.xlsx'
    else:
        df = pd.DataFrame(columns=[
            'Sana (kun.oy.yil)', 'Hisob raqami (yoki PINFL/STIR)',
            "F.I.Sh / Nomi (ixtiyoriy)", "Summa (so'm)",
            "Tranzaksiya raqami (bir xil kun/hisobga bir nechta tolov bolsa, dublikatni aniqlash uchun)"])
        nomi = 'kunlik_29801_tolovlar_shabloni.xlsx'
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name=nomi)


@app.route('/api/mib/tolovlar_import', methods=['POST'])
def mib_tolovlar_import():
    """Kunlik (29801-hisobvaraq) yoki MIBdan kelgan to'lovlar Excel faylini
    yuklaydi. Har bir qator uchun, ustun nomidan qat'i nazar (hisob raqami,
    PINFL, STIR yoki erkin to'lov maqsadi matni bo'lishi mumkin), tizim
    KO'P BOSQICHLI usul bilan mos anketani aniqlashga harakat qiladi
    (batafsil: database.py -> tolov_qoshish)."""
    import tempfile
    import pandas as pd
    manba = request.form.get('manba', 'kunlik_29801')
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

    sana_col = next((c for c in df.columns if str(c).startswith('Sana')), None)
    # Moslashuvchan: "Hisob raqami", "PINFL", "STIR", yoki "Naznacheniye" —
    # qaysi biri bo'lsa ham, xom matn sifatida qabul qilinadi va
    # tolov_qoshish() ichida ko'p bosqichli aniqlash ishga tushadi.
    xom_col = next((c for c in df.columns if any(
        k in str(c).upper() for k in ['HISOB', 'PINFL', 'STIR', 'NAZNACHENIYE', 'MAQSAD'])), None)
    summa_col = next((c for c in df.columns if 'Summa' in str(c)), None)
    ism_col = next((c for c in df.columns if 'F.I.Sh' in str(c) or 'Nomi' in str(c)), None)
    tranzaksiya_col = next((c for c in df.columns if 'Tranzaksiya' in str(c)), None)
    if not sana_col or not xom_col or not summa_col:
        return jsonify({'xato': (
            "Fayl tuzilmasi tanilmadi — 'Sana', 'Hisob raqami/PINFL/STIR/Naznacheniye' "
            "va 'Summa' ustunlari kerak.")}), 400

    tasdiqlangan, aniqlash_kerak, mos_kelmadi, dublikat, xatolar = 0, 0, 0, 0, []
    for i, row in df.iterrows():
        try:
            xom_qiymat = row[xom_col]
            # MUHIM: Excel/pandas uzun raqamli qiymatlarni ba'zan sonli
            # qiymat (masalan 42701766360013.0) sifatida o'qib, oxiriga
            # ".0" qo'shib qo'yishi yoki oldindagi nollarni yo'qotishi
            # mumkin. Shu sabab, matn ko'rinishini to'g'ri tiklaymiz.
            if isinstance(xom_qiymat, float):
                xom_matn = str(int(xom_qiymat))
            else:
                xom_matn = str(xom_qiymat).strip()
                if xom_matn.endswith('.0'):
                    xom_matn = xom_matn[:-2]
            if not xom_matn or xom_matn.lower() == 'nan':
                continue
            summa = float(row[summa_col])
            sana_qiymat = row[sana_col]
            sana = sana_qiymat.strftime('%d.%m.%Y') if hasattr(sana_qiymat, 'strftime') else str(sana_qiymat)
            ism = str(row[ism_col]).strip() if ism_col and str(row[ism_col]).strip().lower() != 'nan' else None
            tranzaksiya = None
            if tranzaksiya_col:
                tval = row[tranzaksiya_col]
                if isinstance(tval, float) and not (tval != tval):  # NaN tekshiruvi
                    tranzaksiya = str(int(tval)) if tval == int(tval) else str(tval)
                elif tval is not None and str(tval).strip().lower() != 'nan':
                    tranzaksiya = str(tval).strip()
            holati, tasdiqlangan_anketa = db.tolov_qoshish(
                manba, sana, summa, xom_matn, toliq_ism=ism, tranzaksiya_raqami=tranzaksiya)
            if holati == 'tasdiqlangan':
                tasdiqlangan += 1
                try:
                    mib_tolov_asosida_avtomatik_yakunlashni_tekshirish(tasdiqlangan_anketa)
                except Exception:
                    pass
            elif holati == 'aniqlash_kerak':
                aniqlash_kerak += 1
            elif holati == 'dublikat':
                dublikat += 1
            else:
                mos_kelmadi += 1
        except Exception as e:
            xatolar.append(f"{i + 2}-qator: {e}")

    return jsonify({
        'tasdiqlangan': tasdiqlangan, 'aniqlash_kerak': aniqlash_kerak,
        'mos_kelmadi': mos_kelmadi, 'dublikat': dublikat, 'xatolar': xatolar,
    })


@app.route('/api/mib/tolovlar_royxat', methods=['GET'])
def mib_tolovlar_royxat():
    manba = request.args.get('manba')
    holati = request.args.get('holati')
    royxat = db.get_tolovlar_royxati(manba=manba, holati=holati)
    return jsonify({'royxat': royxat})


@app.route('/api/mib/anketa_tolovlari', methods=['GET'])
def mib_anketa_tolovlari():
    """Bitta anketaga tegishli (tasdiqlangan) barcha to'lovlarni ko'rsatadi
    — 'Jarayondagi hujjatlar' jadvalidagi 'To'langan summa' ustuniga
    bosilganda tafsilotni ko'rish uchun."""
    anketa = request.args.get('anketa', '').strip()
    jami, royxat = db.tolovlar_jami_va_royxat(anketa)
    return jsonify({'jami': jami, 'royxat': royxat})


@app.route('/api/mib/tolov_nomzodlar', methods=['GET'])
def mib_tolov_nomzodlar():
    """Bitta to'lov uchun, uning saqlangan identifikatoriga (PINFL/STIR
    YOKI 'unikal' kodi bo'lishi mumkin — manbaga qarab) mos barcha
    anketalarni qaytaradi — foydalanuvchi qaysi birini tanlashini bilish
    uchun. Avval PINFL/STIR bo'yicha, topilmasa 'unikal' bo'yicha ham
    qidiriladi (chunki "29801..." hisob raqamlari asosida aniqlangan
    to'lovlarda identifikator aslida unikal kod bo'ladi)."""
    pinfl = request.args.get('pinfl', '')
    nomzodlar = db.tolov_uchun_anketalarni_topish(pinfl)
    if not nomzodlar:
        conn = db.get_conn()
        rows = conn.execute('''
            SELECT anketa_raqami, mijoz_nomi, asosiy_qarz, foiz_qarz, jarima
            FROM portfel WHERE faol=1 AND unikal=?
        ''', (pinfl,)).fetchall()
        conn.close()
        nomzodlar = [dict(r) for r in rows]
    natija = []
    for n in nomzodlar:
        jami = (n.get('asosiy_qarz') or 0) + (n.get('foiz_qarz') or 0) + (n.get('jarima') or 0)
        natija.append({'anketa_raqami': n['anketa_raqami'], 'mijoz_nomi': n['mijoz_nomi'], 'jami_qarz': jami})
    return jsonify({'nomzodlar': natija})


@app.route('/api/mib/tolov_anketa_tanlash', methods=['POST'])
def mib_tolov_anketa_tanlash():
    data = request.get_json() or {}
    tolov_id = data.get('tolov_id')
    anketa = data.get('anketa_raqami')
    if not tolov_id or not anketa:
        return jsonify({'xato': 'tolov_id va anketa_raqami kerak'}), 400
    db.tolov_anketa_biriktirish(tolov_id, anketa)
    try:
        mib_tolov_asosida_avtomatik_yakunlashni_tekshirish(anketa)
    except Exception:
        pass
    return jsonify({'ok': True})


@app.route('/api/mib/tolov_qidirish', methods=['GET'])
def mib_tolov_qidirish():
    """Avtomatik aniqlash umuman ishlamagan ('mos_kelmadi') to'lovlar uchun
    — anketa raqami yoki mijoz nomi bo'yicha QO'LDA qidirib topish."""
    q = request.args.get('q', '')
    natija = db.tolov_qidirib_biriktirish(q)
    for n in natija:
        n['jami_qarz'] = (n.pop('asosiy_qarz', 0) or 0) + (n.pop('foiz_qarz', 0) or 0) + (n.pop('jarima', 0) or 0)
    return jsonify({'natija': natija})


@app.route('/api/mib/harakatsizlar_excel', methods=['GET'])
def mib_harakatsizlar_excel():
    import tempfile
    from flask import send_file
    import pandas as pd
    xatlar = db.get_mib_harakatsizlar()
    if not xatlar:
        return jsonify({'xato': "Hozircha harakatsiz qolgan MIB ishi yo'q"}), 400
    rows = []
    for x in xatlar:
        prow = db.get_portfel_by_id(x['portfel_id'])
        jami = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0) if prow else 0
        rows.append({
            'Anketa raqami': x['anketa_raqami'], 'Mijoz': x['mijoz_nomi'], 'Turi': x['mijoz_turi'],
            "Qarzdorlik (so'm)": jami, 'MIB ish raqami': x.get('mib_ish_raqami', '') or '',
            'Necha kun harakatsiz': x.get('harakatsizlik_kun', ''),
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='mib_harakatsiz_qolganlar.xlsx')


@app.route('/api/davo-ariza/hisobot', methods=['GET'])
def davo_ariza_hisobot():
    muddat_kun = int(db.get_all_settings().get('davo_ariza_muddati_kun', 5))
    sabab_nomlari = {'qarz_yopilgan': "Qarz to'liq yopilgan", 'mijoz_arizasi': "Mijozning yozma arizasi asosida",
                      'xodim_iltimosi': "Bank xodimi iltimosiga asosan",
                      'dpd_kamaygan_avtomatik': "Avtomatik: DPD/qarz kamaygani sababli"}
    natija = []
    for x in db.get_davo_ariza_hisoboti():
        prow = db.get_portfel_by_id(x['portfel_id'])
        jami_joriy = (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0) if prow else 0
        davo_asosiy = x.get('davo_summasi_asosiy') or 0
        davo_foiz = x.get('davo_summasi_foiz') or 0
        davo_jarima = x.get('davo_summasi_jarima') or 0

        olib_kelindi = x.get('davo_ariza_holati') == 'olib_kelindi'
        yaratilgan, davo_dt = '', None
        try:
            davo_dt = datetime.datetime.fromisoformat(x['davo_ariza_sana'])
            yaratilgan = davo_dt.strftime('%d.%m.%Y')
        except Exception:
            yaratilgan = x.get('davo_ariza_sana', '') or ''

        holat_pill = 'yoq'
        if olib_kelindi and davo_dt:
            try:
                imzo_dt = datetime.datetime.strptime(x['davo_ariza_imzo_sana'], '%d.%m.%Y')
                kutilgan_kun = max((imzo_dt.date() - davo_dt.date()).days, 0)
            except Exception:
                kutilgan_kun = ''
            holati = "✓ Olib kelindi"
            holat_pill = 'olib_kelindi'
        elif davo_dt:
            kutilgan_kun = (datetime.datetime.now() - davo_dt).days
            if kutilgan_kun > muddat_kun:
                holati = f"⚠ Muddati o'tgan ({kutilgan_kun} kun)"
                holat_pill = 'otgan'
            else:
                holati = f"Kutilmoqda ({muddat_kun - kutilgan_kun} kun qoldi)"
                holat_pill = 'tayyor'
        else:
            kutilgan_kun, holati = '', ''

        sud_topshirildi = x.get('sud_holati') == 'topshirildi'
        sud_kiritilmadi_sababi = x.get('sud_kiritilmadi_sababi')
        if sud_topshirildi:
            sud_holati_matn = "✓ Sudga kiritildi"
        elif sud_kiritilmadi_sababi:
            izoh_qoshimcha = ''
            if sud_kiritilmadi_sababi == 'xodim_iltimosi':
                izoh_qoshimcha = f" ({x.get('sud_kiritilmadi_xodim_ism', '')} — {x.get('sud_kiritilmadi_izoh', '')})"
            sud_holati_matn = f"✕ Sudga kiritilmadi: {sabab_nomlari.get(sud_kiritilmadi_sababi, sud_kiritilmadi_sababi)}{izoh_qoshimcha}"
        elif olib_kelindi:
            sud_holati_matn = "Sudga jo'natish kutilmoqda"
        else:
            sud_holati_matn = "—"

        # MUHIM: bitta, KONSOLIDATSIYALANGAN ustun — bu Davo ariza AYNAN
        # QAYSI bosqichgacha borganini (Xat -> Davo ariza -> SSPga
        # topshirilgan -> Sudga kiritilgan -> MIBga o'tkazilgan ->
        # Yakunlangan) darhol ko'rsatadi.
        if x.get('mib_yakunlangan'):
            joriy_bosqich = f"✓ Yakunlandi (MIB) — {x.get('mib_yakunlash_sababi', '')}"
        elif x.get('mib_holati') == 'otkazildi':
            joriy_bosqich = f"⚙ MIB jarayonida (ish №{x.get('mib_ish_raqami', '')})"
        elif sud_kiritilmadi_sababi:
            joriy_bosqich = f"✕ Sudga kiritilmadi: {sabab_nomlari.get(sud_kiritilmadi_sababi, sud_kiritilmadi_sababi)}"
        elif x.get('sud_qaror_natija') == 'rad_etildi':
            joriy_bosqich = "✕ Sud rad etdi"
        elif sud_topshirildi:
            joriy_bosqich = f"⚖ Sudga topshirilgan (ish №{x.get('sud_ish_raqami', '')})"
        elif olib_kelindi:
            joriy_bosqich = "📋 SSPdan qaytgan — sudga topshirish kutilmoqda"
        elif x.get('davo_ariza_ish_raqami'):
            joriy_bosqich = "📤 SSPga topshirilgan — javob kutilmoqda"
        else:
            joriy_bosqich = "📝 Davo ariza tayyorlangan"

        natija.append({
            'anketa_raqami': x['anketa_raqami'], 'mijoz_nomi': x['mijoz_nomi'], 'mijoz_turi': x['mijoz_turi'],
            'jami_qarz': jami_joriy,
            'davo_summasi_asosiy': davo_asosiy, 'davo_summasi_foiz': davo_foiz, 'davo_summasi_jarima': davo_jarima,
            'davo_summasi_jami': davo_asosiy + davo_foiz + davo_jarima,
            'yaratilgan': yaratilgan, 'kutilgan_kun': kutilgan_kun,
            'ish_raqami': x.get('davo_ariza_ish_raqami', '') or '', 'imzo_sana': x.get('davo_ariza_imzo_sana', '') or '',
            'holati': holati, 'holat_pill': holat_pill,
            'sud_ish_raqami': x.get('sud_ish_raqami', '') or '', 'sud_sana': x.get('sud_topshirilgan_sana', '') or '',
            'sud_holati': sud_holati_matn,
            'joriy_bosqich': joriy_bosqich,
        })
    return jsonify({'royxat': natija})


@app.route('/api/davo-ariza/hisobot_excel', methods=['GET'])
def davo_ariza_hisobot_excel():
    import tempfile
    from flask import send_file
    import pandas as pd
    resp = davo_ariza_hisobot()
    rows = resp.get_json()['royxat']
    if not rows:
        return jsonify({'xato': "Hali birorta Davo ariza yaratilmagan"}), 400
    excel_qatorlar = []
    for r in rows:
        excel_qatorlar.append({
            'Anketa raqami': r['anketa_raqami'], 'Mijoz': r['mijoz_nomi'], 'Turi': r['mijoz_turi'],
            'Ish raqami': r['ish_raqami'], 'Tayyorlangan sanasi': r['yaratilgan'],
            'Davo summasi (asosiy)': r['davo_summasi_asosiy'], 'Davo summasi (foiz)': r['davo_summasi_foiz'],
            'Davo summasi (penya)': r['davo_summasi_jarima'], 'Davo summasi (jami)': r['davo_summasi_jami'],
            "Joriy qarzdorlik (bugun)": r['jami_qarz'],
            'Holati (Palata/SSP)': r['holati'],
            'Sud ish raqami': r['sud_ish_raqami'], 'Sudga topshirilgan sana': r['sud_sana'],
            'Sudga jo\'natish holati / izoh': r['sud_holati'],
            'Joriy bosqich (qaysi jarayongacha borgan)': r['joriy_bosqich'],
        })
    df = pd.DataFrame(excel_qatorlar)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='davo_ariza_hisoboti.xlsx')


# ---------------------------------------------------------------------------
# VAFOT ETGANLAR
# ---------------------------------------------------------------------------
@app.route('/api/vafot/royxat', methods=['GET'])
def vafot_royxat():
    royxat = db.get_vafot_etganlar_royxati()
    return jsonify({'royxat': royxat})


@app.route('/api/vafot/excel', methods=['GET'])
def vafot_excel():
    import tempfile
    from flask import send_file
    import pandas as pd
    royxat = db.get_vafot_etganlar_royxati()
    if not royxat:
        return jsonify({'xato': "Hozircha vafot etgan mijoz qayd qilinmagan"}), 400
    rows = []
    for x in royxat:
        prow = db.get_portfel_by_id(x.get('portfel_id')) if x.get('portfel_id') else None
        if not prow:
            plist = db.get_portfel_by_anketa(x.get('anketa_raqami', ''))
            prow = plist[0] if plist else None
        prow = prow or {}
        muddati_otgan_asosiy = prow.get('asosiy_qarz') or 0
        muddati_otgan_foiz = prow.get('foiz_qarz') or 0
        muddati_otgan_jarima = prow.get('jarima') or 0
        rows.append({
            'Anketa raqami': x.get('anketa_raqami', ''),
            'F.I.Sh': x.get('mijoz_nomi', ''),
            'PINFL': prow.get('pinfl') or prow.get('stir') or '',
            "O'limlik kuni": x.get('vafot_sanasi', ''),
            'Kredit hisob raqami': prow.get('kredit_hisob_raqami', ''),
            'Jami olingan summasi': prow.get('jami_berilgan_summa') or 0,
            'Bugungi kundagi qoldiq': prow.get('jami_qarz') or 0,
            "Shundan muddati o'tgan jami qoldiq": muddati_otgan_asosiy + muddati_otgan_foiz + muddati_otgan_jarima,
            'Asosiy qarz': muddati_otgan_asosiy,
            'Foiz': muddati_otgan_foiz,
            'Penya': muddati_otgan_jarima,
            "Sug'urta nomi": x.get('sugurta_kompaniya', '') or '',
            'Shartnoma raqami': x.get('sugurta_polis_raqam', '') or '',
            'Amalda yoki tugagan': {'amalda': 'Amalda', 'muddati_otgan': 'Muddati tugagan',
                                     'tekshirilmagan': 'Tekshirilmagan'}.get(x.get('polis_holati', ''), x.get('polis_holati', '')),
            'Tarmoq kodi': prow.get('tarmoq', '') or '',
            'Kredit maqsadi': prow.get('tulov_maqsadi', '') or '',
        })
    df = pd.DataFrame(rows)
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='vafot_etganlar.xlsx')


@app.route('/api/vafot/qoshish', methods=['POST'])
def vafot_qoshish():
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami', '').strip()
    vafot_sanasi = data.get('vafot_sanasi', '').strip()
    if not anketa or not vafot_sanasi:
        return jsonify({'xato': 'anketa_raqami va vafot_sanasi kerak'}), 400
    prow_list = db.get_portfel_by_anketa(anketa)
    mijoz_nomi = prow_list[0].get('mijoz_nomi', '') if prow_list else data.get('mijoz_nomi', '')
    conn = db.get_conn()
    conn.execute(
        "INSERT INTO vafot_etganlar (anketa_raqami, mijoz_nomi, vafot_sanasi, polis_holati) "
        "VALUES (?, ?, ?, 'amalda')", (anketa, mijoz_nomi, vafot_sanasi))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/vafot/fayl_yuklash', methods=['POST'])
def vafot_fayl_yuklash():
    """Vafot etgan mijoz uchun hujjat (o'limlik guvohnomasi / pasport / sug'urta
    polis) yuklaydi va uni ko'rish/yuklab olish mumkin bo'lgan holatda saqlaydi."""
    vafot_id = request.form.get('id')
    turi = request.form.get('turi')  # olimlik | pasport | sugurta_polis
    maydon_map = {
        'olimlik': 'olimlik_guvohnomasi_fayl',
        'pasport': 'pasport_fayl',
        'sugurta_polis': 'sugurta_polis_fayl',
    }
    if not vafot_id or turi not in maydon_map:
        return jsonify({'xato': "id va to'g'ri turi (olimlik/pasport/sugurta_polis) kerak"}), 400
    f = request.files.get('file')
    if not f or not f.filename:
        return jsonify({'xato': 'Fayl yuborilmadi'}), 400

    conn = db.get_conn()
    row = conn.execute('SELECT anketa_raqami FROM vafot_etganlar WHERE id=?', (vafot_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'xato': 'Yozuv topilmadi'}), 404
    anketa = row['anketa_raqami']
    out_dir = os.path.join(hujjatlar_papkasi(), 'vafot_etganlar', letters.safe_filename(anketa))
    os.makedirs(out_dir, exist_ok=True)
    fayl_yoli = os.path.join(out_dir, f"{turi}_{f.filename}")
    mustahkam_fayl_saqlash(f, fayl_yoli, ozbek_kengaytma_tekshiruvi=False)

    ustun = maydon_map[turi]
    conn.execute(f'UPDATE vafot_etganlar SET {ustun}=? WHERE id=?', (fayl_yoli, vafot_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/vafot/yangilash', methods=['POST'])
def vafot_yangilash():
    data = request.get_json() or {}
    vafot_id = data.get('id')
    if not vafot_id:
        return jsonify({'xato': 'id kerak'}), 400
    ruxsat_etilgan = ['polis_holati', 'sugurta_kompaniya', 'sugurta_polis_raqam', 'xabarnoma_holati',
                       'xabarnoma_yuborilgan_sana', 'javob_kelgan_sana']
    updates = {k: v for k, v in data.items() if k in ruxsat_etilgan}
    if not updates:
        return jsonify({'xato': "Yangilanadigan maydon topilmadi"}), 400
    conn = db.get_conn()
    set_clause = ', '.join(f'{k}=?' for k in updates)
    conn.execute(f'UPDATE vafot_etganlar SET {set_clause} WHERE id=?', (*updates.values(), vafot_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@app.route('/api/vafot/sugurta_kiritish', methods=['POST'])
def vafot_sugurta_kiritish():
    vafot_id = request.form.get('id')
    kompaniya = request.form.get('kompaniya', '')
    raqam = request.form.get('raqam', '')
    if not vafot_id:
        return jsonify({'xato': 'id kerak'}), 400
    v = db.get_vafot_etgan_by_id(vafot_id)
    if not v:
        return jsonify({'xato': 'Yozuv topilmadi'}), 404
    if v['polis_holati'] != 'amalda':
        return jsonify({'xato': "Sug'urta polisi amalda emas — sug'urta ma'lumoti kiritilmaydi."}), 400
    polis_dest = None
    f = request.files.get('polis_fayl')
    if f and f.filename:
        out_dir = os.path.join(hujjatlar_papkasi(), 'vafot_etganlar', letters.safe_filename(v['anketa_raqami']))
        os.makedirs(out_dir, exist_ok=True)
        polis_dest = os.path.join(out_dir, f"Polis_{f.filename}")
        mustahkam_fayl_saqlash(f, polis_dest, ozbek_kengaytma_tekshiruvi=False)
    db.update_sugurta_malumot(vafot_id, kompaniya, raqam, polis_dest)
    return jsonify({'ok': True})


@app.route('/api/vafot/xabarnoma_tayyorlash', methods=['GET'])
def vafot_xabarnoma_tayyorlash():
    from flask import send_file
    vafot_id = request.args.get('id')
    v = db.get_vafot_etgan_by_id(vafot_id)
    if not v:
        return jsonify({'xato': 'Yozuv topilmadi'}), 404
    if v['polis_holati'] != 'amalda':
        return jsonify({'xato': "Sug'urta polisi amalda bo'lmagan mijoz uchun xabarnoma tayyorlanmaydi."}), 400
    if not v.get('sugurta_kompaniya'):
        return jsonify({'xato': "Avval sug'urta ma'lumotini kiriting."}), 400
    prow = db.get_portfel_by_id(v['portfel_id']) if v.get('portfel_id') else None
    if not prow:
        rows = db.get_portfel_by_anketa(v['anketa_raqami'])
        prow = rows[0] if rows else None
    if not prow:
        return jsonify({'xato': "Bog'liq portfel yozuvi topilmadi."}), 404
    turi_m, mijoz = util.resolve_mijoz(prow)
    settings = db.get_all_settings()
    out_dir = os.path.join(hujjatlar_papkasi(), 'vafot_etganlar', letters.safe_filename(v['anketa_raqami']))
    os.makedirs(out_dir, exist_ok=True)
    fname = f"Xabarnoma_{letters.safe_filename(v['anketa_raqami'])}_{letters.safe_filename(v['mijoz_nomi'])}.docx"
    out_path = os.path.join(out_dir, fname)
    try:
        letters.generate_sugurta_xabarnoma(out_path, v, prow, mijoz, settings)
    except Exception as e:
        return jsonify({'xato': f"Xabarnoma yaratishda xato: {e}"}), 400
    return send_file(out_path, as_attachment=True, download_name=fname)


@app.route('/api/vafot/xabarnoma_yuborildi', methods=['POST'])
def vafot_xabarnoma_yuborildi():
    data = request.get_json() or {}
    vafot_id = data.get('id')
    sana = data.get('sana', '').strip()
    if not vafot_id or not sana:
        return jsonify({'xato': 'id va sana kerak'}), 400
    db.mark_xabarnoma_yuborildi(vafot_id, sana)
    return jsonify({'ok': True})


@app.route('/api/vafot/javob_keldi', methods=['POST'])
def vafot_javob_keldi():
    vafot_id = request.form.get('id')
    sana = request.form.get('sana', '').strip()
    if not vafot_id or not sana:
        return jsonify({'xato': 'id va sana kerak'}), 400
    v = db.get_vafot_etgan_by_id(vafot_id)
    if not v:
        return jsonify({'xato': 'Yozuv topilmadi'}), 404
    if v['xabarnoma_holati'] != 'yuborildi':
        return jsonify({'xato': "Avval xabarnoma yuborilgani belgilanishi kerak."}), 400
    fayl_dest = None
    f = request.files.get('fayl')
    if f and f.filename:
        out_dir = os.path.join(hujjatlar_papkasi(), 'vafot_etganlar', letters.safe_filename(v['anketa_raqami']))
        os.makedirs(out_dir, exist_ok=True)
        fayl_dest = os.path.join(out_dir, f"Javob_{f.filename}")
        mustahkam_fayl_saqlash(f, fayl_dest, ozbek_kengaytma_tekshiruvi=False)
    db.mark_sugurta_javob_keldi(vafot_id, sana, fayl_dest)
    return jsonify({'ok': True})


@app.route('/api/fayl_korish', methods=['GET'])
def fayl_korish():
    """Har qanday yaratilgan/yuklangan hujjatni (Word, PDF va h.k.) ko'rsatish
    yoki yuklab olish uchun umumiy endpoint."""
    from flask import send_file
    yol = request.args.get('yol', '')
    if not yol or not os.path.isfile(yol):
        return jsonify({'xato': 'Fayl topilmadi'}), 404
    return send_file(yol, as_attachment=request.args.get('yuklab_olish') == '1')


# ---------------------------------------------------------------------------
# PORTFEL
# ---------------------------------------------------------------------------
@app.route('/api/portfel/import', methods=['POST'])
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


@app.route('/api/portfel/royxat', methods=['GET'])
def portfel_royxat():
    dpd_chegara = int(db.get_all_settings().get('dpd_chegara_kun', 45))
    rows = db.get_portfel_45_kun(dpd_chegara)
    natija = []
    for r in rows[:500]:
        turi, mijoz = util.resolve_mijoz(r)
        jami = (r.get('asosiy_qarz') or 0) + (r.get('foiz_qarz') or 0) + (r.get('jarima') or 0)
        natija.append({
            'anketa_raqami': r['anketa_raqami'], 'mijoz_nomi': r['mijoz_nomi'], 'turi': turi,
            'dpd': r.get('dpd_max', 0), 'jami_qarz': jami,
        })
    return jsonify({'royxat': natija, 'jami': len(rows)})


# ---------------------------------------------------------------------------
# MIJOZLAR BAZASI
# ---------------------------------------------------------------------------
@app.route('/api/mijozlar/stats', methods=['GET'])
def mijozlar_stats():
    conn = db.get_conn()
    jis = conn.execute("SELECT COUNT(*) c FROM mijozlar WHERE turi='jismoniy'").fetchone()['c']
    yur = conn.execute("SELECT COUNT(*) c FROM mijozlar WHERE turi='yuridik'").fetchone()['c']
    conn.close()
    return jsonify({'jismoniy': jis, 'yuridik': yur})


@app.route('/api/mijozlar/import_txt', methods=['POST'])
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


@app.route('/api/mijozlar/excel_ustunlari', methods=['POST'])
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


@app.route('/api/mijozlar/excel_import', methods=['POST'])
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


# ---------------------------------------------------------------------------
# REJA GRAFIK
# ---------------------------------------------------------------------------
@app.route('/api/sud/kunlari', methods=['GET'])
def sud_kunlari_royxat_endpoint():
    return jsonify({'royxat': db.sud_kunlari_royxati()})


@app.route('/api/sud/kunlari', methods=['POST'])
def sud_kuni_qoshish_endpoint():
    """Sud kunini qo'lda (anketa raqami bilan) qo'shadi. Agar sud ish
    raqami berilgan bo'lsa, u shu anketaning yig'ma jild tituli va boshqa
    tegishli joylariga AVTOMATIK to'ldiriladi."""
    data = request.get_json() or {}
    anketa = data.get('anketa_raqami', '').strip()
    if not anketa:
        return jsonify({'xato': 'anketa_raqami kerak'}), 400
    rows = db.get_portfel_by_anketa(anketa)
    mijoz_nomi = rows[0]['mijoz_nomi'] if rows else data.get('mijoz_nomi', '')
    db.sud_kuni_qoshish(anketa, mijoz_nomi, data.get('sud_sanasi', ''), data.get('sud_vaqti', ''),
                         data.get('sud_nomi', ''), data.get('sud_ish_raqami', ''))
    return jsonify({'ok': True})


@app.route('/api/sud/kunlari/excel_yuklash', methods=['POST'])
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


@app.route('/api/sud/kunlari/<int:sud_kuni_id>', methods=['DELETE'])
def sud_kuni_ochirish_endpoint(sud_kuni_id):
    db.sud_kuni_ochirish(sud_kuni_id)
    return jsonify({'ok': True})


@app.route('/api/sud/kunlari/eslatmalar', methods=['GET'])
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


@app.route('/api/sud/xarajatlar', methods=['GET'])
def sud_xarajatlar_royxat_endpoint():
    db.sud_xarajatlar_tolov_moslashtirish_tekshirish()
    return jsonify({'royxat': db.sud_xarajatlar_royxati()})


@app.route('/api/sud/xarajatlar', methods=['POST'])
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


@app.route('/api/sud/xarajatlar_shablon', methods=['GET'])
def sud_xarajatlar_shablon():
    import tempfile
    from flask import send_file
    import pandas as pd
    df = pd.DataFrame(columns=['Anketa raqami', 'Mijoz nomi (ixtiyoriy)', 'PINFL/STIR (ixtiyoriy)', 'Xarajat summasi'])
    with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp:
        tmp_path = tmp.name
    df.to_excel(tmp_path, index=False)
    return send_file(tmp_path, as_attachment=True, download_name='sud_xarajatlar_shabloni.xlsx')


@app.route('/api/sud/xarajatlar_excel_yuklash', methods=['POST'])
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


@app.route('/api/sud/xarajatlar/<int:xarajat_id>/mib_ochish', methods=['POST'])
def sud_xarajat_mib_ochish_endpoint(xarajat_id):
    """Mijozning sud qarori 'bank foydasiga' bo'lib, MIBga o'tkazilgach —
    pochta xarajati summasiga teng YANGI, ALOHIDA ijro ishi avtomatik
    ochiladi (o'sha sud ish raqami bilan bog'liq holda)."""
    data = request.get_json() or {}
    mib_ijro_ish_raqami = data.get('mib_ijro_ish_raqami', '')
    db.sud_xarajat_mib_ish_ochish(xarajat_id, mib_ijro_ish_raqami)
    return jsonify({'ok': True})


@app.route('/api/reja/kunlik', methods=['GET'])
def reja_kunlik():
    return jsonify(db.get_ish_kuni_rejasi())


@app.route('/api/reja/tarmoq', methods=['GET'])
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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    # MUHIM: backend har doim '0.0.0.0' ga bog'lanadi — ya'ni shu
    # kompyuter tarmoqdagi boshqa kompyuterlar uchun ham "server" bo'la
    # oladi (agar ular shu kompyuterning IP manziliga ulansa). Bitta,
    # yagona kompyuterda ishlatilganda buning hech qanday farqi yo'q —
    # Windows Firewall baribir ruxsat so'raydi/yopadi, shuning uchun bu
    # xavfsiz standart holat.
    host = os.environ.get('BACKEND_HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=False)
