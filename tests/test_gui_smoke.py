"""Offscreen render-smoke for the chart components — the permanent version of
the manual offscreen renders. Skipped unless PySide6 is installed (the CI `gui`
job); needs QT_QPA_PLATFORM=offscreen. Asserts each card builds, computes the
expected series, and paints (.grab()) without raising."""

import pytest

pytest.importorskip("PySide6")

from finance.models.accounts import (  # noqa: E402
    BankAccount,
    MoneySnapshot,
    Savings,
    SavingsAccount,
)
from finance.models.bank_movement import BankMovement, MovementType  # noqa: E402
from finance.qt import QApplication  # noqa: E402
from finance.widgets.bank_history_chart import BankHistoryChartCard  # noqa: E402
from finance.widgets.one_time_event_expenses_chart import (  # noqa: E402
    ExpensePoint,
    OneTimeEventExpensesOverTimeChart,
)
from finance.widgets.savings_history_chart import SavingsHistoryChartCard  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def _mv(amount, date):
    return BankMovement(
        amount=amount, date=date, account_name="בנק",
        category="מזון", type=MovementType.MONTHLY,
    )


def test_bank_history_card_builds_and_paints(app):
    bank = BankAccount(name="בנק", total_amount=0.0, is_liquid=True,
                       active=True, baseline_amount=100000.0)
    movs = [_mv(-5000, "2025-02-01"), _mv(-300, "2025-03-05"), _mv(20000, "2025-04-25")]
    card = BankHistoryChartCard(None, bank, lambda v: f"{v:.0f}", movements=movs)
    # running balance: 100000 − 5000 − 300 + 20000 = 114700 (last point)
    assert round(card._bv_bank[-1], 2) == 114700.0
    card.grab()  # force an offscreen paint — must not raise


def test_savings_history_card_builds_and_paints(app):
    acc = SavingsAccount(
        name="קופה", total_amount=0.0, is_liquid=True,
        savings=[Savings(name="חירום", amount=5000.0, history=[
            MoneySnapshot("2025-01-01", 3000.0),
            MoneySnapshot("2025-02-01", 4000.0),
            MoneySnapshot("2025-03-01", 5000.0),
        ])],
    )
    card = SavingsHistoryChartCard(None, acc, lambda v: f"{v:.0f}")
    card.grab()


def test_one_time_expenses_chart_cumulates_and_paints(app):
    chart = OneTimeEventExpensesOverTimeChart(None)
    chart.set_expenses([
        ExpensePoint("2026-01-01", -100.0),
        ExpensePoint("2026-01-03", -50.0),
    ])
    # gap-filled cumulative: [-100, -100, -150]
    assert chart._all_values[-1] == -150.0
    chart.grab()
