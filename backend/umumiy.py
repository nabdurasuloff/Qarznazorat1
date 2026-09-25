# -*- coding: utf-8 -*-
"""
UMUMIY YORDAMCHILAR — bir necha bo'lim baravar ishlatadigan funksiyalar.

Bu yerga fayl saqlash, hujjat papkalari tuzilmasi va mijozni aniqlash
kabi, hech bir aniq bo'limga tegishli bo'lmagan, lekin hammasiga kerak
bo'ladigan funksiyalar yig'ilgan. Ilgari ular server.py ichida edi;
server.py bo'laklarga ajratilganda bu yerga ko'chirildi.
"""
import os
import sys
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database as db
import letters


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


def anketa_mijoz_nomi(anketa_raqami, xat=None):
    """Anketa raqamiga QAYSI mijoz to'g'ri kelishini aniqlaydi.

    MUHIM (real bazada aniqlangan muammo): portfelda BITTA anketa raqami
    ostida IKKI xil mijoz uchrashi mumkin (masalan eski, yopilgan jismoniy
    shaxs krediti va yangi yuridik shaxs krediti bir xil raqamni olgan).
    Shunday holatda `get_portfel_by_anketa(...)[0]` TASODIFIY qatorni
    qaytaradi va hujjatlar BOSHQA mijozning papkasiga tushib ketardi.
    Shuning uchun:
      1) agar xat yozuvi bo'lsa — uning O'Z portfel_id si bo'yicha
         (xat aniq qaysi kredit uchun ochilgani ma'lum);
      2) aks holda — qarzi eng katta (ya'ni haqiqatda faol) qator."""
    if xat and xat.get('portfel_id'):
        prow = db.get_portfel_by_id(xat['portfel_id'])
        if prow and prow.get('mijoz_nomi'):
            return prow['mijoz_nomi']
    if xat and xat.get('mijoz_nomi'):
        return xat['mijoz_nomi']
    rows = db.get_portfel_by_anketa(anketa_raqami) or []
    if not rows:
        return ''
    rows = sorted(rows, key=lambda p: (p.get('asosiy_qarz') or 0) + (p.get('foiz_qarz') or 0), reverse=True)
    return rows[0].get('mijoz_nomi', '')


def sugurta_hujjatlari_mijoz_papkasi(mijoz_nomi, anketa_raqami=None):
    """Sug'urtadan undirish bo'yicha barcha hujjatlar (MIB asos hujjati,
    polis, ariza, javob, qo'shimcha hujjatlar) uchun papka:
        Huquqiy choralar/Sug'urta undirish/[mijoz nomi]_[anketa]/
    MUHIM: papka nomiga ANKETA RAQAMI ham qo'shiladi — bir mijozning
    bir necha anketasi bo'lsa, hujjatlar aralashib ketmasligi uchun."""
    papka_nomi = letters.safe_filename(mijoz_nomi)
    if anketa_raqami:
        papka_nomi = f"{papka_nomi}_{letters.safe_filename(anketa_raqami)}"
    path = os.path.join(huquqiy_choralar_papkasi(), "Sug'urta undirish", papka_nomi)
    os.makedirs(path, exist_ok=True)
    return path


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


def yigma_jild_javobi(fayllar, output_path, download_name):
    """Yig'ma jildni (Sud yoki MIB) tayyorlab, brauzerga yuboradi.

    MUHIM: ilgari Sud va MIB yig'ma jildlari bir-biridan mustaqil yozilgan
    edi va bir xil kamchiliklar ikki joyda takrorlanardi. Endi ikkalasi ham
    shu yagona funksiyani chaqiradi — bir joyda tuzatilgan xato ikkalasida
    ham tuzaladi.

    Qo'shilmay qolgan hujjatlar (masalan buzilgan skaner fayli) BUTUN
    jildni to'xtatib qo'ymaydi: qolganlari birlashtiriladi, qo'shilmaganlar
    esa javob sarlavhasi orqali foydalanuvchiga ogohlantirish bo'lib boradi.
    """
    import urllib.parse
    from flask import jsonify, send_file

    if not fayllar:
        return jsonify({'xato': "Hujjatlar topilmadi"}), 400

    xatolar = []
    try:
        letters._birlashtir_pdf(fayllar, output_path, xatolar=xatolar)
    except Exception as e:
        return jsonify({'xato': f"Birlashtirishda xato: {e}"}), 500

    javob = send_file(output_path, as_attachment=True, download_name=download_name)
    if xatolar:
        # HTTP sarlavhasi faqat ASCII bo'lishi mumkin — shu sabab kodlaymiz
        matn = "Quyidagi hujjatlar jildga qo'shilmadi:\n• " + "\n• ".join(xatolar)
        javob.headers['X-Jild-Ogohlantirish'] = urllib.parse.quote(matn)
    return javob


def ruxsat_etilgan_papkalar():
    """Dastur o'z hujjatlarini saqlaydigan barcha ildiz papkalar ro'yxati."""
    papkalar = []
    try:
        papkalar.append(hujjatlar_papkasi())
    except Exception:
        pass
    try:
        papkalar.append(db._app_dir())
    except Exception:
        pass
    sozlama = db.get_setting('hujjatlar_papkasi', '')
    if sozlama:
        papkalar.append(sozlama)
    # tizimdan oldingi (eski) hujjatlar papkasi ham ko'rsatilishi mumkin
    eski = db.get_setting('tizimdan_oldingi_papka', '')
    if eski:
        papkalar.append(eski)
    natija = []
    for p in papkalar:
        try:
            natija.append(os.path.realpath(p))
        except Exception:
            continue
    return natija


def fayl_ruxsat_etilganmi(yol):
    """Berilgan fayl dasturning O'Z papkalari ichidami?

    MUHIM XAVFSIZLIK: fayl ko'rsatish endpointi ilgari kompyuterdagi
    ISTALGAN faylni berardi. Bu tekshiruv faqat dastur papkalari ichidagi
    hujjatlarga ruxsat beradi. `os.path.realpath` ishlatiladi — shunda
    `..` orqali chiqib ketish yoki yorliq (symlink) orqali aylanib o'tish
    ham ishlamaydi, va papka nomi bir xil BOSHLANADIGAN qo'shni papka
    ("Hujjatlar_eski") noto'g'ri ruxsat olmasligi uchun ajratuvchi belgi
    bilan solishtiriladi."""
    try:
        haqiqiy = os.path.realpath(yol)
    except Exception:
        return False
    for papka in ruxsat_etilgan_papkalar():
        if haqiqiy == papka or haqiqiy.startswith(papka + os.sep):
            return True
    return False
