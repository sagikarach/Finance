"""End-to-end characterization of the calc pipeline on a fixed fixture.

Seeds a deterministic workspace (accounts + movements + one house mortgage) into
tmp files, then drives the real provider→service pipeline and locks the derived
figures the UI shows. This is the permanent replacement for a one-off fingerprint:
if any extracted calculation drifts, a golden here breaks.

Every asserted figure is date-independent (a pure function of the fixture data),
so the test is stable across days."""

import pytest

from finance.data.provider import JsonFileAccountsProvider
from finance.data.bank_movement_provider import JsonFileBankMovementProvider
from finance.data.mortgage_provider import JsonFileMortgageProvider
from finance.models.account_history import balance_timeline
from finance.models.accounts import BankAccount
from finance.models.asset_expense_service import AssetExpenseService
from finance.models.bank_movement import BankMovement, MovementType
from finance.models.movement_filters import movements_for_month
from finance.models.mortgage import (
    AmortizationType,
    AssetKind,
    CostItem,
    Mortgage,
    MortgageTrack,
    TrackKind,
)
from finance.models.mortgage_service import MortgageService


def _mv(amount, date, cat, desc, mtype=MovementType.ONE_TIME):
    return BankMovement(
        amount=amount, date=date, account_name="בנק",
        category=cat, type=mtype, description=desc,
    )


_MOVEMENTS = [
    _mv(-5000, "2025-02-01", "דיור", "משכנתא ינואר", MovementType.MONTHLY),
    _mv(-5000, "2025-03-01", "דיור", "משכנתא פברואר", MovementType.MONTHLY),
    _mv(-5000, "2025-04-01", "דיור", "משכנתא מרץ", MovementType.MONTHLY),
    _mv(-300, "2025-02-05", "בית", "ארנונה", MovementType.MONTHLY),
    _mv(-300, "2025-03-05", "בית", "ארנונה", MovementType.MONTHLY),
    _mv(-300, "2025-04-05", "בית", "ארנונה", MovementType.MONTHLY),
    _mv(-100000, "2025-01-10", "העברה", "מקדמה לדירה"),
    _mv(-5000, "2025-01-12", "שירותים", "עורך דין"),
    _mv(-1200, "2025-01-20", "בית", "ביטוח מבנה"),
    _mv(-400, "2025-02-08", "רכב", "דלק"),
    _mv(-400, "2025-03-08", "רכב", "דלק"),
    _mv(20000, "2025-02-25", "הכנסה", "משכורת", MovementType.MONTHLY),
    _mv(20000, "2025-03-25", "הכנסה", "משכורת", MovementType.MONTHLY),
    _mv(20000, "2025-04-25", "הכנסה", "משכורת", MovementType.MONTHLY),
]


def _mortgage():
    return Mortgage(
        name="דירה", kind=AssetKind.PURCHASE, property_price=2_000_000.0,
        start_date="2025-01-01", account_name="בנק", vendor_query="משכנתא",
        price_query="מקדמה",
        one_time_costs=[CostItem(name="עו״ד", query="עורך דין")],
        monthly_costs=[CostItem(name="ארנונה", query="ארנונה")],
        yearly_costs=[CostItem(name="ביטוח מבנה", query="ביטוח מבנה", renewal_month=1)],
        tracks=[MortgageTrack(
            name="קבועה", kind=TrackKind.FIXED_UNLINKED, principal=1_000_000.0,
            annual_rate=5.0, term_months=120, amortization=AmortizationType.SPITZER,
        )],
    )


@pytest.fixture
def pipeline(tmp_path):
    mv_p, mg_p = tmp_path / "mv.json", tmp_path / "mg.json"
    bank_p, sav_p = tmp_path / "bank.json", tmp_path / "sav.json"

    JsonFileBankMovementProvider(movements_path=mv_p).save_movements(_MOVEMENTS)
    JsonFileMortgageProvider(path=mg_p).save_mortgages([_mortgage()])
    JsonFileAccountsProvider(
        bank_accounts_path=bank_p, savings_accounts_path=sav_p
    ).save_bank_accounts(
        [BankAccount(name="בנק", total_amount=0.0, is_liquid=True,
                     active=True, baseline_amount=100000.0)]
    )

    svc = MortgageService(
        mortgages_provider=JsonFileMortgageProvider(path=mg_p),
        movements_provider=JsonFileBankMovementProvider(movements_path=mv_p),
    )
    bank = JsonFileAccountsProvider(
        bank_accounts_path=bank_p, savings_accounts_path=sav_p
    ).list_accounts()[0]
    return {
        "svc": svc,
        "exp": AssetExpenseService(svc),
        "m": svc.list_mortgages()[0],
        "bank": bank,
        "movements": _MOVEMENTS,
    }


def test_mortgage_matched_totals(pipeline):
    mt = pipeline["svc"].matched_totals(pipeline["m"])
    assert mt.total_paid == 15000.0  # 3 × 5000 matched by vendor_query "משכנתא"
    assert mt.total_in == 0.0


def test_acquisition_paid_and_financing_gap(pipeline):
    exp, m = pipeline["exp"], pipeline["m"]
    assert exp.acquisition_paid(m) == 105000.0  # 100k down-payment + 5k lawyer
    assert exp.financing_gap(m, 900000.0) == 795000.0


def test_house_cost_monthly(pipeline):
    # ארנונה avg (900/3=300) + ביטוח מבנה yearly folded (1200/12=100)
    assert round(pipeline["exp"].house_cost_expenses(pipeline["m"]).monthly, 2) == 400.0


def test_balance_timeline(pipeline):
    tl = balance_timeline(pipeline["bank"], pipeline["movements"])
    assert len(tl.month_keys) == 4  # Jan–Apr 2025
    assert len(tl.values) == 6  # baseline + 4 months + today
    assert round(tl.values[-1], 2) == 37100.0  # 100000 baseline − 62900 net flow


def test_movements_for_month_filter(pipeline):
    feb = movements_for_month(pipeline["movements"], MovementType.MONTHLY, 2025, 2)
    assert len(feb) == 3  # משכנתא + ארנונה + משכורת (transfers/one-time excluded)
