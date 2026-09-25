# -*- coding: utf-8 -*-
"""Huquqiy jarayon tahlili testlari."""
import datetime
import importlib


def _tj(muhit):
    import tahlil_jarayon
    importlib.reload(tahlil_jarayon)
    tahlil_jarayon.db = muhit['db']
    return tahlil_jarayon


def _kun(n):
    return (datetime.date.today() - datetime.timedelta(days=n)).strftime('%d.%m.%Y')


def _iso(n):
    return (datetime.datetime.now() - datetime.timedelta(days=n)).isoformat()


def _xat(db, prow, **maydonlar):
    conn = db.get_conn()
    cur = conn.execute('''
        INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi,
                            xat_turi, holat, yaratilgan_sana)
        VALUES (?, ?, ?, 'jismoniy', 'talabnoma', 'yuborildi', ?)
    ''', (prow['id'], prow['anketa_raqami'], prow['mijoz_nomi'], _iso(100)))
    xat_id = cur.lastrowid
    if maydonlar:
        sc = ', '.join(f'{k}=?' for k in maydonlar)
        conn.execute(f'UPDATE xatlar SET {sc} WHERE id=?',
                     list(maydonlar.values()) + [xat_id])
    conn.commit()
    conn.close()
    return xat_id


# ── Yordamchi funksiyalar ───────────────────────────────────────────

def test_kun_farqi_hisobi(muhit):
    tj = _tj(muhit)
    assert tj._kun_farqi('01.09.2026', '15.09.2026') == 14
    assert tj._kun_farqi('15.09.2026', '01.09.2026') is None   # teskari — hisobga olinmaydi
    assert tj._kun_farqi('', '15.09.2026') is None
    assert tj._kun_farqi('01.01.2000', '15.09.2026') is None   # 10 yildan ortiq — xato sana


def test_statistika(muhit):
    tj = _tj(muhit)
    st = tj._statistika([10, 20, 30, 100])
    assert st['soni'] == 4
    assert st['mediana'] == 25
    assert st['eng_uzun'] == 100
    # Bo'sh ro'yxat xato bermasligi kerak
    assert tj._statistika([])['soni'] == 0
    assert tj._statistika([None, None])['soni'] == 0


# ── Voronka ─────────────────────────────────────────────────────────

def test_voronka_bosqichlarni_ajratadi(muhit, mijoz):
    tj = _tj(muhit)
    db = muhit['db']
    _xat(db, mijoz, holat='tayyor')
    v = {x['kod']: x for x in tj.voronka()}
    assert v['xat_tayyor']['soni'] == 1
    assert v['mibda']['soni'] == 0


def test_voronka_summani_qoshadi(muhit, mijoz):
    tj = _tj(muhit)
    _xat(muhit['db'], mijoz, holat='tayyor')
    v = {x['kod']: x for x in tj.voronka()}
    # 50 mln asosiy + 5 mln foiz + 1 mln jarima
    assert v['xat_tayyor']['summa'] == 56000000


def test_arxivlangan_voronkada_yoq(muhit, mijoz):
    tj = _tj(muhit)
    _xat(muhit['db'], mijoz, holat='tayyor', arxivlangan=1)
    assert sum(x['soni'] for x in tj.voronka()) == 0


def test_mib_bosqichi_togri_ajratiladi(muhit, mijoz):
    tj = _tj(muhit)
    db = muhit['db']
    _xat(db, mijoz, mib_holati='otkazildi', mib_yakunlangan=0)
    v = {x['kod']: x for x in tj.voronka()}
    assert v['mibda']['soni'] == 1 and v['mib_yakunlangan']['soni'] == 0

    conn = db.get_conn()
    conn.execute('UPDATE xatlar SET mib_yakunlangan=1')
    conn.commit()
    conn.close()
    v = {x['kod']: x for x in tj.voronka()}
    assert v['mibda']['soni'] == 0 and v['mib_yakunlangan']['soni'] == 1


# ── Bosqich davomiyligi ─────────────────────────────────────────────

def test_davomiylik_kunlarni_hisoblaydi(muhit, mijoz):
    tj = _tj(muhit)
    _xat(muhit['db'], mijoz,
         yuborilgan_sana=_iso(60), davo_ariza_sana=_iso(40))   # 20 kun
    d = {x['kod']: x for x in tj.bosqich_davomiyligi()}
    assert d['xat_davo']['soni'] == 1
    assert 19 <= d['xat_davo']['mediana'] <= 21


def test_davomiylik_bosh_bazada_xato_bermaydi(muhit):
    tj = _tj(muhit)
    natija = tj.bosqich_davomiyligi()
    assert len(natija) == 7
    assert all(d['soni'] == 0 for d in natija)


def test_toliq_yol_hisoblanadi(muhit, mijoz):
    tj = _tj(muhit)
    _xat(muhit['db'], mijoz, yuborilgan_sana=_iso(150),
         mib_yakunlangan_sana=_kun(10))
    d = {x['kod']: x for x in tj.bosqich_davomiyligi()}
    assert d['toliq']['soni'] == 1
    assert 139 <= d['toliq']['mediana'] <= 141


# ── Undirish ────────────────────────────────────────────────────────

def test_undirish_manbalarga_ajratiladi(muhit, mijoz):
    tj = _tj(muhit)
    db = muhit['db']
    xat_id = _xat(db, mijoz, mib_holati='otkazildi')
    db.add_mib_amal(xat_id, 'Ish haqiga qaratish', _kun(10), '', undirilgan_summa=5000000)
    db.add_mib_amal(xat_id, 'Auksion', _kun(5), '', auksion_narxi=20000000)
    db.sugurta_undirish_saqlash('10001', tur='vafot')
    db.sugurta_holat_ozgartirish('10001', 'tolandi', tur='vafot',
                                 tolangan_summa=7000000, tolov_sana=_kun(3))

    u = tj.undirish_samaradorligi()
    manbalar = {m['kod']: m['summa'] for m in u['manbalar']}
    assert manbalar['ish_haqi'] == 5000000
    assert manbalar['auksion'] == 20000000
    assert manbalar['sugurta_vafot'] == 7000000
    assert u['jami'] == 32000000
    # Ulushlar jami 100% ga yaqin bo'lishi kerak
    assert abs(sum(m['ulush'] for m in u['manbalar']) - 100) < 0.5


def test_mib_va_vafot_sugurtasi_alohida_hisoblanadi(muhit, mijoz):
    tj = _tj(muhit)
    db = muhit['db']
    db.sugurta_undirish_saqlash('10001', tur='mib')
    db.sugurta_holat_ozgartirish('10001', 'tolandi', tur='mib', tolangan_summa=1000000)
    db.sugurta_undirish_saqlash('10001', tur='vafot')
    db.sugurta_holat_ozgartirish('10001', 'tolandi', tur='vafot', tolangan_summa=2000000)
    manbalar = {m['kod']: m['summa'] for m in tj.undirish_samaradorligi()['manbalar']}
    assert manbalar['sugurta_mib'] == 1000000
    assert manbalar['sugurta_vafot'] == 2000000


def test_tolanmagan_sugurta_hisobga_olinmaydi(muhit, mijoz):
    tj = _tj(muhit)
    db = muhit['db']
    db.sugurta_undirish_saqlash('10001', tur='mib', talab_summasi=9000000)
    db.sugurta_holat_ozgartirish('10001', 'yuborildi', tur='mib')
    assert tj.undirish_samaradorligi()['jami'] == 0


# ── Oylik dinamika ──────────────────────────────────────────────────

def test_dinamika_12_oy_qaytaradi(muhit):
    tj = _tj(muhit)
    d = tj.oylik_dinamika()
    assert len(d) == 12
    assert all('oy' in x for x in d)


def test_dinamika_joriy_oyga_yozadi(muhit, mijoz):
    tj = _tj(muhit)
    _xat(muhit['db'], mijoz, yuborilgan_sana=_iso(1))
    d = tj.oylik_dinamika()
    assert d[-1]['xat'] >= 1, "Bugungi xat joriy oyga tushmadi"


# ── Harakatlar samaradorligi ────────────────────────────────────────

def test_harakat_samaradorligi(muhit, mijoz):
    tj = _tj(muhit)
    db = muhit['db']
    xat_id = _xat(db, mijoz, mib_holati='otkazildi')
    db.add_mib_amal(xat_id, 'Auksion', _kun(5), '', auksion_narxi=10000000)
    db.add_mib_amal(xat_id, 'Auksion', _kun(3), '', auksion_narxi=20000000)
    db.add_mib_amal(xat_id, 'Mol-mulk qidiruvi', _kun(2), '')

    h = {a['amal_turi']: a for a in tj.harakat_samaradorligi()}
    assert h['Auksion']['soni'] == 2
    assert h['Auksion']['summa'] == 30000000
    assert h['Auksion']['ortacha'] == 15000000
    assert h['Mol-mulk qidiruvi']['summa'] == 0
    # Eng ko'p pul qaytargani birinchi bo'lishi kerak
    assert tj.harakat_samaradorligi()[0]['amal_turi'] == 'Auksion'


# ── Endpointlar ─────────────────────────────────────────────────────

def test_jarayon_endpointi(muhit, mijoz, klient):
    _xat(muhit['db'], mijoz, holat='tayyor')
    r = klient.get('/api/tahlil/jarayon')
    assert r.status_code == 200
    d = r.get_json()
    for kalit in ('voronka', 'davomiylik', 'undirish', 'dinamika', 'harakatlar'):
        assert kalit in d, f"{kalit} javobda yo'q"


def test_jarayon_bosh_bazada_ishlaydi(muhit, klient):
    r = klient.get('/api/tahlil/jarayon')
    assert r.status_code == 200


def test_jarayon_excel(muhit, mijoz, klient):
    _xat(muhit['db'], mijoz, holat='tayyor', yuborilgan_sana=_iso(50),
         davo_ariza_sana=_iso(30))
    r = klient.get('/api/tahlil/jarayon_excel')
    assert r.status_code == 200
    assert len(r.data) > 3000
