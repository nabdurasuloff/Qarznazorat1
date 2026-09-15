@echo off
echo ============================================
echo   Backend (Python) - .exe yig'ish
echo ============================================

echo [1/3] Kerakli kutubxonalar o'rnatilmoqda...
python -m pip install -r requirements.txt

echo [2/3] backend.exe yig'ilmoqda...
pyinstaller --noconfirm --onefile --console ^
    --name "backend" ^
    --add-data "templates;templates" ^
    --collect-all "pyxlsb" ^
    --collect-all "openpyxl" ^
    --collect-all "docx2pdf" ^
    --collect-all "pypdf" ^
    --collect-all "flask" ^
    --collect-all "flask_cors" ^
    --hidden-import "win32com" ^
    --hidden-import "win32com.client" ^
    --hidden-import "win32timezone" ^
    --hidden-import "pythoncom" ^
    --hidden-import "pywintypes" ^
    --collect-all "win32com" ^
    server.py

echo [3/3] Tayyor!
echo Natija: dist\backend.exe
pause
