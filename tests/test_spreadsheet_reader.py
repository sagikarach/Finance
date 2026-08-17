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
