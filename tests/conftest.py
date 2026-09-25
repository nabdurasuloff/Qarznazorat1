# -*- coding: utf-8 -*-
"""
Avtotestlar uchun umumiy tayyorgarlik (fixtures).

MUHIM: testlar HECH QACHON haqiqiy bazaga tegmaydi. Har bir test uchun
vaqtinchalik papkada yangi, bo'sh baza yaratiladi — shuning uchun
testlarni ishchi kompyuterda ham xavfsiz ishlatish mumkin.
"""
import os
import sys
import shutil
import tempfile
import importlib
import datetime

import pytest

BACKEND = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend')
if BACKEND not in sys.path:
    sys.path.insert(0, BACKEND)


@pytest.fixture()
def muhit(monkeypatch):
    """Har bir test uchun toza baza + toza hujjatlar papkasi."""
    vaqtinchalik = tempfile.mkdtemp(prefix='qn_test_')

    import database as db
    importlib.reload(db)
    db.DB_PATH = os.path.join(vaqtinchalik, 'test.db')
    db.init_db()
    db.set_setting('hujjatlar_papkasi', os.path.join(vaqtinchalik, 'hujjatlar'))
    os.makedirs(os.path.join(vaqtinchalik, 'hujjatlar'), exist_ok=True)

    import util
    importlib.reload(util)
    util.db = db

    import letters
    importlib.reload(letters)

    import umumiy
    importlib.reload(umumiy)
    umumiy.db = db
    umumiy.letters = letters

    import server
    importlib.reload(server)
    server.db = db
    server.util = util
    server.letters = letters
    server.app.config['TESTING'] = True

    yield {'db': db, 'util': util, 'letters': letters, 'server': server,
           'umumiy': umumiy, 'papka': vaqtinchalik}

    shutil.rmtree(vaqtinchalik, ignore_errors=True)


@pytest.fixture()
def mijoz(muhit):
    """Portfelga bitta sinov mijozini qo'shadi va uning qatorini qaytaradi."""
    db = muhit['db']
    conn = db.get_conn()
    cur = conn.execute('''
        INSERT INTO portfel (anketa_raqami, mijoz_nomi, mijoz_turi, mijoz_turi_kodi,
                             pinfl, stir, asosiy_qarz, foiz_qarz, jarima,
                             shartnoma_sanasi, shartnoma_tugash_sanasi,
                             dpd_max, dpd_asosiy, jami_berilgan_summa, faol)
        VALUES ('10001', 'TESTOV TEST TESTOVICH', 'Individual', '8',
                '12345678901234', '', 50000000, 5000000, 1000000,
                '10.01.2024', '10.01.2027', 95, 95, 60000000, 1)
    ''')
    conn.commit()
    pid = cur.lastrowid
    row = dict(conn.execute('SELECT * FROM portfel WHERE id=?', (pid,)).fetchone())
    conn.close()
    return row


@pytest.fixture()
def klient(muhit):
    """Flask test klienti — endpointlarni to'g'ridan chaqirish uchun."""
    return muhit['server'].app.test_client()


def sana(kun_oldin=0):
    """Bugundan N kun oldingi sanani kk.oo.yyyy ko'rinishida qaytaradi."""
    return (datetime.date.today() - datetime.timedelta(days=kun_oldin)).strftime('%d.%m.%Y')
