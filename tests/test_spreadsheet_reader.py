from datetime import date, datetime

import pytest

from finance.models.csv_expense_parser import CsvExpenseParser
from finance.models.spreadsheet_reader import _cell_to_str, file_to_csv_text


def test_cell_to_str_formats():
    assert _cell_to_str(datetime(2026, 1, 5)) == "05/01/2026"
    assert _cell_to_str(date(2026, 1, 5)) == "05/01/2026"
    assert _cell_to_str(200.0) == "200"  # whole float, no trailing .0
    assert _cell_to_str(120.5) == "120.5"
    assert _cell_to_str(None) == ""
    assert _cell_to_str("סופר") == "סופר"


def test_csv_is_passed_through_unchanged(tmp_path):
    p = tmp_path / "e.csv"
    p.write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    assert file_to_csv_text(p) == "a,b,c\n1,2,3\n"


def test_xlsx_expenses_flow_through_the_csv_parser(tmp_path):
    openpyxl = pytest.importorskip("openpyxl")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["תאריך עסקה", "שם בית העסק", "סכום חיוב"])
    ws.append([datetime(2026, 1, 5), "סופר", 120.5])
    ws.append([datetime(2026, 1, 10), "דלק", 200])
    path = tmp_path / "expenses.xlsx"
    wb.save(path)

    text = file_to_csv_text(path)
    assert "תאריך עסקה" in text  # header preserved for the parser to detect

    expenses = CsvExpenseParser().parse(text)
    assert [(e.date, e.description, e.amount) for e in expenses] == [
        ("2026-01-05", "סופר", -120.5),
        ("2026-01-10", "דלק", -200.0),
    ]


# Bank Leumi (and other Israeli issuers) hand out an HTML table saved as ``.xls``.
# It must load by *content*, not be trusted/rejected on its ``.xls`` extension.
_LEUMI_HTML = """<HTML dir="RTL"><head><meta charset="UTF-8"></head><body>
<table>
  <tr><td>פרוט עסקאות לכרטיס ויזה</td></tr>
</table>
<table>
  <tr>
    <th>תאריך העסקה</th><th>שם בית העסק</th><th>סכום העסקה</th>
    <th>סוג העסקה</th><th>פרטים</th><th>סכום חיוב</th>
  </tr>
  <tr>
    <td>29/07/26</td><td>סופרפארם מגדלי אלון</td><td>29.24</td>
    <td>עסקה רגילה</td><td></td><td>29.24</td>
  </tr>
  <tr>
    <td>16/07/26</td><td>רמי לוי - לוד</td><td>174.98</td>
    <td>עסקה רגילה</td><td></td><td>174.98</td>
  </tr>
  <tr><td></td><td></td><td></td><td></td><td>סה&quot;כ:</td><td>204.22</td></tr>
</table>
</body></HTML>"""


def test_html_export_saved_as_xls_loads_by_content(tmp_path):
    # Extension says .xls but the bytes are HTML — must still parse.
    path = tmp_path / "BankLeumi.xls"
    path.write_text(_LEUMI_HTML, encoding="utf-8")

    text = file_to_csv_text(path)
    expenses = CsvExpenseParser().parse(text)

    # The two real rows load; the title row and the סה"כ total are ignored.
    assert [(e.date, e.description, e.amount) for e in expenses] == [
        ("2026-07-29", "סופרפארם מגדלי אלון", -29.24),
        ("2026-07-16", "רמי לוי - לוד", -174.98),
    ]


def test_xlsx_bytes_saved_as_xls_loads_by_content(tmp_path):
    # A real .xlsx (ZIP) renamed to .xls must dispatch on the ZIP signature,
    # not the extension (which would send it to the xls reader and fail).
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["תאריך עסקה", "שם בית העסק", "סכום חיוב"])
    ws.append([datetime(2026, 1, 5), "סופר", 120.5])
    path = tmp_path / "mislabeled.xls"  # .xls extension, xlsx content
    wb.save(path)

    expenses = CsvExpenseParser().parse(file_to_csv_text(path))
    assert [(e.date, e.description, e.amount) for e in expenses] == [
        ("2026-01-05", "סופר", -120.5),
    ]


def test_xlsx_with_dash_dates_normalizes_to_iso(tmp_path):
    # The detailed-export xlsx writes dd-mm-yyyy dates as text; they must land
    # as ISO so mobile (ISO-only) can read them.
    openpyxl = pytest.importorskip("openpyxl")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["תאריך עסקה", "שם בית העסק", "קטגוריה", "סכום חיוב"])
    ws.append(["16-07-2026", "רמי לוי", "מזון", 174.98])
    ws.append(["29-07-2026", "איקאה", "בית", 139])
    path = tmp_path / "detailed.xlsx"
    wb.save(path)

    expenses = CsvExpenseParser().parse(file_to_csv_text(path))
    assert [(e.date, e.description, e.amount) for e in expenses] == [
        ("2026-07-16", "רמי לוי", -174.98),
        ("2026-07-29", "איקאה", -139.0),
    ]
