@echo off
REM ============================================================
REM  Ekranlarni tekshirish — har bir bo'lim ochiladimi?
REM  Avval backend ishga tushirilgan bo'lishi kerak.
REM ============================================================
cd /d "%~dp0"
echo.
echo  Ekranlar tekshirilmoqda (backend 5001-portda ishlashi kerak)...
echo.
python tests\ekranlarni_tekshirish.py
pause
