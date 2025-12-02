## Finence — Qt Desktop App (PySide/PyQt)

Finence is a Qt-based desktop application scaffolded to support multiple pages. It ships with a Home page and a simple router. It prefers PySide6 but includes a compatibility layer that also works with PyQt6.

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

### User data (accounts.json)

- The Home page loads accounts from a JSON file at the project root: `accounts.json`.
- Edit this file to update your data; the app will reflect totals and the pie chart.
- Format:
  ```json
  [
    {
      "name": "Checking",
      "is_liquid": true,
      "history": [
        { "date": "2025-01-01", "amount": 2100.0 },
        { "date": "2025-02-01", "amount": 2450.0 }
      ]
    }
  ]
  ```
  - `name`: string
  - `is_liquid`: boolean
  - `history` (optional): array of `{ "date": ISO date string, "amount": number }`
  - `amount` (optional): number (float). If `history` is present, the app uses the latest snapshot by date as the current amount.

### Notes

- The `finence/qt.py` module provides a small compatibility layer:
  - It tries to import PySide6 first.
  - If that fails, it falls back to PyQt6.
- Pages live under `finence/pages/`. Navigation is handled by a simple router in `finence/ui/router.py` using a `QStackedWidget`.

### Add a New Page (example)

1. Create a widget under `finence/pages/your_page.py`.
2. Register it in `MainWindow` via `self.router.register("your-route", lambda: YourPage(parent=self._stack))`.
3. Add a menu/toolbar action to navigate to the route with `self.router.navigate("your-route")`.
