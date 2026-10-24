#!/bin/bash
set -e
cd "$(dirname "$0")"
python3 -m venv .build-env
.build-env/bin/python -m pip install 'pyinstaller>=6,<7' -r requirements.txt
.build-env/bin/python -m PyInstaller --noconfirm --clean --windowed --name ChuniVaina --osx-bundle-identifier com.chunivaina.studio --icon assets/ChuniVaina.icns --collect-all cricodecs --add-data 'templates:templates' --add-data 'assets:assets' app.py
echo 'Built: dist/ChuniVaina.app'
