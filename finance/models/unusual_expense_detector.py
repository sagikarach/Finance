"""Conservative, explainable detector for the "unusual expense" alert.

Pure decision logic — no Qt, no file/network I/O, no AI. The notifications
service feeds it the workspace's movements plus the ids of movements that are
explicitly tied to a plan/asset/event, and gets back one inspectable
:class:`CandidateDecision` per movement of the evaluated month.

Decision order for an expense in the evaluated calendar month:

1. **Planned** — explicitly linked to an installment plan, direct debit, asset
   (mortgage, purchase price, cost item) or budgeted event → suppressed. This is
   the strongest evidence and is checked first.
2. **Recurring** — the same account + the same (conservatively normalized)
   description was charged a similar amount at a regular monthly or weekly
   rhythm (see :class:`FrequencyRule`), established only by charges dated
   *before* the evaluated month, the latest one about one period before this
   charge:

   * the amount fits the pattern → suppressed (``RECURRING``);
   * the amount rose by at least ``increase_min_pct`` *and*
     ``increase_min_abs`` over the pattern → its own alert
     (``RECURRING_INCREASE``), so a category whose history is dominated by the
     payment itself can't hide the rise — unless the regular charge *also*
     appears in the same period, in which case this is an additional charge
     (not a price change) and it goes to step 3;
   * anything else (a decrease, a small rise) → falls through to step 3.

   A "monthly" movement type or a shared category is never evidence.
3. **Category history** — the same category's expenses over the
   ``baseline_months`` complete months before the evaluated month (never the
   evaluated month itself or anything later):

   * fewer than ``min_history_transactions`` or spanning fewer than
     ``min_history_distinct_months`` months → no alert (no looser fallback);
   * ``typical = median(history)``, ``mad = median(|x - typical|)``;
   * ``base = max(min_amount, typical + min_abs_difference,
     typical * median_multiplier, typical + mad_multiplier * mad)``;
   * ``upper = P(upper_percentile)`` (nearest-rank, see :func:`nearest_rank`)
     over the same history *minus* payments already known to be expected
     (planned links, or charges that themselves fit an earlier monthly
     pattern) — a large fixed bill such as rent would otherwise stretch the
     category's "ordinary" upper range. With at least
     ``percentile_min_samples`` such samples,
     ``threshold = max(base, upper * percentile_margin)``; otherwise
     ``threshold = base``;
   * alert only when ``amount > threshold`` (strictly).

Account coverage: every non-transfer expense in the workspace is a candidate
and feeds its category's history, whatever account it was paid from (bank,
cash, Bit/PayBox wallets, the Sibus budget card). Category history is
deliberately *not* split by account — a category is the user's own
classification of what the money bought, the account is only how it was paid.
Recurrence, by contrast, always requires the same account.

Currency: the data model has **no currency field** — every stored amount is
assumed to be in ILS, and all monetary settings below are ILS values. The
detector does not (and cannot) tell currencies apart.

Money is handled as :class:`~decimal.Decimal` (two places), converted from the
stored float through its shortest ``repr`` so ``-1200.1`` stays ``1200.10``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from decimal import ROUND_CEILING, Decimal, InvalidOperation
from enum import StrEnum
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Sequence, Set, Tuple

from .bank_movement import counts_as_transfer
from .movement_matching import normalize_text
from ..utils.dates import parse_iso_date
from ..utils.formatting import fmt_money
from ..utils.safe import PARSE_ERRORS

YearMonth = Tuple[int, int]

_CENT = Decimal("0.01")
_MONEY_ERRORS: Tuple[type[Exception], ...] = (InvalidOperation, *PARSE_ERRORS)

# All amounts in the app are ILS (there is no currency field to say otherwise).
ASSUMED_CURRENCY = "ILS"


# ── configuration ─────────────────────────────────────────────────────────


@dataclass(frozen=True)
class FrequencyRule:
    """One recurrence rhythm.

    * ``min_gap_days``/``max_gap_days`` — allowed spacing between consecutive
      charges in the chain (and between the latest one and the candidate).
    * ``min_occurrences`` — supporting prior charges needed.
    * ``distinct_months`` — each chain charge must fall in a different month.
    * ``max_charges_per_month`` — every chain month may hold at most this many
      charges from the same account + payee (a regular payment is charged once
      a month; a shop visited often could otherwise form a chance chain).
    * ``max_extra_charges_in_span`` — between the first and last chain charge,
      at most this many *other* charges from the same account + payee (a
      weekly payment has no room for extra visits; frequent shopping does).
    """

    name: str
    min_gap_days: int
    max_gap_days: int
    min_occurrences: int
    distinct_months: bool = False
    max_charges_per_month: Optional[int] = None
    max_extra_charges_in_span: Optional[int] = None


# 28–31 day months ± a week: weekend/holiday shifts and month-end dates
# (31 Jan → 28 Feb → 31 Mar, or the 1st paid on the 30th).
MONTHLY = FrequencyRule(
    name="monthly",
    min_gap_days=21,
    max_gap_days=38,
    min_occurrences=3,
    distinct_months=True,
    max_charges_per_month=2,
)
# 7 ± 2 days; four prior charges ≈ a month of evidence; no extra charges from
# the same payee in between.
WEEKLY = FrequencyRule(
    name="weekly",
    min_gap_days=5,
    max_gap_days=9,
    min_occurrences=4,
    max_extra_charges_in_span=0,
)


@dataclass(frozen=True)
class RecurrenceConfig:
    """When a charge counts as an established recurring payment.

    * Amounts are "similar" when within ``max(amount_tolerance_abs,
      amount_tolerance_pct × reference)`` of the chain's median amount.
    * A charge above that is a *significant increase* when it exceeds the
      pattern by at least ``increase_min_pct`` **and** ``increase_min_abs``.
      These are tunable starting values, not validated guarantees.
    """

    frequencies: Tuple[FrequencyRule, ...] = (MONTHLY, WEEKLY)
    amount_tolerance_pct: Decimal = Decimal("0.10")
    amount_tolerance_abs: Decimal = Decimal("10")
    increase_min_pct: Decimal = Decimal("0.15")
    increase_min_abs: Decimal = Decimal("100")


@dataclass(frozen=True)
class UnusualExpenseConfig:
    """All detector parameters in one place. Monetary values are ILS."""

    # Significance thresholds (ILS).
    min_amount: Decimal = Decimal("300")
    min_abs_difference: Decimal = Decimal("250")
    median_multiplier: Decimal = Decimal("3")
    mad_multiplier: Decimal = Decimal("4")
    # Upper-range threshold for categories with a broad amount distribution.
    upper_percentile: Decimal = Decimal("0.95")
    percentile_margin: Decimal = Decimal("1.25")
    percentile_min_samples: int = 20
    # Leave planned/recurring payments out of the percentile sample (they stay
    # in the median/MAD history).
    percentile_excludes_expected: bool = True
    # Categories where the percentile adjustment is not applied (base threshold
    # only). Empty by default: the app has no metadata marking catch-all
    # categories, so which ones mix unrelated spending is a user choice.
    percentile_excluded_categories: FrozenSet[str] = frozenset()
    # Categories with no statistical comparison at all: expenses whose purpose
    # is unknown ("טרם סווג") are not a comparable group. Independent checks
    # (recurring-price increase) still apply to them.
    unclassified_categories: FrozenSet[str] = frozenset({"טרם סווג"})
    # Category history requirements.
    baseline_months: int = 6
    min_history_transactions: int = 12
    min_history_distinct_months: int = 3
    recurrence: RecurrenceConfig = field(default_factory=RecurrenceConfig)


DEFAULT_CONFIG = UnusualExpenseConfig()


# ── result types ──────────────────────────────────────────────────────────


class Outcome(StrEnum):
    ALERT = "alert"
    NOT_EXPENSE = "not_expense"  # income, refund, transfer, zero/invalid amount
    NO_CATEGORY = "no_category"
    PLANNED = "planned"  # explicit plan / asset / event link
    RECURRING = "recurring"  # fits an established monthly/weekly payment
    RECURRING_INCREASE = "recurring_increase"  # alert: a recurring charge rose
    INSUFFICIENT_HISTORY = "insufficient_history"
    UNCLASSIFIED = "unclassified"  # no statistical decision: purpose unknown
    WITHIN_THRESHOLD = "within_threshold"


@dataclass(frozen=True)
class RecurrenceEvidence:
    """Why a charge was (or was not) recognised as an established payment.
    Holds dates and amounts only — never description text."""

    frequency: str  # FrequencyRule.name
    occurrence_dates: Tuple[str, ...]  # the supporting prior charges, oldest first
    reference_amount: Decimal  # median of the supporting charges
    tolerance: Decimal
    fits: bool  # this charge's amount and timing fit the pattern
    increase: Decimal = Decimal("0")  # amount − reference when above it
    significant_increase: bool = False


@dataclass(frozen=True)
class CategoryBaseline:
    """Robust summary of one category's history."""

    typical_amount: Decimal  # median
    mad: Decimal  # median absolute deviation from the median
    count: int
    distinct_months: int
    # Over history excluding expected payments; None when too few samples.
    upper_percentile: Optional[Decimal] = None


@dataclass(frozen=True)
class CandidateDecision:
    """The inspectable outcome for one movement of the evaluated month."""

    movement_id: str
    date: str
    amount: Optional[Decimal]  # positive expense amount (None if not an expense)
    category: str
    outcome: Outcome
    evaluated_month: YearMonth
    period_start: YearMonth  # first baseline month (inclusive)
    period_end: YearMonth  # last baseline month (inclusive)
    baseline: Optional[CategoryBaseline] = None
    base_threshold: Optional[Decimal] = None
    percentile_threshold: Optional[Decimal] = None
    threshold: Optional[Decimal] = None
    recurrence: Optional[RecurrenceEvidence] = None

    @property
    def eligible(self) -> bool:
        """Whether the movement was compared against the category history."""
        return self.outcome in (
            Outcome.ALERT,
            Outcome.RECURRING_INCREASE,
            Outcome.WITHIN_THRESHOLD,
            Outcome.INSUFFICIENT_HISTORY,
        )

    @property
    def is_alert(self) -> bool:
        return self.outcome in (Outcome.ALERT, Outcome.RECURRING_INCREASE)


# ── small pure helpers ────────────────────────────────────────────────────


def to_money(value: Any) -> Optional[Decimal]:
    """A finite amount as a 2-place Decimal, or None if it isn't a number."""
    if value is None or isinstance(value, bool):
        return None
    try:
        if isinstance(value, Decimal):
            dec = value
        elif isinstance(value, float):
            if not math.isfinite(value):
                return None
            dec = Decimal(repr(value))
        else:
            dec = Decimal(str(value).strip())
        if not dec.is_finite():
            return None
        return dec.quantize(_CENT)
    except _MONEY_ERRORS:
        return None


def expense_amount(movement: Any) -> Optional[Decimal]:
    """The positive amount of a genuine expense, else None.

    Expenses are stored negative. Income, refunds/credits (non-negative),
    transfers, zero and unparseable amounts are all excluded.
    """
    try:
        if counts_as_transfer(movement):
            return None
    except PARSE_ERRORS:
        return None
    amount = to_money(getattr(movement, "amount", None))
    if amount is None or amount >= 0:
        return None
    return -amount


def movement_category(movement: Any) -> str:
    text = str(getattr(movement, "category", "") or "")
    # Drop the RTL embedding marks the UI sometimes wraps Hebrew text in.
    return text.replace("‫", "").replace("‬", "").strip()


def movement_date(movement: Any) -> Optional[date]:
    text = str(getattr(movement, "date", "") or "").strip()
    if not text:
        return None
    try:
        dt = parse_iso_date(text)
    except PARSE_ERRORS:
        return None
    # parse_iso_date returns datetime.min for unparseable text.
    if dt.year <= 1:
        return None
    return dt.date()


def movement_month(movement: Any) -> Optional[YearMonth]:
    d = movement_date(movement)
    return (d.year, d.month) if d is not None else None


def merchant_key(movement: Any) -> str:
    """Conservative identity for recurrence: the shared ``normalize_text``
    (Unicode NFKC, direction marks, niqqud, quote variants, whitespace) plus
    case-folding. Digits, words and punctuation are kept, so different
    merchants never collapse into one key. Empty when there is no description."""
    return normalize_text(str(getattr(movement, "description", "") or "")).casefold()


def account_key(movement: Any) -> str:
    return normalize_text(str(getattr(movement, "account_name", "") or "")).casefold()


def shift_month(ym: YearMonth, delta: int) -> YearMonth:
    total = ym[0] * 12 + (ym[1] - 1) + int(delta)
    return (total // 12, total % 12 + 1)


def baseline_window(evaluated: YearMonth, months: int) -> List[YearMonth]:
    """The ``months`` complete months strictly before ``evaluated``, oldest first."""
    return [shift_month(evaluated, -k) for k in range(int(months), 0, -1)]


def median(values: Iterable[Decimal]) -> Decimal:
    ordered = sorted(values)
    if not ordered:
        raise ValueError("median of empty sequence")
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


def nearest_rank(values: Sequence[Decimal], p: Decimal) -> Decimal:
    """Nearest-rank percentile: the ``ceil(p × n)``-th smallest value (1-based,
    clamped to [1, n]). Deterministic, no interpolation, always an observed
    amount. E.g. n=20, p=0.95 → the 19th smallest (second largest)."""
    ordered = sorted(values)
    if not ordered:
        raise ValueError("percentile of empty sequence")
    n = len(ordered)
    rank = int((Decimal(p) * n).to_integral_value(rounding=ROUND_CEILING))
    rank = min(max(rank, 1), n)
    return ordered[rank - 1]


def compute_baseline(
    amounts_by_month: Iterable[Tuple[YearMonth, Decimal]],
    config: UnusualExpenseConfig = DEFAULT_CONFIG,
    percentile_amounts: Optional[Sequence[Decimal]] = None,
) -> Optional[CategoryBaseline]:
    """Median/MAD over all history; the upper percentile over
    ``percentile_amounts`` (defaults to the same history)."""
    pairs = list(amounts_by_month)
    if not pairs:
        return None
    amounts = [a for _, a in pairs]
    typical = median(amounts)
    mad = median(abs(a - typical) for a in amounts)
    sample = list(amounts if percentile_amounts is None else percentile_amounts)
    upper = (
        nearest_rank(sample, config.upper_percentile)
        if sample and len(sample) >= int(config.percentile_min_samples)
        else None
    )
    return CategoryBaseline(
        typical_amount=typical,
        mad=mad,
        count=len(amounts),
        distinct_months=len({ym for ym, _ in pairs}),
        upper_percentile=upper,
    )


def compute_base_threshold(
    baseline: CategoryBaseline, config: UnusualExpenseConfig = DEFAULT_CONFIG
) -> Decimal:
    typical = baseline.typical_amount
    return max(
        config.min_amount,
        typical + config.min_abs_difference,
        typical * config.median_multiplier,
        typical + config.mad_multiplier * baseline.mad,
    )


def compute_percentile_threshold(
    baseline: CategoryBaseline, config: UnusualExpenseConfig = DEFAULT_CONFIG
) -> Optional[Decimal]:
    if baseline.upper_percentile is None:
        return None
    return (baseline.upper_percentile * config.percentile_margin).quantize(_CENT)


def compute_threshold(
    baseline: CategoryBaseline, config: UnusualExpenseConfig = DEFAULT_CONFIG
) -> Decimal:
    base = compute_base_threshold(baseline, config)
    upper = compute_percentile_threshold(baseline, config)
    return base if upper is None else max(base, upper)


def has_sufficient_history(
    baseline: CategoryBaseline, config: UnusualExpenseConfig = DEFAULT_CONFIG
) -> bool:
    return (
        baseline.count >= int(config.min_history_transactions)
        and baseline.distinct_months >= int(config.min_history_distinct_months)
    )


def _tolerance(reference: Decimal, rc: RecurrenceConfig) -> Decimal:
    return max(rc.amount_tolerance_abs, (reference * rc.amount_tolerance_pct).quantize(_CENT))


def recurrence_evidence(
    candidate_date: date,
    candidate_amount: Decimal,
    prior: Sequence[Tuple[date, Decimal]],
    rc: RecurrenceConfig,
    freq: FrequencyRule = MONTHLY,
    history_end: Optional[date] = None,
) -> Optional[RecurrenceEvidence]:
    """Look for an established ``freq`` payment among ``prior`` charges (same
    account + payee, all strictly before the evaluated month).

    Walk back from the candidate: each step takes an earlier charge spaced
    ``min_gap_days``–``max_gap_days`` before the current one (in a new month
    for monthly rules) whose amount is similar to the most recent charge in the
    chain. Returns None when there is no chain of ``min_occurrences`` or the
    payee's charges are too frequent to be one regular payment.

    ``history_end`` is the first day that may not be used as evidence (the
    evaluated month's start). For sub-monthly rhythms the charges between it
    and the candidate are unseen rather than missing, so the first link may
    span a whole number of periods — but only if the pattern was still active
    right up to ``history_end``.
    """
    if not prior:
        return None
    chain: List[Tuple[date, Decimal]] = []
    used_months: Set[YearMonth] = set()
    current = candidate_date
    anchor: Optional[Decimal] = None
    remaining = sorted(prior, key=lambda p: p[0], reverse=True)

    def linked(d: date) -> bool:
        gap = (current - d).days
        if freq.min_gap_days <= gap <= freq.max_gap_days:
            return True
        if chain or freq.distinct_months or history_end is None:
            return False
        if (history_end - d).days > freq.max_gap_days:
            return False  # the pattern had already lapsed before the month
        nominal = Decimal(freq.min_gap_days + freq.max_gap_days) / 2
        slack = Decimal(freq.max_gap_days - freq.min_gap_days) / 2
        k = int((Decimal(gap) / nominal).to_integral_value())
        return k >= 2 and abs(Decimal(gap) - k * nominal) <= slack

    while True:
        options = [
            (d, a)
            for d, a in remaining
            if linked(d)
            and not (freq.distinct_months and (d.year, d.month) in used_months)
        ]
        if anchor is not None:
            tol = _tolerance(anchor, rc)
            options = [(d, a) for d, a in options if abs(a - anchor) <= tol]
        if not options:
            break
        # Prefer the charge closest in amount to the pattern (then the latest).
        ref = anchor if anchor is not None else candidate_amount
        d, a = min(options, key=lambda p: (abs(p[1] - ref), -p[0].toordinal()))
        chain.append((d, a))
        used_months.add((d.year, d.month))
        anchor = anchor if anchor is not None else a
        current = d
    if len(chain) < int(freq.min_occurrences):
        return None
    if freq.max_charges_per_month is not None:
        per_month: Dict[YearMonth, int] = {}
        for d, _ in prior:
            per_month[(d.year, d.month)] = per_month.get((d.year, d.month), 0) + 1
        if any(per_month.get(ym, 0) > int(freq.max_charges_per_month) for ym in used_months):
            return None
    if freq.max_extra_charges_in_span is not None:
        first, last = chain[-1][0], chain[0][0]
        in_span = sum(1 for d, _ in prior if first <= d <= last)
        if in_span - len(chain) > int(freq.max_extra_charges_in_span):
            return None
    reference = median(a for _, a in chain)
    tol = _tolerance(reference, rc)
    fits = abs(candidate_amount - reference) <= tol
    rise = candidate_amount - reference
    significant = (
        not fits
        and rise >= rc.increase_min_abs
        and rise >= (reference * rc.increase_min_pct).quantize(_CENT)
    )
    return RecurrenceEvidence(
        frequency=freq.name,
        occurrence_dates=tuple(d.isoformat() for d, _ in reversed(chain)),
        reference_amount=reference,
        tolerance=tol,
        fits=fits,
        increase=max(rise, Decimal("0")),
        significant_increase=significant,
    )


def best_recurrence(
    candidate_date: date,
    candidate_amount: Decimal,
    prior: Sequence[Tuple[date, Decimal]],
    rc: RecurrenceConfig,
    history_end: Optional[date] = None,
) -> Optional[RecurrenceEvidence]:
    """The most telling evidence across the configured rhythms: a fitting
    pattern first, then a significant increase, then any other evidence."""
    found = [
        ev
        for freq in rc.frequencies
        if (
            ev := recurrence_evidence(
                candidate_date, candidate_amount, prior, rc, freq, history_end
            )
        )
        is not None
    ]
    for pick in (lambda e: e.fits, lambda e: e.significant_increase, lambda e: True):
        for ev in found:
            if pick(ev):
                return ev
    return None


# ── the detector ──────────────────────────────────────────────────────────


@dataclass
class _Row:
    movement: Any
    movement_id: str
    day: date
    month: YearMonth
    amount: Optional[Decimal]  # expense amount, None when not an expense
    category: str
    merchant: Tuple[str, str]  # (account key, merchant key); merchant "" = none


class DetectionIndex:
    """Movements parsed once and indexed for repeated month evaluations.

    Building it is one pass over the movements; evaluating a month then reads
    only that month's rows, the baseline-window months and the candidate's own
    payee history — never the whole history per transaction. Whether a history
    row fits an established payment depends only on data before its *own*
    month, so that answer is cached across evaluated months."""

    def __init__(self, movements: Iterable[Any]) -> None:
        self.by_month: Dict[YearMonth, List[_Row]] = {}
        self.by_merchant: Dict[Tuple[str, str], List[_Row]] = {}
        self._fits_cache: Dict[Tuple[int, str], bool] = {}
        for m in movements:
            d = movement_date(m)
            if d is None:
                continue
            row = _Row(
                movement=m,
                movement_id=str(getattr(m, "id", "") or ""),
                day=d,
                month=(d.year, d.month),
                amount=expense_amount(m),
                category=movement_category(m),
                merchant=(account_key(m), merchant_key(m)),
            )
            self.by_month.setdefault(row.month, []).append(row)
            if row.amount is not None and row.merchant[1]:
                self.by_merchant.setdefault(row.merchant, []).append(row)

    def prior(self, merchant: Tuple[str, str], before: date) -> List[Tuple[date, Decimal]]:
        return [
            (r.day, r.amount)
            for r in self.by_merchant.get(merchant, [])
            if r.day < before and r.amount is not None
        ]

    def fits_established_payment(self, row: _Row, rc: RecurrenceConfig) -> bool:
        key = (id(rc), row.movement_id or str(id(row.movement)))
        cached = self._fits_cache.get(key)
        if cached is None:
            own_month_start = date(row.day.year, row.day.month, 1)
            assert row.amount is not None
            ev = best_recurrence(
                row.day, row.amount, self.prior(row.merchant, own_month_start), rc,
                own_month_start,
            )
            cached = ev is not None and ev.fits
            self._fits_cache[key] = cached
        return cached


def evaluate_month(
    movements: Iterable[Any],
    *,
    evaluated_month: YearMonth,
    planned_movement_ids: Optional[Set[str]] = None,
    config: UnusualExpenseConfig = DEFAULT_CONFIG,
    index: Optional[DetectionIndex] = None,
) -> List[CandidateDecision]:
    """One :class:`CandidateDecision` per movement dated in ``evaluated_month``.

    ``movements`` must all belong to one workspace (the caller's provider is
    already workspace-scoped). Only data dated before ``evaluated_month`` feeds
    the category baseline and recurrence evidence; planned movements still count
    as ordinary history. Pass a prebuilt ``index`` (over the same movements) to
    evaluate several months without re-parsing."""
    idx = index if index is not None else DetectionIndex(movements)
    planned = {str(x) for x in (planned_movement_ids or set())}
    window = baseline_window(evaluated_month, config.baseline_months)
    month_start = date(evaluated_month[0], evaluated_month[1], 1)

    history: Dict[str, List[Tuple[YearMonth, Decimal]]] = {}
    history_rows: Dict[str, List[_Row]] = {}
    for ym in window:  # window months are all strictly before evaluated_month
        for r in idx.by_month.get(ym, []):
            if r.amount is None or not r.category:
                continue
            history.setdefault(r.category, []).append((ym, r.amount))
            history_rows.setdefault(r.category, []).append(r)

    in_month = idx.by_month.get(evaluated_month, [])
    in_month_by_merchant: Dict[Tuple[str, str], List[Tuple[str, date, Decimal]]] = {}
    for r in in_month:
        if r.amount is not None and r.merchant[1]:
            in_month_by_merchant.setdefault(r.merchant, []).append(
                (r.movement_id, r.day, r.amount)
            )

    def is_expected(r: _Row) -> bool:
        """Planned, or fits a recurring pattern established before its own month."""
        if r.movement_id in planned:
            return True
        if not r.merchant[1]:
            return False
        return idx.fits_established_payment(r, config.recurrence)

    def baseline_for(category: str) -> Optional[CategoryBaseline]:
        rows = history_rows.get(category, [])
        if category in config.percentile_excluded_categories:
            sample: Optional[List[Decimal]] = []  # no percentile adjustment
        elif config.percentile_excludes_expected:
            sample = [r.amount for r in rows if r.amount is not None and not is_expected(r)]
        else:
            sample = None  # the full history
        return compute_baseline(history.get(category, []), config, sample)

    freq_by_name = {f.name: f for f in config.recurrence.frequencies}

    def regular_charge_also_present(r: _Row, ev: RecurrenceEvidence) -> bool:
        """Another charge from the same account + payee in the same period
        already matches the pattern → this higher one is extra, not a rise."""
        freq = freq_by_name.get(ev.frequency)
        for oid, od, oa in in_month_by_merchant.get(r.merchant, []):
            if oid == r.movement_id or abs(oa - ev.reference_amount) > ev.tolerance:
                continue
            if freq is None or freq.distinct_months:
                return True  # same calendar month
            if abs((od - r.day).days) < freq.min_gap_days:
                return True
        return False

    baselines: Dict[str, Optional[CategoryBaseline]] = {}
    decisions: List[CandidateDecision] = []

    def decide(m: Any, outcome: Outcome, **kw: Any) -> None:
        decisions.append(
            CandidateDecision(
                movement_id=str(getattr(m, "id", "") or ""),
                date=str(getattr(m, "date", "") or ""),
                amount=kw.pop("amount", None),
                category=kw.pop("category", movement_category(m)),
                outcome=outcome,
                evaluated_month=evaluated_month,
                period_start=window[0],
                period_end=window[-1],
                **kw,
            )
        )

    for r in in_month:
        m = r.movement
        amount = r.amount
        if amount is None:
            decide(m, Outcome.NOT_EXPENSE)
            continue
        category = r.category
        if r.movement_id in planned:
            decide(m, Outcome.PLANNED, amount=amount, category=category)
            continue

        recurrence: Optional[RecurrenceEvidence] = None
        if r.merchant[1]:
            recurrence = best_recurrence(
                r.day, amount, idx.prior(r.merchant, month_start), config.recurrence,
                month_start,
            )
            if recurrence is not None and recurrence.fits:
                decide(m, Outcome.RECURRING, amount=amount, category=category, recurrence=recurrence)
                continue
            if (
                recurrence is not None
                and recurrence.significant_increase
                and not regular_charge_also_present(r, recurrence)
            ):
                decide(
                    m, Outcome.RECURRING_INCREASE, amount=amount, category=category,
                    recurrence=recurrence,
                )
                continue

        if not category:
            decide(m, Outcome.NO_CATEGORY, amount=amount, category=category, recurrence=recurrence)
            continue
        if category in config.unclassified_categories:
            # No statistical decision: the purpose is not known, so there is no
            # comparable group. Not a confirmed normal expense.
            decide(m, Outcome.UNCLASSIFIED, amount=amount, category=category, recurrence=recurrence)
            continue
        if category not in baselines:
            baselines[category] = baseline_for(category)
        baseline = baselines[category]
        if baseline is None or not has_sufficient_history(baseline, config):
            decide(
                m, Outcome.INSUFFICIENT_HISTORY, amount=amount, category=category,
                baseline=baseline, recurrence=recurrence,
            )
            continue
        base = compute_base_threshold(baseline, config)
        upper = compute_percentile_threshold(baseline, config)
        threshold = base if upper is None else max(base, upper)
        decide(
            m,
            Outcome.ALERT if amount > threshold else Outcome.WITHIN_THRESHOLD,
            amount=amount,
            category=category,
            baseline=baseline,
            base_threshold=base,
            percentile_threshold=upper,
            threshold=threshold,
            recurrence=recurrence,
        )

    decisions.sort(key=lambda x: (x.date, x.movement_id))
    return decisions


def outcome_counts(decisions: Iterable[CandidateDecision]) -> Dict[str, int]:
    """``{outcome: count}`` — e.g. how many expenses received no statistical
    decision because they are unclassified or lack comparable history."""
    out: Dict[str, int] = {}
    for d in decisions:
        out[str(d.outcome)] = out.get(str(d.outcome), 0) + 1
    return dict(sorted(out.items()))


def detect_unusual_expenses(
    movements: Iterable[Any],
    *,
    evaluated_month: YearMonth,
    planned_movement_ids: Optional[Set[str]] = None,
    config: UnusualExpenseConfig = DEFAULT_CONFIG,
    index: Optional[DetectionIndex] = None,
) -> List[CandidateDecision]:
    """Only the decisions that warrant an alert."""
    return [
        d
        for d in evaluate_month(
            movements,
            evaluated_month=evaluated_month,
            planned_movement_ids=planned_movement_ids,
            config=config,
            index=index,
        )
        if d.is_alert
    ]


# ── user-facing explanation ───────────────────────────────────────────────


def _fmt_amount(value: Decimal) -> str:
    decimals = 0 if value == value.to_integral_value() else 2
    return fmt_money(float(value), decimals)


def _fmt_month(ym: YearMonth) -> str:
    return f"{ym[1]:02d}/{ym[0]:04d}"


_FREQUENCY_HE = {"monthly": "חודשי", "weekly": "שבועי"}


def decision_title(decision: CandidateDecision) -> str:
    if decision.outcome == Outcome.RECURRING_INCREASE:
        return "עלייה בחיוב קבוע"
    return "הוצאה חריגה"


def format_unusual_expense_message(decision: CandidateDecision) -> str:
    """Hebrew, factual explanation built only from the calculated values."""
    assert decision.amount is not None
    if decision.outcome == Outcome.RECURRING_INCREASE:
        ev = decision.recurrence
        assert ev is not None
        freq = _FREQUENCY_HE.get(ev.frequency, "")
        where = f" בקטגוריית {decision.category}" if decision.category else ""
        return (
            f"חיוב {freq} קבוע{where} עלה מ־{_fmt_amount(ev.reference_amount)} ש״ח "
            f"ל־{_fmt_amount(decision.amount)} ש״ח, "
            f"על סמך {len(ev.occurrence_dates)} חיובים קודמים."
        )
    assert decision.baseline is not None
    return (
        f"הוצאה של {_fmt_amount(decision.amount)} ש״ח "
        f"בקטגוריית {decision.category}. "
        f"חציון העסקאות בקטגוריה בששת החודשים הקודמים "
        f"({_fmt_month(decision.period_start)} עד {_fmt_month(decision.period_end)}) "
        f"הוא {_fmt_amount(decision.baseline.typical_amount)} ש״ח, "
        f"על בסיס {decision.baseline.count} עסקאות."
    )


def decision_context(decision: CandidateDecision) -> Dict[str, Any]:
    """JSON/Firestore-safe alert context. Money is stored as exact decimal
    strings; ``amount`` keeps the stored (negative) float shape the rest of the
    app already reads. No description text is copied here."""
    assert decision.amount is not None
    ctx: Dict[str, Any] = {
        "movement_id": decision.movement_id,
        "date": decision.date,
        "amount": float(-decision.amount),
        "category": decision.category,
        "reason": decision.outcome.value,
        "expense_amount": str(decision.amount),
        "baseline_start": _fmt_month(decision.period_start),
        "baseline_end": _fmt_month(decision.period_end),
        "target_year": int(decision.evaluated_month[0]),
        "target_month": int(decision.evaluated_month[1]),
        "detector": "category_median_v3",
    }
    b = decision.baseline
    if b is not None:
        ctx.update(
            {
                "typical_amount": str(b.typical_amount),
                "mad": str(b.mad),
                "upper_percentile": None if b.upper_percentile is None else str(b.upper_percentile),
                "history_count": int(b.count),
                "history_months": int(b.distinct_months),
            }
        )
    if decision.threshold is not None:
        ctx["threshold"] = str(decision.threshold)
    ev = decision.recurrence
    if ev is not None and decision.outcome == Outcome.RECURRING_INCREASE:
        ctx.update(
            {
                "recurrence_frequency": ev.frequency,
                "recurrence_reference": str(ev.reference_amount),
                "recurrence_occurrences": len(ev.occurrence_dates),
                "recurrence_increase": str(ev.increase),
            }
        )
    return ctx
