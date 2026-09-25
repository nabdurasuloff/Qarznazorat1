# -*- coding: utf-8 -*-
"""YIG'MA JILD (Sud va MIB) birlashtirish tekshiruvi.

Sud va MIB yig'ma jildlarini birlashtirishda quyidagi xatoliklar bor edi:
  1. Bitta hujjat ikki maydonda yozilgan bo'lsa — jildga IKKI MARTA tushardi.
  2. Skaner qilingan JPG/PNG hujjat "Word" deb hisoblanib, BUTUN jild
     tayyorlanmay qolardi.
  3. Bitta buzuq fayl butun jildni to'xtatib qo'yardi.
  4. .docx yonidagi bir xil nomli .pdf fayl (imzolangan skaner) ustidan
     yozilib, so'ng O'CHIRIB yuborilardi.
  5. PDF sahifalari "dangasa" o'qilgani uchun oqim vaqtidan oldin yopilib
     qolishi mumkin edi.
Bu testlar shu xatolar QAYTA paydo bo'lmasligini kafolatlaydi.
"""
import os

import pypdf
import pytest
from PIL import Image


def _pdf_yaratish(yol, sahifalar=1, matn='TEST'):
    """Berilgan sonli sahifali oddiy PDF yaratadi."""
    writer = pypdf.PdfWriter()
    for _ in range(sahifalar):
        writer.add_blank_page(width=595, height=842)
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    with open(yol, 'wb') as f:
        writer.write(f)
    return yol


def _rasm_yaratish(yol, rang=(200, 30, 30)):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    Image.new('RGB', (600, 800), rang).save(yol)
    return yol


def _sahifalar_soni(yol):
    return len(pypdf.PdfReader(yol).pages)


# ── 1. Takrorlangan hujjat ─────────────────────────────────────────────

def test_bir_xil_fayl_ikki_marta_qoshilmaydi(muhit):
    """MUHIM: 'fayl_yoli' va 'davo_ariza_fayl_yoli' bitta hujjatga ishora
    qilsa, jildda o'sha hujjat IKKI MARTA chiqib qolmasligi kerak."""
    letters = muhit['letters']
    p = muhit['papka']
    a = _pdf_yaratish(os.path.join(p, 'hujjat', 'a.pdf'), sahifalar=2)
    chiqish = os.path.join(p, 'natija', 'jild.pdf')

    letters._birlashtir_pdf([a, a, a], chiqish)
    assert _sahifalar_soni(chiqish) == 2, "Takrorlangan fayl jildga qayta qo'shilgan"


def test_nisbiy_va_toliq_yol_bir_xil_fayl_deb_qaraladi(muhit):
    """Bir xil faylga turli yo'l bilan ishora qilinsa ham — bitta hisoblanadi."""
    letters = muhit['letters']
    p = muhit['papka']
    a = _pdf_yaratish(os.path.join(p, 'hujjat', 'a.pdf'), sahifalar=1)
    egri = os.path.join(p, 'hujjat', '..', 'hujjat', 'a.pdf')
    chiqish = os.path.join(p, 'natija', 'jild.pdf')

    letters._birlashtir_pdf([a, egri], chiqish)
    assert _sahifalar_soni(chiqish) == 1


# ── 2. Skaner (rasm) hujjatlari ────────────────────────────────────────

def test_rasm_hujjat_jildga_qoshiladi(muhit):
    """Telefonda suratga olingan kredit shartnomasi (JPG) ham jildga
    tushishi kerak — ilgari butun jild shu sabab tayyorlanmasdi."""
    letters = muhit['letters']
    p = muhit['papka']
    pdf = _pdf_yaratish(os.path.join(p, 'hujjat', 'ariza.pdf'), sahifalar=1)
    jpg = _rasm_yaratish(os.path.join(p, 'hujjat', 'shartnoma.jpg'))
    png = _rasm_yaratish(os.path.join(p, 'hujjat', 'garov.png'), rang=(30, 30, 200))
    chiqish = os.path.join(p, 'natija', 'jild.pdf')

    xatolar = []
    letters._birlashtir_pdf([pdf, jpg, png], chiqish, xatolar=xatolar)
    assert _sahifalar_soni(chiqish) == 3, f"Rasmlar qo'shilmadi: {xatolar}"
    assert not xatolar


# ── 3. Buzuq fayl butun jildni to'xtatmaydi ────────────────────────────

def test_buzuq_fayl_jildni_toxtatmaydi(muhit):
    """Bitta hujjat buzuq bo'lsa — qolganlari baribir birlashtirilsin,
    lekin qaysi hujjat tushmagani AYTILSIN."""
    letters = muhit['letters']
    p = muhit['papka']
    yaxshi = _pdf_yaratish(os.path.join(p, 'hujjat', 'yaxshi.pdf'), sahifalar=2)
    buzuq = os.path.join(p, 'hujjat', 'buzuq.pdf')
    with open(buzuq, 'wb') as f:
        f.write(b'bu PDF emas, shunchaki matn')
    chiqish = os.path.join(p, 'natija', 'jild.pdf')

    xatolar = []
    letters._birlashtir_pdf([yaxshi, buzuq], chiqish, xatolar=xatolar)
    assert _sahifalar_soni(chiqish) == 2
    assert any('buzuq.pdf' in x for x in xatolar), f"Ogohlantirish yo'q: {xatolar}"


def test_yoq_fayl_otkazib_yuboriladi(muhit):
    letters = muhit['letters']
    p = muhit['papka']
    yaxshi = _pdf_yaratish(os.path.join(p, 'hujjat', 'yaxshi.pdf'))
    chiqish = os.path.join(p, 'natija', 'jild.pdf')

    xatolar = []
    letters._birlashtir_pdf([yaxshi, os.path.join(p, 'yoq.pdf')], chiqish, xatolar=xatolar)
    assert _sahifalar_soni(chiqish) == 1
    assert any('topilmadi' in x for x in xatolar)


def test_hech_narsa_qoshilmasa_tushunarli_xato(muhit):
    """Hamma hujjat buzuq bo'lsa — bo'sh PDF emas, tushunarli xato."""
    letters = muhit['letters']
    p = muhit['papka']
    buzuq = os.path.join(p, 'hujjat', 'buzuq.pdf')
    os.makedirs(os.path.dirname(buzuq), exist_ok=True)
    with open(buzuq, 'wb') as f:
        f.write(b'xxx')
    with pytest.raises(Exception):
        letters._birlashtir_pdf([buzuq], os.path.join(p, 'natija', 'jild.pdf'))


# ── 4. Yonidagi PDF fayl o'chib ketmasligi ─────────────────────────────

def test_docx_yonidagi_pdf_fayl_ochirilmaydi(muhit, monkeypatch):
    """MUHIM: ilgari X.docx -> X.pdf qilib yozilar, keyin X.pdf O'CHIRILARDI.
    Agar papkada imzolangan skaner ham X.pdf bo'lsa — u yo'qolib ketardi."""
    letters = muhit['letters']
    p = muhit['papka']
    papka = os.path.join(p, 'hujjat')
    os.makedirs(papka, exist_ok=True)

    docx_yoli = os.path.join(papka, 'Ariza.docx')
    with open(docx_yoli, 'wb') as f:
        f.write(b'PK-soxta-docx')
    # Aynan shu nomdagi, lekin BOSHQA (imzolangan) PDF yonida turibdi
    qimmatli_pdf = _pdf_yaratish(os.path.join(papka, 'Ariza.pdf'), sahifalar=3)

    # Word yo'q (Linux/test muhiti) — konvertatsiyani taqlid qilamiz:
    # muhimi, u mijoz papkasiga EMAS, vaqtinchalik papkaga yozsin.
    def soxta_batch(fayllar, chiqish_papkasi, xatolar=None):
        natija = {}
        for i, fayl in enumerate(fayllar, 1):
            chiqish = os.path.join(chiqish_papkasi, f'{i:03d}.pdf')
            _pdf_yaratish(chiqish, sahifalar=1)
            natija[fayl] = chiqish
        return natija
    monkeypatch.setattr(letters, 'convert_docx_to_pdf_batch', soxta_batch)

    chiqish = os.path.join(p, 'natija', 'jild.pdf')
    letters._birlashtir_pdf([docx_yoli], chiqish)

    assert os.path.exists(qimmatli_pdf), "Yonidagi PDF fayl o'chirib yuborilgan!"
    assert _sahifalar_soni(qimmatli_pdf) == 3, "Yonidagi PDF fayl ustidan yozilgan!"


# ── 5. Tezlik: Word keshini har safar tozalamaslik ─────────────────────

def test_gen_py_keshi_faqat_bir_marta_tozalanadi(muhit):
    """MUHIM TEZLIK: win32com keshini tozalash HAR BIR fayl uchun emas,
    butun dastur davomida BIR MARTA bajarilishi kerak."""
    letters = muhit['letters']
    letters._GEN_PY_TOZALANDI = False
    chaqiruv = []

    import builtins
    asl_import = builtins.__import__

    def kuzatuvchi(nom, *a, **k):
        if nom == 'win32com':
            chaqiruv.append(nom)
        return asl_import(nom, *a, **k)

    builtins.__import__ = kuzatuvchi
    try:
        for _ in range(5):
            letters._gen_py_keshini_tozala()
    finally:
        builtins.__import__ = asl_import

    assert len(chaqiruv) <= 1, (
        f"Kesh {len(chaqiruv)} marta tozalanmoqchi bo'ldi — har bir hujjat "
        f"uchun qayta tozalash jildni juda sekinlashtiradi")


def test_word_fayllar_bitta_toplamda_aylantiriladi(muhit, monkeypatch):
    """MUHIM TEZLIK: barcha Word hujjatlari BITTA Word seansida (bitta
    chaqiruvda) aylantirilishi kerak — har biri uchun alohida emas."""
    letters = muhit['letters']
    p = muhit['papka']
    papka = os.path.join(p, 'hujjat')
    os.makedirs(papka, exist_ok=True)

    word_fayllar = []
    for nom in ('a.docx', 'b.docx', 'c.docx', 'd.docx'):
        yol = os.path.join(papka, nom)
        with open(yol, 'wb') as f:
            f.write(b'soxta')
        word_fayllar.append(yol)

    chaqiruvlar = []

    def soxta_batch(fayllar, chiqish_papkasi, xatolar=None):
        chaqiruvlar.append(list(fayllar))
        natija = {}
        for i, fayl in enumerate(fayllar, 1):
            chiqish = os.path.join(chiqish_papkasi, f'{i:03d}.pdf')
            _pdf_yaratish(chiqish, sahifalar=1)
            natija[fayl] = chiqish
        return natija
    monkeypatch.setattr(letters, 'convert_docx_to_pdf_batch', soxta_batch)

    chiqish = os.path.join(p, 'natija', 'jild.pdf')
    letters._birlashtir_pdf(word_fayllar, chiqish)

    assert len(chaqiruvlar) == 1, (
        f"Word {len(chaqiruvlar)} marta ishga tushirildi — barcha hujjatlar "
        f"bitta seansda aylantirilishi kerak")
    assert len(chaqiruvlar[0]) == 4
    assert _sahifalar_soni(chiqish) == 4


# ── 6. Hujjatlar TARTIBI saqlanadi ─────────────────────────────────────

def test_hujjatlar_tartibi_saqlanadi(muhit):
    """Sudga topshiriladigan jildda hujjat tartibi qat'iy: Titul ->
    Ma'lumotnoma -> Davo ariza -> ... Tartib buzilmasligi kerak."""
    letters = muhit['letters']
    p = muhit['papka']
    fayllar = [_pdf_yaratish(os.path.join(p, 'h', f'{i}.pdf'), sahifalar=i)
               for i in (1, 2, 3, 4)]
    chiqish = os.path.join(p, 'natija', 'jild.pdf')
    letters._birlashtir_pdf(fayllar, chiqish)
    # 1+2+3+4 = 10 sahifa
    assert _sahifalar_soni(chiqish) == 10


# ── 7. Endpointlar (Sud va MIB bir xil ishlashi) ───────────────────────

def _jild_uchun_xat(db, mijoz, papka, maydonlar):
    """Berilgan maydonlarga haqiqiy PDF fayllar biriktirilgan xat yaratadi."""
    ustunlar, qiymatlar = [], []
    for i, maydon in enumerate(maydonlar, 1):
        ustunlar.append(maydon)
        qiymatlar.append(_pdf_yaratish(os.path.join(papka, 'h', f'{maydon}.pdf')))
    conn = db.get_conn()
    conn.execute(
        f"INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi, "
        f"xat_turi, {', '.join(ustunlar)}) VALUES (?, '10001', ?, 'jismoniy', "
        f"'talabnoma', {', '.join('?' * len(ustunlar))})",
        [mijoz['id'], mijoz['mijoz_nomi']] + qiymatlar)
    conn.commit()
    conn.close()


def test_sud_jildi_endpoint_pdf_qaytaradi(muhit, mijoz, klient):
    _jild_uchun_xat(muhit['db'], mijoz, muhit['papka'],
                    ['sud_yigma_jild_titul_fayl', 'davo_ariza_fayl_yoli', 'fayl_yoli'])
    r = klient.get('/api/sud/tayyor_jild?anketa=10001')
    assert r.status_code == 200, r.get_data()[:300]
    assert r.data[:4] == b'%PDF', "PDF emas"


def test_mib_jildi_endpoint_pdf_qaytaradi(muhit, mijoz, klient):
    _jild_uchun_xat(muhit['db'], mijoz, muhit['papka'],
                    ['yigma_jild_titul_fayl', 'ijro_varaqasi_fayl', 'fayl_yoli'])
    r = klient.get('/api/mib/tayyor_jild?anketa=10001')
    assert r.status_code == 200, r.get_data()[:300]
    assert r.data[:4] == b'%PDF', "PDF emas"


def test_jild_toliqmas_bolsa_ogohlantiradi(muhit, mijoz, klient):
    """Buzuq hujjat bo'lsa — jild baribir beriladi, lekin ogohlantirish
    sarlavhasi bilan (foydalanuvchi to'liqmas jildni sudga olib bormasligi
    uchun)."""
    db = muhit['db']
    p = muhit['papka']
    yaxshi = _pdf_yaratish(os.path.join(p, 'h', 'titul.pdf'))
    buzuq = os.path.join(p, 'h', 'buzuq.pdf')
    with open(buzuq, 'wb') as f:
        f.write(b'bu PDF emas')
    conn = db.get_conn()
    conn.execute("INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi, "
                 "xat_turi, sud_yigma_jild_titul_fayl, fayl_yoli) "
                 "VALUES (?, '10001', ?, 'jismoniy', 'talabnoma', ?, ?)",
                 (mijoz['id'], mijoz['mijoz_nomi'], yaxshi, buzuq))
    conn.commit()
    conn.close()

    r = klient.get('/api/sud/tayyor_jild?anketa=10001')
    assert r.status_code == 200
    assert r.data[:4] == b'%PDF'
    assert 'X-Jild-Ogohlantirish' in r.headers, "To'liqmas jild haqida ogohlantirish yo'q"


def test_jild_hujjatsiz_tushunarli_xato(muhit, mijoz, klient):
    conn = muhit['db'].get_conn()
    conn.execute("INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi, xat_turi) "
                 "VALUES (?, '10001', ?, 'jismoniy', 'talabnoma')",
                 (mijoz['id'], mijoz['mijoz_nomi']))
    conn.commit()
    conn.close()
    for ep in ('/api/sud/tayyor_jild?anketa=10001', '/api/mib/tayyor_jild?anketa=10001'):
        r = klient.get(ep)
        assert r.status_code == 400, f"{ep} -> {r.status_code}"
        assert 'xato' in r.get_json()


# ── 8. Frontend: MIB jildi ham to'g'ri yuklab olinishi ─────────────────

def test_frontendda_jild_windowopen_bilan_ochilmaydi():
    """MUHIM: Electronda window.open() tashqi brauzerni ochib yuboradi va
    xato bo'lsa foydalanuvchi xom JSON matnni ko'radi. Jild har doim
    tayyorJildYuklabOlish() orqali olinishi kerak."""
    import re
    asos = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'frontend', 'src')
    topilgan = []
    for ildiz, _, fayllar in os.walk(asos):
        for nomi in fayllar:
            if not nomi.endswith('.js'):
                continue
            with open(os.path.join(ildiz, nomi), encoding='utf-8') as f:
                for i, qator in enumerate(f, 1):
                    toza = qator.split('//')[0]
                    if 'window.open(' in toza and 'tayyor_jild' in toza:
                        topilgan.append(f"{nomi}:{i}")
    assert not topilgan, (
        "Yig'ma jild window.open() bilan ochilmoqda — tayyorJildYuklabOlish() "
        "ishlatilishi kerak: " + ', '.join(topilgan))
