# QARZ NAZORAT (Web/Electron versiyasi) — .exe qilib yig'ish va eski bazani ulash

## Kerakli dasturlar (kompyuteringizda oldindan o'rnatilgan bo'lishi kerak)

1. **Python** (3.10+) — https://www.python.org/downloads/ dan
   - O'rnatishda **"Add Python to PATH"** katakchasini albatta belgilang
2. **Node.js** (18+) — https://nodejs.org dan (LTS versiyani tanlang)

---

## 1-QADAM: To'liq yig'ish

`qarz_nazorat_web` papkasini kompyuteringizga oching, so'ng ichidagi
**`build_all.bat`** faylini ikki marta bosib ishga tushiring.

Bu skript avtomatik:
1. Python backend'ni (`backend.exe`) yig'adi
2. Electron kutubxonalarini o'rnatadi (birinchi safar internetdan yuklab oladi, biroz vaqt olishi mumkin)
3. Yakuniy o'rnatuvchi faylni (`QarzNazorat Setup 1.0.0.exe`) tayyorlaydi

**Natija:** `frontend\dist\QarzNazorat Setup 1.0.0.exe`

---

## 2-QADAM: Dasturni o'rnatish

1. `QarzNazorat Setup 1.0.0.exe` faylini ishga tushiring
2. O'rnatish joyini tanlang (masalan: `C:\QarzNazorat` — ixtiyoriy joy tanlashingiz mumkin, "Program Files" shart emas)
3. O'rnatish tugagach, dastur **hali ochilmasin** — avval eski bazangizni ulashimiz kerak

---

## 3-QADAM: Eski bazangizni ulash (ENG MUHIM QADAM)

O'rnatilgan papkaga o'ting:
```
<siz tanlagan joy>\resources\backend\
```
Masalan: `C:\QarzNazorat\resources\backend\`

U yerda **`backend.exe`** faylini ko'rasiz. Eski dasturingizdagi
**`qarz_nazorat.db`** faylingizni nusxalab, **aynan shu papkaga** joylashtiring
(backend.exe bilan bir qatorda).

```
resources\backend\
   ├── backend.exe
   ├── qarz_nazorat.db     <-- SIZ BU YERGA QO'YASIZ
   └── templates\
```

---

## 4-QADAM: Ishga tushirish

Endi dasturni oddiy ishga tushiring — masalan ish stolidagi yorliqdan.
Dastur ochilganda, **eski ma'lumotlaringiz** (portfel, xatlar, mijozlar va h.k.)
bilan ishga tushadi.

---

## Muhim eslatmalar

- **Zaxira nusxa:** ishga tushirishdan oldin `qarz_nazorat.db` faylingizning
  zaxira nusxasini boshqa joyga saqlab qo'ying (ehtiyot chorasi uchun).
- **Yangilash:** kelajakda dastur yangilansa, faqat `resources\backend\` va
  boshqa dastur fayllarini yangilang — `qarz_nazorat.db` faylingizga tegmang,
  u har doim shu joyda, o'zgarishsiz qolaveradi.
- **Xatolik yuz bersa:** dastur ochilmasa yoki ma'lumot ko'rinmasa, ushbu
  papkadagi ma'lumotlarni tekshiring:
  `%APPDATA%\QarzNazorat\` (agar log fayllari bo'lsa)
