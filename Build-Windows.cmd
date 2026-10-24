@echo off
setlocal
cd /d "%~dp0"
py -3 -m venv .build-env
if errorlevel 1 goto error
.build-env\Scripts\python.exe -m pip install "pyinstaller>=6,<7" -r requirements.txt
if errorlevel 1 goto error
.build-env\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --name ChuniVaina --icon assets\ChuniVaina.ico --collect-all cricodecs --add-data "templates;templates" --add-data "assets;assets" app.py
if errorlevel 1 goto error
echo Built: dist\ChuniVaina\ChuniVaina.exe
pause
exit /b 0
:error
echo Build stopped. See the error above.
pause
exit /b 1
