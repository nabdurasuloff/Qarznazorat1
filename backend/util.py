# -*- coding: utf-8 -*-
"""
main.py va importer.py ikkalasida ham kerak bo'ladigan umumiy funksiyalar.
"""
import re
import database as db

# Bank eksport faylida mijoz F.I.Sh oldiga QO'SHILIB QOLADIGAN, ba'zan
# takrorlanib yoki boshqa mijoz bilan chalkashib ketadigan prefikslar.
# Bular BAZADA saqlanadigan F.I.Sh dan olib tashlanadi (qidiruv/moslashtirish
# to'g'ri ishlashi uchun); rasmiy hujjatlarda kerak bo'lsa,
# `mijoz_ism_hujjat_uchun()` orqali "YaTT" alohida, nazorat ostida qayta
# qo'shiladi.
_ISM_PREFIKSLARI = [
    r'^ЯТТ\s*', r'^YATT\s*', r'^YaTT\s*', r'^YTT\s*',
    r'^ЯККА ТАРТИБДАГИ ТАДБИРКОР\s*', r'^YAKKA TARTIBDAGI TADBIRKOR\s*',
]


def clean_mijoz_ism(ism):
    """
    Mijoz F.I.Sh dagi "YATT"/"ЯТТ" kabi tashkiliy-huquqiy shakl
    prefikslarini olib tashlaydi — bular hujjatlarda (xat, Davo ariza,
    yig'ma jild) F.I.Sh oldida ko'rinib qolmasligi kerak. Ba'zan ikkita
    prefiks ustma-ust yozilgan bo'ladi (masalan "YATT ЯТТ ..."), shu sabab
    hech qanday prefiks qolmaguncha takroriy tozalanadi.
    """
    if not ism:
        return ism
    natija = str(ism).strip()
    while True:
        oldingi = natija
        for pattern in _ISM_PREFIKSLARI:
            natija = re.sub(pattern, '', natija, flags=re.IGNORECASE).strip()
        if natija == oldingi:
            break
    return natija


def mijoz_ism_hujjat_uchun(ism, turi):
    """
    Rasmiy hujjat (xat, Davo ariza, yig'ma jild tituli) uchun mijoz nomini
    tayyorlaydi. Bazada F.I.Sh har doim TOZA (prefikssiz) saqlanadi — bu
    qidiruv/moslashtirish uchun kerak. Lekin YaTT (yakka tartibdagi
    tadbirkor) mijozlar uchun rasmiy hujjatlarda huquqiy maqomni
    ko'rsatish talab qilinadi, shu sabab "YaTT" so'zi hujjat darajasida
    (faqat ko'rsatish/chop etish vaqtida) qayta qo'shiladi.
    """
    if turi == 'yatt' and ism:
        return f"YaTT {ism}"
    return ism


def mijoz_hujjat_id(portfel_row, turi=None):
    """
    Mijozning hujjat identifikatorini qaytaradi — jismoniy shaxs uchun
    PINFL, yuridik shaxs (yoki YaTT) uchun STIR. Excel eksportlarida
    "PINFL" ustuniga faqat jismoniy shaxslar PINFL'i yozilib, yuridik/YaTT
    mijozlarning STIR raqami bo'sh qolib ketmasligi uchun ishlatiladi.
    """
    if turi is None:
        turi = turi_kodidan(portfel_row.get('mijoz_turi_kodi'), portfel_row.get('mijoz_turi'))
    if turi in ('yuridik', 'yatt'):
        stir = portfel_row.get('stir')
        if stir and str(stir).strip('0') != '':
            return str(stir).strip()
        # STIR bo'sh/soxta bo'lsa, baribir PINFL bilan almashtirib qo'yamiz
        # (YaTT holatida ba'zan faqat PINFL to'ldirilgan bo'ladi)
        return str(portfel_row.get('pinfl') or '').strip()
    return str(portfel_row.get('pinfl') or '').strip()


def turi_kodidan(mijoz_turi_kodi, mijoz_turi):
    """
    Jismoniy/yuridik/YaTT ekanini aniqlaydi. Asosiy manba — portfeldagi
    "Мижоз тури" ustuni ('LE' / 'Individual'), bu eng ishonchli maydon.

    Diqqat: "Жис/юр/Ятт коди" raqamli kodi ("mijoz_turi_kodi") mustaqil
    ishonchli belgi EMAS — tekshiruv shuni ko'rsatdiki, kod=8 (asosiy
    jismoniy) va kod=11 (YaTT) Individual'ga, kod=9 esa aslida YURIDIK
    (LE) ga to'g'ri keladi (2, 3, 7, 10, 12 kodlari ham barchasi LE).
    Shu sabab bu yerda faqat 'LE' matn qiymati tekshiriladi — FAQAT
    kod=11 (YaTT) bundan mustasno: garchi bank uni "Individual" deb
    belgilagan bo'lsa-da (chunki YaTT shaxsan jismoniy shaxs), YaTT
    tadbirkorlik faoliyati yuritgani uchun huquqiy jihatdan (xat turi,
    sud turi, Davo ariza turi) YURIDIK shaxsga o'xshab ko'riladi —
    nizolari odatda iqtisodiy sudda ko'riladi, fuqarolik sudida emas.
    Shu sabab alohida 'yatt' turi qaytariladi (kerakli joylarda
    `yuridik_kabi()` orqali yuridikka teng deb hisoblanadi).
    """
    turi = str(mijoz_turi or '').strip().upper()
    if turi == 'LE':
        return 'yuridik'
    kod = str(mijoz_turi_kodi or '').strip()
    if kod == '11':
        return 'yatt'
    return 'jismoniy'


def yuridik_kabi(turi):
    """
    Xat turi, sud turi, Davo ariza turi kabi HUQUQIY qarorlar uchun —
    yuridik shaxs VA YaTT ikkalasi ham "yuridik" kabi ko'riladi (garchi
    YaTT shaxsan jismoniy shaxs bo'lsa-da). Faqat statistik hisoblarda
    (Tahlil bo'limidagi jismoniy/yuridik soni kabi) bu funksiya
    ISHLATILMAYDI — u yerda haqiqiy shaxs turi (portfeldagi LE/Individual)
    ishlatiladi, chunki YaTT baribir jismoniy shaxs sifatida sanaladi.
    """
    return turi in ('yuridik', 'yatt')


def kalit_candidates(portfel_row):
    """
    Mijozni bog'lash uchun ishlatilishi mumkin bo'lgan ID'lar ro'yxati.

    MUHIM: bank eksport faylida jismoniy shaxslarning STIR maydoni ko'pincha
    "0" (bo'sh/placeholder qiymat) bo'lib to'ldiriladi — bu esa haqiqiy
    identifikator EMAS. Agar buni filtlamasak, "0" kalitiga ega BOSHQA
    (tasodifiy) mijoz Mijozlar bazasida topilib, unga noto'g'ri bog'lanib
    qolish xavfi bor (masalan xat/yig'ma jild boshqa odamning F.I.Sh bilan
    chiqib qolishi mumkin). Shu sabab bunday "soxta" qiymatlar chiqarib
    tashlanadi.
    """
    xom = [portfel_row.get('pinfl'), portfel_row.get('stir'), portfel_row.get('unikal')]
    natija = []
    for val in xom:
        if not val:
            continue
        val_str = str(val).strip()
        # "0", "00...0", bo'sh qatorlar — haqiqiy identifikator emas
        if not val_str or val_str.strip('0') == '':
            continue
        natija.append(val_str)
    return natija


def resolve_mijoz(portfel_row):
    """Portfel qatoriga mos mijozni (agar bazada bo'lsa) topadi. Topilgan
    (yoki topilmagan holda portfeldan olingan) F.I.Sh har doim "YATT" kabi
    prefikslardan tozalangan holda qaytariladi."""
    turi = turi_kodidan(portfel_row.get('mijoz_turi_kodi'), portfel_row.get('mijoz_turi'))
    for kalit in kalit_candidates(portfel_row):
        if not kalit:
            continue
        kalit = str(kalit).strip()
        m = db.find_mijoz(turi, kalit)
        if m:
            m = dict(m)
            m['ism'] = clean_mijoz_ism(m.get('ism'))
            return turi, m
    return turi, None
