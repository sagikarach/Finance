### App icon (macOS + Windows)

You have `app-icon.icns` in the project root. That’s the correct format for **macOS app bundles**.

#### 1) During development (running with `python main.py`)
- Already implemented: the app now tries to load `app-icon.icns` (or `app-icon.ico`) and calls `QApplication.setWindowIcon(...)`.

#### 2) macOS installed app icon (Dock / Finder / `.app`)
If you build with **PyInstaller**, use:

```bash
pyinstaller --noconfirm --windowed --name Finence --icon app-icon.icns main.py
```

#### 3) Windows installed app icon (shortcut / taskbar / `.exe`)
Windows needs an **`.ico`** file (not `.icns`).

- Create `app-icon.ico` (same design), then build with:

```powershell
pyinstaller --noconfirm --windowed --name Finence --icon app-icon.ico main.py
```

#### Notes
- Without signing, Windows will still show warnings; the icon will still work.
- If you bundle files, make sure `app-icon.icns` / `app-icon.ico` is included in the build output (PyInstaller `--add-data` / spec file). The runtime code looks for it in the bundle too.


