# -*- coding: utf-8 -*-
"""
Qarz Nazorat — API server (kirish nuqtasi).

Bu fayl faqat ilovani yig'adi: Flask ilovasini yaratadi, bazani
tayyorlaydi, kunlik zaxira nusxani oladi va bo'limlarni (blueprint)
ro'yxatdan o'tkazadi.

Marshrutlarning O'ZI bo'limlar bo'yicha `yollar/` papkasida:
    yollar/sud.py, yollar/mib.py, yollar/sugurta.py, ...
Umumiy yordamchi funksiyalar — `umumiy.py` da.
Ish mantig'i esa avvalgidek: database.py, letters.py, importer.py, util.py.
"""
import os
import sys
from flask import Flask
from flask_cors import CORS

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import database as db

app = Flask(__name__)
# MUHIM: brauzer standart holatda faqat bir nechta "xavfsiz" sarlavhani
# JavaScript'ga ko'rsatadi. Yig'ma jild to'liqmas bo'lganda yuboriladigan
# ogohlantirish sarlavhasini frontend o'qiy olishi uchun uni alohida
# ochiq (expose) qilib qo'yish kerak.
CORS(app, expose_headers=['X-Jild-Ogohlantirish', 'Content-Disposition'])

db.init_db()

# MUHIM: dastur ishga tushganda, agar bugun hali zaxira nusxa olinmagan
# bo'lsa — darhol olinadi. Shunday qilib har ish kuni boshida bazaning
# butun nusxasi saqlanib qoladi, foydalanuvchi hech narsa qilmasa ham.
try:
    if db.zaxira_kerakmi():
        _z = db.zaxira_yaratish('kunlik')
        if _z:
            print(f"[zaxira] Kunlik zaxira nusxa olindi: {_z}")
except Exception as _e:
    print(f"[zaxira] Zaxira olishda xato (dastur ishlashda davom etadi): {_e}")



# ══ MARSHRUTLAR ══════════════════════════════════════════════════════
# Har bir bo'lim o'z faylida (yollar/ papkasi). Yangi bo'lim qo'shilganda
# uni shu yerga ham qo'shish kerak — aks holda marshrutlari ishlamaydi.
from yollar import (
    bh, chora, dashboard, davo, f95413, mib, portfel, shablon,
    sozlamalar, sud, sugurta, tahlil, talabnoma, tarix, vafot,
    vazifalar, zaxira,
)

BOLIMLAR = [
    bh.bp,
    chora.bp,
    dashboard.bp,
    davo.bp,
    f95413.bp,
    mib.bp,
    portfel.bp,
    shablon.bp,
    sozlamalar.bp,
    sud.bp,
    sugurta.bp,
    tahlil.bp,
    talabnoma.bp,
    tarix.bp,
    vafot.bp,
    vazifalar.bp,
    zaxira.bp,
]

for _bolim in BOLIMLAR:
    app.register_blueprint(_bolim)


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    # MUHIM: backend har doim '0.0.0.0' ga bog'lanadi — ya'ni shu
    # kompyuter tarmoqdagi boshqa kompyuterlar uchun ham "server" bo'la
    # oladi (agar ular shu kompyuterning IP manziliga ulansa). Bitta,
    # yagona kompyuterda ishlatilganda buning hech qanday farqi yo'q —
    # Windows Firewall baribir ruxsat so'raydi/yopadi, shuning uchun bu
    # xavfsiz standart holat.
    host = os.environ.get('BACKEND_HOST', '0.0.0.0')
    app.run(host=host, port=port, debug=False)
