"""בדיקות ללוח הסילוקין הטהור של המשכנתא.

ניתן להריץ עם pytest (``python -m pytest tests/test_mortgage_math.py``)
או ישירות (``python tests/test_mortgage_math.py``) כי בפרויקט אין עדיין
תשתית בדיקות מותקנת.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from finance.models.mortgage import (  # noqa: E402
    AmortizationType,
    CostItem,
    Mortgage,
    MortgageTrack,
    TrackKind,
)
from finance.models.mortgage_math import (  # noqa: E402
    MortgageAssumptions,
    annuity_payment,
    months_between,
    mortgage_initial_monthly,
    mortgage_outstanding,
    mortgage_total_interest,
    outstanding_projection,
    purchase_summary,
    track_schedule,
    track_total_interest,
)

TOL = 0.5  # סובלנות בש"ח לחישובי כסף


def _approx(a: float, b: float, tol: float = TOL) -> bool:
    return abs(float(a) - float(b)) <= tol


def test_spitzer_payment_known_value() -> None:
    # 1,000,000 ש"ח, 4% שנתי, 360 חודשים → ~4774.15 לחודש.
    pay = annuity_payment(1_000_000, 0.04 / 12, 360)
    assert _approx(pay, 4774.15, 1.0), pay


def test_spitzer_payment_is_constant() -> None:
    track = MortgageTrack(
        principal=1_000_000,
        annual_rate=4.0,
        term_months=360,
        amortization=AmortizationType.SPITZER,
    )
    sched = track_schedule(track)
    assert len(sched) == 360
    payments = [round(row.payment, 2) for row in sched]
    assert max(payments) - min(payments) < 0.05, (min(payments), max(payments))


def test_spitzer_fully_amortizes() -> None:
    track = MortgageTrack(
        principal=500_000,
        annual_rate=3.5,
        term_months=240,
        amortization=AmortizationType.SPITZER,
    )
    sched = track_schedule(track)
    assert _approx(sched[-1].remaining_balance, 0.0)
    total_principal = sum(r.principal_part for r in sched)
    assert _approx(total_principal, 500_000, 1.0)


def test_equal_principal_constant_principal_and_declining_payment() -> None:
    track = MortgageTrack(
        principal=600_000,
        annual_rate=5.0,
        term_months=120,
        amortization=AmortizationType.EQUAL_PRINCIPAL,
    )
    sched = track_schedule(track)
    expected_principal = 600_000 / 120
    for row in sched:
        assert _approx(row.principal_part, expected_principal, 0.01)
    # התשלום יורד משורה לשורה (ריבית על יתרה קטֵנה).
    assert sched[0].payment > sched[-1].payment
    # ריבית התשלום הראשון = קרן * ריבית חודשית.
    assert _approx(sched[0].interest_part, 600_000 * (0.05 / 12), 0.01)


def test_zero_interest() -> None:
    track = MortgageTrack(
        principal=120_000,
        annual_rate=0.0,
        term_months=12,
        amortization=AmortizationType.SPITZER,
    )
    sched = track_schedule(track)
    for row in sched:
        assert _approx(row.payment, 10_000, 0.01)
        assert _approx(row.interest_part, 0.0)


def test_empty_for_invalid_inputs() -> None:
    assert track_schedule(MortgageTrack(principal=0, term_months=120)) == []
    assert track_schedule(MortgageTrack(principal=100_000, term_months=0)) == []


def test_prime_uses_assumption_rate() -> None:
    track = MortgageTrack(
        kind=TrackKind.PRIME,
        principal=400_000,
        prime_spread=-0.5,
        term_months=240,
        amortization=AmortizationType.SPITZER,
    )
    low = MortgageAssumptions(prime_rate=5.0)  # אפקטיבי 4.5%
    high = MortgageAssumptions(prime_rate=7.0)  # אפקטיבי 6.5%
    assert track_total_interest(track, high) > track_total_interest(track, low)


def test_cpi_linkage_increases_interest() -> None:
    track = MortgageTrack(
        kind=TrackKind.FIXED_LINKED,
        principal=300_000,
        annual_rate=3.0,
        term_months=240,
        amortization=AmortizationType.SPITZER,
        cpi_linked=True,
    )
    no_cpi = MortgageAssumptions(cpi_annual=0.0)
    with_cpi = MortgageAssumptions(cpi_annual=3.0)
    assert track_total_interest(track, with_cpi) > track_total_interest(track, no_cpi)


def test_mortgage_outstanding_endpoints() -> None:
    mortgage = Mortgage(
        start_date="2020-01-01",
        tracks=[
            MortgageTrack(
                principal=400_000,
                annual_rate=4.0,
                term_months=240,
                amortization=AmortizationType.SPITZER,
            ),
            MortgageTrack(
                principal=300_000,
                annual_rate=3.0,
                term_months=180,
                amortization=AmortizationType.EQUAL_PRINCIPAL,
            ),
        ],
    )
    # בתחילת הדרך — יתרה = סך הקרן.
    assert _approx(mortgage_outstanding(mortgage, "2020-01-01"), 700_000, 1.0)
    # אחרי תום המסלול הארוך — יתרה אפס.
    assert _approx(mortgage_outstanding(mortgage, "2045-01-01"), 0.0, 1.0)


def test_months_between() -> None:
    assert months_between("2020-01-01", "2020-01-01") == 0
    assert months_between("2020-01-01", "2021-01-01") == 12
    assert months_between("2020-06-01", "2020-01-01") == 0  # לא שלילי


def test_outstanding_projection_monotonic_nonincreasing() -> None:
    mortgage = Mortgage(
        start_date="2024-01-01",
        tracks=[
            MortgageTrack(
                principal=500_000,
                annual_rate=4.0,
                term_months=120,
                amortization=AmortizationType.SPITZER,
            )
        ],
    )
    pts = outstanding_projection(mortgage, months=120, step=6)
    values = [p.outstanding for p in pts]
    assert values[0] > values[-1]
    assert _approx(values[-1], 0.0, 1.0)
    for earlier, later in zip(values, values[1:]):
        assert later <= earlier + TOL


def test_total_interest_positive() -> None:
    mortgage = Mortgage(
        tracks=[
            MortgageTrack(
                principal=1_000_000,
                annual_rate=4.0,
                term_months=360,
                amortization=AmortizationType.SPITZER,
            )
        ]
    )
    assert mortgage_total_interest(mortgage) > 0


def test_purchase_summary_basic() -> None:
    m = Mortgage(
        property_price=2_000_000,
        equity=500_000,
        tracks=[
            MortgageTrack(
                principal=1_500_000,
                annual_rate=4.5,
                term_months=300,
                amortization=AmortizationType.SPITZER,
            )
        ],
        one_time_costs=[CostItem("מס רכישה", 60_000), CostItem("עו\"ד", 12_000)],
        monthly_costs=[CostItem("ארנונה", 600), CostItem("ביטוח", 150)],
    )
    s = purchase_summary(m)
    assert _approx(s.required_mortgage, 1_500_000, 1.0)
    assert _approx(s.ltv, 0.75, 1e-6)
    assert s.ltv_exceeds_75 is False
    assert s.principal_mismatch is False  # tracks sum == required loan
    assert _approx(s.one_time_total, 72_000, 1.0)
    assert _approx(s.upfront_cash, 572_000, 1.0)  # equity + one-time
    assert _approx(s.monthly_costs_total, 750, 1.0)
    assert s.mortgage_monthly > 0
    assert _approx(s.monthly_total, s.mortgage_monthly + 750, 1.0)
    assert _approx(s.total_cost, 2_000_000 + s.total_interest + 72_000, 1.0)


def test_purchase_summary_flags() -> None:
    m = Mortgage(
        property_price=1_000_000,
        equity=100_000,  # 90% LTV
        tracks=[
            MortgageTrack(principal=800_000, annual_rate=4.0, term_months=240)
        ],  # tracks (800k) != required (900k)
    )
    s = purchase_summary(m)
    assert s.ltv_exceeds_75 is True
    assert s.principal_mismatch is True


def test_purchase_summary_empty_when_no_price() -> None:
    m = Mortgage(tracks=[MortgageTrack(principal=500_000, annual_rate=4.0, term_months=120)])
    s = purchase_summary(m)
    assert s.ltv == 0.0
    assert s.principal_mismatch is False  # no price -> no cross-check
    assert s.required_mortgage == 0.0


def test_initial_monthly_matches_first_payment() -> None:
    track = MortgageTrack(
        principal=1_000_000,
        annual_rate=4.0,
        term_months=360,
        amortization=AmortizationType.SPITZER,
    )
    m = Mortgage(tracks=[track])
    assert _approx(mortgage_initial_monthly(m), track_schedule(track)[0].payment, 0.01)


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
