#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

rm -rf build dist Finence.spec

python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

python3 -m PyInstaller --clean --noconfirm --windowed --name Finence --icon app-icon.icns \
  --add-data "data/assets/icons:data/assets/icons" \
  --hidden-import PySide6 --hidden-import shiboken6 \
  --hidden-import PySide6.QtCore --hidden-import PySide6.QtGui \
  --hidden-import PySide6.QtWidgets --hidden-import PySide6.QtCharts \
  main.py

# Create a shareable zip that preserves macOS bundle metadata.
ditto -c -k --sequesterRsrc --keepParent "dist/Finence.app" "dist/Finence-mac.zip"

echo "Built: dist/Finence.app"
echo "Zipped: dist/Finence-mac.zip"


