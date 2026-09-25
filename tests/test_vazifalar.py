# -*- coding: utf-8 -*-
"""Aqlli yordamchi ("Bugungi vazifalar") testlari.

Har bir bosqich uchun to'g'ri vazifa chiqishini va ustuvorlik to'g'ri
hisoblanishini tekshiradi.
"""
import datetime
import importlib


def _vzf(muhit):
    import vazifalar
    importlib.reload(vazifalar)
    vazifalar.db = muhit['db']
    return vazifalar


def _xat(db, prow, **maydonlar):
    conn = db.get_conn()
    cur = conn.execute('''
        INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi,
                            xat_turi, fayl_yoli, holat, yaratilgan_sana)
        VALUES (?, ?, ?, 'jismoniy', 'talabnoma', '/tmp/x.docx', 'tayyor', ?)
    ''', (prow['id'], prow['anketa_raqami'], prow['mijoz_nomi'],
          datetime.datetime.now().isoformat()))
    xat_id = cur.lastrowid
    if maydonlar:
        sc = ', '.join(f'{k}=?' for k in maydonlar)
        conn.execute(f'UPDATE xatlar SET {sc} WHERE id=?',
                     list(maydonlar.values()) + [xat_id])
    conn.commit()
    conn.close()
    return xat_id


def _kun_oldin(n):
    return (datetime.date.today() - datetime.timedelta(days=n)).strftime('%d.%m.%Y')


def _iso_kun_oldin(n):
    return (datetime.datetime.now() - datetime.timedelta(days=n)).isoformat()


# ── Ustuvorlik hisobi ────────────────────────────────────────────────

def test_ustuvorlik_hisobi(muhit):
    v = _vzf(muhit)
    assert v._ustuvorlik(-5) == 'kechikkan'
    assert v._ustuvorlik(0) == 'bugun'
    assert v._ustuvorlik(2) == 'bugun'
    assert v._ustuvorlik(10) == 'rejali'
    assert v._ustuvorlik(None) == 'rejali'


def test_sana_oqish(muhit):
    v = _vzf(muhit)
    assert v._sana_dt('15.09.2026') == datetime.date(2026, 9, 15)
    assert v._sana_dt('2026-09-15') == datetime.date(2026, 9, 15)
    assert v._sana_dt('') is None
    assert v._sana_dt('axlat') is None


# ── Har bir bosqich o'z vazifasini beradi ───────────────────────────

def test_yuborilmagan_xat_vazifasi(muhit, mijoz):
    v = _vzf(muhit)
    _xat(muhit['db'], mijoz, holat='tayyor', yaratilgan_sana=_iso_kun_oldin(10))
    vazifalar = [t for t in v.bugungi_vazifalar() if t['anketa_raqami'] == '10001']
    assert vazifalar, "Yuborilmagan xat uchun vazifa chiqmadi"
    assert 'yuborish' in vazifalar[0]['vazifa'].lower()
    assert vazifalar[0]['ustuvorlik'] == 'kechikkan'


def test_davo_ariza_vazifasi(muhit, mijoz):
    v = _vzf(muhit)
    _xat(muhit['db'], mijoz, holat='yuborildi', yuborilgan_sana=_iso_kun_oldin(30))
    vazifalar = [t for t in v.bugungi_vazifalar() if t['anketa_raqami'] == '10001']
    assert vazifalar and 'Davo ariza' in vazifalar[0]['vazifa']
    assert vazifalar[0]['ustuvorlik'] == 'kechikkan'


def test_tolov_muddati_tugamagan_bolsa_davo_vazifasi_yoq(muhit, mijoz):
    """Xat endi yuborilgan — to'lov muddati (10 kun) hali tugamagan,
    shuning uchun "Davo ariza" bosqichi vazifasi chiqmasligi kerak.

    Diqqat: mijoz baribir "Chora ko'rish" ro'yxatida bo'lishi mumkin
    (u yerda o'z qoidasi bor — DPD 60+ dan keyin tavsiya beriladi).
    Bu yerda faqat DAVO bosqichining o'z qoidasi tekshiriladi."""
    v = _vzf(muhit)
    _xat(muhit['db'], mijoz, holat='yuborildi', yuborilgan_sana=_iso_kun_oldin(1))
    davo = [t for t in v.bugungi_vazifalar()
            if t['anketa_raqami'] == '10001' and t['bolim'] == 'davo_ariza']
    assert not davo, "To'lov muddati tugamagan bo'lsa ham Davo vazifasi chiqdi"


def test_sudga_topshirish_vazifasi(muhit, mijoz):
    v = _vzf(muhit)
    _xat(muhit['db'], mijoz, holat='yuborildi', davo_ariza_fayl_yoli='/tmp/d.docx',
         davo_ariza_holati='olib_kelindi', davo_ariza_imzo_sana=_kun_oldin(12),
         sud_hujjatlar_ruxsat=1)
    vazifalar = [t for t in v.bugungi_vazifalar() if t['anketa_raqami'] == '10001']
    assert vazifalar and 'Sudga topshirish' in vazifalar[0]['vazifa']
    assert vazifalar[0]['ustuvorlik'] == 'kechikkan'


def test_ruxsatsiz_bolsa_boshqa_vazifa(muhit, mijoz):
    """Ruxsat berilmagan bo'lsa — "topshirish" emas, "ruxsat olish" deyishi kerak."""
    v = _vzf(muhit)
    _xat(muhit['db'], mijoz, holat='yuborildi', davo_ariza_fayl_yoli='/tmp/d.docx',
         davo_ariza_holati='olib_kelindi', davo_ariza_imzo_sana=_kun_oldin(12),
         sud_hujjatlar_ruxsat=0)
    vazifalar = [t for t in v.bugungi_vazifalar() if t['anketa_raqami'] == '10001']
    assert vazifalar and 'ruxsat' in vazifalar[0]['vazifa'].lower()


def test_vafot_sugurta_vazifasi(muhit, mijoz):
    v = _vzf(muhit)
    muhit['db'].mark_vafot_etgan(mijoz['id'], '10001', mijoz['mijoz_nomi'],
                                 _kun_oldin(60), '/tmp/guvohnoma.pdf', None)
    vazifalar = [t for t in v.bugungi_vazifalar() if t['anketa_raqami'] == '10001']
    assert vazifalar, "Vafot etgan mijoz uchun vazifa chiqmadi"
    assert "sug'urta" in vazifalar[0]['vazifa'].lower()


def test_guvohnomasiz_vafotda_boshqa_vazifa(muhit, mijoz):
    v = _vzf(muhit)
    muhit['db'].mark_vafot_etgan(mijoz['id'], '10001', mijoz['mijoz_nomi'],
                                 _kun_oldin(60), None, None)   # guvohnoma yo'q
    vazifalar = [t for t in v.bugungi_vazifalar() if t['anketa_raqami'] == '10001']
    assert vazifalar and 'guvohnoma' in vazifalar[0]['vazifa'].lower()


def test_sud_majlisi_eslatmasi(muhit, mijoz):
    v = _vzf(muhit)
    ertaga = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%d.%m.%Y')
    muhit['db'].sud_kuni_qoshish('10001', mijoz['mijoz_nomi'], ertaga,
                                 '10:00', 'Iqtisodiy sud', 'A-1')
    vazifalar = [t for t in v.bugungi_vazifalar() if t['anketa_raqami'] == '10001']
    assert vazifalar and 'Sud majlisi' in vazifalar[0]['vazifa']


# ── Takrorlanmaslik va tartib ───────────────────────────────────────

def test_bitta_mijozga_bitta_vazifa(muhit, mijoz):
    """Mijoz bir nechta ro'yxatga tushsa ham — faqat eng shoshilinch
    vazifasi ko'rsatilishi kerak."""
    v = _vzf(muhit)
    _xat(muhit['db'], mijoz, holat='yuborildi', yuborilgan_sana=_iso_kun_oldin(40),
         davo_ariza_fayl_yoli='/tmp/d.docx', davo_ariza_holati='olib_kelindi',
         davo_ariza_imzo_sana=_kun_oldin(20), sud_hujjatlar_ruxsat=1)
    muhit['db'].mark_vafot_etgan(mijoz['id'], '10001', mijoz['mijoz_nomi'],
                                 _kun_oldin(60), '/tmp/g.pdf', None)
    vazifalar = [t for t in v.bugungi_vazifalar() if t['anketa_raqami'] == '10001']
    assert len(vazifalar) == 1, f"Bitta mijozga {len(vazifalar)} ta vazifa chiqdi"


def test_kechikkanlar_tepada(muhit, mijoz):
    v = _vzf(muhit)
    db = muhit['db']
    conn = db.get_conn()
    conn.execute('''INSERT INTO portfel (anketa_raqami, mijoz_nomi, mijoz_turi,
                    pinfl, asosiy_qarz, faol) VALUES ('10002','IKKINCHI','Individual','2',1000,1)''')
    conn.commit()
    ikkinchi = dict(conn.execute("SELECT * FROM portfel WHERE anketa_raqami='10002'").fetchone())
    conn.close()

    _xat(db, mijoz, holat='tayyor', yaratilgan_sana=_iso_kun_oldin(30))     # kechikkan
    _xat(db, ikkinchi, holat='tayyor', yaratilgan_sana=datetime.datetime.now().isoformat())

    royxat = v.bugungi_vazifalar()
    assert royxat[0]['ustuvorlik'] == 'kechikkan'


def test_xulosa_hisobi(muhit, mijoz):
    v = _vzf(muhit)
    _xat(muhit['db'], mijoz, holat='tayyor', yaratilgan_sana=_iso_kun_oldin(30))
    royxat = v.bugungi_vazifalar()
    x = v.vazifalar_xulosasi(royxat)
    assert x['jami'] == len(royxat)
    assert x['kechikkan'] + x['bugun'] + x['rejali'] == x['jami']
    assert x['jami_qarz'] > 0


def test_chora_royxati_cheklanadi(muhit):
    """Minglab "chora ko'rish" mijozi kundalik ro'yxatni ko'mib
    yubormasligi kerak."""
    v = _vzf(muhit)
    db = muhit['db']
    conn = db.get_conn()
    for i in range(60):
        conn.execute('''INSERT INTO portfel (anketa_raqami, mijoz_nomi, mijoz_turi,
                        pinfl, asosiy_qarz, dpd_max, dpd_asosiy, faol)
                        VALUES (?, ?, 'Individual', ?, 5000000, 200, 200, 1)''',
                     (f'2{i:04d}', f'CHORA MIJOZ {i}', str(i)))
    conn.commit()
    conn.close()
    royxat = v.bugungi_vazifalar()
    chora = [t for t in royxat if t['bolim'] == 'chora']
    assert len(chora) <= v.CHORA_KORSATISH_SONI, f"{len(chora)} ta chora vazifasi chiqdi"
    x = v.vazifalar_xulosasi(royxat)
    assert x['chora_jami'] > x['chora_korsatildi'], "Qolganlar soni ko'rsatilmayapti"


# ── Endpoint ────────────────────────────────────────────────────────

def test_vazifalar_endpointi(muhit, mijoz, klient):
    _xat(muhit['db'], mijoz, holat='tayyor', yaratilgan_sana=_iso_kun_oldin(30))
    r = klient.get('/api/vazifalar/bugun')
    assert r.status_code == 200
    d = r.get_json()
    assert 'royxat' in d and 'xulosa' in d
    assert d['xulosa']['jami'] >= 1


def test_vazifalar_filtri(muhit, mijoz, klient):
    _xat(muhit['db'], mijoz, holat='tayyor', yaratilgan_sana=_iso_kun_oldin(30))
    r = klient.get('/api/vazifalar/bugun?ustuvorlik=kechikkan')
    d = r.get_json()
    assert all(v['ustuvorlik'] == 'kechikkan' for v in d['royxat'])
    # Xulosa filtrdan QAT'I NAZAR to'liq bo'lishi kerak
    assert d['xulosa']['jami'] >= len(d['royxat'])


def test_vazifalar_excel(muhit, mijoz, klient):
    _xat(muhit['db'], mijoz, holat='tayyor', yaratilgan_sana=_iso_kun_oldin(30))
    r = klient.get('/api/vazifalar/excel')
    assert r.status_code == 200
    assert len(r.data) > 1000


def test_bosh_bazada_vazifa_yoq(muhit, klient):
    r = klient.get('/api/vazifalar/bugun')
    assert r.status_code == 200
    assert r.get_json()['xulosa']['jami'] == 0
