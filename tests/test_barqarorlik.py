# -*- coding: utf-8 -*-
"""BARQARORLIK — to'liq tekshiruvda topilgan xatolar qayta paydo bo'lmasin.

Bu testlar 2026-09-23 dagi to'liq audit natijasida yozildi. Har biri
AYNAN bitta haqiqiy xatoni qo'riqlaydi.
"""
import datetime
import importlib
import os

import pytest


# ── 1. Aniqlanmagan nomlar (NameError -> butun bo'lim 500 berardi) ────

def test_bolimlarda_aniqlanmagan_nom_yoq(muhit):
    """MUHIM: bo'limlar server.py dan ajratilganda ba'zi nomlar import
    qilinmay qolgan edi (AMAL_TURLARI_MAP, app) — natijada MIB ro'yxati,
    bosh sahifa qidiruvi va Chora ko'rishdagi ommaviy amal HAR DOIM ichki
    xato (500) berardi. Bu test har bir modulni tekshiradi."""
    import ast
    import builtins
    import glob
    asos = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'backend', 'yollar')
    muammolar = []
    for yol in sorted(glob.glob(os.path.join(asos, '*.py'))):
        manba = open(yol, encoding='utf-8').read()
        daraxt = ast.parse(manba)
        # Modul darajasida aniqlangan/import qilingan nomlar
        aniqlangan = set(dir(builtins)) | {'__name__', '__file__', '__doc__'}
        for tugun in ast.walk(daraxt):
            if isinstance(tugun, (ast.Import, ast.ImportFrom)):
                for n in tugun.names:
                    aniqlangan.add((n.asname or n.name).split('.')[0])
            elif isinstance(tugun, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                aniqlangan.add(tugun.name)
            elif isinstance(tugun, ast.Name) and isinstance(tugun.ctx, ast.Store):
                aniqlangan.add(tugun.id)
            elif isinstance(tugun, ast.arg):
                aniqlangan.add(tugun.arg)
            elif isinstance(tugun, ast.ExceptHandler) and tugun.name:
                aniqlangan.add(tugun.name)
            elif isinstance(tugun, (ast.comprehension,)):
                pass
        for tugun in ast.walk(daraxt):
            if isinstance(tugun, ast.Name) and isinstance(tugun.ctx, ast.Load):
                if tugun.id not in aniqlangan:
                    muammolar.append(f"{os.path.basename(yol)}:{tugun.lineno}: '{tugun.id}'")
    assert not muammolar, ("Aniqlanmagan nomlar (ishlaganda 500 xato beradi):\n  "
                           + "\n  ".join(sorted(set(muammolar))))


def test_mib_royxati_harakat_bilan_ishlaydi(muhit, mijoz, klient):
    """MIB ishida harakat qayd etilgan bo'lsa ham ro'yxat ochilishi kerak
    (ilgari AYNAN shunda 500 berardi — ya'ni haqiqiy ishlarning hammasida)."""
    db = muhit['db']
    conn = db.get_conn()
    cur = conn.execute("""INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi,
        xat_turi, holat, mib_holati, mib_ish_raqami, mib_otkazilgan_sana, yaratilgan_sana)
        VALUES (?, '10001', ?, 'jismoniy', 'talabnoma', 'yuborildi', 'otkazildi',
                'MIB-1', '01.08.2026', ?)""",
        (mijoz['id'], mijoz['mijoz_nomi'], datetime.datetime.now().isoformat()))
    xat_id = cur.lastrowid
    conn.commit()
    conn.close()
    db.add_mib_amal(xat_id, 'hisob_raqam_qidirish', '05.09.2026', 'Test harakat')

    for ep in ('/api/mib/faol', '/api/dashboard/qidirish?anketa=10001',
               '/api/mib/jarayondagilar_excel'):
        r = klient.get(ep)
        assert r.status_code < 500, f"{ep} -> {r.status_code} (ichki xato)"


# ── 2. Anketa raqami bo'yicha ANIQ moslik ────────────────────────────

def test_anketa_qidiruvi_boshqa_mijozni_qaytarmaydi(muhit, mijoz):
    """ENG XAVFLI XATO: qidiruv `LIKE '%raqam%'` bo'lgani uchun "1234"
    so'ralganda "91234" mijozi ham topilardi va chaqiruvchi birinchi
    natijani olgani uchun HUJJAT BOSHQA MIJOZ nomiga tayyorlanib qolishi
    mumkin edi. Haqiqiy portfelda 300 anketadan 70 tasi shu xavf ostida edi."""
    db = muhit['db']
    conn = db.get_conn()
    conn.execute("""INSERT INTO portfel (anketa_raqami, mijoz_nomi, mijoz_turi, port_kod, faol)
                    VALUES ('91234', 'BOSHQA ODAM', 'Individual', 'PK2', 1)""")
    conn.execute("""INSERT INTO portfel (anketa_raqami, mijoz_nomi, mijoz_turi, port_kod, faol)
                    VALUES ('1234', 'HAQIQIY MIJOZ', 'Individual', 'PK3', 1)""")
    conn.commit()
    conn.close()

    topilgan = db.get_portfel_by_anketa('1234')
    assert len(topilgan) == 1, f"Bir nechta mijoz topildi: {[t['mijoz_nomi'] for t in topilgan]}"
    assert topilgan[0]['mijoz_nomi'] == 'HAQIQIY MIJOZ'


def test_bosh_anketa_hech_narsa_qaytarmaydi(muhit, mijoz):
    """Bo'sh so'rov butun portfelni qaytarib yubormasligi kerak."""
    db = muhit['db']
    assert db.get_portfel_by_anketa('') == []
    assert db.get_portfel_by_anketa(None) == []


# ── 3. Sozlamalar noto'g'ri bo'lsa ham ekran ishlaydi ────────────────

def test_bosh_sozlama_ekranni_ochirmaydi(muhit, mijoz, klient):
    """MUHIM: foydalanuvchi Sozlamalarda raqamli maydonni BO'SHATIB saqlasa,
    ilgari Bosh sahifa, Talabnoma va Chora ko'rish butunlay ochilmay qolardi
    (int('') xatosi). Endi standart qiymat ishlatiladi."""
    db = muhit['db']
    for yomon in ('', '   ', '45 kun', 'abc'):
        db.set_setting('dpd_chegara_kun', yomon)
        for ep in ('/api/dashboard/summary', '/api/talabnoma/royxat',
                   '/api/portfel/royxat', '/api/chora/royxat'):
            r = klient.get(ep)
            assert r.status_code < 500, f"'{yomon}' qiymatida {ep} -> {r.status_code}"


def test_notogri_sozlama_saqlanmaydi(muhit, klient):
    """Foydalanuvchi darhol tushunarli xato olishi kerak."""
    r = klient.post('/api/sozlamalar', json={'dpd_chegara_kun': 'abc'})
    assert r.status_code == 400
    assert 'dpd_chegara_kun' in r.get_json()['xato']

    r = klient.post('/api/sozlamalar', json={'davo_ariza_muddati_kun': ''})
    assert r.status_code == 400

    # To'g'ri qiymat — saqlanadi
    r = klient.post('/api/sozlamalar', json={'dpd_chegara_kun': '60'})
    assert r.status_code == 200
    assert muhit_sozlama(muhit, 'dpd_chegara_kun') == 60


def muhit_sozlama(muhit, kalit):
    return muhit['db'].get_all_settings().get(kalit)


def test_bosh_joyli_summa_qabul_qilinadi(muhit):
    """«1 500 000» — O'zbekistonda odatiy yozuv. Ilgari 500 xato berardi."""
    util = muhit['util']
    assert util.son_tekshir('1 500 000', 'Summa')[0] == 1500000
    assert util.son_tekshir('1,200,000', 'Summa')[0] == 1200000
    assert util.son_tekshir('45,5', 'Summa')[0] == 45.5
    son, xato = util.son_tekshir('abc', 'Summa')
    assert son is None and 'raqam' in xato


# ── 4. Fayl xavfsizligi ──────────────────────────────────────────────

def test_fayl_korish_tashqi_faylni_bermaydi(muhit, klient):
    """MUHIM XAVFSIZLIK: bu endpoint ilgari kompyuterdagi ISTALGAN faylni
    berardi (baza fayli, mijozlarning pasport skanerlari). Server tarmoqda
    ochiq bo'lgani uchun buni har kim qila olardi."""
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.txt', delete=False, dir='/tmp') as t:
        t.write(b'maxfiy')
        tashqi = t.name
    r = klient.get(f'/api/fayl_korish?yol={tashqi}')
    assert r.status_code == 403, "Dastur papkasidan tashqaridagi fayl berilmoqda!"


def test_fayl_korish_ozining_faylini_beradi(muhit, klient):
    """Dastur papkasidagi hujjat esa avvalgidek ochilishi kerak."""
    papka = muhit['db'].get_setting('hujjatlar_papkasi', '')
    yol = os.path.join(papka, 'sinov.txt')
    with open(yol, 'w') as f:
        f.write('hujjat')
    r = klient.get(f'/api/fayl_korish?yol={yol}')
    assert r.status_code == 200


def test_yuklangan_fayl_nomi_tozalanadi():
    """Yuklangan fayl nomi to'g'ridan-to'g'ri yo'lga qo'shilmasligi kerak —
    aks holda nomdagi '..' yoki '/' orqali boshqa papkaga yozib yuborish
    (masalan shablon faylini almashtirib qo'yish) mumkin edi."""
    import re
    import glob
    asos = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'backend', 'yollar')
    topilgan = []
    for yol in sorted(glob.glob(os.path.join(asos, '*.py'))):
        for i, qator in enumerate(open(yol, encoding='utf-8'), 1):
            toza = qator.split('#')[0]
            if 'splitext' in toza or '.filename:' in toza:
                continue
            if re.search(r'[{+]\s*\w*f\.filename', toza) and 'safe_filename' not in toza:
                topilgan.append(f"{os.path.basename(yol)}:{i}")
    assert not topilgan, ("Yuklangan fayl nomi tozalanmagan: " + ', '.join(topilgan))


# ── 5. Yuklash xatosi yashirilmasin ──────────────────────────────────

def test_yuklash_natijasi_har_doim_tekshiriladi():
    """MUHIM: bo'sh/buzuq fayl yuklansa, tizim "yuklandi" deb yozib
    qo'yardi va jild (masalan MIBga) ijro varaqasisiz ketardi."""
    import glob
    asos = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'backend', 'yollar')
    topilgan = []
    for yol in sorted(glob.glob(os.path.join(asos, '*.py'))):
        qatorlar = open(yol, encoding='utf-8').readlines()
        for i, q in enumerate(qatorlar):
            if 'mustahkam_fayl_saqlash(' not in q or 'import' in q or 'def ' in q:
                continue
            if '=' not in q.split('mustahkam_fayl_saqlash(')[0]:
                topilgan.append(f"{os.path.basename(yol)}:{i+1}")
    assert not topilgan, ("Yuklash natijasi tekshirilmagan joylar: " + ', '.join(topilgan))


# ── 6. Sana tekshiruvi ───────────────────────────────────────────────

def test_notogri_sana_qabul_qilinmaydi(muhit, mijoz, klient):
    """Noto'g'ri formatdagi sana jim qabul qilinsa, shu ish uchun barcha
    muddat ogohlantirishlari ishlamay qolardi."""
    db = muhit['db']
    conn = db.get_conn()
    conn.execute("""INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi,
        xat_turi, holat, davo_ariza_holati, sud_hujjatlar_ruxsat, yaratilgan_sana)
        VALUES (?, '10001', ?, 'jismoniy', 'talabnoma', 'yuborildi', 'olib_kelindi', 1, ?)""",
        (mijoz['id'], mijoz['mijoz_nomi'], datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

    r = klient.post('/api/sud/topshirildi', data={
        'anketa_raqami': '10001', 'ish_raqami': 'A-1', 'sana': '32.13.2026'})
    assert r.status_code == 400, "Mavjud bo'lmagan sana qabul qilindi"


# ── 7. Tahlil tarixi — oxirgi kunlar ─────────────────────────────────

def test_tahlil_tarixi_oxirgi_kunlarni_beradi(muhit):
    """MUHIM: grafik ENG ESKI N kunni ko'rsatardi — ya'ni 90 kundan keyin
    tendensiya grafigi "muzlab" qolib, joriy holatni ko'rsatmay qo'yardi."""
    db = muhit['db']
    conn = db.get_conn()
    for i in range(1, 8):
        conn.execute("INSERT INTO tahlil_tarixi (sana, jami_soni) VALUES (?, ?)",
                     (f"2026-09-{i:02d}", i * 100))
    conn.commit()
    conn.close()

    tarix = db.get_tahlil_tarixi(3)
    sanalar = [t['sana'] for t in tarix]
    assert sanalar == ['2026-09-05', '2026-09-06', '2026-09-07'], \
        f"Oxirgi 3 kun emas: {sanalar}"


# ── 8. Indekslar ─────────────────────────────────────────────────────

def test_tezlik_indekslari_yaratilgan(muhit):
    """55 000 qatorli portfelda indekssiz qidiruv butun jadvalni skanerlaydi."""
    conn = muhit['db'].get_conn()
    idx = {r['name'] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index'").fetchall()}
    conn.close()
    kerakli = {'idx_portfel_anketa', 'idx_xatlar_anketa', 'idx_xatlar_portfel',
               'idx_mib_amallar_xat', 'idx_vafot_anketa'}
    yetishmayotgan = kerakli - idx
    assert not yetishmayotgan, f"Indekslar yaratilmagan: {yetishmayotgan}"


def test_anketa_qidiruvi_indeksdan_foydalanadi(muhit):
    conn = muhit['db'].get_conn()
    reja = [r['detail'] for r in conn.execute(
        "EXPLAIN QUERY PLAN SELECT * FROM portfel WHERE anketa_raqami = '123'").fetchall()]
    conn.close()
    assert any('idx_portfel_anketa' in r for r in reja), f"Indeks ishlatilmayapti: {reja}"


# ── 9. Frontend ──────────────────────────────────────────────────────

def _frontend_fayllar():
    import glob
    asos = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'frontend', 'src')
    return sorted(glob.glob(os.path.join(asos, '**', '*.js'), recursive=True))


def test_hisobotlar_windowopen_bilan_ochilmaydi():
    """Electronda window.open TASHQI brauzerni ochadi — ro'yxat bo'sh bo'lsa
    foydalanuvchi xom JSON matnni ko'rardi."""
    topilgan = []
    for yol in _frontend_fayllar():
        for i, q in enumerate(open(yol, encoding='utf-8'), 1):
            toza = q.split('//')[0]
            if 'window.open(' in toza and 'API_BASE' in toza and 'fayl_korish' not in toza:
                topilgan.append(f"{os.path.basename(yol)}:{i}")
    assert not topilgan, ("Hisobot window.open bilan ochilmoqda: " + ', '.join(topilgan))


def test_xavfsizmatn_yordamchisi_mavjud():
    """Mijoz nomida qo'shtirnoq bo'lsa ("AGRO" MCHJ) — atribut uzilib,
    tugma noto'g'ri ishlardi."""
    yol = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'frontend', 'src', 'ekranlar', 'umumiy.js')
    matn = open(yol, encoding='utf-8').read()
    assert 'function xavfsizMatn(' in matn
    for belgi in ('&amp;', '&lt;', '&quot;'):
        assert belgi in matn


def test_nom_saqlaydigan_atributlar_xavfsiz():
    topilgan = []
    import re
    for yol in _frontend_fayllar():
        for i, q in enumerate(open(yol, encoding='utf-8'), 1):
            if re.search(r'data-mijoz="\$\{(?!xavfsizMatn)', q):
                topilgan.append(f"{os.path.basename(yol)}:{i}")
    assert not topilgan, ("Mijoz nomi xavfsizlantirilmagan: " + ', '.join(topilgan))


def test_dastur_tuzilmasi_tiklanadi():
    """«Qayta urinish» bosilganda oyna mangu bo'sh qolib ketmasligi kerak."""
    yol = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'frontend', 'src', 'ekranlar', 'umumiy.js')
    matn = open(yol, encoding='utf-8').read()
    assert 'function dasturTuzilmasiniTiklash(' in matn
    assert 'dasturTuzilmasiniTiklash();' in matn.split('function dasturniBoshlash(')[1][:1200]


def test_backend_xatosi_dasturni_yiqitmaydi():
    """spawn 'error' tinglanmasa, Electron butunlay yopilib ketardi."""
    yol = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'frontend', 'main.js')
    matn = open(yol, encoding='utf-8').read()
    assert "backendProcess.on('error'" in matn
