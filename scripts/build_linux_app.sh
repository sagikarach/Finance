#!/usr/bin/env bash
# Build Linux executable with PyInstaller.

set -euo pipefail

cd "$(dirname "$0")/.."

rm -rf build dist Finance.spec

python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

icon_flag=""
if [[ -f "app-icon.ico" ]]; then
  icon_flag="--icon app-icon.ico"
elif [[ -f "app-icon.icns" ]]; then
  icon_flag="--icon app-icon.icns"
else
  echo "Warning: no app icon found, building without icon."
fi

python3 -m PyInstaller --clean --noconfirm --windowed --name Finance ${icon_flag} \
  --add-data "data/assets/icons:data/assets/icons" \
  --hidden-import PySide6 --hidden-import shiboken6 \
  --hidden-import PySide6.QtCore --hidden-import PySide6.QtGui \
  --hidden-import PySide6.QtWidgets --hidden-import PySide6.QtCharts \
  main.py

# Create a zip of the dist folder for easy sharing.
(cd dist && zip -r ../Finance-linux.zip Finance)
echo "Zipped: dist/Finance-linux.zip"
echo "Built: dist/Finance/"


