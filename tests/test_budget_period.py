from datetime import date

from finance.models.budget_period import future_months, next_month


def test_future_months_after_anchor():
    assert future_months(3, after=(2026, 11)) == [(2026, 12), (2027, 1), (2027, 2)]


def test_future_months_year_rollover():
    assert future_months(2, after=(2025, 12)) == [(2026, 1), (2026, 2)]


def test_future_months_zero_and_negative_are_empty():
    assert future_months(0, after=(2026, 5)) == []
    assert future_months(-3, after=(2026, 5)) == []


def test_future_months_defaults_to_month_after_today():
    today = date.today()
    assert future_months(1) == [next_month(today.year, today.month)]
