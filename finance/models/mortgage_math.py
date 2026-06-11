"""משכנתא — חישובי לוח סילוקין טהורים (ללא Qt, ללא קלט/פלט).

המודול הזה הוא הליבה החישובית של פיצ'ר המשכנתא. כל הפונקציות כאן טהורות
(pure) וניתנות לבדיקה ישירה. כל מצב צד (קבצים, רשת, Firebase, UI) נשאר
בשכבת ה-service וה-provider, בדיוק כמו בשאר הפרויקט.

הערה חשובה לגבי הצמדה / פריים / משתנה:
    ערכי מדד עתידיים, ריבית הפריים העתידית ועדכוני ריבית במסלול משתנה אינם
    ידועים מראש. לכן הם מתקבלים כ-*הנחות* (``MortgageAssumptions``) ולא
    כתחזית. ברירת המחדל: מדד 0%, פריים נוכחי קבוע. כך החישוב דטרמיניסטי
    ושקוף — לוח הסילוקין מדויק *בהינתן ההנחות*.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

from .accounts import parse_iso_date
from .mortgage import AmortizationType, CostItem, Mortgage, MortgageTrack, TrackKind
from .movement_matching import match_movements

# ריבית פריים נוכחית בישראל (ברירת מחדל הניתנת לעקיפה דרך ההנחות).
DEFAULT_PRIME_RATE = 6.0


@dataclass(frozen=True)
class MortgageAssumptions:
    """הנחות חיצוניות הדרושות לחישוב מסלולים מסוימים."""

    cpi_annual: float = 0.0  # הנחת מדד שנתי באחוזים (להצמדה)
    prime_rate: float = DEFAULT_PRIME_RATE  # ריבית פריים נוכחית באחוזים


DEFAULT_ASSUMPTIONS = MortgageAssumptions()


@dataclass(frozen=True)
class ScheduleRow:
    """שורה אחת בלוח הסילוקין של מסלול."""

    period: int  # מספר תשלום (1-based)
    payment: float  # סך התשלום החודשי
    principal_part: float  # מרכיב הקרן
    interest_part: float  # מרכיב הריבית
    remaining_balance: float  # יתרת קרן לאחר התשלום


# ─────────────────────────── ריבית אפקטיבית ───────────────────────────


def effective_annual_rate(
    track: MortgageTrack, assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS
) -> float:
    """הריבית השנתית האפקטיבית באחוזים עבור מסלול נתון."""
    if track.kind == TrackKind.PRIME:
        return float(assumptions.prime_rate) + float(track.prime_spread)
    return float(track.annual_rate)


def _monthly_rate(annual_rate_pct: float) -> float:
    return float(annual_rate_pct) / 100.0 / 12.0


def _monthly_linkage_factor(
    track: MortgageTrack, assumptions: MortgageAssumptions
) -> float:
    """מקדם הצמדה חודשי (1.0 אם המסלול אינו צמוד)."""
    if not bool(track.cpi_linked):
        return 1.0
    cpi = float(assumptions.cpi_annual) / 100.0
    if cpi <= -1.0:
        return 1.0
    return (1.0 + cpi) ** (1.0 / 12.0)


def annuity_payment(balance: float, monthly_rate: float, remaining_months: int) -> float:
    """תשלום שפיצר (אנונה) עבור יתרה, ריבית חודשית ומספר תשלומים שנותרו."""
    n = int(remaining_months)
    b = float(balance)
    r = float(monthly_rate)
    if n <= 0 or b <= 0:
        return 0.0
    if r == 0.0:
        return b / n
    return b * r / (1.0 - (1.0 + r) ** (-n))


# ─────────────────────────── לוח סילוקין ───────────────────────────


def track_schedule(
    track: MortgageTrack, assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS
) -> List[ScheduleRow]:
    """לוח הסילוקין המלא של מסלול בודד.

    התשלום מחושב מחדש בכל חודש על היתרה והתקופה שנותרו. עבור מסלול קבוע לא
    צמוד זה מניב תשלום שפיצר קבוע; עבור מסלול צמוד התשלום גדל באופן טבעי ככל
    שהיתרה מוצמדת. כך אותו קוד מטפל בכל הסוגים.
    """
    n = int(track.term_months)
    principal = float(track.principal)
    if n <= 0 or principal <= 0:
        return []

    r = _monthly_rate(effective_annual_rate(track, assumptions))
    linkage = _monthly_linkage_factor(track, assumptions)
    is_spitzer = track.amortization == AmortizationType.SPITZER

    rows: List[ScheduleRow] = []
    balance = principal
    for k in range(1, n + 1):
        remaining_months = n - k + 1
        # הצמדת היתרה לפני חישוב הריבית של החודש.
        if linkage != 1.0:
            balance *= linkage

        interest = balance * r
        if is_spitzer:
            payment = annuity_payment(balance, r, remaining_months)
            principal_part = payment - interest
        else:  # קרן שווה
            principal_part = balance / remaining_months
            payment = principal_part + interest

        balance -= principal_part
        if k == n or balance < 0:
            balance = 0.0  # תיקון שאריות עיגול בתשלום האחרון
        rows.append(
            ScheduleRow(
                period=k,
                payment=payment,
                principal_part=principal_part,
                interest_part=interest,
                remaining_balance=balance,
            )
        )
    return rows


def track_outstanding(
    track: MortgageTrack,
    months_elapsed: int,
    assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
) -> float:
    """יתרת הקרן של מסלול לאחר ``months_elapsed`` תשלומים."""
    m = int(months_elapsed)
    if m <= 0:
        return float(track.principal)
    schedule = track_schedule(track, assumptions)
    if not schedule:
        return float(track.principal)
    if m >= len(schedule):
        return 0.0
    return float(schedule[m - 1].remaining_balance)


def track_total_interest(
    track: MortgageTrack, assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS
) -> float:
    return float(sum(row.interest_part for row in track_schedule(track, assumptions)))


# ─────────────────────── אגרגציה ברמת המשכנתא ───────────────────────


def months_between(start_date: str, as_of_date: Optional[str]) -> int:
    """מספר החודשים השלמים בין שני תאריכים (לא שלילי)."""
    start = parse_iso_date(str(start_date or "").strip())
    if as_of_date is None:
        from datetime import datetime

        as_of = datetime.now()
    else:
        as_of = parse_iso_date(str(as_of_date or "").strip())
    diff = (as_of.year - start.year) * 12 + (as_of.month - start.month)
    return max(0, int(diff))


def mortgage_outstanding(
    mortgage: Mortgage,
    as_of_date: Optional[str] = None,
    assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
) -> float:
    """סך יתרת הקרן של המשכנתא בתאריך נתון (סכום כל המסלולים)."""
    months = months_between(mortgage.start_date, as_of_date)
    return float(
        sum(track_outstanding(t, months, assumptions) for t in mortgage.tracks)
    )


def mortgage_total_interest(
    mortgage: Mortgage, assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS
) -> float:
    return float(sum(track_total_interest(t, assumptions) for t in mortgage.tracks))


def mortgage_total_payment(
    mortgage: Mortgage, assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS
) -> float:
    """סך כל התשלומים לאורך חיי המשכנתא (קרן + ריבית + הצמדה)."""
    total = 0.0
    for t in mortgage.tracks:
        total += sum(row.payment for row in track_schedule(t, assumptions))
    return float(total)


def mortgage_initial_monthly(
    mortgage: Mortgage, assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS
) -> float:
    """סך התשלום החודשי ההתחלתי על פני כל המסלולים (תשלום ראשון)."""
    total = 0.0
    for t in mortgage.tracks:
        sched = track_schedule(t, assumptions)
        if sched:
            total += float(sched[0].payment)
    return float(total)


@dataclass(frozen=True)
class PurchaseSummary:
    """סיכום עלויות רכישת דירה — שלוש השכבות: מקדמה, חודשי, ועלות כוללת."""

    property_price: float
    equity: float
    required_mortgage: float  # מחיר − הון עצמי
    tracks_total: float  # סכום הקרן של המסלולים בפועל
    ltv: float  # יחס מימון (0..1)
    one_time_total: float  # סך עלויות חד-פעמיות (ללא הון עצמי)
    monthly_costs_total: float  # סך עלויות חודשיות נלוות
    mortgage_monthly: float  # תשלום משכנתא חודשי (התחלתי)
    upfront_cash: float  # מזומן נדרש לרכישה = הון עצמי + עלויות חד-פעמיות
    monthly_total: float  # סך חודשי = משכנתא + עלויות נלוות
    total_interest: float  # סך ריבית לאורך חיי ההלוואה
    total_cost: float  # מחיר + ריבית + עלויות חד-פעמיות
    ltv_exceeds_75: bool  # התראה: מעל 75% מימון
    principal_mismatch: bool  # המסלולים אינם מסתכמים לסכום ההלוואה הדרוש


def cost_effective_amount(cost: CostItem, movements: Optional[list] = None) -> float:
    """הסכום בפועל של שורת עלות: אם יש ``query`` והוא תואם תנועות — סכום
    התנועות התואמות; אחרת הסכום המתוכנן (``amount``)."""
    query = str(getattr(cost, "query", "") or "").strip()
    if query and movements:
        matched = match_movements(movements, vendor_query=query)
        if matched:
            return float(sum(abs(float(m.amount)) for m in matched))
    return float(cost.amount)


def cost_paid_amount(
    cost: CostItem,
    movements: Optional[list] = None,
    *,
    include_transfers: bool = False,
) -> float:
    """כמה שולם בפועל עבור שורת עלות — סכום התנועות התואמות ל-``query`` (0 אם
    אין שאילתה או אין התאמה). בניגוד ל-cost_effective_amount, אין נפילה לסכום
    המתוכנן — זהו ה'שולם בפועל'. ``include_transfers`` שימושי להון עצמי
    (מקדמה משולמת לרוב כהעברה)."""
    query = str(getattr(cost, "query", "") or "").strip()
    if query and movements:
        matched = match_movements(
            movements, vendor_query=query, include_transfers=include_transfers
        )
        return float(sum(abs(float(m.amount)) for m in matched))
    return 0.0


def query_paid_amount(
    query: str, movements: Optional[list] = None, *, include_transfers: bool = False
) -> float:
    """כמו cost_paid_amount אך מקבל טקסט חיפוש ישירות (להון עצמי)."""
    return cost_paid_amount(
        CostItem(query=str(query or "")),
        movements,
        include_transfers=include_transfers,
    )


def purchase_summary(
    mortgage: Mortgage,
    assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
    movements: Optional[list] = None,
) -> PurchaseSummary:
    price = float(mortgage.property_price or 0.0)
    equity = float(mortgage.equity or 0.0)
    required = max(0.0, price - equity)
    tracks_total = float(mortgage.original_principal)
    ltv = (required / price) if price > 0 else 0.0
    # עלויות חד-פעמיות — שווי בפועל לפי שיוך תנועות (עם נפילה לסכום המתוכנן).
    one_time_total = float(
        sum(cost_effective_amount(c, movements) for c in mortgage.one_time_costs)
    )
    # עלויות חודשיות נשארות מתוכננות (סכום חודשי — לא מסכמים תנועות רבות).
    monthly_costs_total = float(
        sum(float(c.amount) for c in mortgage.monthly_costs)
    )
    mortgage_monthly = mortgage_initial_monthly(mortgage, assumptions)
    total_interest = mortgage_total_interest(mortgage, assumptions)
    return PurchaseSummary(
        property_price=price,
        equity=equity,
        required_mortgage=required,
        tracks_total=tracks_total,
        ltv=ltv,
        one_time_total=one_time_total,
        monthly_costs_total=monthly_costs_total,
        mortgage_monthly=mortgage_monthly,
        upfront_cash=equity + one_time_total,
        monthly_total=mortgage_monthly + monthly_costs_total,
        total_interest=total_interest,
        total_cost=price + total_interest + one_time_total,
        ltv_exceeds_75=bool(ltv > 0.75),
        principal_mismatch=bool(price > 0 and abs(tracks_total - required) > 1.0),
    )


@dataclass(frozen=True)
class OutstandingPoint:
    months_from_start: int
    outstanding: float


def outstanding_projection(
    mortgage: Mortgage,
    *,
    months: int,
    step: int = 1,
    assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
) -> List[OutstandingPoint]:
    """תחזית דטרמיניסטית של יתרת הקרן ל-``months`` חודשים קדימה.

    משמש לשילוב בגרפי התחזית והשווי הנקי. בניגוד לתחזית החיסכון (שמבוססת
    הערכה), כאן היתרה ידועה במדויק בהינתן ההנחות.
    """
    schedules: Dict[str, List[ScheduleRow]] = {
        t.id: track_schedule(t, assumptions) for t in mortgage.tracks
    }
    points: List[OutstandingPoint] = []
    step = max(1, int(step))
    for m in range(0, int(months) + 1, step):
        total = 0.0
        for t in mortgage.tracks:
            sched = schedules.get(t.id, [])
            if m <= 0:
                total += float(t.principal)
            elif m >= len(sched):
                total += 0.0
            else:
                total += float(sched[m - 1].remaining_balance)
        points.append(OutstandingPoint(months_from_start=m, outstanding=total))
    return points
