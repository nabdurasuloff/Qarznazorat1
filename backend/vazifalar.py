# -*- coding: utf-8 -*-
"""
AQLLI YORDAMCHI — "Bugungi vazifalar".

Maqsad: xodim har bir bo'limni alohida ochib, kim qayerda qolganini
qidirib yurmasin. Tizim BARCHA bosqichlarni bir marta ko'rib chiqadi va
har bir mijoz uchun "keyingi qadam nima" degan savolga javob beradi,
muddati bo'yicha tartiblab.

Har bir vazifa uchta ustuvorlikdan birini oladi:
    kechikkan — muddat o'tib ketgan (qizil)
    bugun     — muddat bugun yoki 1-2 kun ichida tugaydi (sariq)
    rejali    — vaqt bor, lekin qilinishi kerak (kulrang)
"""
import datetime

import database as db


USTUVORLIK_TARTIBI = {'kechikkan': 0, 'bugun': 1, 'rejali': 2}

# "Chora ko'rish" ro'yxatidan kundalik vazifalarga nechta eng shoshilinch
# mijoz olinadi (qolganlari o'z bo'limida turaveradi).
CHORA_KORSATISH_SONI = 20

BOLIM_NOMLARI = {
    'talabnoma': 'Talabnoma',
    'davo_ariza': 'Davo Ariza',
    'biznes_hamroh': 'Biznes-hamroh',
    'sud': 'SUD Ishlari',
    'mib': 'MIB ijro harakatlari',
    'sugurta_undirish': "Sug'urtadan undirish",
    'vafot': 'Vafot etganlar',
    'chora': "Chora ko'rish",
}


def _sana_dt(qiymat):
    """Turli ko'rinishdagi sanani date obyektiga aylantiradi (bo'lmasa None)."""
    if not qiymat:
        return None
    if isinstance(qiymat, datetime.datetime):
        return qiymat.date()
    if isinstance(qiymat, datetime.date):
        return qiymat
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


def _ustuvorlik(qolgan_kun):
    """Muddatgacha qolgan kunga qarab ustuvorlikni aniqlaydi."""
    if qolgan_kun is None:
        return 'rejali'
    if qolgan_kun < 0:
        return 'kechikkan'
    if qolgan_kun <= 2:
        return 'bugun'
    return 'rejali'


def _qarz(prow):
    if not prow:
        return 0
    return (prow.get('asosiy_qarz') or 0) + (prow.get('foiz_qarz') or 0) + (prow.get('jarima') or 0)


def _vazifa(anketa, mijoz, bolim, vazifa, izoh='', qolgan_kun=None,
            qarz=0, pinfl_stir='', bosqich=''):
    return {
        'anketa_raqami': anketa, 'mijoz_nomi': mijoz, 'pinfl_stir': pinfl_stir,
        'qarz': qarz, 'bosqich': bosqich, 'vazifa': vazifa, 'izoh': izoh,
        'qolgan_kun': qolgan_kun, 'ustuvorlik': _ustuvorlik(qolgan_kun),
        'bolim': bolim, 'bolim_nomi': BOLIM_NOMLARI.get(bolim, bolim),
    }


def bugungi_vazifalar():
    """Barcha bosqichlarni ko'rib chiqib, bajarilishi kerak bo'lgan
    ishlar ro'yxatini qaytaradi (ustuvorlik va muddat bo'yicha
    tartiblangan)."""
    settings = db.get_all_settings()
    bugun = datetime.date.today()
    vazifalar = []
    # Bitta mijoz bir nechta ro'yxatda chiqib qolmasligi uchun: har bir
    # anketa uchun FAQAT eng ustuvor (eng shoshilinch) vazifa qoldiriladi.
    korilgan = {}

    def qosh(v):
        # MUHIM: QARZI QOLMAGAN mijozga huquqiy chora vazifasi
        # berilmaydi. Mijoz qarzini to'lab bo'lgan bo'lsa, unga qarshi
        # davo ariza tayyorlash, sudga topshirish yoki sug'urtadan
        # undirish — hammasi ma'nosiz va zararli. Tizim ilgari bunday
        # holatda ham eski bosqich bo'yicha vazifa berib turardi.
        # (Sud majlisi eslatmasi bundan mustasno — majlis baribir
        # bo'ladi va unga borish kerak.)
        if (v.get('qarz') or 0) <= 0 and v.get('bosqich') != 'Sud majlisi':
            return
        anketa = v['anketa_raqami']
        eski = korilgan.get(anketa)
        if eski is None:
            korilgan[anketa] = v
            vazifalar.append(v)
            return
        # Ustuvorligi yuqori bo'lsa — almashtiramiz
        if USTUVORLIK_TARTIBI[v['ustuvorlik']] < USTUVORLIK_TARTIBI[eski['ustuvorlik']]:
            vazifalar[vazifalar.index(eski)] = v
            korilgan[anketa] = v

    def prow_olish(portfel_id):
        return db.get_portfel_by_id(portfel_id) if portfel_id else None

    # ── 1. Sud majlisi yaqinlashgan (eng shoshilinch) ────────────────
    try:
        eslatmalar = db.sud_kunlari_eslatmalari()
        for turi, royxat in (('bugun', eslatmalar.get('bugun', [])),
                             ('ertaga', eslatmalar.get('ertaga', []))):
            for s in royxat:
                qosh(_vazifa(
                    s.get('anketa_raqami', ''), s.get('mijoz_nomi', ''), 'sud',
                    'Sud majlisi' + (' — BUGUN' if turi == 'bugun' else ' — ertaga'),
                    f"{s.get('sud_sanasi', '')} {s.get('sud_vaqti', '') or ''} · "
                    f"{s.get('sud_nomi', '') or ''}".strip(),
                    qolgan_kun=0 if turi == 'bugun' else 1,
                    bosqich='Sud majlisi'))
    except Exception:
        pass

    # ── 2. Xat tayyor, lekin yuborilmagan ───────────────────────────
    try:
        muddat = int(settings.get('eslatma_muddati_kun', 3))
        conn = db.get_conn()
        rows = conn.execute(
            "SELECT * FROM xatlar WHERE holat IN ('tayyor','muddati_otgan') "
            "AND (arxivlangan IS NULL OR arxivlangan=0) ORDER BY id DESC").fetchall()
        conn.close()
        for r in rows:
            x = dict(r)
            yaratilgan = _sana_dt(x.get('yaratilgan_sana'))
            qolgan = (yaratilgan + datetime.timedelta(days=muddat) - bugun).days if yaratilgan else None
            prow = prow_olish(x.get('portfel_id'))
            qosh(_vazifa(
                x['anketa_raqami'], x.get('mijoz_nomi', ''), 'talabnoma',
                'Xatni mijozga yuborish',
                f"Xat {yaratilgan.strftime('%d.%m.%Y') if yaratilgan else ''} da tayyorlangan",
                qolgan, _qarz(prow),
                (prow.get('pinfl') or prow.get('stir') or '') if prow else '',
                'Talabnoma'))
    except Exception:
        pass

    # ── 3. Davo ariza tayyorlanishi kerak ───────────────────────────
    try:
        tolov_muddat = int(settings.get('tolov_muddati_kun', 10))
        conn = db.get_conn()
        rows = conn.execute(
            "SELECT * FROM xatlar WHERE holat='yuborildi' "
            "AND (davo_ariza_fayl_yoli IS NULL OR davo_ariza_fayl_yoli='') "
            "AND (arxivlangan IS NULL OR arxivlangan=0) ORDER BY id DESC").fetchall()
        conn.close()
        for r in rows:
            x = dict(r)
            yuborilgan = _sana_dt(x.get('yuborilgan_sana'))
            if not yuborilgan:
                continue
            qolgan = (yuborilgan + datetime.timedelta(days=tolov_muddat) - bugun).days
            if qolgan > 0:
                continue    # to'lov muddati hali tugamagan — vazifa emas
            prow = prow_olish(x.get('portfel_id'))
            qosh(_vazifa(
                x['anketa_raqami'], x.get('mijoz_nomi', ''), 'davo_ariza',
                'Davo ariza tayyorlash',
                f"Xat {yuborilgan.strftime('%d.%m.%Y')} da yuborilgan, "
                f"to'lov muddati ({tolov_muddat} kun) tugadi",
                qolgan, _qarz(prow),
                (prow.get('pinfl') or prow.get('stir') or '') if prow else '',
                'Davo ariza'))
    except Exception:
        pass

    # ── 4. Portalga (biznes-hamroh) yuborilishi kerak ───────────────
    try:
        bh_muddat = int(settings.get('davo_ariza_muddati_kun', 5))
        for item in db.get_bh_royxati():
            x, m = item['xat'], (item['murojaat'] or {})
            holati = m.get('holati') or 'tayyorlanmoqda'
            # Portal QABUL qilgan bo'lsa — keyingi qadam sudga topshirish
            # (uni quyidagi 5-bo'lim beradi), bu yerda ish qolmadi.
            if holati == 'qabul_qilindi':
                continue
            # MUHIM (tuzatildi): ariza ALLAQACHON tasdiqlangan bo'lsa
            # (eski yo'l bilan SSPdan qaytgan), uni portalga yuborish
            # kerak emas — aks holda tizim tasdiqlangan arizani qayta
            # yuborishga undab, ikki marta ish qilinishiga olib kelardi.
            if x.get('davo_ariza_holati') == 'olib_kelindi' and holati == 'tayyorlanmoqda':
                continue
            prow = prow_olish(x.get('portfel_id'))
            asos_sana = _sana_dt(m.get('holat_sana')) or _sana_dt(x.get('davo_ariza_sana'))
            qolgan = (asos_sana + datetime.timedelta(days=bh_muddat) - bugun).days if asos_sana else None
            if holati == 'rad_etildi':
                # MUHIM (tuzatildi): rad etilgan murojaat ilgari HECH
                # QAYERDA eslatilmasdi — ish jimgina "yo'qolib" qolardi.
                # Endi u kechikkan vazifa sifatida ro'yxatda turadi.
                sabab = (m.get('natija_izoh') or '').strip()
                vazifa = 'Portal rad etdi — tuzatib qayta yuborish'
                izoh = (f"Sabab: {sabab}" if sabab else 'Rad etish sababi ko\'rsatilmagan') \
                    + f" (№{m.get('murojaat_raqami', '') or '—'})"
                # Rad etilgan ish kutib turmasligi kerak: rad etilgan KUNI
                # shoshilinch, undan keyin har kuni kechikish ortib boradi.
                rad_sana = _sana_dt(m.get('holat_sana'))
                qolgan = -(bugun - rad_sana).days if rad_sana else 0
            elif holati == 'tayyorlanmoqda':
                vazifa, izoh = ('Portalga (biznes-hamroh.uz) yuborish',
                                'Davo ariza tayyor, portalga hali yuborilmagan')
            else:
                vazifa, izoh = ("Portal javobini tekshirish",
                                f"№{m.get('murojaat_raqami', '') or '—'} — javob kutilmoqda")
            qosh(_vazifa(x['anketa_raqami'], x.get('mijoz_nomi', ''), 'biznes_hamroh',
                         vazifa, izoh, qolgan, _qarz(prow),
                         (prow.get('pinfl') or prow.get('stir') or '') if prow else '',
                         'Biznes-hamroh'))
    except Exception:
        pass

    # ── 5. Sudga topshirish kerak ───────────────────────────────────
    try:
        sud_muddat = int(settings.get('sud_topshirish_muddati_kun', 5))
        for x in db.get_sud_topshirish_kerak():
            imzo = _sana_dt(x.get('davo_ariza_imzo_sana'))
            qolgan = (imzo + datetime.timedelta(days=sud_muddat) - bugun).days if imzo else None
            prow = prow_olish(x.get('portfel_id'))
            ruxsat = bool(x.get('sud_hujjatlar_ruxsat'))
            # MUHIM: iqtisodiy sud ishlarida taraflarga yuborilganlik
            # tasdig'i majburiy — vazifada AYNAN shu yetishmayotgani
            # ko'rsatilsa, xodim nima qilish kerakligini darhol biladi.
            yetishmayotgan = [nomi for maydon, nomi in db.sud_majburiy_hujjatlar_royxati(x)
                              if not x.get(maydon)]
            qosh(_vazifa(
                x['anketa_raqami'], x.get('mijoz_nomi', ''), 'sud',
                'Sudga topshirish' if ruxsat else 'Hujjatlarni yig\'ib, ruxsat olish',
                'Ruxsat berilgan — topshirish mumkin' if ruxsat
                else (f"Yetishmayapti: {', '.join(yetishmayotgan)}" if yetishmayotgan
                      else "Yig'ma jild to'liq emas yoki ruxsat berilmagan"),
                qolgan, _qarz(prow),
                (prow.get('pinfl') or prow.get('stir') or '') if prow else '',
                'Sudga topshirish'))
    except Exception:
        pass

    # ── 6. MIBga o'tkazish kerak ────────────────────────────────────
    try:
        for x in db.get_mib_otkazish_kerak():
            topshirilgan = _sana_dt(x.get('sud_topshirilgan_sana'))
            # Sud qarori odatda 1-2 oyda chiqadi; 60 kundan oshsa — tekshirish kerak
            qolgan = (topshirilgan + datetime.timedelta(days=60) - bugun).days if topshirilgan else None
            prow = prow_olish(x.get('portfel_id'))
            qaror_bor = bool(x.get('sud_qaror_fayl') or x.get('sud_buyrugi_fayl'))
            qosh(_vazifa(
                x['anketa_raqami'], x.get('mijoz_nomi', ''), 'mib',
                "MIBga o'tkazish" if qaror_bor else 'Sud qarorini olish va yuklash',
                'Sud qarori yuklangan — ijro varaqasi bilan MIBga o\'tkazing' if qaror_bor
                else f"Sudga {topshirilgan.strftime('%d.%m.%Y') if topshirilgan else ''} da topshirilgan",
                qolgan, _qarz(prow),
                (prow.get('pinfl') or prow.get('stir') or '') if prow else '',
                'MIB'))
    except Exception:
        pass

    # ── 7. MIBda harakatsiz qolganlar ───────────────────────────────
    try:
        harakatsizlik_muddat = int(settings.get('mib_harakatsizlik_muddati_kun', 15))
        for x in db.get_mib_harakatsizlar():
            kun = x.get('harakatsizlik_kun')
            prow = prow_olish(x.get('portfel_id'))
            qosh(_vazifa(
                x['anketa_raqami'], x.get('mijoz_nomi', ''), 'mib',
                'MIB harakatini qilish',
                f"{kun} kundan beri harakat yo'q" if kun else 'Uzoq vaqt harakat qilinmagan',
                -(kun - harakatsizlik_muddat) if kun else None, _qarz(prow),
                (prow.get('pinfl') or prow.get('stir') or '') if prow else '',
                'MIB harakatlari'))
    except Exception:
        pass

    # ── 8. Sug'urtadan undirish (MIB qarori bo'yicha) ───────────────
    try:
        sug_muddat = int(settings.get('sugurta_undirish_muddat_kun', 30))
        for item in db.get_sugurta_undirish_royxati():
            x, u = item['xat'], (item['undirish'] or {})
            holati = u.get('holati') or 'tayyorlanmoqda'
            if holati in ('tolandi', 'rad_etildi'):
                continue
            prow = prow_olish(x.get('portfel_id'))
            # MUHIM (tuzatildi): MIB ishi QARZ TO'LANGANI uchun yakunlangan
            # bo'lsa (yoki qoldiq qarz qolmagan bo'lsa) — sug'urtadan
            # undiradigan narsa yo'q. Ilgari tizim bunday mijoz uchun ham
            # "sug'urtaga ariza bering" deb turardi, ya'ni to'langan qarzni
            # sug'urtadan qayta talab qilishga undardi.
            if _qarz(prow) <= 0 and holati == 'tayyorlanmoqda':
                continue
            if holati == 'yuborildi':
                ariza_sana = _sana_dt(u.get('ariza_sana'))
                qolgan = (ariza_sana + datetime.timedelta(days=sug_muddat) - bugun).days if ariza_sana else None
                vazifa = "Sug'urta javobini tekshirish"
                izoh = f"Ariza {u.get('ariza_sana', '')} da yuborilgan"
            else:
                qolgan = None
                asos_bor = bool(u.get('mib_asos_fayl'))
                # MUHIM (tuzatildi): sug'urtadan undirish uchun ASOS —
                # MIB "undirib bo'lmadi" degan hujjat chiqargani. Ish
                # MIBda HALI FAOL bo'lsa va bunday hujjat ham yo'q bo'lsa,
                # sug'urta haqida gapirish erta: avval MIB ijro
                # harakatlari qilinishi kerak. Aks holda tizim MIB ishini
                # endigina boshlaganda ham "sug'urtaga ariza bering" deb,
                # xodimni noto'g'ri yo'naltirardi.
                if not asos_bor and not x.get('mib_yakunlangan'):
                    continue
                vazifa = "Sug'urtaga ariza berish" if asos_bor else 'MIB asos hujjatini yuklash'
                izoh = ('Asos hujjat tayyor — arizani yuborishingiz mumkin' if asos_bor
                        else "MIB ishi yakunlangan — undirib bo'lmaganlik hujjatini yuklang")
            qosh(_vazifa(x['anketa_raqami'], x.get('mijoz_nomi', ''), 'sugurta_undirish',
                         vazifa, izoh, qolgan, _qarz(prow),
                         (prow.get('pinfl') or prow.get('stir') or '') if prow else '',
                         "Sug'urta (MIB)"))
    except Exception:
        pass

    # ── 9. Vafot etganlar bo'yicha sug'urta ─────────────────────────
    try:
        sug_muddat = int(settings.get('sugurta_undirish_muddat_kun', 30))
        for item in db.get_sugurta_vafot_royxati():
            v, u = item['vafot'], (item['undirish'] or {})
            holati = u.get('holati') or 'tayyorlanmoqda'
            if holati in ('tolandi', 'rad_etildi'):
                continue
            prow = prow_olish(v.get('portfel_id'))
            if holati == 'yuborildi':
                ariza_sana = _sana_dt(u.get('ariza_sana'))
                qolgan = (ariza_sana + datetime.timedelta(days=sug_muddat) - bugun).days if ariza_sana else None
                vazifa, izoh = ("Sug'urta javobini tekshirish",
                                f"Ariza {u.get('ariza_sana', '')} da yuborilgan")
            else:
                guvohnoma = bool(v.get('olimlik_guvohnomasi_fayl'))
                vafot_dt = _sana_dt(v.get('vafot_sanasi'))
                # Vafotdan keyin sug'urtaga murojaat kechiktirilmasligi kerak
                qolgan = (vafot_dt + datetime.timedelta(days=sug_muddat) - bugun).days if vafot_dt else None
                vazifa = ("Vafot bo'yicha sug'urta arizasini berish" if guvohnoma
                          else 'Vafot guvohnomasini yuklash')
                izoh = (f"Vafot sanasi: {v.get('vafot_sanasi', '')}" if guvohnoma
                        else "Guvohnomasiz ariza yuborib bo'lmaydi")
            qosh(_vazifa(v['anketa_raqami'], v.get('mijoz_nomi', ''), 'sugurta_undirish',
                         vazifa, izoh, qolgan, _qarz(prow),
                         (prow.get('pinfl') or prow.get('stir') or '') if prow else '',
                         "Sug'urta (vafot)"))
    except Exception:
        pass

    # ── 10. Chora ko'rish kerak (hali xat yozilmaganlar) ────────────
    # MUHIM: bu ro'yxat juda katta bo'lishi mumkin (butun muddati o'tgan
    # portfel — minglab mijoz). Agar hammasi qo'shilsa, kundalik vazifalar
    # ro'yxati ko'milib ketardi va jarayondagi HAQIQIY ishlar ko'rinmay
    # qolardi. Shu sabab bu yerdan faqat ENG SHOSHILINCH bir nechtasi
    # olinadi; qolganlari "Chora ko'rish" bo'limida turaveradi va ularning
    # soni alohida ko'rsatiladi.
    chora_jami = 0
    try:
        chora_royxati = db.get_chora_korish_royxati()
        qoshildi = 0
        for c in chora_royxati:
            prow = c.get('portfel') or {}
            anketa = prow.get('anketa_raqami') or c.get('anketa_raqami', '')
            if anketa in korilgan:
                continue    # bu mijoz uchun kuchliroq vazifa allaqachon bor
            chora_jami += 1
            if qoshildi >= CHORA_KORSATISH_SONI:
                continue
            qoshildi += 1
            qosh(_vazifa(
                anketa, prow.get('mijoz_nomi', ''), 'chora',
                c.get('chora_nomi') or "Chora ko'rish",
                c.get('tafsilot') or f"DPD {c.get('dpd', 0)} kun",
                None, _qarz(prow),
                prow.get('pinfl') or prow.get('stir') or '',
                "Chora ko'rish"))
    except Exception:
        pass

    # Tartiblash: avval kechikkanlar, keyin muddat yaqinlari; teng bo'lsa —
    # qarzi kattaroq mijoz yuqorida (ko'proq pul xavf ostida).
    vazifalar.sort(key=lambda v: (
        USTUVORLIK_TARTIBI[v['ustuvorlik']],
        v['qolgan_kun'] if v['qolgan_kun'] is not None else 9999,
        -(v['qarz'] or 0),
    ))
    # Ro'yxatga sig'maganlar soni — bosh sahifada "va yana N ta" deb
    # ko'rsatish uchun birinchi vazifaga biriktirib yuboriladi.
    if vazifalar:
        vazifalar[0]['_chora_jami'] = chora_jami
        vazifalar[0]['_chora_korsatildi'] = min(chora_jami, CHORA_KORSATISH_SONI)
    return vazifalar


def vazifalar_xulosasi(vazifalar=None):
    """Vazifalar bo'yicha qisqa statistika (bosh sahifa kartalari uchun)."""
    if vazifalar is None:
        vazifalar = bugungi_vazifalar()
    xulosa = {'jami': len(vazifalar), 'kechikkan': 0, 'bugun': 0, 'rejali': 0,
              'jami_qarz': 0, 'bolimlar': {},
              'chora_jami': (vazifalar[0].get('_chora_jami', 0) if vazifalar else 0),
              'chora_korsatildi': (vazifalar[0].get('_chora_korsatildi', 0) if vazifalar else 0)}
    for v in vazifalar:
        xulosa[v['ustuvorlik']] += 1
        xulosa['jami_qarz'] += v.get('qarz') or 0
        nomi = v['bolim_nomi']
        xulosa['bolimlar'][nomi] = xulosa['bolimlar'].get(nomi, 0) + 1
    return xulosa
