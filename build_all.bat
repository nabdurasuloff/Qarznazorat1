@echo off
echo ================================================================
echo   QARZ NAZORAT — to'liq .exe yig'ish (backend + Electron)
echo ================================================================
echo.

echo [1/4] Backend (Python) .exe qilib yig'ilmoqda...
cd backend
call build_backend.bat
cd ..

if not exist "backend\dist\backend.exe" (
    echo.
    echo XATO: backend.exe yaratilmadi! Yuqoridagi xatolarni tekshiring.
    pause
    exit /b 1
)

echo.
echo [2/4] Electron kutubxonalari o'rnatilmoqda...
cd frontend
call npm install

echo.
echo [3/4] Final o'rnatuvchi (.exe) yig'ilmoqda...
call npm run build

echo.
echo [4/4] TAYYOR!
echo Natija: frontend\dist\QarzNazorat Setup 1.0.0.exe
echo.
echo ================================================================
echo   KEYINGI QADAM — eski bazangizni ulash:
echo   1. Yuqoridagi o'rnatuvchini ishga tushiring va o'rnating
echo   2. O'rnatilgan papkaga o'ting (masalan:
echo      C:\Users\SIZ\AppData\Local\Programs\QarzNazorat\resources\backend\)
echo   3. Eski "qarz_nazorat.db" faylingizni O'SHA PAPKAGA nusxalang
echo   4. Dasturni ishga tushiring — eski ma'lumotlaringiz bilan ochiladi
echo ================================================================
cd ..
pause
