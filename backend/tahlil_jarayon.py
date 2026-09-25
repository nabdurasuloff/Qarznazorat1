# -*- coding: utf-8 -*-
"""
HUQUQIY JARAYON TAHLILI.

Mavjud "Tahlil" bo'limi PORTFELNI (tarmoq, stage, EAD) tahlil qiladi.
Bu modul esa ISHNING O'ZINI tahlil qiladi:

  • Voronka        — hozir qaysi bosqichda nechta mijoz va qancha pul turibdi
  • Davomiylik     — har bir bosqich o'rtacha necha kun olayapti (qayerda tiqilib qolgan)
  • Undirish       — qaysi yo'l bilan qancha pul qaytdi (MIB, sug'urta, ixtiyoriy to'lov)
  • Oylik dinamika — oylar bo'yicha ish hajmi va qaytgan pul
  • Harakatlar     — qaysi MIB harakati amalda ko'proq pul qaytarayapti
"""
import datetime
import statistics

import database as db


def _sana_dt(qiymat):
    if not qiymat:
        return None
    matn = str(qiymat).strip()
    for fmt in ('%d.%m.%Y', '%Y-%m-%d'):
        try:
            return datetime.datetime.strptime(matn[:10], fmt).date()
        except ValueError:
            continue
    try:
        return datetime.datetime.fromisoformat(matn).date()
    except ValueError:
        return None


def _kun_farqi(boshlanish, tugash):
    a, b = _sana_dt(boshlanish), _sana_dt(tugash)
    if not a or not b:
        return None
    kun = (b - a).days
    # Manfiy yoki aqlga sig'maydigan (10 yildan ortiq) farq — sana
    # xato kiritilgan degani, hisobga olinmaydi.
    return kun if 0 <= kun <= 3650 else None


def _statistika(kunlar):
    """Kunlar ro'yxatidan o'rtacha / mediana / eng uzun qiymatlarni beradi."""
    kunlar = [k for k in kunlar if k is not None]
    if not kunlar:
        return {'soni': 0, 'ortacha': 0, 'mediana': 0, 'eng_uzun': 0}
    return {
        'soni': len(kunlar),
        'ortacha': round(statistics.mean(kunlar), 1),
        'mediana': round(statistics.median(kunlar), 1),
        'eng_uzun': max(kunlar),
    }


# ── 1. VORONKA: hozir qayerda nechta ish turibdi ────────────────────

def voronka():
    """Har bir bosqichda hozir nechta mijoz va qancha qarz turganini
    qaytaradi. Voronkaning qayerida ish tiqilib qolganini ko'rsatadi."""
    conn = db.get_conn()
    xatlar = [dict(r) for r in conn.execute(
        'SELECT * FROM xatlar WHERE arxivlangan IS NULL OR arxivlangan=0').fetchall()]
    conn.close()

    # Qarz summalarini bitta so'rov bilan olamiz (har biri uchun alohida
    # so'rov qilinsa, minglab ish bo'lganda sekinlashardi).
    portfel_ids = {x.get('portfel_id') for x in xatlar if x.get('portfel_id')}
    qarzlar = {}
    if portfel_ids:
        conn = db.get_conn()
        placeholders = ','.join('?' * len(portfel_ids))
        for r in conn.execute(
                f'SELECT id, asosiy_qarz, foiz_qarz, jarima FROM portfel '
                f'WHERE id IN ({placeholders})', list(portfel_ids)).fetchall():
            qarzlar[r['id']] = (r['asosiy_qarz'] or 0) + (r['foiz_qarz'] or 0) + (r['jarima'] or 0)
    conn = None

    bosqichlar = [
        ('xat_tayyor', 'Xat tayyorlangan',
         lambda x: x.get('holat') in ('tayyor', 'muddati_otgan')),
        ('xat_yuborilgan', 'Xat yuborilgan, davo ariza yo\'q',
         lambda x: x.get('holat') == 'yuborildi' and not x.get('davo_ariza_fayl_yoli')),
        ('davo_tayyor', "Davo ariza tayyorlangan",
         lambda x: x.get('davo_ariza_fayl_yoli') and x.get('davo_ariza_holati') != 'olib_kelindi'
                   and x.get('sud_holati') != 'topshirildi'),
        ('sudga_tayyor', 'Tasdiqlangan — sudga topshirish kutilmoqda',
         lambda x: x.get('davo_ariza_holati') == 'olib_kelindi'
                   and x.get('sud_holati') != 'topshirildi'
                   and not (x.get('sud_kiritilmadi_sababi') or '')),
        ('sudda', 'Sudda — qaror kutilmoqda',
         lambda x: x.get('sud_holati') == 'topshirildi'
                   and not (x.get('sud_qaror_fayl') or x.get('sud_buyrugi_fayl'))
                   and x.get('mib_holati') != 'otkazildi'),
        ('qaror_bor', "Sud qarori bor — MIBga o'tkazish kerak",
         lambda x: (x.get('sud_qaror_fayl') or x.get('sud_buyrugi_fayl'))
                   and x.get('mib_holati') != 'otkazildi'),
        ('mibda', 'MIBda ijro jarayonida',
         lambda x: x.get('mib_holati') == 'otkazildi' and not x.get('mib_yakunlangan')),
        ('mib_yakunlangan', 'MIB ishi yakunlangan',
         lambda x: x.get('mib_holati') == 'otkazildi' and x.get('mib_yakunlangan')),
    ]

    natija = []
    for kod, nomi, shart in bosqichlar:
        moslar = [x for x in xatlar if shart(x)]
        summa = sum(qarzlar.get(x.get('portfel_id'), 0) for x in moslar)
        natija.append({'kod': kod, 'nomi': nomi, 'soni': len(moslar), 'summa': summa})
    return natija


# ── 2. BOSQICHLAR DAVOMIYLIGI: qayerda vaqt yo'qolyapti ────────────

def bosqich_davomiyligi():
    """Har bir o'tish uchun necha kun ketganini hisoblaydi.
    Bu — jarayonning "tor joyi" qayerda ekanini ko'rsatadi."""
    conn = db.get_conn()
    xatlar = [dict(r) for r in conn.execute('SELECT * FROM xatlar').fetchall()]
    conn.close()

    otishlar = [
        ('xat_davo', "Xat yuborildi → Davo ariza tayyorlandi",
         'yuborilgan_sana', 'davo_ariza_sana'),
        ('davo_tasdiq', "Davo ariza → Tasdiqlanib qaytdi",
         'davo_ariza_sana', 'davo_ariza_imzo_sana'),
        ('tasdiq_sud', "Tasdiqlandi → Sudga topshirildi",
         'davo_ariza_imzo_sana', 'sud_topshirilgan_sana'),
        ('sud_qaror', "Sudga topshirildi → Qaror chiqdi",
         'sud_topshirilgan_sana', 'sud_qaror_sana'),
        ('qaror_mib', "Sud qarori → MIBga o'tkazildi",
         'sud_qaror_sana', 'mib_otkazilgan_sana'),
        ('mib_yakun', "MIBga o'tkazildi → Ish yakunlandi",
         'mib_otkazilgan_sana', 'mib_yakunlangan_sana'),
    ]

    natija = []
    for kod, nomi, boshi, oxiri in otishlar:
        kunlar = [_kun_farqi(x.get(boshi), x.get(oxiri)) for x in xatlar]
        st = _statistika(kunlar)
        st.update({'kod': kod, 'nomi': nomi})
        natija.append(st)

    # To'liq yo'l: xat yuborilgandan MIB yakunlanguncha
    toliq = [_kun_farqi(x.get('yuborilgan_sana'), x.get('mib_yakunlangan_sana'))
             for x in xatlar]
    st = _statistika(toliq)
    st.update({'kod': 'toliq', 'nomi': "To'liq yo'l: Xat → Ish yakuni"})
    natija.append(st)
    return natija


# ── 3. UNDIRISH: qaysi yo'l bilan qancha pul qaytdi ────────────────

def undirish_samaradorligi():
    """Qaytgan pulni manbalar bo'yicha ajratadi."""
    conn = db.get_conn()

    mib = conn.execute('''
        SELECT COALESCE(SUM(COALESCE(undirilgan_summa,0)),0) AS ish_haqi,
               COALESCE(SUM(COALESCE(sotilgan_summasi,0)),0) AS sotish,
               COALESCE(SUM(COALESCE(auksion_narxi,0)),0)   AS auksion
        FROM mib_amallar''').fetchone()

    sugurta = conn.execute('''
        SELECT COALESCE(SUM(COALESCE(tolangan_summa,0)),0) AS summa,
               COUNT(*) AS soni
        FROM sugurta_undirish WHERE holati='tolandi' ''').fetchone()

    sugurta_turi = {}
    for r in conn.execute('''
            SELECT COALESCE(tur,'mib') AS tur,
                   COALESCE(SUM(COALESCE(tolangan_summa,0)),0) AS summa,
                   COUNT(*) AS soni
            FROM sugurta_undirish WHERE holati='tolandi' GROUP BY COALESCE(tur,'mib')''').fetchall():
        sugurta_turi[r['tur']] = {'summa': r['summa'], 'soni': r['soni']}

    try:
        tolovlar = conn.execute('''
            SELECT COALESCE(SUM(COALESCE(summa,0)),0) AS summa, COUNT(*) AS soni
            FROM tolovlar WHERE holati='tasdiqlangan' ''').fetchone()
        tolov_summa, tolov_soni = tolovlar['summa'], tolovlar['soni']
    except Exception:
        tolov_summa, tolov_soni = 0, 0
    conn.close()

    manbalar = [
        {'kod': 'ish_haqi', 'nomi': "MIB — ish haqiga qaratish", 'summa': mib['ish_haqi']},
        {'kod': 'sotish', 'nomi': "MIB — mulk sotish", 'summa': mib['sotish']},
        {'kod': 'auksion', 'nomi': 'MIB — auksion', 'summa': mib['auksion']},
        {'kod': 'sugurta_mib', 'nomi': "Sug'urta — MIB qarori bo'yicha",
         'summa': sugurta_turi.get('mib', {}).get('summa', 0)},
        {'kod': 'sugurta_vafot', 'nomi': "Sug'urta — vafot bo'yicha",
         'summa': sugurta_turi.get('vafot', {}).get('summa', 0)},
        {'kod': 'tolov', 'nomi': "Ixtiyoriy to'lovlar", 'summa': tolov_summa},
    ]
    jami = sum(m['summa'] for m in manbalar)
    for m in manbalar:
        m['ulush'] = round(m['summa'] / jami * 100, 1) if jami else 0
    manbalar.sort(key=lambda m: -m['summa'])
    return {'manbalar': manbalar, 'jami': jami,
            'sugurta_soni': sugurta['soni'], 'tolov_soni': tolov_soni}


# ── 4. OYLIK DINAMIKA ───────────────────────────────────────────────

def oylik_dinamika(oylar=12):
    """So'nggi N oy bo'yicha: nechta xat yuborilgan, nechta ish sudga
    kiritilgan, nechta MIBga o'tkazilgan va qancha pul qaytgan."""
    bugun = datetime.date.today()
    # Oy kalitlari (eskisidan yangisiga)
    kalitlar = []
    yil, oy = bugun.year, bugun.month
    for _ in range(oylar):
        kalitlar.append((yil, oy))
        oy -= 1
        if oy == 0:
            oy = 12
            yil -= 1
    kalitlar.reverse()

    OY_NOMLARI = ['yan', 'fev', 'mar', 'apr', 'may', 'iyn',
                  'iyl', 'avg', 'sen', 'okt', 'noy', 'dek']
    natija = {(y, o): {'oy': f"{OY_NOMLARI[o-1]} {str(y)[2:]}",
                       'xat': 0, 'sud': 0, 'mib': 0, 'undirilgan': 0}
              for (y, o) in kalitlar}

    def qosh(sana, maydon, qiymat=1):
        d = _sana_dt(sana)
        if not d:
            return
        kalit = (d.year, d.month)
        if kalit in natija:
            natija[kalit][maydon] += qiymat

    conn = db.get_conn()
    for r in conn.execute(
            'SELECT yuborilgan_sana, sud_topshirilgan_sana, mib_otkazilgan_sana '
            'FROM xatlar').fetchall():
        qosh(r['yuborilgan_sana'], 'xat')
        qosh(r['sud_topshirilgan_sana'], 'sud')
        qosh(r['mib_otkazilgan_sana'], 'mib')

    for r in conn.execute(
            'SELECT amal_sanasi, COALESCE(undirilgan_summa,0) + COALESCE(sotilgan_summasi,0) '
            '+ COALESCE(auksion_narxi,0) AS summa FROM mib_amallar').fetchall():
        if r['summa']:
            qosh(r['amal_sanasi'], 'undirilgan', r['summa'])

    for r in conn.execute(
            "SELECT tolov_sana, COALESCE(tolangan_summa,0) AS summa "
            "FROM sugurta_undirish WHERE holati='tolandi'").fetchall():
        if r['summa']:
            qosh(r['tolov_sana'], 'undirilgan', r['summa'])
    conn.close()

    return [natija[k] for k in kalitlar]


# ── 5. MIB HARAKATLARI SAMARADORLIGI ───────────────────────────────

def harakat_samaradorligi():
    """Qaysi MIB harakati amalda ko'proq pul qaytarganini ko'rsatadi —
    kelgusida qaysi choraga kuch sarflashni tanlash uchun."""
    conn = db.get_conn()
    rows = conn.execute('''
        SELECT amal_turi,
               COUNT(*) AS soni,
               COALESCE(SUM(COALESCE(undirilgan_summa,0) + COALESCE(sotilgan_summasi,0)
                            + COALESCE(auksion_narxi,0)), 0) AS summa
        FROM mib_amallar
        GROUP BY amal_turi
        ORDER BY summa DESC''').fetchall()
    conn.close()
    natija = []
    for r in rows:
        soni = r['soni'] or 0
        natija.append({
            'amal_turi': r['amal_turi'] or "Noma'lum",
            'soni': soni, 'summa': r['summa'] or 0,
            'ortacha': round((r['summa'] or 0) / soni) if soni else 0,
        })
    return natija


# ── Hammasini birga ────────────────────────────────────────────────

def toliq_hisobot():
    return {
        'voronka': voronka(),
        'davomiylik': bosqich_davomiyligi(),
        'undirish': undirish_samaradorligi(),
        'dinamika': oylik_dinamika(),
        'harakatlar': harakat_samaradorligi(),
        'sana': datetime.date.today().strftime('%d.%m.%Y'),
    }
