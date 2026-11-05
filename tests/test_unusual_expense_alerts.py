"""Unusual-expense alert: the conservative local detector and its lifecycle.

Detector tests call the pure functions directly; lifecycle tests drive
``NotificationsService.refresh()`` against a real JSON notifications file in a
sandboxed data dir, with the network blocked and no AI key.
"""

from __future__ import annotations

import socket
from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import List, Sequence

import pytest

import finance.models.gemini_classifier as gemini_classifier
from finance.data.bank_movement_provider import JsonFileBankMovementProvider
from finance.data.notifications_provider import JsonFileNotificationsProvider
from finance.models.bank_movement import BankMovement, MovementType
from finance.models.firebase_session import FirebaseSession, FirebaseSessionStore
from finance.models.installment_plan import (
    KIND_DIRECT_DEBIT,
    InstallmentPlan,
    direct_debit_movement_id,
)
from finance.models.mortgage import CostItem, Mortgage
from finance.models.notifications import (
    CLOSED_BY_SYSTEM,
    CLOSED_BY_USER,
    Notification,
    NotificationSeverity,
    NotificationStatus,
    NotificationType,
)
from finance.models.notifications_service import NotificationsService
from finance.models.one_time_event import OneTimeEvent
from finance.models.unusual_expense_detector import (
    MONTHLY,
    Outcome,
    RecurrenceConfig,
    UnusualExpenseConfig,
    baseline_window,
    compute_baseline,
    compute_threshold,
    detect_unusual_expenses,
    evaluate_month,
    expense_amount,
    merchant_key,
    nearest_rank,
    to_money,
)

CAT = "מסעדות"
EVAL = (2026, 10)  # evaluated month when "today" is in November 2026
TODAY = date(2026, 11, 5)
BASELINE = baseline_window(EVAL, 6)  # 04/2026 … 09/2026


# ── fixtures & helpers ────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    """Sandbox the data dir, block all network access, and make any AI call a
    test failure — the detector must work fully offline without a key."""
    monkeypatch.setenv("FINANCE_DATA_DIR", str(tmp_path / "data"))

    def _no_network(*_a, **_k):
        raise OSError("network disabled in tests")

    monkeypatch.setattr(socket.socket, "connect", _no_network)
    monkeypatch.setattr(socket, "create_connection", _no_network)

    def _no_ai(*_a, **_k):
        raise AssertionError("AI service must not be used")

    monkeypatch.setattr(gemini_classifier, "get_gemini_classifier", _no_ai)
    monkeypatch.setattr(gemini_classifier, "has_gemini_api_key", _no_ai)
    monkeypatch.setattr(gemini_classifier, "get_gemini_api_key", _no_ai)
    return tmp_path


_seq = [0]


def mv(amount, date_str, category=CAT, *, id=None, **kw) -> BankMovement:
    _seq[0] += 1
    return BankMovement(
        amount=amount,
        date=date_str,
        account_name=kw.pop("account_name", "בנק"),
        category=category,
        type=kw.pop("type", MovementType.ONE_TIME),
        id=id or f"m{_seq[0]}",
        **kw,
    )


def history(amounts_per_month: Sequence[float], months=BASELINE, category=CAT) -> List[BankMovement]:
    """The same list of (positive) expense amounts in each given month."""
    out = []
    for y, m in months:
        for i, a in enumerate(amounts_per_month):
            out.append(mv(-a, f"{y:04d}-{m:02d}-{i + 1:02d}", category))
    return out


NORMAL = [150, 180, 200, 250]  # 24 transactions over 6 months, median 190


class ListProvider:
    def __init__(self, items=None):
        self.items = list(items or [])

    def list_movements(self):
        return list(self.items)

    def list_plans(self):
        return list(self.items)

    def list_mortgages(self):
        return list(self.items)

    def list_events(self):
        return list(self.items)


def service(tmp_path, movements, *, plans=(), assets=(), events=(), today=TODAY, **kw):
    return NotificationsService(
        provider=JsonFileNotificationsProvider(tmp_path / "notifications.json"),
        movement_provider=ListProvider(movements),  # type: ignore[arg-type]
        installment_provider=kw.pop("installment_provider", ListProvider(plans)),  # type: ignore[arg-type]
        mortgage_provider=ListProvider(assets),  # type: ignore[arg-type]
        event_provider=kw.pop("event_provider", ListProvider(events)),  # type: ignore[arg-type]
        today=lambda: today,
        **kw,
    )


def unusual(svc: NotificationsService, *, include_closed=False) -> List[Notification]:
    items = svc._provider.list_notifications()  # noqa: SLF001
    return [
        n
        for n in items
        if n.type == NotificationType.UNEXPECTED_EXPENSE
        and ":duplicate:" not in n.key
        and (include_closed or n.status in (NotificationStatus.UNREAD, NotificationStatus.READ))
    ]


def detect(movements, **kw):
    return detect_unusual_expenses(movements, evaluated_month=kw.pop("month", EVAL), **kw)


# ── detector ──────────────────────────────────────────────────────────────


def test_normal_month_produces_no_alerts():
    # Large-but-ordinary October spending: several items that the old
    # top-20% rule would have flagged, none far from its category's history.
    movements = history(NORMAL) + history([900, 1100], category="סופר") + [
        mv(-260, "2026-10-03"),
        mv(-240, "2026-10-12"),
        mv(-1150, "2026-10-15", "סופר"),
        mv(-980, "2026-10-28", "סופר"),
    ]
    assert detect(movements) == []


def test_expense_exceeding_every_threshold_alerts_with_explanation(tmp_path):
    big = mv(-1200, "2026-10-14", id="big")
    svc = service(tmp_path, history(NORMAL) + [big, mv(-200, "2026-10-02")])
    svc.refresh()

    [n] = unusual(svc)
    assert n.key == "unexpected_expense:big"
    assert n.title == "הוצאה חריגה"
    assert n.severity == NotificationSeverity.WARNING
    assert n.message == (
        "הוצאה של 1,200 ש״ח בקטגוריית מסעדות. "
        "חציון העסקאות בקטגוריה בששת החודשים הקודמים (04/2026 עד 09/2026) "
        "הוא 190 ש״ח, על בסיס 24 עסקאות."
    )
    assert n.context["movement_id"] == "big"  # navigation to the movement
    assert n.context["history_count"] == 24
    assert n.context["typical_amount"] == "190.00"
    # threshold = max(300, 190+250, 190*3, 190+4*MAD(=25)) = 570
    assert n.context["threshold"] == "570.00"


def test_insufficient_history_never_alerts_or_falls_back():
    huge = mv(-50_000, "2026-10-10")
    eleven = history([100, 100])[:11]  # 11 transactions over 6 months
    assert detect(eleven + [huge]) == []

    two_months = history([100] * 6, months=BASELINE[-2:])  # 12 tx, 2 months
    assert detect(two_months + [huge]) == []

    three_months = history([100] * 4, months=BASELINE[-3:])  # 12 tx, 3 months
    assert [f.movement_id for f in detect(three_months + [huge])] == [huge.id]

    # Another category's rich history never substitutes for this one's.
    assert detect(history(NORMAL, category="סופר") + [huge]) == []


def test_identical_history_mad_zero_and_strict_boundary():
    base = history([100, 100])  # 12 identical amounts → median 100, MAD 0
    b = compute_baseline((ym, Decimal("100")) for ym in BASELINE for _ in range(2))
    assert b is not None and b.mad == 0 and b.typical_amount == 100
    # max(300, 350, 300, 100) = 350
    at = mv(-350, "2026-10-05")
    above = mv(-350.01, "2026-10-06")
    found = detect(base + [at, above])
    assert [f.movement_id for f in found] == [above.id]
    assert found[0].threshold == Decimal("350.00")


@pytest.mark.parametrize(
    "amounts, expected_threshold",
    [
        ([100] * 12, Decimal("350")),  # typical + min_abs_difference
        ([50] * 12, Decimal("300")),  # min_amount floor
        ([400] * 12, Decimal("1200")),  # typical * median_multiplier
    ],
)
def test_each_threshold_term_is_strict(amounts, expected_threshold):
    hist = history(amounts[:2])  # two per month × 6 months = 12 transactions
    b = compute_baseline((ym, Decimal(amounts[0])) for ym in BASELINE for _ in range(2))
    assert b is not None and b.upper_percentile is None  # 12 samples < 20
    assert compute_threshold(b) == expected_threshold
    equal = mv(-float(expected_threshold), "2026-10-01")
    over = mv(-float(expected_threshold + Decimal("0.01")), "2026-10-02")
    assert [f.movement_id for f in detect(hist + [equal, over])] == [over.id]


def test_mad_term_can_dominate():
    # median 200; |dev| 150,100,100,150 → MAD 125
    # threshold = max(300, 200+250, 200*3, 200+4*125) = 700
    hist = history([50, 100, 300, 350])
    over, equal = mv(-700.01, "2026-10-09"), mv(-700, "2026-10-08")
    assert [f.movement_id for f in detect(hist + [over, equal])] == [over.id]


def test_baseline_window_and_january_boundaries():
    assert baseline_window((2027, 1), 6) == [
        (2026, 7), (2026, 8), (2026, 9), (2026, 10), (2026, 11), (2026, 12),
    ]
    # Today 2027-01-10 → evaluated December 2026, baseline 06/2026 … 11/2026.
    dec_window = baseline_window((2026, 12), 6)
    assert dec_window[0] == (2026, 6) and dec_window[-1] == (2026, 11)

    rich = history([1000, 1000], months=dec_window)  # median 1000 → threshold 3000
    big = mv(-1500, "2026-12-20")
    # Small amounts just *outside* the window (May 2026, the evaluated month,
    # and the future) would drag the median down and flag ``big`` if counted.
    outside = (
        history([10] * 6, months=[(2026, 5)])
        + [mv(-10, f"2026-12-{d:02d}") for d in range(1, 10)]
        + history([10] * 6, months=[(2027, 1)])
    )
    assert detect(rich + outside + [big], month=(2026, 12)) == []
    # Sanity: the same small amounts *inside* the window do flag ``big``.
    inside = history([10] * 12, months=dec_window[:3])
    assert [f.movement_id for f in detect(inside + [big], month=(2026, 12))] == [big.id]


def test_january_alert_through_service_uses_previous_year(tmp_path):
    hist = history(NORMAL, months=baseline_window((2026, 12), 6))
    big = mv(-1200, "2026-12-30", id="dec-big")
    svc = service(tmp_path, hist + [big], today=date(2027, 1, 2))
    svc.refresh()
    [n] = unusual(svc)
    assert n.key == "unexpected_expense:dec-big"
    assert "(06/2026 עד 11/2026)" in n.message
    assert n.context["target_year"] == 2026 and n.context["target_month"] == 12


def test_transfers_refunds_and_invalid_amounts_are_excluded():
    assert expense_amount(mv(-500, "2026-10-01", is_transfer=True)) is None
    assert expense_amount(mv(-500, "2026-10-01", "העברה")) is None
    assert expense_amount(mv(-500, "2026-10-01", transfer_to="חיסכון")) is None
    assert expense_amount(mv(500, "2026-10-01")) is None  # refund / income
    assert expense_amount(mv(0, "2026-10-01")) is None
    assert expense_amount(mv(float("nan"), "2026-10-01")) is None
    assert expense_amount(mv(float("-inf"), "2026-10-01")) is None
    assert to_money("abc") is None and to_money(None) is None
    assert to_money(-1200.1) == Decimal("-1200.10")
    assert expense_amount(mv(-0.1 - 0.2, "2026-10-01")) == Decimal("0.30")

    # Excluded rows don't feed the baseline: only transfers/refunds of 5,000
    # in history → no eligible history → no alert even for a big expense.
    noisy = (
        history([5000] * 3, category="העברה")
        + [replace(m, is_transfer=True, category=CAT) for m in history([5000, 5000])]
        + [replace(m, amount=-m.amount) for m in history([5000, 5000])]
    )
    assert detect(noisy + [mv(-9000, "2026-10-04")]) == []

    # Excluded candidates are never alerted on.
    hist = history(NORMAL)
    candidates = [
        mv(-5000, "2026-10-04", is_transfer=True),
        mv(-5000, "2026-10-05", transfer_from="בנק"),
        mv(5000, "2026-10-06"),  # refund
    ]
    assert detect(hist + candidates) == []


def test_explicitly_planned_expenses_are_suppressed(tmp_path):
    hist = history(NORMAL)
    sofa = InstallmentPlan(
        id="p1", name="ספה", vendor_query="רהיטים", account_name="בנק",
        start_date="2026-01-01", payments_count=10,
    )
    debit = InstallmentPlan(id="dd1", name="ביטוח", kind=KIND_DIRECT_DEBIT, monthly_amount=1500)
    trip = OneTimeEvent(id="ev1", name="טיול", budget=8000)
    house = Mortgage(
        id="h1", name="דירה", vendor_query="משכנתא", account_name="בנק",
        yearly_costs=[CostItem(name="ארנונה שנתית", query="עירייה")],
    )
    planned = [
        mv(-2000, "2026-10-01", id="inst", description="רהיטים בע\"מ"),
        mv(-1500, "2026-10-02", id=direct_debit_movement_id("dd1", 3)),
        mv(-3000, "2026-10-03", id="event", event_id="ev1"),
        mv(-4000, "2026-10-04", id="mortgage", description="משכנתא לאומי"),
        mv(-2500, "2026-10-05", id="annual", description="עירייה תל אביב"),
    ]
    # Generic MONTHLY/YEARLY type alone doesn't make an amount expected, and an
    # event without a budget isn't a budgeted event.
    unplanned = [
        mv(-1800, "2026-10-06", id="monthly", type=MovementType.MONTHLY),
        mv(-1800, "2026-10-07", id="yearly", type=MovementType.YEARLY),
        mv(-1800, "2026-10-08", id="nobudget", event_id="ev2"),
    ]
    svc = service(
        tmp_path, hist + planned + unplanned,
        plans=[sofa, debit], assets=[house],
        events=[trip, OneTimeEvent(id="ev2", name="ללא תקציב", budget=0)],
    )
    svc.refresh()
    keys = {n.key for n in unusual(svc)}
    assert keys == {
        "unexpected_expense:monthly",
        "unexpected_expense:yearly",
        "unexpected_expense:nobudget",
    }


def _login(wid: str) -> None:
    FirebaseSessionStore().save(
        FirebaseSession(
            api_key="k", project_id="p", email="a@x.com", uid="uidA",
            workspace_id=wid, refresh_token="",
        )
    )


def test_workspace_isolation():
    # Workspace A: rich history. Workspace B: the same big expense, no history.
    _login("WS-A")
    JsonFileBankMovementProvider().save_movements(history(NORMAL) + [mv(-1200, "2026-10-10", id="a-big")])
    svc_a = NotificationsService(
        movement_provider=JsonFileBankMovementProvider(),
        installment_provider=ListProvider(),  # type: ignore[arg-type]
        mortgage_provider=ListProvider(),  # type: ignore[arg-type]
        event_provider=ListProvider(),  # type: ignore[arg-type]
        today=lambda: TODAY,
    )
    svc_a.refresh()
    assert [n.key for n in unusual(svc_a)] == ["unexpected_expense:a-big"]

    _login("WS-B")
    JsonFileBankMovementProvider().save_movements([mv(-1200, "2026-10-10", id="b-big")])
    svc_b = NotificationsService(
        movement_provider=JsonFileBankMovementProvider(),
        installment_provider=ListProvider(),  # type: ignore[arg-type]
        mortgage_provider=ListProvider(),  # type: ignore[arg-type]
        event_provider=ListProvider(),  # type: ignore[arg-type]
        today=lambda: TODAY,
    )
    svc_b.refresh()
    # A's history doesn't make B's expense unusual, and A's alert isn't visible in B.
    assert unusual(svc_b, include_closed=True) == []

    _login("WS-A")
    assert [n.key for n in unusual(svc_a)] == ["unexpected_expense:a-big"]


# ── lifecycle ─────────────────────────────────────────────────────────────


def test_repeated_evaluation_creates_no_duplicates(tmp_path):
    svc = service(tmp_path, history(NORMAL) + [mv(-1200, "2026-10-14", id="big")])
    svc.refresh()
    first = unusual(svc)
    svc.refresh()
    svc.refresh()
    again = unusual(svc)
    assert len(again) == 1 and again[0].id == first[0].id
    assert again[0].created_at == first[0].created_at


@pytest.mark.parametrize("handled", [NotificationStatus.RESOLVED, NotificationStatus.DISMISSED])
def test_legacy_closed_alert_without_reason_stays_closed(tmp_path, handled):
    """A closed record with no ``closed_by`` (written before the field
    existed) is treated as a user decision, even while it still qualifies."""
    svc = service(tmp_path, history(NORMAL) + [mv(-1200, "2026-10-14", id="big")])
    svc.refresh()
    svc._provider.update_status(key="unexpected_expense:big", status=handled)  # noqa: SLF001
    svc.refresh()
    svc.refresh()
    [n] = unusual(svc, include_closed=True)
    assert n.status == handled and n.closed_by is None


def _seed(svc: NotificationsService, key: str, *, status=NotificationStatus.UNREAD, message="הוצאה חריגה (טופ 20%) בסכום ₪260.00", context=None, closed_by=None) -> Notification:
    n = Notification(
        id=f"id-{key}", key=key, type=NotificationType.UNEXPECTED_EXPENSE,
        title="הוצאה חריגה", message=message, severity=NotificationSeverity.WARNING,
        created_at="2026-10-01", status=status, source="rule:unexpected_expense",
        context=context or {}, closed_by=closed_by,
    )
    svc._provider.upsert(n)  # noqa: SLF001
    return n


def test_reconciles_obsolete_open_alerts_but_not_duplicates(tmp_path):
    normal = mv(-260, "2026-10-03", id="normal")
    big = mv(-1200, "2026-10-14", id="big")
    old_month = mv(-240, "2026-08-20", id="aug")  # old alert, ordinary for August
    dups = [mv(-99, "2026-10-09", id="d1", description="x"), mv(-99, "2026-10-09", id="d2", description="x")]
    svc = service(tmp_path, history(NORMAL, months=baseline_window((2026, 8), 6)) + history(NORMAL) + [normal, big, old_month] + dups)

    _seed(svc, "unexpected_expense:normal")
    _seed(svc, "unexpected_expense:aug", status=NotificationStatus.READ)
    _seed(svc, "unexpected_expense:gone")  # movement was deleted
    _seed(svc, "unexpected_expense:big", status=NotificationStatus.READ)  # old-style text
    dup_key = "unexpected_expense:duplicate:2026-09-01:50.00:old"
    _seed(svc, dup_key, message="זוהו 2 הוצאות זהות באותו יום (₪50.00).")

    svc.refresh()
    by_key = {n.key: n for n in svc._provider.list_notifications()}  # noqa: SLF001

    for k in ("normal", "aug", "gone"):
        n = by_key[f"unexpected_expense:{k}"]
        assert n.status == NotificationStatus.RESOLVED  # closed, history kept
        assert n.closed_by == CLOSED_BY_SYSTEM
        assert n.message == "הוצאה חריגה (טופ 20%) בסכום ₪260.00"

    # Still-qualifying open alert: same identity & status, refreshed explanation.
    b = by_key["unexpected_expense:big"]
    assert b.id == "id-unexpected_expense:big" and b.status == NotificationStatus.READ
    assert b.created_at == "2026-10-01"
    assert b.message.startswith("הוצאה של 1,200 ש״ח בקטגוריית מסעדות.")

    # Duplicate-charge alerts are untouched, and new ones still get created.
    assert by_key[dup_key].status == NotificationStatus.UNREAD
    assert by_key[dup_key].closed_by is None
    assert any(k.startswith("unexpected_expense:duplicate:2026-10-09") for k in by_key)


def test_old_month_alert_that_still_qualifies_stays_open(tmp_path):
    aug_window = baseline_window((2026, 8), 6)
    svc = service(tmp_path, history(NORMAL, months=aug_window) + [mv(-1500, "2026-08-11", id="aug-big")])
    _seed(svc, "unexpected_expense:aug-big")
    svc.refresh()
    [n] = unusual(svc)
    assert n.key == "unexpected_expense:aug-big" and n.status == NotificationStatus.UNREAD
    assert "(02/2026 עד 07/2026)" in n.message


def test_detector_error_creates_nothing_and_closes_nothing(tmp_path):
    class Broken:  # only the unusual-expense detector reads installment plans
        def list_plans(self):
            raise RuntimeError("boom")

    dups = [mv(-99, "2026-10-09", id="d1", description="x"), mv(-99, "2026-10-09", id="d2", description="x")]
    svc = service(
        tmp_path,
        history(NORMAL) + [mv(-1200, "2026-10-14", id="big"), mv(-260, "2026-10-03", id="normal")] + dups,
        installment_provider=Broken(),
    )
    _seed(svc, "unexpected_expense:normal")
    svc.refresh()
    items = {n.key: n for n in svc._provider.list_notifications()}  # noqa: SLF001
    assert "unexpected_expense:big" not in items  # no fallback alert
    assert items["unexpected_expense:normal"].status == NotificationStatus.UNREAD
    assert any(":duplicate:" in k for k in items)  # duplicates unaffected


def test_works_without_ai_key_or_network(tmp_path):
    # The autouse fixture blocks sockets and makes any Gemini call fail.
    svc = service(tmp_path, history(NORMAL) + [mv(-1200, "2026-10-14", id="big")])
    svc.refresh()
    assert [n.key for n in unusual(svc)] == ["unexpected_expense:big"]
    assert svc.unread_count() >= 1


# ── recurring payments ────────────────────────────────────────────────────

# 12 small housing expenses (median 90): fewer than 20 samples even with a few
# rents added, so these tests isolate recurrence from the percentile term.
SMALL_HOUSING = [60, 120]


def rent(amount, date_str, *, account="בנק", desc="שכר דירה", id=None, category="מגורים"):
    return mv(-amount, date_str, category, id=id, account_name=account, description=desc)


def _rent_history(dates, amount=3600, **kw):
    return [rent(amount, d, **kw) for d in dates]


def _decision(movements, movement_id, month=EVAL, **kw):
    [d] = [x for x in evaluate_month(movements, evaluated_month=month, **kw) if x.movement_id == movement_id]
    return d


def test_stable_monthly_payment_is_suppressed_after_three_prior_months():
    base = history(SMALL_HOUSING, category="מגורים")
    cand = rent(3600, "2026-10-01", id="oct")
    two = _rent_history(["2026-08-01", "2026-09-01"])
    d = _decision(base + two + [cand], "oct")
    assert d.outcome == Outcome.ALERT  # two months is not yet a pattern

    three = _rent_history(["2026-07-01", "2026-08-01", "2026-09-01"])
    d = _decision(base + three + [cand], "oct")
    assert d.outcome == Outcome.RECURRING and not d.eligible
    assert d.recurrence is not None and d.recurrence.fits
    assert d.recurrence.occurrence_dates == ("2026-07-01", "2026-08-01", "2026-09-01")
    assert d.recurrence.reference_amount == Decimal("3600.00")
    assert d.recurrence.tolerance == Decimal("360.00")
    # A "monthly" type or the category alone is not evidence of anything.
    monthly_only = mv(-3600, "2026-10-01", "מגורים", id="typed", type=MovementType.MONTHLY)
    assert _decision(base + [monthly_only], "typed").outcome == Outcome.ALERT


def test_materially_increased_recurring_payment_stays_eligible():
    base = history(SMALL_HOUSING, category="מגורים")
    prior = _rent_history(["2026-06-01", "2026-07-01", "2026-08-01", "2026-09-01"])
    small_rise = rent(3700, "2026-10-01", id="rise")  # within 10%
    assert _decision(base + prior + [small_rise], "rise").outcome == Outcome.RECURRING

    jump = rent(4500, "2026-10-01", id="jump")  # +25%
    d = _decision(base + prior + [jump], "jump")
    assert d.outcome == Outcome.RECURRING_INCREASE and d.is_alert
    assert d.recurrence is not None and not d.recurrence.fits  # evidence kept for inspection


def test_unrelated_merchants_and_other_accounts_are_not_merged():
    base = history(SMALL_HOUSING, category="מגורים")
    prior = _rent_history(["2026-07-01", "2026-08-01", "2026-09-01"])
    other_account = rent(3600, "2026-10-01", id="acct", account="כרטיס אשראי")
    other_merchant = rent(3600, "2026-10-01", id="merch", desc="שכר דירה חניה")
    for mid, cand in (("acct", other_account), ("merch", other_merchant)):
        assert _decision(base + prior + [cand], mid).outcome == Outcome.ALERT

    # Three different payees, one month each, are not one monthly payment.
    mixed = [
        rent(3600, "2026-07-01", desc="ספק א"),
        rent(3600, "2026-08-01", desc="ספק ב"),
        rent(3600, "2026-09-01", desc="ספק ג"),
    ]
    assert _decision(base + mixed + [rent(3600, "2026-10-01", id="x", desc="ספק ג")], "x").outcome == Outcome.ALERT

    # Normalization is conservative: marks/quotes/spacing/case only.
    a = mv(-1, "2026-01-01", description="\u202bביטוח  מקיף\u202c")
    b = mv(-1, "2026-01-01", description="ביטוח מקיף")
    assert merchant_key(a) == merchant_key(b)
    assert merchant_key(mv(-1, "2026-01-01", description="Netflix")) == merchant_key(mv(-1, "2026-01-01", description="NETFLIX"))
    assert merchant_key(mv(-1, "2026-01-01", description="ביטוח 2025")) != merchant_key(mv(-1, "2026-01-01", description="ביטוח 2026"))


def test_month_end_and_shifted_payment_dates_are_monthly():
    base = history(SMALL_HOUSING, category="מגורים")
    month_end = _rent_history(["2026-06-30", "2026-07-31", "2026-08-31", "2026-09-30"])
    assert _decision(base + month_end + [rent(3600, "2026-10-31", id="eom")], "eom").outcome == Outcome.RECURRING

    # July's payment went out early (29 Jun), August's late (3 Aug).
    shifted = _rent_history(["2026-06-29", "2026-08-03", "2026-09-01"])
    assert _decision(base + shifted + [rent(3600, "2026-10-02", id="sh")], "sh").outcome == Outcome.RECURRING

    # A missed month breaks the chain: Jun, Jul, (no Aug), Sep → not established.
    gap = _rent_history(["2026-06-01", "2026-07-01", "2026-09-01"])
    assert _decision(base + gap + [rent(3600, "2026-10-01", id="gap")], "gap").outcome == Outcome.ALERT


def test_frequent_shop_is_not_a_monthly_payment():
    # Several similar charges a month at one shop: never "recurring", even
    # though a monthly chain of similar amounts could be picked out.
    base = history(NORMAL, category="סופר")
    shop = []
    for y, m in BASELINE[-4:]:
        for day in (3, 10, 17):
            shop.append(mv(-1000, f"{y}-{m:02d}-{day:02d}", "סופר", description="שופרסל"))
    cand = mv(-1000, "2026-10-04", "סופר", id="shop", description="שופרסל")
    assert _decision(base + shop + [cand], "shop").outcome != Outcome.RECURRING


def test_recurrence_uses_only_history_before_the_evaluated_month():
    base = history(SMALL_HOUSING, category="מגורים")
    # Earlier same-month and later charges must not count as evidence.
    same_month_and_future = _rent_history(["2026-10-01", "2026-11-01", "2026-12-01", "2027-01-01"])
    cand = rent(3600, "2026-10-28", id="late")
    assert _decision(base + same_month_and_future + [cand], "late").outcome == Outcome.ALERT


# ── broad distributions / percentile ──────────────────────────────────────


def _shopping_history():
    """Mostly small purchases plus a regular tail of larger weekly shops."""
    out = []
    for y, m in BASELINE:
        for i, a in enumerate([25, 35, 40, 50, 55, 60, 65, 70, 80, 90]):
            out.append(mv(-a, f"{y}-{m:02d}-{i + 1:02d}", "קניות"))
        for i, a in enumerate([320, 380, 450, 520]):
            out.append(mv(-a, f"{y}-{m:02d}-{i + 15:02d}", "קניות"))
    return out  # 84 samples; median 67.5; P95 = 450..520 range


def test_broad_shopping_distribution_keeps_ordinary_big_shops_quiet():
    hist = _shopping_history()
    ordinary = mv(-600, "2026-10-08", "קניות", id="ordinary")
    exceptional = mv(-2400, "2026-10-09", "קניות", id="exceptional")
    decisions = {d.movement_id: d for d in evaluate_month(hist + [ordinary, exceptional], evaluated_month=EVAL)}
    o, e = decisions["ordinary"], decisions["exceptional"]
    assert o.baseline is not None
    # Median-only checks would flag 600 (base threshold is ~300)…
    assert o.base_threshold is not None and Decimal("600") > o.base_threshold
    # …but the historical upper range says it's an ordinary large shop.
    assert o.baseline.upper_percentile == Decimal("520.00")  # nearest-rank P95 of 84
    assert o.percentile_threshold == Decimal("650.00")  # 520 × 1.25
    assert o.threshold == Decimal("650.00") and o.outcome == Outcome.WITHIN_THRESHOLD
    assert e.outcome == Outcome.ALERT


def test_nearest_rank_percentile_is_deterministic():
    vals = [Decimal(x) for x in range(1, 21)]  # 1..20
    assert nearest_rank(vals, Decimal("0.95")) == Decimal(19)
    assert nearest_rank(vals, Decimal("1")) == Decimal(20)
    assert nearest_rank(vals, Decimal("0")) == Decimal(1)
    assert nearest_rank(list(reversed(vals)), Decimal("0.5")) == Decimal(10)


def test_percentile_needs_enough_samples_and_boundary_is_strict():
    # 19 samples → percentile term unused; 20 → used.
    def hist(n):
        amounts = [Decimal(100)] * (n - 2) + [Decimal(1000), Decimal(1000)]
        return [(BASELINE[i % 6], a) for i, a in enumerate(amounts)]

    b19 = compute_baseline(hist(19))
    b20 = compute_baseline(hist(20))
    assert b19 is not None and b19.upper_percentile is None and compute_threshold(b19) == Decimal("350")
    assert b20 is not None and b20.upper_percentile == Decimal("1000")
    assert compute_threshold(b20) == Decimal("1250.00")

    movements = []
    for i in range(20):
        y, m = BASELINE[i % 6]
        movements.append(mv(-(1000 if i >= 18 else 100), f"{y}-{m:02d}-{i + 1:02d}"))
    at = mv(-1250, "2026-10-01", id="at")
    over = mv(-1250.01, "2026-10-02", id="over")
    assert [d.movement_id for d in detect(movements + [at, over])] == ["over"]


def test_percentile_ignores_evaluated_month_future_and_expected_payments():
    hist = _shopping_history()
    # Huge purchases in the evaluated month and in the future must not stretch
    # the upper range used to judge October.
    noise = [mv(-5000, f"2026-10-{d:02d}", "קניות") for d in range(10, 20)]
    noise += [mv(-5000, f"2026-11-{d:02d}", "קניות") for d in range(1, 20)]
    d = _decision(hist + noise + [mv(-2400, "2026-10-21", "קניות", id="big")], "big")
    assert d.baseline is not None and d.baseline.upper_percentile == Decimal("520.00")
    assert d.outcome == Outcome.ALERT

    # A large fixed bill (rent) stays in the median, but is not "ordinary"
    # spending for the percentile, so it can't hide other large housing costs.
    base = history([60, 80, 100, 120], category="מגורים")  # 24 samples
    rents = _rent_history([f"{y}-{m:02d}-01" for y, m in [(2026, 1), (2026, 2), (2026, 3)] + BASELINE])
    bill = mv(-1500, "2026-10-15", "מגורים", id="bill", description="ארנונה")
    d = _decision(base + rents + [bill], "bill")
    assert d.baseline is not None and d.baseline.count == 30  # rent counted in median history
    assert d.baseline.upper_percentile == Decimal("120.00")  # but not in the percentile sample
    assert d.outcome == Outcome.ALERT


def test_unlinked_large_payment_alerts_and_price_link_suppresses(tmp_path):
    base = history(NORMAL, category="שונות")
    pay = mv(-181000, "2026-10-09", "שונות", id="house", description="קניית דירה")
    svc = service(tmp_path, base + [pay])
    svc.refresh()
    assert [n.key for n in unusual(svc)] == ["unexpected_expense:house"]

    linked = Mortgage(id="h1", name="דירה", price_query="קניית דירה")
    (tmp_path / "linked").mkdir()
    svc2 = service(tmp_path / "linked", base + [pay], assets=[linked])
    svc2.refresh()
    assert unusual(svc2, include_closed=True) == []


def test_decisions_are_inspectable_and_carry_no_description_text():
    hist = history(NORMAL)
    cand = mv(-1200, "2026-10-14", id="big", description="מסעדת הסוד")
    decisions = evaluate_month(hist + [cand, mv(500, "2026-10-02", id="refund")], evaluated_month=EVAL)
    by = {d.movement_id: d for d in decisions}
    assert by["refund"].outcome == Outcome.NOT_EXPENSE and not by["refund"].eligible
    d = by["big"]
    assert d.eligible and d.is_alert
    assert (d.period_start, d.period_end) == ((2026, 4), (2026, 9))
    assert d.baseline is not None and d.baseline.count == 24 and d.baseline.distinct_months == 6
    assert d.baseline.typical_amount == Decimal("190") and d.baseline.mad == Decimal("25")
    assert d.base_threshold == Decimal("570") and d.threshold == Decimal("570")
    assert "מסעדת הסוד" not in repr(d)


# ── automatic closure vs user handling ────────────────────────────────────


def test_auto_closed_alert_reopens_same_record_when_it_qualifies_again(tmp_path):
    hist = history(NORMAL)
    big = mv(-1200, "2026-10-14", id="big")
    movements = ListProvider(hist + [big])
    svc = NotificationsService(
        provider=JsonFileNotificationsProvider(tmp_path / "n.json"),
        movement_provider=movements,  # type: ignore[arg-type]
        installment_provider=ListProvider(),  # type: ignore[arg-type]
        mortgage_provider=ListProvider(),  # type: ignore[arg-type]
        event_provider=ListProvider(),  # type: ignore[arg-type]
        today=lambda: TODAY,
    )
    svc.refresh()
    [first] = unusual(svc)

    # The user corrects the amount → no longer unusual → closed automatically.
    movements.items[-1] = replace(big, amount=-200)
    svc.refresh()
    [closed] = unusual(svc, include_closed=True)
    assert closed.status == NotificationStatus.RESOLVED and closed.closed_by == CLOSED_BY_SYSTEM
    svc.refresh()  # idempotent while closed
    assert unusual(svc, include_closed=True) == [closed]

    # Corrected back → the *same* record reopens.
    movements.items[-1] = replace(big, amount=-1500)
    svc.refresh()
    [reopened] = unusual(svc, include_closed=True)
    assert reopened.id == first.id and reopened.created_at == first.created_at
    assert reopened.status == NotificationStatus.UNREAD and reopened.closed_by is None
    assert reopened.message.startswith("הוצאה של 1,500 ש״ח")
    svc.refresh()
    assert unusual(svc, include_closed=True) == [reopened]


def test_user_handled_alert_never_reopens(tmp_path):
    svc = service(tmp_path, history(NORMAL) + [mv(-1200, "2026-10-14", id="big")])
    svc.refresh()
    svc.resolve("unexpected_expense:big")
    for _ in range(3):
        svc.refresh()
    [n] = unusual(svc, include_closed=True)
    assert n.status == NotificationStatus.RESOLVED and n.closed_by == CLOSED_BY_USER


def test_closure_reason_survives_local_storage(tmp_path):
    prov = JsonFileNotificationsProvider(tmp_path / "n.json")
    svc = service(tmp_path, [])
    n = _seed(svc, "unexpected_expense:a")
    prov.upsert(n)
    prov.update_status(key=n.key, status=NotificationStatus.RESOLVED, closed_by=CLOSED_BY_SYSTEM)
    assert JsonFileNotificationsProvider(tmp_path / "n.json").list_notifications()[0].closed_by == CLOSED_BY_SYSTEM
    prov.update_status(key=n.key, status=NotificationStatus.UNREAD, closed_by=CLOSED_BY_SYSTEM)
    assert prov.list_notifications()[0].closed_by is None  # reopening clears it
    # Legacy JSON without the field loads as unknown.
    raw = (tmp_path / "n.json").read_text(encoding="utf-8").replace('"closed_by": null, ', "").replace(', "closed_by": null', "")
    (tmp_path / "n.json").write_text(raw, encoding="utf-8")
    assert prov.list_notifications()[0].closed_by is None


class FakeFirestore:
    """Just enough of FirestoreClient for the notifications puller."""

    def __init__(self, docs):
        self.docs = docs

    def list_collection(self, **_kw):
        return list(self.docs)

    @staticmethod
    def parse_any_doc(doc):
        return doc["key"], dict(doc)


def _remote(key, status, closed_by=None, message="remote", id=None):
    return {
        "id": id or f"id-{key}", "key": key, "type": "unexpected_expense", "title": "הוצאה חריגה",
        "message": message, "severity": "warning", "created_at": "2026-10-01",
        "status": status, "source": "rule:unexpected_expense", "context": {},
        "closed_by": closed_by,
    }


def test_sync_pull_keeps_closure_reasons_and_never_duplicates(tmp_path, monkeypatch):
    from finance.models.firebase_sync_workspace_cache import pull_notifications_to_local_cache

    _login("WS-SYNC")
    local = JsonFileNotificationsProvider()  # default path = this workspace
    big = mv(-1200, "2026-10-14", id="big")
    svc = NotificationsService(
        provider=local,
        movement_provider=ListProvider(history(NORMAL) + [big]),  # type: ignore[arg-type]
        installment_provider=ListProvider(),  # type: ignore[arg-type]
        mortgage_provider=ListProvider(),  # type: ignore[arg-type]
        event_provider=ListProvider(),  # type: ignore[arg-type]
        today=lambda: TODAY,
    )
    svc.refresh()
    [mine] = unusual(svc)

    # Another device: the user handled it. Pull keeps a tombstone with the reason.
    fs = FakeFirestore([_remote("unexpected_expense:big", "resolved", CLOSED_BY_USER, id=mine.id)])
    pull_notifications_to_local_cache(fs=fs, workspace_id="WS-SYNC", id_token="t")  # type: ignore[arg-type]
    [n] = unusual(svc, include_closed=True)
    assert n.status == NotificationStatus.RESOLVED and n.closed_by == CLOSED_BY_USER
    svc.refresh()  # still qualifies, but the user's decision stands; no duplicate
    assert unusual(svc, include_closed=True) == [n]

    # A local user decision beats a remote open copy.
    fs.docs = [_remote("unexpected_expense:big", "unread", id=mine.id)]
    pull_notifications_to_local_cache(fs=fs, workspace_id="WS-SYNC", id_token="t")  # type: ignore[arg-type]
    assert unusual(svc, include_closed=True)[0].closed_by == CLOSED_BY_USER

    # An automatic local closure yields to the remote copy.
    _seed(svc, "unexpected_expense:auto", status=NotificationStatus.RESOLVED, closed_by=CLOSED_BY_SYSTEM)
    fs.docs = [_remote("unexpected_expense:auto", "unread", message="reopened elsewhere")]
    pull_notifications_to_local_cache(fs=fs, workspace_id="WS-SYNC", id_token="t")  # type: ignore[arg-type]
    auto = {x.key: x for x in local.list_notifications()}["unexpected_expense:auto"]
    assert auto.status == NotificationStatus.UNREAD and auto.closed_by is None

    # A remote automatic closure is stored with its reason (not dropped).
    fs.docs = [_remote("unexpected_expense:auto", "resolved", CLOSED_BY_SYSTEM)]
    pull_notifications_to_local_cache(fs=fs, workspace_id="WS-SYNC", id_token="t")  # type: ignore[arg-type]
    auto = {x.key: x for x in local.list_notifications()}["unexpected_expense:auto"]
    assert auto.status == NotificationStatus.RESOLVED and auto.closed_by == CLOSED_BY_SYSTEM
    assert len([x for x in local.list_notifications() if x.key == "unexpected_expense:big"]) == 1
    assert mine.id == n.id


def test_writer_pushes_closure_reason(monkeypatch):
    from finance.models.firebase_workspace_writer import FirebaseWorkspaceWriter

    sent = {}

    class FS:
        def upsert_document(self, *, document_path, id_token, fields):
            sent[document_path] = fields

    w = FirebaseWorkspaceWriter()
    monkeypatch.setattr(w, "_load_session_refresh_if_needed", lambda: type("S", (), {"project_id": "p", "id_token": "t"})())
    monkeypatch.setattr(w, "_ensure_workspace", lambda _s: "WS")
    monkeypatch.setattr(w, "_fs", lambda _p: FS())
    n = Notification(
        id="i", key="unexpected_expense:k", type=NotificationType.UNEXPECTED_EXPENSE, title="t",
        message="m", severity=NotificationSeverity.WARNING, created_at="2026-10-01",
        status=NotificationStatus.RESOLVED, closed_by=CLOSED_BY_SYSTEM,
    )
    w.upsert_notification(n)
    assert sent["workspaces/WS/notifications/unexpected_expense:k"]["closed_by"] == CLOSED_BY_SYSTEM


# ── account coverage & comparison boundaries ──────────────────────────────


def test_every_spending_account_is_evaluated_and_shares_category_history():
    # History spread across bank, Sibus (budget card), cash and a Bit wallet:
    # one category history for the whole budget, regardless of account.
    hist = []
    for i, (y, m) in enumerate(BASELINE):
        for j, acct in enumerate(("בנק", "סיבוס", "מזומן", "ביט")):
            hist.append(mv(-(150 + 10 * j), f"{y}-{m:02d}-{j + 1:02d}", account_name=acct))
    cands = [
        mv(-1200, "2026-10-03", id=f"c-{acct}", account_name=acct)
        for acct in ("בנק", "סיבוס", "מזומן", "ביט", "פייבוקס")
    ]
    decisions = {d.movement_id: d for d in evaluate_month(hist + cands, evaluated_month=EVAL)}
    for acct in ("בנק", "סיבוס", "מזומן", "ביט", "פייבוקס"):
        d = decisions[f"c-{acct}"]
        assert d.is_alert, acct
        assert d.baseline is not None and d.baseline.count == 24  # all accounts' history


def test_median_mad_and_percentile_share_the_same_account_boundary():
    # 30 samples split across two accounts; the percentile sample is the same
    # set (nothing here is planned or recurring).
    hist = []
    for i in range(30):
        y, m = BASELINE[i % 6]
        hist.append(mv(-(100 + i), f"{y}-{m:02d}-{i % 28 + 1:02d}", account_name="בנק" if i % 2 else "סיבוס"))
    b = _decision(hist + [mv(-50, "2026-10-01", id="c")], "c").baseline
    amounts = sorted(Decimal(100 + i) for i in range(30))
    assert b is not None and b.count == 30
    assert b.typical_amount == (amounts[14] + amounts[15]) / 2
    assert b.upper_percentile == nearest_rank(amounts, Decimal("0.95"))


def test_transfers_and_settlement_legs_are_not_spending():
    hist = history(NORMAL)
    # A savings withdrawal / wallet top-up recorded by the app's transfer flow
    # (both legs flagged), a legacy leg identified only by its endpoints, and a
    # row in the "העברה" category: none of them is spending, on any account.
    legs = [
        mv(-5000, "2026-10-05", "העברה", id="out", account_name="פיקדון -- חיסכון", is_transfer=True),
        mv(5000, "2026-10-05", "העברה", id="in", account_name="בנק", is_transfer=True),
        mv(-800, "2026-10-06", CAT, id="topup", account_name="בנק", transfer_to="ביט"),
        mv(-900, "2026-10-07", "העברה", id="cat-only", account_name="בנק"),
    ]
    decisions = {d.movement_id: d for d in evaluate_month(hist + legs, evaluated_month=EVAL)}
    assert all(decisions[k].outcome == Outcome.NOT_EXPENSE for k in ("out", "in", "topup", "cat-only"))
    # …and they never enter the category history either.
    old_legs = [replace(x, date="2026-08-05", id=x.id + "-old") for x in legs]
    d = _decision(hist + old_legs + [mv(-10, "2026-10-01", id="c")], "c")
    assert d.baseline is not None and d.baseline.count == 24


def test_reimbursement_income_does_not_offset_or_join_expense_history():
    hist = history(NORMAL)
    refunds = [mv(400, f"{y}-{m:02d}-20", "החזר") for y, m in BASELINE]  # income
    d = _decision(hist + refunds + [mv(-1200, "2026-10-14", id="big")], "big")
    assert d.baseline is not None and d.baseline.count == 24 and d.is_alert


# ── significant increase of a recurring payment ───────────────────────────


def _rent_dominated_category():
    """A category whose history is mostly the rent itself (median ≈ 3,600):
    the category threshold alone (≥ 3 × 3,600) would hide a rent rise."""
    months = [(2026, 1), (2026, 2), (2026, 3)] + BASELINE
    rents = _rent_history([f"{y}-{m:02d}-01" for y, m in months], category="שכר דירה")
    extras = [mv(-3500, f"{y}-{m:02d}-15", "שכר דירה", description=f"תיקון {i}") for i, (y, m) in enumerate(BASELINE)]
    return rents + extras


def test_rent_rising_from_3600_to_4200_is_reported():
    hist = _rent_dominated_category()
    cand = rent(4200, "2026-10-01", id="rise", category="שכר דירה")
    d = _decision(hist + [cand], "rise")
    assert d.outcome == Outcome.RECURRING_INCREASE
    ev = d.recurrence
    assert ev is not None and ev.frequency == "monthly"
    assert ev.reference_amount == Decimal("3600.00") and ev.increase == Decimal("600.00")
    assert not d.recurrence is None and len(ev.occurrence_dates) >= 3

    # Without the dedicated path, the category threshold would have hidden it.
    no_increase = UnusualExpenseConfig(recurrence=RecurrenceConfig(increase_min_abs=Decimal("1e9")))
    hidden = _decision(hist + [cand], "rise", config=no_increase)
    assert hidden.outcome == Outcome.WITHIN_THRESHOLD

    from finance.models.unusual_expense_detector import decision_title, format_unusual_expense_message
    assert decision_title(d) == "עלייה בחיוב קבוע"
    assert format_unusual_expense_message(d) == (
        "חיוב חודשי קבוע בקטגוריית שכר דירה עלה מ־3,600 ש״ח ל־4,200 ש״ח, "
        f"על סמך {len(ev.occurrence_dates)} חיובים קודמים."
    )


def test_small_rises_decreases_and_timing_shifts_are_not_increases():
    hist = _rent_dominated_category()
    for amount, mid in ((3950, "small"), (3000, "down")):  # +9.7% fits; −17%
        d = _decision(hist + [rent(amount, "2026-10-01", id=mid, category="שכר דירה")], mid)
        assert d.outcome != Outcome.RECURRING_INCREASE, mid
    # +12% (outside tolerance, below the 15% increase bar) → category path.
    d = _decision(hist + [rent(4040, "2026-10-01", id="mid", category="שכר דירה")], "mid")
    assert d.outcome == Outcome.WITHIN_THRESHOLD
    # Paid 10 days late (40-day gap): no established timing → no increase claim.
    d = _decision(hist + [rent(4200, "2026-10-11", id="late", category="שכר דירה")], "late")
    assert d.outcome != Outcome.RECURRING_INCREASE
    # The increase rule needs both bars: +₪60 on a ₪300 charge is +20% but < ₪100.
    small = _rent_history(["2026-07-05", "2026-08-05", "2026-09-05"], amount=300, desc="מנוי", category=CAT)
    d = _decision(history(NORMAL) + small + [rent(360, "2026-10-05", id="sub", desc="מנוי", category=CAT)], "sub")
    assert d.outcome != Outcome.RECURRING_INCREASE


def test_increase_that_is_also_unusual_creates_one_notification(tmp_path):
    base = history(SMALL_HOUSING, category="מגורים")
    prior = _rent_history(["2026-07-01", "2026-08-01", "2026-09-01"])
    cand = rent(9000, "2026-10-01", id="both")  # far above category threshold too
    svc = service(tmp_path, base + prior + [cand])
    svc.refresh()
    svc.refresh()
    [n] = unusual(svc)
    assert n.key == "unexpected_expense:both" and n.title == "עלייה בחיוב קבוע"
    assert n.context["reason"] == "recurring_increase"
    assert n.context["recurrence_reference"] == "3600.00"


# ── weekly recurrence ─────────────────────────────────────────────────────


def _weekly(dates, amount=450, account="מזומן", desc="טיפול"):
    return [mv(-amount, d, "בריאות", account_name=account, description=desc) for d in dates]


WEEKLY_SEP = ["2026-09-01", "2026-09-08", "2026-09-15", "2026-09-22", "2026-09-29"]
HEALTH = history([80, 120], category="בריאות")  # 12 samples, median 100


def test_regular_weekly_payment_is_recognised_all_month():
    for day, mid in (("2026-10-06", "early"), ("2026-10-27", "late")):
        cand = mv(-450, day, "בריאות", id=mid, account_name="מזומן", description="טיפול")
        d = _decision(HEALTH + _weekly(WEEKLY_SEP) + [cand], mid)
        assert d.outcome == Outcome.RECURRING, mid
        assert d.recurrence is not None and d.recurrence.frequency == "weekly"
        assert d.recurrence.occurrence_dates[-1] == "2026-09-29"


def test_weekly_needs_enough_history_and_ignores_the_evaluated_month():
    cand = mv(-450, "2026-10-06", "בריאות", id="c", account_name="מזומן", description="טיפול")
    three = _weekly(WEEKLY_SEP[-3:])
    assert _decision(HEALTH + three + [cand], "c").outcome == Outcome.ALERT
    # Earlier charges in the evaluated month itself are not evidence.
    in_month = _weekly(["2026-10-01", "2026-10-08", "2026-10-15", "2026-10-22"])
    late = mv(-450, "2026-10-29", "בריאות", id="late", account_name="מזומן", description="טיפול")
    assert _decision(HEALTH + in_month + [late], "late").outcome == Outcome.ALERT


def test_weekly_missing_occurrences_break_the_pattern():
    cand = mv(-450, "2026-10-06", "בריאות", id="c", account_name="מזומן", description="טיפול")
    lapsed = _weekly(["2026-08-25", "2026-09-01", "2026-09-08", "2026-09-15"])  # then stopped
    assert _decision(HEALTH + lapsed + [cand], "c").outcome == Outcome.ALERT
    holey = _weekly(["2026-09-01", "2026-09-15", "2026-09-22", "2026-09-29"])  # 8 Sep missing
    assert _decision(HEALTH + holey + [cand], "c").outcome == Outcome.ALERT


def test_irregular_or_frequent_shopping_is_not_weekly():
    cand = mv(-450, "2026-10-06", "בריאות", id="c", account_name="מזומן", description="טיפול")
    irregular = _weekly(["2026-09-02", "2026-09-05", "2026-09-15", "2026-09-21", "2026-09-30"])
    d = _decision(HEALTH + irregular + [cand], "c")
    assert d.outcome not in (Outcome.RECURRING, Outcome.RECURRING_INCREASE) and d.recurrence is None
    # Weekly-looking chain plus extra visits in between → a shop, not a payment.
    busy = _weekly(WEEKLY_SEP) + _weekly(["2026-09-04", "2026-09-11", "2026-09-18"], amount=430)
    d = _decision(HEALTH + busy + [cand], "c")
    assert d.outcome not in (Outcome.RECURRING, Outcome.RECURRING_INCREASE) and d.recurrence is None


def test_weekly_increase_is_reported_and_other_accounts_do_not_count():
    up = mv(-600, "2026-10-06", "בריאות", id="up", account_name="מזומן", description="טיפול")
    d = _decision(HEALTH + _weekly(WEEKLY_SEP) + [up], "up")
    assert d.outcome == Outcome.RECURRING_INCREASE
    assert d.recurrence is not None and d.recurrence.frequency == "weekly"
    from finance.models.unusual_expense_detector import format_unusual_expense_message
    assert format_unusual_expense_message(d).startswith("חיוב שבועי קבוע בקטגוריית בריאות עלה מ־450 ש״ח ל־600 ש״ח")
    other = mv(-450, "2026-10-06", "בריאות", id="o", account_name="ביט", description="טיפול")
    assert _decision(HEALTH + _weekly(WEEKLY_SEP) + [other], "o").outcome == Outcome.ALERT


def test_monthly_rule_is_unchanged_by_weekly_support():
    assert MONTHLY.min_occurrences == 3 and MONTHLY.max_charges_per_month == 2


# ── catch-all categories (explicit configuration only) ────────────────────


def test_percentile_can_be_disabled_for_configured_categories():
    # A mixed category: 36 small items plus two one-off gifts. With 38
    # samples the nearest-rank P95 is the 37th value — the smaller gift — so
    # two unrelated one-offs define the "ordinary" upper range.
    hist = []
    for y, m in BASELINE:
        for j, a in enumerate([40, 60, 80, 100, 120, 150]):
            hist.append(mv(-a, f"{y}-{m:02d}-{j + 1:02d}", "שונות"))
    hist += [mv(-1650, "2026-05-20", "שונות"), mv(-1500, "2026-07-20", "שונות")]
    cand = mv(-890, "2026-10-12", "שונות", id="pc")
    d = _decision(hist + [cand], "pc")
    assert d.baseline is not None and d.baseline.upper_percentile == Decimal("1500.00")
    assert d.base_threshold == Decimal("350.00") and d.percentile_threshold == Decimal("1875.00")
    assert d.outcome == Outcome.WITHIN_THRESHOLD  # hidden by the percentile term

    cfg = UnusualExpenseConfig(percentile_excluded_categories=frozenset({"שונות"}))
    d2 = _decision(hist + [cand], "pc", config=cfg)
    assert d2.baseline is not None and d2.baseline.upper_percentile is None
    assert d2.outcome == Outcome.ALERT and d2.threshold == d2.base_threshold == Decimal("350.00")
    # Other categories keep the adjustment.
    assert _decision(hist + [cand], "pc", config=UnusualExpenseConfig(
        percentile_excluded_categories=frozenset({"קניות"}))).outcome == Outcome.WITHIN_THRESHOLD


def test_extra_charge_beside_the_regular_one_is_not_an_increase():
    # Regular ₪70 on the 1st was paid as usual; a separate ₪180 from the same
    # payee two days later is an additional charge, not a price rise.
    base = history(NORMAL, category="שונות")
    regular = _rent_history(["2026-06-01", "2026-07-01", "2026-08-01", "2026-09-01"], amount=70, desc="מתנ״ס", category="שונות")
    this_month = rent(70, "2026-10-01", id="reg", desc="מתנ״ס", category="שונות")
    extra = rent(180, "2026-10-03", id="extra", desc="מתנ״ס", category="שונות")
    decisions = {d.movement_id: d for d in evaluate_month(base + regular + [this_month, extra], evaluated_month=EVAL)}
    assert decisions["reg"].outcome == Outcome.RECURRING
    assert decisions["extra"].outcome != Outcome.RECURRING_INCREASE
    assert decisions["extra"].recurrence is not None  # evidence still inspectable
    # Without the regular charge in the same month, ₪180 is a genuine rise.
    alone = {d.movement_id: d for d in evaluate_month(base + regular + [extra], evaluated_month=EVAL)}
    assert alone["extra"].outcome == Outcome.RECURRING_INCREASE

