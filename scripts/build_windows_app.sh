#!/usr/bin/env bash

# Build Windows executable with PyInstaller (similar to build_macos_app.sh)
# Run this from Git Bash or WSL on Windows.

set -e
set -u
set -o pipefail 2>/dev/null || true

cd "$(dirname "$0")/.."

rm -rf build dist Finance.spec

# GitHub's Windows runners expose `python`, not always `python3`.
PY=python3
command -v python3 >/dev/null 2>&1 || PY=python

"$PY" -m pip install -r requirements.txt
"$PY" -m pip install pyinstaller
"$PY" scripts/write_firebase_defaults.py

icon_flag=""
if [[ -f "app-icon.ico" ]]; then
  icon_flag="--icon app-icon.ico"
else
  echo "Warning: app-icon.ico not found, building without a Windows icon."
fi

# Note: on Windows, PyInstaller uses ';' to separate add-data paths.
"$PY" -m PyInstaller --clean --noconfirm --windowed --name Finance ${icon_flag} \
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


