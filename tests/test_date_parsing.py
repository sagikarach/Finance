from datetime import datetime

from finance.models.accounts import parse_iso_date, to_iso_date


def test_to_iso_date_handles_dash_day_first():
    # Newer Leumi/credit-card xlsx exports use dd-mm-yyyy with dashes.
    assert to_iso_date("16-07-2026") == "2026-07-16"
    assert to_iso_date("6-7-2026") == "2026-07-06"
    assert to_iso_date("16-07-26") == "2026-07-16"  # 2-digit year


def test_to_iso_date_still_handles_slash_dot_and_iso():
    assert to_iso_date("16/07/2026") == "2026-07-16"
    assert to_iso_date("16.07.2026") == "2026-07-16"
    assert to_iso_date("2026-07-16") == "2026-07-16"  # real ISO, unchanged


def test_iso_yyyy_mm_dd_not_mistaken_for_dash_day_first():
    # The ISO fast-path must win so a leading 4-digit year is read as the year.
    assert parse_iso_date("2026-07-16") == datetime(2026, 7, 16)


def test_unparseable_date_is_returned_unchanged():
    assert to_iso_date("not a date") == "not a date"
    assert to_iso_date("") == ""
