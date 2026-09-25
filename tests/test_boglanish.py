# -*- coding: utf-8 -*-
"""BO'LIMLARARO BOG'LANISH testlari.

Bu testlar tizimning eng nozik joyini qo'riqlaydi: ish bir bo'limdan
ikkinchisiga o'tganda, u KERAKLI ro'yxatda paydo bo'lishi va KERAKMAS
ro'yxatdan chiqib ketishi shart.

Auditda topilgan HAQIQIY xatolar (endi shu yerda qo'riqlanadi):
  1. Allaqachon tasdiqlangan davo ariza Biznes-hamrohda "Tayyorlanmoqda"
     bo'lib turardi — xodim uni portalga QAYTA yuborishi mumkin edi.
  2. Tizim tasdiqlangan arizaga "portalga yuboring" deb vazifa berardi.
  3. Portal RAD etgan murojaat hech qayerda eslatilmasdi — ish jimgina
     yo'qolib qolardi.
  4. Qarzi to'liq to'langan mijoz uchun "sug'urtaga ariza bering" deb
     turardi — ya'ni to'langan qarzni sug'urtadan qayta talab qilishga.
"""
import datetime
import importlib


def _vzf(muhit):
    import vazifalar
    importlib.reload(vazifalar)
    vazifalar.db = muhit['db']
    return vazifalar


def _kun(n):
    return (datetime.date.today() - datetime.timedelta(days=n)).strftime('%d.%m.%Y')


def _iso(n):
    return (datetime.datetime.now() - datetime.timedelta(days=n)).isoformat()


def _davo_tayyor(db, prow, **maydonlar):
    """Davo arizasi tayyorlangan ish yaratadi."""
    conn = db.get_conn()
    cur = conn.execute('''
        INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi,
                            xat_turi, holat, yuborilgan_sana, yaratilgan_sana,
                            davo_ariza_fayl_yoli, davo_ariza_sana, davo_ariza_turi)
        VALUES (?, ?, ?, 'jismoniy', 'talabnoma', 'yuborildi', ?, ?,
                '/tmp/d.docx', ?, 'muddatidan_oldin')
    ''', (prow['id'], prow['anketa_raqami'], prow['mijoz_nomi'],
          _iso(20), _iso(25), _iso(15)))
    xat_id = cur.lastrowid
    if maydonlar:
        sc = ', '.join(f'{k}=?' for k in maydonlar)
        conn.execute(f'UPDATE xatlar SET {sc} WHERE id=?',
                     list(maydonlar.values()) + [xat_id])
    conn.commit()
    conn.close()
    return xat_id


def _vazifa(v, anketa):
    for t in v.bugungi_vazifalar():
        if t['anketa_raqami'] == anketa:
            return t
    return None


def _bh_da_bormi(db, anketa):
    return any(i['xat']['anketa_raqami'] == anketa for i in db.get_bh_royxati())


def _sudda_bormi(db, anketa):
    return any(x['anketa_raqami'] == anketa for x in db.get_sud_topshirish_kerak())


# ── 1. Tasdiqlangan ariza portalda "tayyorlanmoqda" bo'lib qolmaydi ──

def test_tasdiqlangan_ariza_portalda_turmaydi(muhit, mijoz):
    """Eski yo'l bilan (SSPdan) tasdiqlanib qaytgan ariza Biznes-hamroh
    ro'yxatida turmasligi kerak — uni portalga yuborish kerak emas."""
    db = muhit['db']
    _davo_tayyor(db, mijoz, davo_ariza_holati='olib_kelindi',
                 davo_ariza_imzo_sana=_kun(5), davo_ariza_ish_raqami='SSP-9')
    assert not _bh_da_bormi(db, '10001'), \
        "Tasdiqlangan ariza portal ro'yxatida qoldi — qayta yuborilishi mumkin"
    # Lekin sudga topshirish ro'yxatida BO'LISHI shart
    assert _sudda_bormi(db, '10001'), "Tasdiqlangan ariza sud ro'yxatiga tushmadi"


def test_tasdiqlanmagan_ariza_portalda_turadi(muhit, mijoz):
    """Oddiy holat: hali tasdiqlanmagan ariza portalda ko'rinishi kerak."""
    db = muhit['db']
    _davo_tayyor(db, mijoz)
    assert _bh_da_bormi(db, '10001')


def test_portal_tasdiqlagan_ish_royxatda_qoladi(muhit, mijoz):
    """Portal orqali tasdiqlangan ish portal ro'yxatida QOLADI —
    murojaat raqami va tarixi ko'rinib turishi kerak."""
    db = muhit['db']
    xat_id = _davo_tayyor(db, mijoz, davo_ariza_holati='olib_kelindi',
                          davo_ariza_imzo_sana=_kun(2))
    db.bh_murojaat_saqlash('10001', xat_id=xat_id, murojaat_raqami='193/002')
    db.bh_holat_ozgartirish('10001', 'qabul_qilindi')
    assert _bh_da_bormi(db, '10001'), "Portal tarixi yo'qoldi"
    assert _sudda_bormi(db, '10001')


# ── 2. Vazifa to'g'ri bosqichni ko'rsatadi ──────────────────────────

def test_tasdiqlangan_arizaga_portal_vazifasi_berilmaydi(muhit, mijoz):
    """Tasdiqlangan arizaning keyingi qadami — SUD, portal emas."""
    db = muhit['db']
    v = _vzf(muhit)
    _davo_tayyor(db, mijoz, davo_ariza_holati='olib_kelindi',
                 davo_ariza_imzo_sana=_kun(5), davo_ariza_ish_raqami='SSP-9')
    t = _vazifa(v, '10001')
    assert t is not None, "Tasdiqlangan ariza uchun vazifa yo'q"
    assert 'portal' not in t['vazifa'].lower(), \
        f"Tasdiqlangan arizaga portal vazifasi berildi: {t['vazifa']}"
    assert t['bolim'] == 'sud', f"Kutilgan bo'lim 'sud', kelgan: {t['bolim']}"


def test_tayyorlangan_arizaga_portal_vazifasi_beriladi(muhit, mijoz):
    db = muhit['db']
    v = _vzf(muhit)
    _davo_tayyor(db, mijoz)
    t = _vazifa(v, '10001')
    assert t and 'portal' in t['vazifa'].lower()


# ── 3. Portal rad etsa — ish yo'qolmaydi ────────────────────────────

def test_portal_rad_etgan_ish_vazifada_qoladi(muhit, mijoz):
    """Rad etilgan murojaat kundalik vazifalarda ko'rinishi SHART —
    aks holda ish jimgina to'xtab qolardi."""
    db = muhit['db']
    v = _vzf(muhit)
    xat_id = _davo_tayyor(db, mijoz)
    db.bh_murojaat_saqlash('10001', xat_id=xat_id, murojaat_raqami='193/003')
    db.bh_holat_ozgartirish('10001', 'rad_etildi', 'Hujjat to\'liq emas')

    t = _vazifa(v, '10001')
    assert t is not None, "Rad etilgan ish vazifalardan yo'qoldi"
    assert 'rad' in t['vazifa'].lower()
    # Bugun rad etilgan — shoshilinch (kechikkan emas, hali vaqt bor)
    assert t['ustuvorlik'] == 'bugun', f"Kutilgan 'bugun', kelgan: {t['ustuvorlik']}"
    assert "to'liq emas" in t['izoh'], "Rad etish sababi ko'rsatilmadi"


def test_eski_rad_etilgan_ish_kechikkan_boladi(muhit, mijoz):
    """Rad etilgandan keyin kun sayin kechikish ortib borishi kerak —
    aks holda e'tibordan chetda qolgan ish hech qachon "qizarmasdi"."""
    db = muhit['db']
    v = _vzf(muhit)
    xat_id = _davo_tayyor(db, mijoz)
    db.bh_murojaat_saqlash('10001', xat_id=xat_id, murojaat_raqami='193/004')
    db.bh_holat_ozgartirish('10001', 'rad_etildi', 'Kamchilik bor')
    # Rad etilganiga 10 kun bo'lgan deb belgilaymiz
    db.bh_murojaat_saqlash('10001', holat_sana=_kun(10))

    t = _vazifa(v, '10001')
    assert t['ustuvorlik'] == 'kechikkan', f"10 kun o'tgan bo'lsa ham: {t['ustuvorlik']}"
    assert t['qolgan_kun'] == -10


# ── 4. Qarzi yopilgan mijozga sug'urta arizasi taklif qilinmaydi ────

def _mib_yakunlangan(db, prow, sabab):
    conn = db.get_conn()
    conn.execute('''INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi,
        mijoz_turi, xat_turi, holat, mib_holati, mib_ish_raqami,
        mib_otkazilgan_sana, davo_ariza_turi, mib_yakunlangan,
        mib_yakunlangan_sana, mib_yakunlash_sababi, yaratilgan_sana)
        VALUES (?, ?, ?, 'jismoniy', 'talabnoma', 'yuborildi', 'otkazildi',
                'MIB-1', ?, 'muddatidan_oldin', 1, ?, ?, ?)''',
        (prow['id'], prow['anketa_raqami'], prow['mijoz_nomi'],
         _kun(60), _kun(5), sabab, datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()


def test_qarzi_yopilganga_sugurta_taklif_qilinmaydi(muhit, mijoz):
    """Qarz to'liq to'langan bo'lsa — sug'urtadan undiradigan narsa yo'q."""
    db = muhit['db']
    v = _vzf(muhit)
    conn = db.get_conn()
    conn.execute("UPDATE portfel SET asosiy_qarz=0, foiz_qarz=0, jarima=0 WHERE anketa_raqami='10001'")
    conn.commit()
    conn.close()
    prow = dict(db.get_conn().execute(
        "SELECT * FROM portfel WHERE anketa_raqami='10001'").fetchone())
    _mib_yakunlangan(db, prow, "To'liq to'landi (tizim avtomatik)")

    t = _vazifa(v, '10001')
    assert t is None or "sug'urta" not in t['vazifa'].lower(), \
        f"To'langan qarz uchun sug'urta vazifasi berildi: {t['vazifa'] if t else ''}"


def test_qarzi_borga_sugurta_taklif_qilinadi(muhit, mijoz):
    """Undirilmagan qarz bor bo'lsa — sug'urta yo'li taklif qilinadi."""
    db = muhit['db']
    v = _vzf(muhit)
    _mib_yakunlangan(db, mijoz, "Undirib bo'lmadi — mol-mulk topilmadi")
    t = _vazifa(v, '10001')
    assert t is not None
    assert 'asos hujjat' in t['vazifa'].lower() or "sug'urta" in t['vazifa'].lower(), \
        f"Kutilmagan vazifa: {t['vazifa']}"


def test_qarzi_yopilgan_royxatda_belgilanadi(muhit, mijoz, klient):
    """Ro'yxatda tarix sifatida qoladi, lekin belgilab qo'yiladi."""
    db = muhit['db']
    conn = db.get_conn()
    conn.execute("UPDATE portfel SET asosiy_qarz=0, foiz_qarz=0, jarima=0 WHERE anketa_raqami='10001'")
    conn.commit()
    conn.close()
    prow = dict(db.get_conn().execute(
        "SELECT * FROM portfel WHERE anketa_raqami='10001'").fetchone())
    _mib_yakunlangan(db, prow, "To'liq to'landi")

    royxat = klient.get('/api/sugurta_undirish/royxat').get_json()['royxat']
    qator = next((r for r in royxat if r['anketa_raqami'] == '10001'), None)
    assert qator is not None, "Ish ro'yxatdan butunlay yo'qoldi"
    assert qator['qarz_yopilgan'] is True


# ── 5. MIB endigina boshlanganda sug'urta erta taklif qilinmaydi ────

def test_mib_faol_bolsa_sugurta_erta_taklif_qilinmaydi(muhit, mijoz):
    """MIB ijro harakatlari hali boshlanmagan bo'lsa — avval MIB ishi,
    keyin sug'urta. Aks holda tizim noto'g'ri yo'naltirardi."""
    db = muhit['db']
    v = _vzf(muhit)
    conn = db.get_conn()
    conn.execute('''INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi,
        mijoz_turi, xat_turi, holat, mib_holati, mib_ish_raqami,
        mib_otkazilgan_sana, davo_ariza_turi, mib_yakunlangan, yaratilgan_sana)
        VALUES (?, '10001', ?, 'jismoniy', 'talabnoma', 'yuborildi', 'otkazildi',
                'MIB-1', ?, 'muddatidan_oldin', 0, ?)''',
        (mijoz['id'], mijoz['mijoz_nomi'], _kun(1), datetime.datetime.now().isoformat()))
    conn.commit()
    conn.close()

    t = _vazifa(v, '10001')
    assert t is not None
    assert "sug'urta" not in t['vazifa'].lower() and 'asos hujjat' not in t['vazifa'].lower(), \
        f"MIB endigina boshlanganda sug'urta taklif qilindi: {t['vazifa']}"


# ── 6. Zanjir uzilmasligi: har bosqichda vazifa bor ─────────────────

def test_har_bosqichda_vazifa_bor(muhit, mijoz):
    """Ish hech bir bosqichda "vazifasiz" qolib ketmasligi kerak."""
    db = muhit['db']
    v = _vzf(muhit)
    xat_id = _davo_tayyor(db, mijoz)

    BOSQICHLAR = [
        ('davo tayyor', {}),
        ('tasdiqlandi', dict(davo_ariza_holati='olib_kelindi',
                             davo_ariza_imzo_sana=_kun(8))),
        ('sudga topshirildi', dict(sud_holati='topshirildi',
                                   sud_topshirilgan_sana=_kun(70))),
        ('qaror chiqdi', dict(sud_qaror_fayl='/tmp/q.pdf',
                              sud_qaror_natija='bank_foydasiga',
                              sud_qaror_sana=_kun(40))),
        ("MIBga o'tkazildi", dict(mib_holati='otkazildi', mib_ish_raqami='M-1',
                                  mib_otkazilgan_sana=_kun(30))),
        ('MIB yakunlandi', dict(mib_yakunlangan=1, mib_yakunlangan_sana=_kun(2),
                                mib_yakunlash_sababi="Undirib bo'lmadi")),
    ]
    uzilgan = []
    for nomi, m in BOSQICHLAR:
        if m:
            conn = db.get_conn()
            sc = ', '.join(f'{k}=?' for k in m)
            conn.execute(f'UPDATE xatlar SET {sc} WHERE id=?',
                         list(m.values()) + [xat_id])
            conn.commit()
            conn.close()
        if _vazifa(v, '10001') is None:
            uzilgan.append(nomi)
    assert not uzilgan, f"Bu bosqichlarda ish vazifasiz qoldi: {', '.join(uzilgan)}"


# ── 7. Qarzi yopilgan mijozga umuman chora vazifasi berilmaydi ──────

def test_qarzsiz_mijozga_huquqiy_chora_taklif_qilinmaydi(muhit, mijoz):
    """Mijoz qarzini to'lab bo'lgan bo'lsa — unga qarshi davo ariza
    tayyorlash, sudga topshirish yoki boshqa chora ko'rish ma'nosiz."""
    db = muhit['db']
    v = _vzf(muhit)
    _davo_tayyor(db, mijoz)                       # davo ariza bosqichida
    conn = db.get_conn()
    conn.execute("UPDATE portfel SET asosiy_qarz=0, foiz_qarz=0, jarima=0 "
                 "WHERE anketa_raqami='10001'")
    conn.commit()
    conn.close()
    assert _vazifa(v, '10001') is None, \
        "Qarzi yo'q mijozga huquqiy chora vazifasi berildi"


def test_qarzi_borga_vazifa_beriladi(muhit, mijoz):
    """Nazorat tekshiruvi: qarz bor bo'lsa vazifa albatta bo'lishi kerak."""
    db = muhit['db']
    v = _vzf(muhit)
    _davo_tayyor(db, mijoz)
    assert _vazifa(v, '10001') is not None


def test_sud_majlisi_qarzdan_qatiy_nazar_eslatiladi(muhit, mijoz):
    """Istisno: sud majlisi baribir bo'ladi — unga borish kerak,
    qarz holatidan qat'i nazar."""
    db = muhit['db']
    v = _vzf(muhit)
    conn = db.get_conn()
    conn.execute("UPDATE portfel SET asosiy_qarz=0, foiz_qarz=0, jarima=0 "
                 "WHERE anketa_raqami='10001'")
    conn.commit()
    conn.close()
    ertaga = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%d.%m.%Y')
    db.sud_kuni_qoshish('10001', mijoz['mijoz_nomi'], ertaga, '10:00', 'Sud', 'A-1')
    t = _vazifa(v, '10001')
    assert t is not None and 'Sud majlisi' in t['vazifa'], \
        "Sud majlisi eslatmasi yo'qoldi"
