"""בדיקות לתחום הנכסים (assets).

נועלות את ההתנהגות הקיימת לפני ואחרי המעבר ל-OOP שבו ``Asset`` הוא השורש
ורכישת דירה (``HousePurchase``) מחזיקה משכנתא (``MortgageLoan``).
ניתן להריץ עם pytest או ישירות.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finance.models.mortgage import (  # noqa: E402
    AmortizationType,
    AssetKind,
    Mortgage,
    MortgageTrack,
    TrackKind,
)
from finance.models.mortgage_math import (  # noqa: E402
    DEFAULT_ASSUMPTIONS,
    mortgage_outstanding,
)
from finance.models.mortgage_service import MortgageService  # noqa: E402


def _approx(a: float, b: float, tol: float = 0.5) -> bool:
    return abs(float(a) - float(b)) <= tol


class _FakeMortgageProvider:
    def __init__(self, mortgages):
        self._m = list(mortgages)

    def list_mortgages(self):
        return list(self._m)


def _purchase():
    return Mortgage(
        name="דירה",
        kind=AssetKind.PURCHASE,
        property_price=2_000_000.0,
        start_date="2025-01-01",
        tracks=[
            MortgageTrack(
                name="קבועה", kind=TrackKind.FIXED_UNLINKED, principal=1_000_000.0,
                annual_rate=5.0, term_months=120, amortization=AmortizationType.SPITZER,
            )
        ],
    )


def _held(name="רכב", value=80_000.0, **kw):
    return Mortgage(name=name, kind=AssetKind.OTHER, current_value=value, **kw)


def _svc(mortgages):
    return MortgageService(
        mortgages_provider=_FakeMortgageProvider(mortgages),
        movements_provider=_FakeMortgageProvider([]),  # unused here; needs list_* duck
    )


# ----- service aggregates (behaviour lock) -----------------------------------

def test_total_outstanding_sums_purchases_only() -> None:
    purchase = _purchase()
    svc = _svc([purchase, _held()])
    expected = mortgage_outstanding(purchase, None, DEFAULT_ASSUMPTIONS)
    assert _approx(svc.total_outstanding(), expected)
    assert expected > 0  # sanity: the purchase actually has debt


def test_total_other_assets_value_sums_held_only() -> None:
    svc = _svc([_purchase(), _held(value=80_000.0)])
    assert _approx(svc.total_other_assets_value(), 80_000.0)


def test_archived_excluded_unless_requested() -> None:
    svc = _svc([_held(value=80_000.0), _held(name="ישן", value=50_000.0, archived=True)])
    assert _approx(svc.total_other_assets_value(), 80_000.0)
    assert _approx(svc.total_other_assets_value(include_archived=True), 130_000.0)


# ----- the OOP Asset model ---------------------------------------------------

def test_build_asset_picks_subtype_by_kind() -> None:
    from finance.models.asset import HeldAsset, HousePurchase, build_asset

    assert isinstance(build_asset(_purchase()), HousePurchase)
    assert isinstance(build_asset(_held()), HeldAsset)


def test_held_asset_value_and_equity() -> None:
    from finance.models.asset import build_asset

    a = build_asset(_held(value=80_000.0))
    assert _approx(a.current_value(), 80_000.0)
    assert _approx(a.outstanding_debt(), 0.0)
    assert _approx(a.equity(), 80_000.0)        # no debt -> equity == value
    assert _approx(a.standalone_value(), 80_000.0)


def test_house_purchase_value_equity_and_mortgage() -> None:
    from finance.models.asset import build_asset
    from finance.models.mortgage_math import mortgage_outstanding

    purchase = _purchase()
    a = build_asset(purchase)
    outstanding = mortgage_outstanding(purchase, None, DEFAULT_ASSUMPTIONS)
    assert _approx(a.current_value(), 2_000_000.0)            # worth its price
    assert _approx(a.outstanding_debt(), outstanding)         # debt via its mortgage
    assert _approx(a.equity(), 2_000_000.0 - outstanding)     # equity = price - debt
    assert _approx(a.standalone_value(), 0.0)                 # tracked via debt, not value
    # has-a mortgage that owns the loan economics
    assert _approx(a.mortgage.outstanding(), outstanding)
    assert _approx(a.mortgage.original_principal, 1_000_000.0)


def test_sold_asset_realized_value_and_inactive() -> None:
    from finance.models.asset import build_asset

    a = build_asset(_held(name="ישן", value=50_000.0, sold=True, sale_price=60_000.0))
    assert a.is_active is False
    assert _approx(a.realized_value(), 60_000.0)


# ----- AssetsPage now routes value/sold through the model --------------------

def test_assets_page_value_and_sold_use_model() -> None:
    from finance.pages.assets_page import AssetsPage

    assert _approx(AssetsPage._asset_value(_purchase()), 2_000_000.0)
    assert _approx(AssetsPage._asset_value(_held(value=80_000.0)), 80_000.0)
    assert AssetsPage._is_sold(_held(value=1.0, sold=True)) is True
    assert AssetsPage._is_sold(_held(value=1.0, archived=True)) is True
    assert AssetsPage._is_sold(_purchase()) is False


def test_mortgage_loan_combined_schedule() -> None:
    from finance.models.asset import MortgageLoan
    from finance.models.mortgage_math import track_schedule

    m = _purchase()  # one track, principal 1,000,000
    rows = MortgageLoan(m).combined_schedule()
    single = track_schedule(m.tracks[0], DEFAULT_ASSUMPTIONS)
    assert len(rows) == len(single)
    assert rows[0][0] == 1                                   # period
    assert _approx(rows[0][1], single[0].payment)           # summed payment
    assert _approx(rows[0][4], single[0].remaining_balance)  # summed remaining


def test_new_asset_record_factory() -> None:
    from finance.models.asset import HeldAsset, HousePurchase, build_asset, new_asset_record

    held = new_asset_record(AssetKind.OTHER, name="רכב", current_value=80_000.0)
    assert held.kind == AssetKind.OTHER
    assert _approx(held.current_value, 80_000.0)
    assert isinstance(build_asset(held), HeldAsset)

    house = new_asset_record(AssetKind.PURCHASE, name="דירה", account_name="בנק")
    assert house.kind == AssetKind.PURCHASE
    assert house.account_name == "בנק"
    assert isinstance(build_asset(house), HousePurchase)


def _run_all() -> int:
    funcs = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failures = 0
    for fn in funcs:
        try:
            fn()
            print(f"PASS {fn.__name__}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failures += 1
            print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(funcs) - failures}/{len(funcs)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_all())
