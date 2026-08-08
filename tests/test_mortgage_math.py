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
    FundingKind,
    FundingSource,
    Mortgage,
    MortgageTrack,
    TrackKind,
)
from finance.models.bank_movement import BankMovement, MovementType  # noqa: E402
from finance.models.movement_matching import (  # noqa: E402
    match_movements,
    normalize_text,
)
from finance.models.mortgage_math import (  # noqa: E402
    MortgageAssumptions,
    annuity_payment,
    cost_paid_amount,
    cost_total_amount,
    assumptions_sensitivity,
    early_payoff_savings,
    months_after,
    months_between,
    payment_split_projection,
    track_end_milestones,
    mortgage_initial_monthly,
    mortgage_outstanding,
    mortgage_total_interest,
    outstanding_projection,
    purchase_summary,
    query_received_amount,
    track_schedule,
    track_total_interest,
)


def _mv(amount: float, desc: str, *, transfer: bool = False) -> BankMovement:
    return BankMovement(
        amount=amount,
        date="2024-01-01",
        account_name="עוש",
        category="x",
        type=MovementType.ONE_TIME,
        description=desc,
        is_transfer=transfer,
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
    # מחיר 2M + עלויות 72k = עלות רכישה 2,072,000. מימון עצמי 572k → משכנתא 1.5M.
    m = Mortgage(
        property_price=2_000_000,
        funding_sources=[
            FundingSource(name="חיסכון", amount=472_000, kind=FundingKind.ACCOUNT),
            FundingSource(name="מתנה", amount=100_000, kind=FundingKind.FUTURE),
        ],
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
    assert _approx(s.acquisition_cost, 2_072_000, 1.0)  # מחיר + עלויות
    assert _approx(s.funding_total, 572_000, 1.0)  # סך מקורות המימון
    # המשכנתא = התמהיל שהמשתמש בנה (1.5M), לא יתרה מחושבת.
    assert _approx(s.required_mortgage, 1_500_000, 1.0)
    assert _approx(s.tracks_total, 1_500_000, 1.0)
    # יתרת חשבון הבנק = עלות − משכנתא − מימון = 2,072,000 − 1,500,000 − 572,000 = 0.
    assert _approx(s.residual_from_bank, 0.0, 1.0)
    assert _approx(s.ltv, 0.75, 1e-6)  # משכנתא / מחיר
    assert s.ltv_exceeds_75 is False
    assert _approx(s.one_time_total, 72_000, 1.0)
    assert _approx(s.upfront_cash, 572_000, 1.0)  # עלות − משכנתא
    assert _approx(s.monthly_costs_total, 750, 1.0)
    assert s.mortgage_monthly > 0
    assert _approx(s.monthly_total, s.mortgage_monthly + 750, 1.0)
    assert _approx(s.total_cost, 2_072_000 + s.total_interest, 1.0)


def test_purchase_summary_bank_residual() -> None:
    # מחיר 1M, אין עלויות; תמהיל 800k; מימון 100k → הבנק צריך לכסות 100k.
    m = Mortgage(
        property_price=1_000_000,
        funding_sources=[FundingSource(name="חיסכון", amount=100_000)],
        tracks=[MortgageTrack(principal=800_000, annual_rate=4.0, term_months=240)],
    )
    s = purchase_summary(m)
    assert _approx(s.required_mortgage, 800_000, 1.0)  # = התמהיל
    assert _approx(s.residual_from_bank, 100_000, 1.0)  # 1M − 800k − 100k
    assert _approx(s.ltv, 0.8, 1e-6)
    assert s.ltv_exceeds_75 is True


def test_purchase_summary_empty() -> None:
    m = Mortgage()  # ללא מחיר, מסלולים או מימון
    s = purchase_summary(m)
    assert s.ltv == 0.0
    assert s.required_mortgage == 0.0  # אין תמהיל → משכנתא 0
    assert s.acquisition_cost == 0.0
    assert s.residual_from_bank == 0.0


def test_initial_monthly_matches_first_payment() -> None:
    track = MortgageTrack(
        principal=1_000_000,
        annual_rate=4.0,
        term_months=360,
        amortization=AmortizationType.SPITZER,
    )
    m = Mortgage(tracks=[track])
    assert _approx(mortgage_initial_monthly(m), track_schedule(track)[0].payment, 0.01)


def test_matcher_substring_and_quote_variants() -> None:
    # תת-מחרוזת: "עו\"ד" נמצא בתוך "מקדמה עו\"ד".
    assert match_movements([_mv(-4000, 'מקדמה עו"ד')], vendor_query='עו"ד')
    # גרשיים (״) מול מרכאות ASCII (") — אמורים להתאים.
    assert match_movements([_mv(-4000, "מקדמה עו״ד")], vendor_query='עו"ד')
    assert normalize_text("עו״ד") == normalize_text('עו"ד')
    # אי-התאמה אמיתית.
    assert not match_movements([_mv(-4000, "ביטוח רכב")], vendor_query='עו"ד')


def test_matcher_income_and_transfers() -> None:
    movs = [_mv(100_000, "מתנה", transfer=True), _mv(-50, "קפה")]
    # הכנסה + העברות מותרות.
    assert match_movements(
        movs, vendor_query="מתנה", match_income=True, include_transfers=True
    )
    # match_income עם העברה שדולגה כברירת מחדל → אין התאמה.
    assert not match_movements(movs, vendor_query="מתנה", match_income=True)
    # ברירת מחדל (ללא match_income) = הוצאות בלבד; הכנסה לא נתפסת.
    assert match_movements([_mv(100, "החזר")], vendor_query="החזר") == []
    # הוצאה רגילה כן נתפסת.
    assert match_movements([_mv(-100, "חניון")], vendor_query="חניון")


def test_cost_paid_amount() -> None:
    movs = [_mv(-4000, 'עו"ד שלב א'), _mv(-3000, 'עו"ד שלב ב')]
    assert _approx(cost_paid_amount(CostItem(query='עו"ד'), movs), 7000, 1.0)
    # ללא שאילתה — 0 (אין נפילה לסכום מתוכנן, בניגוד ל-effective).
    assert cost_paid_amount(CostItem(name="x", amount=999, query=""), movs) == 0.0


def test_query_received_amount() -> None:
    movs = [_mv(120_000, "תמורת מכירה", transfer=True)]
    assert _approx(
        query_received_amount("תמורת מכירה", movs, include_transfers=True),
        120_000,
        1.0,
    )
    # ללא include_transfers — העברה לא נספרת.
    assert query_received_amount("תמורת מכירה", movs) == 0.0


def test_cost_total_amount_planned_wins() -> None:
    # סכום מתוכנן קיים → משתמשים בו (לא מתכווץ לפי מה ששולם בפועל).
    movs = [_mv(-20_000, "מס רכישה חלקי")]
    assert _approx(
        cost_total_amount(CostItem("מס רכישה", 60_000, "מס רכישה"), movs), 60_000, 1.0
    )
    # אין סכום מתוכנן → נופלים לסכום ששולם בפועל.
    assert _approx(
        cost_total_amount(CostItem('עו"ד', 0, 'עו"ד'), [_mv(-5_000, 'עו"ד')]),
        5_000,
        1.0,
    )


def test_acquisition_cost_uses_planned_not_paid() -> None:
    # רגרסיה: עלות הרכישה לא מתכווצת לסכום ששולם כשיש חיפוש תנועות חלקי.
    movs = [_mv(-20_000, "מס רכישה חלקי")]
    m = Mortgage(
        property_price=2_000_000,
        one_time_costs=[CostItem("מס רכישה", 60_000, "מס רכישה")],
    )
    s = purchase_summary(m, movements=movs)
    assert _approx(s.acquisition_cost, 2_060_000, 1.0)  # מחיר + מתוכנן, לא ששולם


def test_months_after() -> None:
    assert months_after("2024-01-01", 0) == (2024, 1)
    assert months_after("2024-01-01", 12) == (2025, 1)
    assert months_after("2024-06-01", 8) == (2025, 2)
    assert months_after("", 12) is None  # אין תאריך התחלה → לא ידוע


def test_loan_status_progress_and_payment_split() -> None:
    from finance.models.asset import MortgageLoan

    m = Mortgage(
        name="t",
        start_date="2024-07-01",
        tracks=[MortgageTrack(principal=500_000, annual_rate=4.0, term_months=240)],
    )
    st = MortgageLoan(m).status(as_of_date="2025-07-01")  # 12 תשלומים אחרי
    assert st.dated is True
    assert st.elapsed_months == 12
    assert st.total_months == 240
    assert st.remaining_payments == 228
    assert (st.payoff_year, st.payoff_month) == (2044, 7)
    # פירוק התשלום הנוכחי לריבית+קרן שווה לתשלום החודשי.
    assert _approx(st.interest_now + st.principal_now, st.monthly_now, 1.0)
    # עלות כוללת = קרן + סך ריבית.
    assert _approx(st.total_cost, st.principal + st.total_interest, 1.0)
    # אחוז ששולם — חיובי אך קטן (שנה מתוך 20).
    assert 0.0 < st.pct_paid < 0.1


def test_loan_status_undated_has_no_progress() -> None:
    from finance.models.asset import MortgageLoan

    m = Mortgage(
        name="t",
        tracks=[MortgageTrack(principal=500_000, annual_rate=4.0, term_months=240)],
    )
    st = MortgageLoan(m).status()
    assert st.dated is False
    assert st.pct_paid == 0.0
    assert st.elapsed_months == 0
    assert st.total_months == 240


def test_payment_split_matches_schedule() -> None:
    t = MortgageTrack(principal=500_000, annual_rate=4.0, term_months=240)
    m = Mortgage(tracks=[t])
    pts = payment_split_projection(m, months=240)
    assert len(pts) == 240
    # פירוק = לוח הסילוקין של המסלול היחיד.
    sched = track_schedule(t)
    assert _approx(pts[0].interest, sched[0].interest_part, 0.5)
    assert _approx(pts[0].principal, sched[0].principal_part, 0.5)
    # התחלה: רוב התשלום ריבית; סוף: רוב התשלום קרן.
    assert pts[0].interest > pts[0].principal
    assert pts[-1].principal > pts[-1].interest
    # סכום הריבית לאורך הזמן = סך הריבית של המסלול.
    assert _approx(sum(p.interest for p in pts), track_total_interest(t), 1.0)


def test_sensitivity_prime_only_affects_prime_tracks() -> None:
    m = Mortgage(
        tracks=[
            MortgageTrack(kind=TrackKind.PRIME, principal=500_000, term_months=240),
            MortgageTrack(kind=TrackKind.FIXED_UNLINKED, principal=500_000,
                          annual_rate=4.0, term_months=240),
        ]
    )
    s = assumptions_sensitivity(m, prime_delta=1.0, cpi_delta=1.0)
    # עליית פריים מייקרת את התשלום (יש מסלול פריים).
    assert s.prime_monthly_delta > 0
    assert s.prime_interest_delta > 0
    # אין מסלול צמוד → עליית מדד לא משנה כלום.
    assert _approx(s.cpi_monthly_delta, 0.0, 0.5)


def test_track_end_milestones_sorted() -> None:
    m = Mortgage(
        tracks=[
            MortgageTrack(name="ארוך", principal=500_000, annual_rate=4.0,
                          term_months=300),
            MortgageTrack(name="קצר", principal=200_000, annual_rate=4.0,
                          term_months=120),
        ]
    )
    ms = track_end_milestones(m)
    assert [x.period for x in ms] == [120, 300]
    assert ms[0].track_name == "קצר"
    assert ms[0].payment_drop > 0


def test_early_payoff_baseline_matches_real_schedule() -> None:
    # ללא תשלום חד-פעמי — עקבי עם שאר המסך: תקופה = המסלול הארוך, ריבית = הסך.
    m = Mortgage(
        tracks=[
            MortgageTrack(principal=620_000, annual_rate=4.5, term_months=240),
            MortgageTrack(principal=700_000, annual_rate=6.0, term_months=300),
        ]
    )
    base = early_payoff_savings(m, 0.0)
    assert base is not None
    assert base.baseline_months == 300  # המסלול הארוך
    assert base.new_months == 300  # ללא תשלום — זהה
    assert base.months_saved == 0
    assert _approx(base.baseline_interest, mortgage_total_interest(m), 5.0)
    assert _approx(base.interest_saved, 0.0, 5.0)


def test_early_payoff_lump_is_modest_not_absurd() -> None:
    # תשלום חד-פעמי קטן חוסך מעט — לא מקצר שנים על גבי שנים (רגרסיה לבאג
    # שהתייחס לסכום כתוספת חודשית).
    m = Mortgage(
        tracks=[MortgageTrack(principal=750_000, annual_rate=4.3, term_months=192)]
    )
    res = early_payoff_savings(m, 10_000.0)  # ~1.3% מהקרן
    assert res is not None
    assert res.new_months < res.baseline_months
    assert res.months_saved <= 6  # תשלום זעיר → חיסכון זמן זעיר


def test_early_payoff_lump_saves_time_and_interest() -> None:
    m = Mortgage(
        tracks=[MortgageTrack(principal=500_000, annual_rate=4.0, term_months=240)]
    )
    res = early_payoff_savings(m, 100_000.0)  # תשלום חד-פעמי משמעותי
    assert res is not None
    assert res.months_saved > 0  # הקטנת הקרן מקצרת את התקופה
    assert res.interest_saved > 0  # וחוסכת ריבית
    assert res.new_months < res.baseline_months


def test_early_payoff_targets_longest_track_to_shorten() -> None:
    # התשלום מופנה למסלול הארוך ביותר (360) כדי לקצר בפועל את המשכנתא,
    # גם כשמסלול אחר יקר יותר.
    m = Mortgage(
        tracks=[
            MortgageTrack(name="קצר יקר", principal=300_000, annual_rate=6.0,
                          term_months=120),
            MortgageTrack(name="ארוך זול", principal=500_000, annual_rate=3.5,
                          term_months=360),
        ]
    )
    res = early_payoff_savings(m, 150_000.0)
    assert res is not None
    assert res.baseline_months == 360
    assert 0 < res.new_months < 360  # המסלול הארוך התקצר → כל המשכנתא התקצרה
    assert res.interest_saved > 0


def test_equity_split_basic() -> None:
    from finance.models.mortgage_math import equity_split

    assert equity_split(1_000_000.0, 300_000.0) == (700_000.0, 0.7)


def test_equity_split_zero_or_negative_value_gives_zero_fraction() -> None:
    from finance.models.mortgage_math import equity_split

    assert equity_split(0.0, 50_000.0) == (-50_000.0, 0.0)
    assert equity_split(-10.0, 5.0) == (-15.0, 0.0)


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
