@echo off
REM ============================================================
REM  Qarz Nazorat — avtotestlar
REM  Har qanday o'zgarishdan KEYIN shuni ishga tushiring.
REM  Hammasi yashil bo'lsa — tizim ishlayapti.
REM ============================================================
cd /d "%~dp0"
echo.
echo  Testlar ishga tushirilmoqda...
echo.
python -m pytest tests -v
echo.
if %ERRORLEVEL% EQU 0 (
    echo  ============================================
    echo   HAMMASI JOYIDA - xatolik topilmadi
    echo  ============================================
) else (
    echo  ============================================
    echo   XATOLIK TOPILDI - yuqoridagi ro'yxatni ko'ring
    echo  ============================================
)
pause
