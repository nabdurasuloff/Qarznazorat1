# -*- coding: utf-8 -*-
"""Sanalarni tekshirish (util.sana_tekshir) testlari."""
import datetime


def test_togri_sanalar_qabul_qilinadi(muhit):
    util = muhit['util']
    for kirish in ['15.09.2026', '2026-09-15', '15/09/2026', '2026.09.15', '15-09-2026']:
        toza, xato = util.sana_tekshir(kirish, 'Sana')
        assert xato is None, f"{kirish} rad etildi: {xato}"
        assert toza == '15.09.2026', f"{kirish} -> {toza}"


def test_notogri_sana_rad_etiladi(muhit):
    util = muhit['util']
    for kirish in ['32.13.2026', 'abc', '15.15.2026', '00.00.0000']:
        toza, xato = util.sana_tekshir(kirish, 'Sana')
        assert xato is not None, f"{kirish} noto'g'ri, lekin qabul qilindi"
        assert toza == ''


def test_shubhali_yil_rad_etiladi(muhit):
    util = muhit['util']
    _, xato = util.sana_tekshir('15.09.1975', 'Qaror sanasi')
    assert xato and 'shubhali' in xato
    _, xato = util.sana_tekshir('15.09.2099', 'Sana')
    assert xato and 'shubhali' in xato


def test_bosh_sana_majburiy_bolmasa_otadi(muhit):
    util = muhit['util']
    toza, xato = util.sana_tekshir('', 'Sana', majburiy=False)
    assert xato is None and toza == ''


def test_bosh_sana_majburiy_bolsa_xato(muhit):
    util = muhit['util']
    _, xato = util.sana_tekshir('', 'Ariza sanasi', majburiy=True)
    assert xato and 'shart' in xato


def test_kelajak_sana_taqiqlanadi(muhit):
    util = muhit['util']
    ertaga = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%d.%m.%Y')
    _, xato = util.sana_tekshir(ertaga, "To'lov sanasi", kelajak_mumkinmi=False)
    assert xato and 'kelajak' in xato
    # Kelajak ruxsat berilganda o'tishi kerak (masalan sud majlisi sanasi)
    toza, xato = util.sana_tekshir(ertaga, 'Sud sanasi', kelajak_mumkinmi=True)
    assert xato is None and toza == ertaga


def test_vafot_sanasi_endpointda_tekshiriladi(muhit, mijoz, klient):
    """Noto'g'ri sana endpointda ham to'xtatilishi kerak."""
    r = klient.post('/api/vafot/qoshish', json={
        'anketa_raqami': '10001', 'vafot_sanasi': '32.13.2026'})
    assert r.status_code == 400
    assert "noto'g'ri" in r.get_json()['xato']

    # To'g'ri sana o'tadi va normallashtiriladi
    r = klient.post('/api/vafot/qoshish', json={
        'anketa_raqami': '10001', 'vafot_sanasi': '2026-08-15'})
    assert r.status_code == 200, r.get_json()
    db = muhit['db']
    conn = db.get_conn()
    v = dict(conn.execute('SELECT * FROM vafot_etganlar WHERE anketa_raqami=?', ('10001',)).fetchone())
    conn.close()
    assert v['vafot_sanasi'] == '15.08.2026'
