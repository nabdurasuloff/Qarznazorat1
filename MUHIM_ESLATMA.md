# MUHIM: Server sinovi haqida eslatma

Bu muhitda (Claude'ning ish konteyneri) har bir bash_tool chaqiruvi
YANGI, ALOHIDA konteynerda ishlaydi — background jarayonlar (masalan
`python3 server.py &`) BIR chaqiruvdan IKKINCHISIGA saqlanib qolmaydi.

Shuning uchun backend server sinovlarini har doim BITTA bash_tool
chaqiruvi ICHIDA — server ishga tushirish + barcha so'rovlar + natija
ko'rish — bajarish kerak.

To'g'ri namuna:
```bash
cd backend
PORT=8877 python3 server.py < /dev/null > /home/claude/srv.log 2>&1 &
sleep 2
curl -s http://127.0.0.1:8877/api/... 
```

Bu — HAQIQIY Windows'da .exe sifatida ishga tushirilganda MUAMMO EMAS
(u yerda Electron va Python server BIR marta, doimiy ishga tushadi).
Bu faqat SHU sinov muhitiga xos xususiyat.
