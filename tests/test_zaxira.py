# -*- coding: utf-8 -*-
"""Zaxira nusxa olish va tiklash testlari.

Butun huquqiy ish bitta baza faylida saqlanadi — shu sabab bu testlar
eng muhimlaridan: ular zaxira haqiqatan TO'LIQ va TIKLANADIGAN ekanini
tekshiradi.
"""
import os
import sqlite3


def _portfel_soni(db):
    conn = db.get_conn()
    n = conn.execute('SELECT COUNT(*) c FROM portfel').fetchone()['c']
    conn.close()
    return n


def test_zaxira_olinadi_va_fayl_yaratiladi(muhit, mijoz):
    db = muhit['db']
    yol = db.zaxira_yaratish('test')
    assert yol and os.path.exists(yol)
    assert os.path.getsize(yol) > 0


def test_zaxira_haqiqiy_sqlite_bazasi(muhit, mijoz):
    """Nusxa ochiladigan, butun SQLite bazasi bo'lishi kerak."""
    db = muhit['db']
    yol = db.zaxira_yaratish('test')
    conn = sqlite3.connect(yol)
    n = conn.execute('SELECT COUNT(*) c FROM portfel').fetchone()[0]
    jadvallar = {r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    conn.close()
    assert n == 1
    # Asosiy jadvallar nusxada ham bo'lishi shart
    for jadval in ('portfel', 'xatlar', 'sugurta_undirish', 'vafot_etganlar', 'sozlamalar'):
        assert jadval in jadvallar, f"{jadval} nusxada yo'q"


def test_tiklash_yoqolgan_malumotni_qaytaradi(muhit, mijoz):
    db = muhit['db']
    boshlangich = _portfel_soni(db)
    yol = db.zaxira_yaratish('test')

    conn = db.get_conn()
    conn.execute('DELETE FROM portfel')
    conn.commit()
    conn.close()
    assert _portfel_soni(db) == 0

    db.zaxiradan_tiklash(yol)
    assert _portfel_soni(db) == boshlangich


def test_tiklashdan_oldin_joriy_holat_saqlanadi(muhit, mijoz):
    """Noto'g'ri nusxa tanlansa ortga qaytish imkoni qolishi kerak."""
    db = muhit['db']
    yol = db.zaxira_yaratish('birinchi')
    db.zaxiradan_tiklash(yol)
    nomlar = [z['nomi'] for z in db.zaxira_royxati()]
    assert any('tiklashdan_oldin' in n for n in nomlar), nomlar


def test_buzuq_fayl_tiklanmaydi(muhit, mijoz):
    db = muhit['db']
    yomon = os.path.join(db.zaxira_papkasi(), 'yomon.db')
    with open(yomon, 'w') as f:
        f.write('bu baza emas')
    try:
        db.zaxiradan_tiklash(yomon)
        assert False, "Buzuq fayl qabul qilindi"
    except Exception:
        pass
    # Baza buzilmagan bo'lishi kerak
    assert _portfel_soni(db) == 1


def test_eski_nusxalar_soni_cheklanadi(muhit, mijoz):
    db = muhit['db']
    papka = db.zaxira_papkasi()
    for i in range(db.ZAXIRA_MAX_SONI + 8):
        yol = os.path.join(papka, f'qarz_nazorat_2026010{i % 9 + 1}_1200{i:02d}_t.db')
        c = sqlite3.connect(yol)
        c.execute('CREATE TABLE IF NOT EXISTS t(a)')
        c.close()
        os.utime(yol, (1700000000 - i * 3600, 1700000000 - i * 3600))
    db.zaxira_eskilarini_tozalash()
    assert len(db.zaxira_royxati()) <= db.ZAXIRA_MAX_SONI


def test_zaxira_kerakmi_bayrogi(muhit, mijoz):
    """Bayroq kuniga bir marta ishlashini tekshiradi.

    Diqqat: server moduli import qilinganda kunlik zaxira ALLAQACHON
    olinadi (bu — to'g'ri xatti-harakat), shuning uchun testda bayroqni
    avval qo'lda tozalaymiz."""
    db = muhit['db']
    db.set_setting('oxirgi_zaxira_sana', '')
    assert db.zaxira_kerakmi() is True      # hali olinmagan
    db.zaxira_yaratish('kunlik')
    assert db.zaxira_kerakmi() is False     # bugun olingan


def test_nusxa_ochirilsa_yangisi_olinadi(muhit, mijoz):
    """HAQIQIY MUAMMO: sana "bugun olingan" deb tursa-da, nusxa fayli
    o'chirilgan bo'lsa — tizim yangisini olmay qo'yardi."""
    db = muhit['db']
    db.zaxira_yaratish('kunlik')
    assert db.zaxira_kerakmi() is False

    for z in db.zaxira_royxati():          # nusxalar yo'qoldi
        os.remove(z['yoli'])
    assert db.zaxira_kerakmi() is True, \
        "Nusxa yo'q bo'lsa ham tizim yangisini olmayapti"


def test_server_ishga_tushganda_zaxira_avtomatik_olinadi(muhit):
    """Dastur ochilishi bilan kunlik nusxa o'zi olinishi kerak —
    foydalanuvchi hech narsa qilmasa ham."""
    db = muhit['db']
    assert db.get_setting('oxirgi_zaxira_sana', '') != ''
    assert len(db.zaxira_royxati()) >= 1


def test_zaxira_endpointlari(muhit, mijoz, klient):
    r = klient.post('/api/zaxira/yaratish')
    assert r.status_code == 200 and r.get_json().get('ok')

    r = klient.get('/api/zaxira/royxat')
    d = r.get_json()
    assert len(d['royxat']) >= 1
    assert d['bugun_olinganmi'] is True


def test_zaxira_papkasidan_tashqari_fayl_rad_etiladi(muhit, mijoz, klient):
    """Xavfsizlik: tashqaridan ixtiyoriy fayl yo'lini yuborib bo'lmasin."""
    r = klient.post('/api/zaxira/tiklash', json={'yoli': '/etc/passwd'})
    assert r.status_code == 400
