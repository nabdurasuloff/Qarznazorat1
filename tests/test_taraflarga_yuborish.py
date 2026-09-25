# -*- coding: utf-8 -*-
"""IQTISODIY SUD — taraflarga yuborilganlik tasdiqnomalari.

Iqtisodiy sudda davo arizani sudga berishdan OLDIN uning nusxasi barcha
taraflarga (javobgar, kafil, garov ta'minlovchi) yuborilishi shart va
sudga bu yuborilganini tasdiqlovchi hujjat (pochta kvitansiyasi yoki
topshirish xabarnomasi) ilova qilinadi. Talabnoma bo'yicha ham xuddi
shunday. Bu hujjatlarsiz sud davo arizani harakatsiz qoldiradi.

Shu sabab tizim:
  • yuridik shaxs / YaTT ishlarida bu ikki hujjatni MAJBURIY qiladi;
  • ularsiz "Sudga yuborishga ruxsat berish" ni bermaydi;
  • jismoniy shaxs (fuqarolik sudi) ishlarida esa TALAB QILMAYDI.
"""
import io
import os


DAVO_TASDIQ = 'davo_ariza_taraflarga_tasdiq_fayl'
TALABNOMA_TASDIQ = 'talabnoma_taraflarga_tasdiq_fayl'


def _xat_yaratish(db, mijoz, mijoz_turi, **maydonlar):
    """Sudga topshirishga tayyor (davo ariza olib kelingan) xat yaratadi."""
    ustunlar = ['portfel_id', 'anketa_raqami', 'mijoz_nomi', 'mijoz_turi', 'xat_turi',
                'davo_ariza_holati', 'davo_ariza_turi']
    qiymatlar = [mijoz['id'], '10001', mijoz['mijoz_nomi'], mijoz_turi, 'talabnoma',
                 'olib_kelindi', 'oddiy']
    for k, v in maydonlar.items():
        ustunlar.append(k)
        qiymatlar.append(v)
    conn = db.get_conn()
    cur = conn.execute(
        f"INSERT INTO xatlar ({', '.join(ustunlar)}) VALUES ({', '.join('?' * len(ustunlar))})",
        qiymatlar)
    xat_id = cur.lastrowid
    conn.commit()
    conn.close()
    return xat_id


def _toliq_jild_maydonlari(papka):
    """Majburiy hujjatlarning hammasi (tasdiqnomalardan tashqari) yuklangan holat."""
    os.makedirs(papka, exist_ok=True)
    fayllar = {}
    for maydon in ('sud_yigma_jild_titul_fayl', 'davo_ariza_fayl_yoli', 'fayl_yoli',
                   'kredit_shartnoma_fayl'):
        yol = os.path.join(papka, f'{maydon}.pdf')
        with open(yol, 'wb') as f:
            f.write(b'%PDF-1.4 test')
        fayllar[maydon] = yol
    fayllar['sud_yigma_jild_papka'] = papka
    return fayllar


# ── Majburiylik qoidasi ────────────────────────────────────────────────

def test_yuridik_shaxsda_tasdiqnomalar_majburiy(muhit, mijoz):
    """Iqtisodiy sud ishida ikkala tasdiqnoma ham majburiy ro'yxatda."""
    db = muhit['db']
    xat = {'mijoz_turi': 'yuridik', 'davo_ariza_turi': 'oddiy'}
    maydonlar = [m for m, _ in db.sud_majburiy_hujjatlar_royxati(xat)]
    assert DAVO_TASDIQ in maydonlar
    assert TALABNOMA_TASDIQ in maydonlar


def test_yattda_ham_majburiy(muhit):
    """YaTT ham iqtisodiy sudda ko'riladi — shart bir xil."""
    db = muhit['db']
    maydonlar = [m for m, _ in db.sud_majburiy_hujjatlar_royxati(
        {'mijoz_turi': 'yatt', 'davo_ariza_turi': 'oddiy'})]
    assert DAVO_TASDIQ in maydonlar and TALABNOMA_TASDIQ in maydonlar


def test_jismoniy_shaxsda_talab_qilinmaydi(muhit):
    """Fuqarolik sudida (jismoniy shaxs) bu hujjatlar talab qilinmaydi —
    aks holda mavjud ishlar ham 'to'liq emas' bo'lib qolardi."""
    db = muhit['db']
    maydonlar = [m for m, _ in db.sud_majburiy_hujjatlar_royxati(
        {'mijoz_turi': 'jismoniy', 'davo_ariza_turi': 'oddiy'})]
    assert DAVO_TASDIQ not in maydonlar
    assert TALABNOMA_TASDIQ not in maydonlar


def test_eski_yozuvdagi_LE_qiymati_ham_iqtisodiy(muhit):
    """Eski yozuvlarda portfeldagi xom 'LE' qiymati saqlangan bo'lishi
    mumkin — u ham iqtisodiy sud deb qaralishi kerak."""
    db = muhit['db']
    assert db.iqtisodiy_sudmi('LE') is True
    assert db.iqtisodiy_sudmi('jismoniy') is False
    assert db.iqtisodiy_sudmi(None) is False


# ── "To'liqmi" tekshiruvi ──────────────────────────────────────────────

def test_tasdiqnomasiz_jild_toliq_emas(muhit, mijoz):
    db = muhit['db']
    fayllar = _toliq_jild_maydonlari(os.path.join(muhit['papka'], 'jild'))
    xat = dict(fayllar)
    xat.update({'mijoz_turi': 'yuridik', 'davo_ariza_turi': 'oddiy'})
    assert db.sud_hujjatlar_toliqmi(xat) is False, \
        "Tasdiqnomalarsiz ham 'to'liq' deb hisoblanmoqda"

    xat[DAVO_TASDIQ] = '/tmp/a.pdf'
    assert db.sud_hujjatlar_toliqmi(xat) is False, "Talabnoma tasdig'i ham kerak"

    xat[TALABNOMA_TASDIQ] = '/tmp/b.pdf'
    assert db.sud_hujjatlar_toliqmi(xat) is True


def test_jismoniy_shaxsda_tasdiqnomasiz_ham_toliq(muhit):
    """Eski (jismoniy shaxs) ishlar yangi shart tufayli bloklanmasligi kerak."""
    db = muhit['db']
    xat = dict(_toliq_jild_maydonlari(os.path.join(muhit['papka'], 'jild2')))
    xat.update({'mijoz_turi': 'jismoniy', 'davo_ariza_turi': 'oddiy'})
    assert db.sud_hujjatlar_toliqmi(xat) is True


# ── Ruxsat berish bloklanishi ──────────────────────────────────────────

def test_tasdiqnomasiz_ruxsat_berilmaydi(muhit, mijoz, klient):
    """Eng muhim tekshiruv: tasdiqnomalar yuklanmasa, ish sudga
    yuborishga ruxsat OLMAYDI."""
    fayllar = _toliq_jild_maydonlari(os.path.join(muhit['papka'], 'jild3'))
    _xat_yaratish(muhit['db'], mijoz, 'yuridik', **fayllar)

    r = klient.post('/api/sud/ruxsat_berish', json={'anketa_raqami': '10001'})
    assert r.status_code == 400
    xato = r.get_json()['xato']
    assert 'Davo ariza taraflarga' in xato, f"Xatoda sabab ko'rsatilmagan: {xato}"
    assert 'Talabnoma taraflarga' in xato


def test_tasdiqnomalar_bilan_ruxsat_beriladi(muhit, mijoz, klient):
    papka = os.path.join(muhit['papka'], 'jild4')
    fayllar = _toliq_jild_maydonlari(papka)
    for maydon in (DAVO_TASDIQ, TALABNOMA_TASDIQ):
        yol = os.path.join(papka, f'{maydon}.pdf')
        with open(yol, 'wb') as f:
            f.write(b'%PDF-1.4 kvitansiya')
        fayllar[maydon] = yol
    _xat_yaratish(muhit['db'], mijoz, 'yuridik', **fayllar)

    r = klient.post('/api/sud/ruxsat_berish', json={'anketa_raqami': '10001'})
    assert r.status_code == 200, r.get_json()


def test_ruxsatsiz_sudga_topshirilmaydi(muhit, mijoz, klient):
    """Ruxsat bo'lmasa, ish 'sudga topshirildi' deb belgilanmasligi kerak."""
    fayllar = _toliq_jild_maydonlari(os.path.join(muhit['papka'], 'jild5'))
    _xat_yaratish(muhit['db'], mijoz, 'yuridik', **fayllar)
    r = klient.post('/api/sud/topshirildi', data={
        'anketa_raqami': '10001', 'ish_raqami': 'A-1',
        'sana': '20.09.2026'})
    assert r.status_code == 400
    assert 'ruxsat' in r.get_json()['xato'].lower()


# ── Yuklash yo'li ──────────────────────────────────────────────────────

def test_tasdiqnoma_yuklanadi_va_sana_saqlanadi(muhit, mijoz, klient):
    papka = os.path.join(muhit['papka'], 'jild6')
    fayllar = _toliq_jild_maydonlari(papka)
    _xat_yaratish(muhit['db'], mijoz, 'yuridik', **fayllar)

    r = klient.post('/api/sud/hujjat_yuklash', data={
        'anketa_raqami': '10001', 'maydon': DAVO_TASDIQ,
        'yuborilgan_sana': '15.09.2026',
        'file': (io.BytesIO(b'%PDF-1.4 pochta kvitansiyasi'), 'kvitansiya.pdf'),
    }, content_type='multipart/form-data')
    assert r.status_code == 200, r.get_json()

    conn = muhit['db'].get_conn()
    row = dict(conn.execute("SELECT * FROM xatlar WHERE anketa_raqami='10001'").fetchone())
    conn.close()
    assert row[DAVO_TASDIQ] and os.path.exists(row[DAVO_TASDIQ])
    assert row['davo_ariza_taraflarga_sana'] == '15.09.2026'


def test_sanasiz_tasdiqnoma_qabul_qilinmaydi(muhit, mijoz, klient):
    """Sana — tasdiqnomaning asosiy ma'nosi (qachon yuborilgani), shuning
    uchun usiz qabul qilinmaydi."""
    fayllar = _toliq_jild_maydonlari(os.path.join(muhit['papka'], 'jild7'))
    _xat_yaratish(muhit['db'], mijoz, 'yuridik', **fayllar)
    r = klient.post('/api/sud/hujjat_yuklash', data={
        'anketa_raqami': '10001', 'maydon': TALABNOMA_TASDIQ,
        'file': (io.BytesIO(b'%PDF-1.4'), 'k.pdf'),
    }, content_type='multipart/form-data')
    assert r.status_code == 400
    assert 'sana' in r.get_json()['xato'].lower()


def test_kelajak_sanasi_rad_etiladi(muhit, mijoz, klient):
    fayllar = _toliq_jild_maydonlari(os.path.join(muhit['papka'], 'jild8'))
    _xat_yaratish(muhit['db'], mijoz, 'yuridik', **fayllar)
    r = klient.post('/api/sud/hujjat_yuklash', data={
        'anketa_raqami': '10001', 'maydon': DAVO_TASDIQ,
        'yuborilgan_sana': '01.01.2099',
        'file': (io.BytesIO(b'%PDF-1.4'), 'k.pdf'),
    }, content_type='multipart/form-data')
    assert r.status_code == 400


def test_notogri_maydon_500_bermaydi(muhit, mijoz, klient):
    """Noto'g'ri hujjat turi — tushunarli 400, ichki xato (500) emas."""
    fayllar = _toliq_jild_maydonlari(os.path.join(muhit['papka'], 'jild9'))
    _xat_yaratish(muhit['db'], mijoz, 'yuridik', **fayllar)
    r = klient.post('/api/sud/hujjat_yuklash', data={
        'anketa_raqami': '10001', 'maydon': 'yoq_maydon',
        'file': (io.BytesIO(b'x'), 'k.pdf'),
    }, content_type='multipart/form-data')
    assert r.status_code == 400


# ── Ekran va yig'ma jild ──────────────────────────────────────────────

def test_ekranda_tasdiqnomalar_korinadi(muhit, mijoz, klient):
    fayllar = _toliq_jild_maydonlari(os.path.join(muhit['papka'], 'jild10'))
    _xat_yaratish(muhit['db'], mijoz, 'yuridik', **fayllar)
    d = klient.get('/api/sud/yigma_jild_holati?anketa=10001').get_json()
    assert d['iqtisodiy_sud'] is True
    maydonlar = {h['maydon']: h for h in d['hujjatlar']}
    assert DAVO_TASDIQ in maydonlar and TALABNOMA_TASDIQ in maydonlar
    # Sana so'raladigan qator sifatida belgilangan bo'lishi kerak
    assert maydonlar[DAVO_TASDIQ].get('sana_soraladi') is True
    assert d['toliqmi'] is False


def test_tasdiqnomalar_yigma_jildga_qoshiladi(muhit, mijoz, klient):
    """Sudga topshiriladigan PDF jildda tasdiqnomalar ham bo'lishi kerak."""
    import pypdf
    papka = os.path.join(muhit['papka'], 'jild11')
    os.makedirs(papka, exist_ok=True)

    def pdf(nomi, sahifalar):
        yol = os.path.join(papka, nomi)
        w = pypdf.PdfWriter()
        for _ in range(sahifalar):
            w.add_blank_page(width=595, height=842)
        with open(yol, 'wb') as f:
            w.write(f)
        return yol

    fayllar = {
        'sud_yigma_jild_papka': papka,
        'sud_yigma_jild_titul_fayl': pdf('titul.pdf', 1),
        'davo_ariza_fayl_yoli': pdf('davo.pdf', 1),
        'fayl_yoli': pdf('xat.pdf', 1),
        DAVO_TASDIQ: pdf('kvit_davo.pdf', 1),
        TALABNOMA_TASDIQ: pdf('kvit_talab.pdf', 1),
    }
    _xat_yaratish(muhit['db'], mijoz, 'yuridik', **fayllar)

    r = klient.get('/api/sud/tayyor_jild?anketa=10001')
    assert r.status_code == 200
    assert r.data[:4] == b'%PDF'
    import io as _io
    assert len(pypdf.PdfReader(_io.BytesIO(r.data)).pages) == 5, \
        "Tasdiqnomalar jildga qo'shilmagan"


def test_vazifada_yetishmayotgan_hujjat_aytiladi(muhit, mijoz):
    """Bosh sahifadagi vazifada AYNAN nima yetishmayotgani ko'rinsin."""
    import importlib
    import vazifalar as vzf
    importlib.reload(vzf)
    vzf.db = muhit['db']

    import datetime
    fayllar = _toliq_jild_maydonlari(os.path.join(muhit['papka'], 'jild12'))
    fayllar['holat'] = 'yuborildi'
    fayllar['davo_ariza_imzo_sana'] = (
        datetime.date.today() - datetime.timedelta(days=12)).strftime('%d.%m.%Y')
    _xat_yaratish(muhit['db'], mijoz, 'yuridik', **fayllar)

    vazifalar = vzf.bugungi_vazifalar()
    sud_vazifalari = [v for v in vazifalar if v.get('bolim') == 'sud']
    assert sud_vazifalari, "Sud vazifasi umuman yaratilmadi"
    matn = ' '.join(v.get('izoh', '') for v in sud_vazifalari)
    assert 'taraflarga' in matn.lower(), f"Vazifada sabab ko'rsatilmagan: {matn}"
