#!/usr/bin/env bash

# Build Windows executable with PyInstaller (similar to build_macos_app.sh)
# Run this from Git Bash or WSL on Windows.

set -e
set -u
set -o pipefail 2>/dev/null || true

cd "$(dirname "$0")/.."

rm -rf build dist Finance.spec

python3 -m pip install -r requirements.txt
python3 -m pip install pyinstaller

# Note: on Windows, PyInstaller uses ';' to separate add-data paths.
python3 -m PyInstaller --clean --noconfirm --windowed --name Finance --icon app-icon.ico \
  --add-data "data/assets/icons;data/assets/icons" \
  --hidden-import PySide6 --hidden-import shiboken6 \
  --hidden-import PySide6.QtCore --hidden-import PySide6.QtGui \
  --hidden-import PySide6.QtWidgets --hidden-import PySide6.QtCharts \
  main.py

# Create a zip of the dist folder for easy sharing.
if command -v zip >/dev/null 2>&1; then
  (cd dist && zip -r ../Finance-win.zip Finance)
  echo "Zipped: dist/Finance-win.zip"
else
  echo "Zip utility not found; executable is in dist/Finance/"
fi

echo "Built: dist/Finance/"


