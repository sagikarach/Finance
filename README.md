## Finance — Qt Desktop App (PySide/PyQt)

Finance is a Qt-based desktop application scaffolded to support multiple pages. It ships with a Home page and a simple router. It prefers PySide6 but includes a compatibility layer that also works with PyQt6.

### Prerequisites

- Python 3.10+ (3.11 recommended)

### Setup

1. Create and activate a virtual environment:
   - macOS/Linux:
     ```bash
     python3 -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```bash
     python -m venv .venv
     .venv\Scripts\Activate.ps1
     ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Run

```bash
python main.py
```

### User data (safe across app updates)

Finance stores all user data **outside** the app bundle so you can replace/update the app without losing data.

- **macOS**: `~/Library/Application Support/Finance/`
  - Accounts JSON: `~/Library/Application Support/Finance/accounts/`
- On first launch, the app will migrate legacy `./data/accounts/*.json` into the per-user folder.

### Build macOS `.app` (unsigned, for personal use)

```bash
./scripts/build_macos_app.sh
```

Output:
- `dist/Finance.app` (double-clickable app)
- `dist/Finance-mac.zip` (easy to share)

### Notes

- The `finance/qt.py` module provides a small compatibility layer:
  - It tries to import PySide6 first.
  - If that fails, it falls back to PyQt6.
- Pages live under `finance/pages/`. Navigation is handled by a simple router in `finance/ui/router.py` using a `QStackedWidget`.

### Add a New Page (example)

1. Create a widget under `finance/pages/your_page.py`.
2. Register it in `MainWindow` via `self.router.register("your-route", lambda: YourPage(parent=self._stack))`.
3. Add a menu/toolbar action to navigate to the route with `self.router.navigate("your-route")`.
