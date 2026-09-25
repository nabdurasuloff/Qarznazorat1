# -*- coding: utf-8 -*-
"""Endpointlar tekshiruvi.

Maqsad: biror o'zgarish bo'limlardan birini "sindirib" qo'ysa, buni
DARHOL aniqlash. Avval har bir bo'limni qo'lda ochib ko'rish kerak edi.
"""
import datetime

# Ma'lumot bo'lmasa ham 200 qaytarishi kerak bo'lgan ekranlar
ROYXAT_ENDPOINTLARI = [
    '/api/dashboard/summary',
    '/api/sugurta_undirish/royxat',
    '/api/sugurta_undirish/vafot_royxat',
    '/api/sugurta_undirish/kompaniyalar',
    '/api/bh/royxat',
    '/api/nazorat95413/royxat',
    '/api/mib/faol',
    '/api/mib/harakat_turlari',
    '/api/davo-ariza/hisobot',
    '/api/sud/topshirish_kerak',
    '/api/vafot/royxat',
    '/api/zaxira/royxat',
    '/api/sozlamalar',
]


def test_barcha_royxat_ekranlari_ochiladi(muhit, klient):
    """Bo'sh bazada ham hamma ekran ochilishi kerak — xato bermasdan."""
    xatolar = []
    for ep in ROYXAT_ENDPOINTLARI:
        r = klient.get(ep)
        if r.status_code != 200:
            xatolar.append(f"{ep} -> {r.status_code}")
    assert not xatolar, "Ochilmagan ekranlar: " + ', '.join(xatolar)


def test_royxat_ekranlari_malumot_bilan_ishlaydi(muhit, mijoz, klient):
    """Ma'lumot bor holatda ham hammasi ishlashi kerak."""
    db = muhit['db']
    conn = db.get_conn()
    conn.execute('''INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi,
                    mijoz_turi, xat_turi, holat, mib_holati, davo_ariza_turi,
                    davo_ariza_fayl_yoli, mib_ish_raqami, mib_otkazilgan_sana,
                    yaratilgan_sana, yuborilgan_sana)
                    VALUES (?, '10001', ?, 'jismoniy', 'talabnoma', 'yuborildi',
                            'otkazildi', 'muddatidan_oldin', '/tmp/d.docx',
                            'MIB-1', '01.08.2026', ?, ?)''',
                 (mijoz['id'], mijoz['mijoz_nomi'],
                  datetime.datetime.now().isoformat(),
                  datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    db.mark_vafot_etgan(mijoz['id'], '10001', mijoz['mijoz_nomi'], '15.08.2026', None, None)

    xatolar = []
    for ep in ROYXAT_ENDPOINTLARI:
        r = klient.get(ep)
        if r.status_code != 200:
            xatolar.append(f"{ep} -> {r.status_code}")
    assert not xatolar, "Ochilmagan ekranlar: " + ', '.join(xatolar)


def test_shablonlar_yuklab_olinadi(muhit, klient):
    turlari = ['xat', 'sugurta_tovon', 'vafot_sugurta_tovon', 'yigma_jild',
               'sud_yigma_jild', 'malumotnoma_topshirishda']
    xatolar = []
    for turi in turlari:
        r = klient.get(f'/api/shablon/korish?turi={turi}')
        if r.status_code != 200:
            xatolar.append(f"{turi} -> {r.status_code}")
    assert not xatolar, "Yuklanmagan shablonlar: " + ', '.join(xatolar)


def test_notogri_shablon_turi_rad_etiladi(muhit, klient):
    r = klient.get('/api/shablon/korish?turi=yoq_shablon')
    assert r.status_code == 400


# ── TO'LIQ SMOKE TEST ────────────────────────────────────────────────
# Maqsad: server.py bo'laklarga ajratilganda yoki boshqa katta
# o'zgarishda birorta marshrut "yo'qolib" qolsa yoki sinsa — darhol
# aniqlanishi. Har bir GET marshrut chaqirilib, 500 (ichki xato)
# qaytarmasligi tekshiriladi.

def _barcha_get_marshrutlar(server):
    """Ilovadagi barcha GET marshrutlarni (parametrsizlarini) yig'adi."""
    yollar = []
    for qoida in server.app.url_map.iter_rules():
        if 'GET' not in qoida.methods:
            continue
        yol = str(qoida)
        if '<' in yol or not yol.startswith('/api/'):
            continue
        yollar.append(yol)
    return sorted(set(yollar))


def test_hech_bir_marshrut_500_bermaydi(muhit, klient):
    """Bo'sh bazada ham hech bir marshrut ichki xato (500) bermasligi
    kerak — 400/404 tushunarli javob, lekin 500 — bu dastur xatosi."""
    server = muhit['server']
    yollar = _barcha_get_marshrutlar(server)
    assert len(yollar) > 50, f"Marshrutlar topilmadi ({len(yollar)} ta)"

    sinqanlar = []
    for yol in yollar:
        try:
            r = klient.get(yol)
        except Exception as e:
            sinqanlar.append(f"{yol} -> {type(e).__name__}: {e}")
            continue
        if r.status_code >= 500:
            sinqanlar.append(f"{yol} -> {r.status_code}")
    assert not sinqanlar, "Ichki xato bergan marshrutlar:\n  " + '\n  '.join(sinqanlar)


def test_hech_bir_marshrut_malumot_bilan_ham_sinmaydi(muhit, mijoz, klient):
    """Ma'lumot bor holatda ham hamma marshrut ishlashi kerak."""
    db = muhit['db']
    conn = db.get_conn()
    conn.execute('''INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi,
                    mijoz_turi, xat_turi, holat, yuborilgan_sana, mib_holati,
                    mib_ish_raqami, mib_otkazilgan_sana, davo_ariza_turi,
                    davo_ariza_fayl_yoli, sud_holati, yaratilgan_sana)
                    VALUES (?, '10001', ?, 'jismoniy', 'talabnoma', 'yuborildi',
                            ?, 'otkazildi', 'MIB-1', '01.08.2026', 'muddatidan_oldin',
                            '/tmp/d.docx', 'topshirildi', ?)''',
                 (mijoz['id'], mijoz['mijoz_nomi'],
                  datetime.datetime.now().isoformat(),
                  datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    db.mark_vafot_etgan(mijoz['id'], '10001', mijoz['mijoz_nomi'], '15.08.2026', None, None)

    server = muhit['server']
    sinqanlar = []
    for yol in _barcha_get_marshrutlar(server):
        r = klient.get(yol)
        if r.status_code >= 500:
            sinqanlar.append(f"{yol} -> {r.status_code}")
    assert not sinqanlar, "Ichki xato bergan marshrutlar:\n  " + '\n  '.join(sinqanlar)


def test_marshrutlar_soni_kamaymagan(muhit):
    """Bo'laklarga ajratishda marshrut YO'QOLIB qolmasligi kerak.
    Bu son bilan solishtirish — eng oddiy, lekin eng ishonchli qo'riqchi."""
    server = muhit['server']
    barchasi = [str(q) for q in server.app.url_map.iter_rules()
                if str(q).startswith('/api/')]
    assert len(barchasi) >= 179, (
        f"Marshrutlar soni kamaydi: {len(barchasi)} ta. "
        f"Boshlangich: 179 ta. Bo'laklarga ajratishda biror blueprint ro'yxatdan o'tmay qolgan bo'lishi mumkin.")


def test_excel_eksportlari(muhit, mijoz, klient):
    """Ma'lumot bo'lganda Excel chiqishi, bo'sh bo'lganda tushunarli
    xato berishi kerak (500 emas)."""
    db = muhit['db']
    conn = db.get_conn()
    conn.execute('''INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi,
                    mijoz_turi, mib_holati, davo_ariza_turi, mib_ish_raqami,
                    yaratilgan_sana)
                    VALUES (?, '10001', ?, 'jismoniy', 'otkazildi',
                            'muddatidan_oldin', 'MIB-1', ?)''',
                 (mijoz['id'], mijoz['mijoz_nomi'], datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()
    db.mark_vafot_etgan(mijoz['id'], '10001', mijoz['mijoz_nomi'], '15.08.2026', None, None)

    for ep in ['/api/sugurta_undirish/excel', '/api/sugurta_undirish/vafot_excel']:
        r = klient.get(ep)
        assert r.status_code == 200, f"{ep} -> {r.status_code}"
        assert len(r.data) > 1000, f"{ep} bo'sh fayl qaytardi"


def test_bosh_excel_tushunarli_xato_beradi(muhit, klient):
    r = klient.get('/api/sugurta_undirish/excel')
    assert r.status_code == 400
    assert 'xato' in r.get_json()


def test_anketasiz_sorov_rad_etiladi(muhit, klient):
    """Majburiy parametrsiz so'rovlar 500 emas, tushunarli 400 berishi kerak."""
    for ep in ['/api/sugurta_undirish/malumot', '/api/sugurta_undirish/vafot_malumot']:
        r = klient.get(ep)
        assert r.status_code == 400, f"{ep} -> {r.status_code}"
        assert 'xato' in r.get_json()


def test_yoq_anketa_404_beradi(muhit, klient):
    r = klient.get('/api/sugurta_undirish/malumot?anketa=YOQ')
    assert r.status_code == 404


# ── FRONTEND: Electronda ishlamaydigan funksiyalar ──────────────────
# MUHIM: Electron (desktop) muhitida brauzerning `prompt()` oynasi
# UMUMAN ishlamaydi — hech narsa ko'rsatmasdan darhol qaytadi. Shu
# sababli "✏ o'zgartirish" tugmasi bosilganda hech narsa bo'lmasdi.
# Uning o'rniga dasturning o'z dialogi (matnSorash) ishlatiladi.

def test_frontendda_prompt_ishlatilmaydi():
    """Kod ichida prompt() qayta paydo bo'lib qolmasin."""
    import os
    import re
    asos = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        'frontend', 'src')
    topilgan = []
    for ildiz, _, fayllar in os.walk(asos):
        for nomi in fayllar:
            if not nomi.endswith('.js'):
                continue
            yol = os.path.join(ildiz, nomi)
            with open(yol, encoding='utf-8') as f:
                for i, qator in enumerate(f, 1):
                    toza = qator.split('//')[0]
                    # window.prompt(...) yoki bevosita prompt(...)
                    if re.search(r'(?<![.\w])prompt\s*\(', toza) or 'window.prompt(' in toza:
                        topilgan.append(f"{nomi}:{i}: {qator.strip()[:70]}")
    assert not topilgan, (
        "Electronda ishlamaydigan prompt() ishlatilgan — o'rniga "
        "matnSorash() dan foydalaning:\n  " + "\n  ".join(topilgan))


def test_matnsorash_dialogi_mavjud():
    """prompt() o'rnini bosuvchi dialog joyida turishi kerak."""
    import os
    yol = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       'frontend', 'src', 'ekranlar', 'umumiy.js')
    matn = open(yol, encoding='utf-8').read()
    assert 'function matnSorash(' in matn, "matnSorash() dialogi yo'qolgan"
    # Dialog kutilgan elementlarni yaratishi kerak
    for kerak in ('ms-qiymat', 'ms-saqlash', 'ms-bekor', 'Escape'):
        assert kerak in matn, f"matnSorash() da '{kerak}' yo'q"
