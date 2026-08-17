"""Write a sample expenses .xlsx (Hebrew credit-card statement shape) so you can
try the Excel import in the sandbox.

    python scripts/make_sample_expenses.py            # -> sample_expenses.xlsx
    python scripts/make_sample_expenses.py /tmp/x.xlsx
"""

from __future__ import annotations

import sys
from datetime import datetime

from openpyxl import Workbook

_ROWS = [
    (datetime(2026, 1, 3), "סופר פארם", 89.90),
    (datetime(2026, 1, 5), "רמי לוי", 342.10),
    (datetime(2026, 1, 8), "פז דלק", 250.00),
    (datetime(2026, 1, 12), "קפה ג׳ו", 34.50),
    (datetime(2026, 1, 20), "חשמל", 410.00),
]


def main() -> None:
    out = sys.argv[1] if len(sys.argv) > 1 else "sample_expenses.xlsx"
    wb = Workbook()
    ws = wb.active
    ws.title = "expenses"
    ws.append(["תאריך עסקה", "שם בית העסק", "סכום חיוב"])
    for d, name, amount in _ROWS:
        ws.append([d, name, amount])
    wb.save(out)
    print(f"wrote {out} ({len(_ROWS)} expenses)")


if __name__ == "__main__":
    main()
