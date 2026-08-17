"""Read an expenses file into CSV text so the existing CSV parser can handle it.

Lets the import flow accept Excel (.xlsx / .xls) as well as .csv: a spreadsheet's
first sheet is flattened into the same comma-separated shape the parser already
understands, so all formats share one code path. openpyxl (.xlsx) / xlrd (.xls)
are optional deps imported lazily.
"""

from __future__ import annotations

import csv
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from typing import Any, Iterable, Sequence


def _cell_to_str(value: Any) -> str:
    """Render a spreadsheet cell the way the CSV parser expects: dates as
    dd/mm/yyyy, whole floats without a trailing .0, everything else as text."""
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, date):
        return value.strftime("%d/%m/%Y")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _rows_to_csv_text(rows: Iterable[Sequence[Any]]) -> str:
    buf = StringIO()
    writer = csv.writer(buf)
    for row in rows:
        writer.writerow([_cell_to_str(c) for c in row])
    return buf.getvalue()


def _xlsx_to_csv_text(path: Path) -> str:
    from openpyxl import load_workbook  # optional dep

    wb = load_workbook(filename=str(path), read_only=True, data_only=True)
    try:
        ws = wb.active
        if ws is None:
            return ""
        return _rows_to_csv_text(ws.iter_rows(values_only=True))
    finally:
        wb.close()


def _xls_to_csv_text(path: Path) -> str:
    import xlrd  # optional dep

    book = xlrd.open_workbook(str(path))
    sheet = book.sheet_by_index(0)
    rows: list[list[Any]] = []
    for r in range(sheet.nrows):
        row: list[Any] = []
        for c in range(sheet.ncols):
            cell = sheet.cell(r, c)
            if cell.ctype == xlrd.XL_CELL_DATE:
                y, mo, d, *_ = xlrd.xldate_as_tuple(float(cell.value), book.datemode)
                row.append(f"{d:02d}/{mo:02d}/{y:04d}")
            else:
                row.append(cell.value)
        rows.append(row)
    return _rows_to_csv_text(rows)


def file_to_csv_text(path: Path) -> str:
    """CSV text for any supported expenses file (.csv / .xlsx / .xls)."""
    suffix = str(path.suffix or "").lower()
    if suffix == ".xlsx":
        return _xlsx_to_csv_text(path)
    if suffix == ".xls":
        return _xls_to_csv_text(path)
    # .csv / .txt / unknown → plain text, tolerant of a UTF-8 BOM
    return path.read_text(encoding="utf-8-sig")
