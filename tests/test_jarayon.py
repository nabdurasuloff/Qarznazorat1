# -*- coding: utf-8 -*-
"""Asosiy ish zanjiri testlari: Xat -> Davo ariza -> Sud -> MIB -> Sug'urta.

Bu testlar tizim ishlab chiqilishi davomida HAQIQATAN uchragan xatolarni
qaytadan sodir bo'lmasligini qo'riqlaydi:
  • bitta anketa ostida ikki xil mijoz -> hujjatlar boshqa papkaga tushishi
  • "Nollashtirish" tarixni o'chirib yuborishi
  • sug'urta ro'yxatiga noto'g'ri ishlar tushishi
  • vafot va MIB jarayonlari bir-biriga aralashib ketishi
"""
import os
import datetime


def _xat_yaratish(db, prow, **maydonlar):
    """Portfel qatori uchun xat yozuvini yaratadi va id qaytaradi."""
    conn = db.get_conn()
    cur = conn.execute('''
        INSERT INTO xatlar (portfel_id, anketa_raqami, mijoz_nomi, mijoz_turi,
                            xat_turi, fayl_yoli, holat, yaratilgan_sana)
        VALUES (?, ?, ?, ?, 'talabnoma', '/tmp/xat.docx', 'yuborildi', ?)
    ''', (prow['id'], prow['anketa_raqami'], prow['mijoz_nomi'], 'jismoniy',
          datetime.datetime.now().isoformat()))
    xat_id = cur.lastrowid
    if maydonlar:
        set_clause = ', '.join(f'{k}=?' for k in maydonlar)
        conn.execute(f'UPDATE xatlar SET {set_clause} WHERE id=?',
                     list(maydonlar.values()) + [xat_id])
    conn.commit()
    conn.close()
    return xat_id


# ── Sug'urta: kimlar ro'yxatga tushadi ────────────────────────────────

def test_sugurta_royxatiga_faqat_muddatidan_oldin_tushadi(muhit, mijoz):
    """Sug'urtadan undirish FAQAT muddatidan oldin undirish qarorlari
    bo'yicha hisoblanadi — boshqa turdagi davo arizalar tushmasligi kerak."""
    db = muhit['db']
    _xat_yaratish(db, mijoz, mib_holati='otkazildi', davo_ariza_turi='jismoniy_oddiy')
    assert len(db.get_sugurta_undirish_royxati()) == 0

    conn = db.get_conn()
    conn.execute("UPDATE xatlar SET davo_ariza_turi='muddatidan_oldin'")
    conn.commit()
    conn.close()
    assert len(db.get_sugurta_undirish_royxati()) == 1


def test_boshlangan_sugurta_ishi_royxatdan_yoqolmaydi(muhit, mijoz):
    """Ariza turi mos bo'lmasa ham, boshlangan ish ko'rinib turishi kerak."""
    db = muhit['db']
    _xat_yaratish(db, mijoz, mib_holati='otkazildi', davo_ariza_turi='jismoniy_oddiy')
    db.sugurta_undirish_saqlash('10001', tur='mib', sugurta_kompaniya='TEST')
    assert len(db.get_sugurta_undirish_royxati()) == 1


def test_arxivlangan_xat_sugurta_royxatiga_tushmaydi(muhit, mijoz):
    db = muhit['db']
    _xat_yaratish(db, mijoz, mib_holati='otkazildi',
                  davo_ariza_turi='muddatidan_oldin', arxivlangan=1)
    assert len(db.get_sugurta_undirish_royxati()) == 0


def test_vafot_etganlar_avtomatik_sugurta_royxatida(muhit, mijoz):
    """Vafot etganlar bo'limiga kiritilgan mijoz — qo'shimcha shartsiz
    sug'urta ro'yxatida ko'rinishi kerak."""
    db = muhit['db']
    assert len(db.get_sugurta_vafot_royxati()) == 0
    db.mark_vafot_etgan(mijoz['id'], '10001', mijoz['mijoz_nomi'],
                        '15.08.2026', None, None)
    assert len(db.get_sugurta_vafot_royxati()) == 1


def test_mib_va_vafot_yozuvlari_aralashmaydi(muhit, mijoz):
    """Bitta mijozda ikkala jarayon ham bo'lishi mumkin — ular alohida
    saqlanishi kerak."""
    db = muhit['db']
    db.sugurta_undirish_saqlash('10001', tur='mib', sugurta_kompaniya='MIB-KOMPANIYA')
    db.sugurta_undirish_saqlash('10001', tur='vafot', sugurta_kompaniya='VAFOT-KOMPANIYA')

    m = db.sugurta_undirish_olish('10001', 'mib')
    v = db.sugurta_undirish_olish('10001', 'vafot')
    assert m['sugurta_kompaniya'] == 'MIB-KOMPANIYA'
    assert v['sugurta_kompaniya'] == 'VAFOT-KOMPANIYA'
    assert m['id'] != v['id']


def test_sugurta_holati_uch_bosqich(muhit, mijoz):
    db = muhit['db']
    db.sugurta_undirish_saqlash('10001', tur='mib')
    for holat in ('yuborildi', 'tolandi'):
        db.sugurta_holat_ozgartirish('10001', holat, tur='mib')
        assert db.sugurta_undirish_olish('10001', 'mib')['holati'] == holat


# ── Bitta anketa ostida ikki mijoz (haqiqiy portfelda uchragan) ───────

def test_bir_anketada_ikki_mijoz_togri_ajratiladi(muhit, mijoz):
    """HAQIQIY MUAMMO: portfelda bitta anketa raqami ostida ikki xil
    mijoz uchraydi (eski yopilgan kredit va yangi kredit bir xil raqam
    olgan). Hujjat BOSHQA mijozning papkasiga tushib ketmasligi kerak."""
    db = muhit['db']
    umumiy = muhit['umumiy']

    conn = db.get_conn()
    conn.execute('''
        INSERT INTO portfel (anketa_raqami, mijoz_nomi, mijoz_turi, pinfl,
                             asosiy_qarz, foiz_qarz, faol)
        VALUES ('10001', 'BOSHQA MIJOZ ESKI KREDIT', 'Individual', '999', 0, 0, 1)
    ''')
    conn.commit()
    conn.close()

    # Xat aynan BIRINCHI mijozga (mijoz['id']) tegishli
    xat_id = _xat_yaratish(db, mijoz, mib_holati='otkazildi')
    conn = db.get_conn()
    xat = dict(conn.execute('SELECT * FROM xatlar WHERE id=?', (xat_id,)).fetchone())
    conn.close()

    nomi = umumiy.anketa_mijoz_nomi('10001', xat)
    assert nomi == mijoz['mijoz_nomi'], f"Noto'g'ri mijoz tanlandi: {nomi}"


def test_xatsiz_holatda_qarzi_katta_mijoz_tanlanadi(muhit, mijoz):
    """Xat yozuvi bo'lmasa — faol (qarzi bor) mijoz tanlanishi kerak,
    tasodifiy birinchisi emas."""
    db = muhit['db']
    umumiy = muhit['umumiy']
    conn = db.get_conn()
    conn.execute('''
        INSERT INTO portfel (anketa_raqami, mijoz_nomi, mijoz_turi, pinfl,
                             asosiy_qarz, foiz_qarz, faol)
        VALUES ('10001', 'YOPILGAN KREDIT MIJOZI', 'Individual', '999', 0, 0, 1)
    ''')
    conn.commit()
    conn.close()
    assert umumiy.anketa_mijoz_nomi('10001') == mijoz['mijoz_nomi']


def test_papka_nomida_anketa_raqami_boladi(muhit, mijoz):
    """Bir mijozning bir necha anketasi bo'lsa, papkalar aralashmasligi
    uchun papka nomiga anketa raqami qo'shilishi kerak."""
    umumiy = muhit['umumiy']
    p1 = umumiy.sugurta_hujjatlari_mijoz_papkasi('TESTOV TEST', '10001')
    p2 = umumiy.sugurta_hujjatlari_mijoz_papkasi('TESTOV TEST', '10002')
    assert p1 != p2
    assert '10001' in p1 and '10002' in p2


# ── Arxiv: tarix yo'qolmasligi ───────────────────────────────────────

def test_nollashtirish_xatni_ochirmaydi_arxivlaydi(muhit, mijoz):
    """HAQIQIY MUAMMO: "Nollashtirish" avval yozuvlarni O'CHIRAR edi va
    o'tmish yig'ma jildlari tarixi yo'qolardi. Endi arxivlanadi."""
    db = muhit['db']
    xat_id = _xat_yaratish(db, mijoz, davo_ariza_fayl_yoli='/tmp/davo.docx')

    db.anketa_jarayonini_nollashtirish('10001')

    conn = db.get_conn()
    qator = conn.execute('SELECT * FROM xatlar WHERE id=?', (xat_id,)).fetchone()
    conn.close()
    assert qator is not None, "Xat o'chirib yuborilgan — tarix yo'qoldi"
    assert dict(qator)['arxivlangan'] == 1


def test_kredit_hujjatlar_arxivi_saqlanadi(muhit, mijoz):
    """Kredit hujjatlari doimiy arxivda saqlanib, keyingi sikllarda
    qayta topilishi kerak."""
    db = muhit['db']
    conn = db.get_conn()
    conn.execute('''INSERT INTO kredit_hujjatlar_arxiv
                    (anketa_raqami, kredit_shartnoma_fayl, yangilangan_sana)
                    VALUES ('10001', '/tmp/kredit.pdf', '2026-01-01')''')
    conn.commit()
    conn.close()

    db.anketa_jarayonini_nollashtirish('10001')

    conn = db.get_conn()
    a = conn.execute('SELECT * FROM kredit_hujjatlar_arxiv WHERE anketa_raqami=?',
                     ('10001',)).fetchone()
    conn.close()
    assert a is not None, "Nollashtirish doimiy arxivni ham o'chirib yubordi"
