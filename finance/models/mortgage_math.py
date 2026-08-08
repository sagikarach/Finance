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

from dataclasses import dataclass, replace
from typing import Dict, List, Optional

from .accounts import parse_iso_date
from .mortgage import AmortizationType, CostItem, Mortgage, MortgageTrack, TrackKind
from .movement_matching import match_movements
from ..utils.safe import PARSE_ERRORS

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


def months_after(start_date: str, months: int) -> Optional[tuple[int, int]]:
    """תאריך (שנה, חודש) שהוא ``months`` חודשים לאחר ``start_date``.

    מחזיר ``None`` כשאין תאריך התחלה תקין. משמש לחישוב חודש סיום ההלוואה.
    """
    s = str(start_date or "").strip()
    if not s:
        return None
    d = parse_iso_date(s)
    if d.year <= 1:  # parse_iso_date מחזיר datetime.min כשהקלט אינו תקין
        return None
    total = d.year * 12 + (d.month - 1) + int(months)
    return (total // 12, total % 12 + 1)


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
    required_mortgage: float  # = סכום המשכנתא שהמשתמש בנה (תמהיל); לא מחושב כיתרה
    tracks_total: float  # סכום הקרן של המסלולים בפועל (= המשכנתא)
    ltv: float  # יחס מימון = משכנתא / מחיר
    one_time_total: float  # סך עלויות חד-פעמיות
    monthly_costs_total: float  # סך עלויות חודשיות נלוות
    mortgage_monthly: float  # תשלום משכנתא חודשי (התחלתי)
    upfront_cash: float  # כסף עצמי = עלות הרכישה − משכנתא
    monthly_total: float  # סך חודשי = משכנתא + עלויות נלוות
    total_interest: float  # סך ריבית לאורך חיי ההלוואה
    total_cost: float  # עלות רכישה + ריבית (לאורך חיי ההלוואה)
    acquisition_cost: float  # עלות הרכישה = מחיר הדירה + עלויות חד-פעמיות (מה שיוצא)
    funding_total: float  # סך מקורות המימון העצמיים (לא כולל משכנתא וחשבון הבנק)
    residual_from_bank: float  # מה שחשבון "בנק" צריך לכסות = עלות − משכנתא − מימון
    ltv_exceeds_75: bool  # התראה: מעל 75% מימון


def cost_paid_amount(
    cost: CostItem,
    movements: Optional[list] = None,
    *,
    include_transfers: bool = False,
    match_income: bool = False,
) -> float:
    """סכום התנועות התואמות ל-``query`` (0 אם אין שאילתה או התאמה). ברירת המחדל
    היא הוצאות; ``match_income=True`` מחזיר את התנועות הנכנסות (למקורות מימון).
    ``include_transfers`` שימושי להון עצמי (מקדמה משולמת לרוב כהעברה)."""
    query = str(getattr(cost, "query", "") or "").strip()
    if query and movements:
        matched = match_movements(
            movements,
            vendor_query=query,
            include_transfers=include_transfers,
            match_income=match_income,
        )
        return float(sum(abs(float(m.amount)) for m in matched))
    return 0.0


def yearly_cost_cycles(
    cost: CostItem,
    movements: Optional[list] = None,
    *,
    n_cycles: int = 2,
) -> List[tuple]:
    """קבץ את תנועות ההוצאה התואמות ל-``cost.query`` למחזורים שנתיים המתחילים
    בחודש ``cost.renewal_month`` (1-12). מחזיר את ``n_cycles`` המחזורים האחרונים
    כרשימת ``(start_year, total)`` מהחדש לישן. הסכום למחזור הוא הסכום שנמצא
    בפועל — כך הוא משתנה משנה לשנה ואין צורך להזין אותו."""
    query = str(getattr(cost, "query", "") or "").strip()
    if not query or not movements:
        return []
    rm = int(getattr(cost, "renewal_month", 0) or 0)
    if rm < 1 or rm > 12:
        rm = 1
    matched = match_movements(movements, vendor_query=query, include_transfers=False)
    totals: Dict[int, float] = {}
    for m in matched:
        try:
            amt = float(getattr(m, "amount", 0.0) or 0.0)
        except PARSE_ERRORS:
            continue
        dt = parse_iso_date(str(getattr(m, "date", "") or ""))
        if dt.year <= 1900:
            continue
        # שנת תחילת המחזור: אם החודש ≥ חודש החידוש — השנה; אחרת השנה הקודמת.
        cy = dt.year if dt.month >= rm else dt.year - 1
        totals[cy] = totals.get(cy, 0.0) + abs(amt)
    if not totals:
        return []
    years = sorted(totals.keys(), reverse=True)[: max(1, int(n_cycles))]
    return [(y, float(totals[y])) for y in years]


def average_monthly(movements: Optional[list] = None, *, months: int = 12):
    """ממוצע חודשי של ההוצאות מתוך רשימת תנועות שכבר נבחרה (לפי חיפוש/קטגוריה
    וכו'): מקבצים לפי (שנה, חודש), מסכמים את ההוצאות, ומחזירים
    ``(ממוצע, מספר_חודשים)`` על פני ``months`` החודשים האחרונים שיש בהם נתונים.
    זהו הלולאה המשותפת ל-cost_monthly_average / הרכב / המשכנתא."""
    totals: Dict[tuple, float] = {}
    for mv in movements or []:
        try:
            amt = float(getattr(mv, "amount", 0.0) or 0.0)
        except PARSE_ERRORS:
            continue
        if amt >= 0:
            continue
        dt = parse_iso_date(str(getattr(mv, "date", "") or ""))
        if dt.year <= 1900:
            continue
        key = (dt.year, dt.month)
        totals[key] = totals.get(key, 0.0) + (-amt)
    if not totals:
        return 0.0, 0
    keys = sorted(totals.keys())[-int(months):]
    return sum(totals[k] for k in keys) / float(len(keys)), len(keys)


def cost_monthly_average(
    cost: CostItem, movements: Optional[list] = None, *, months: int = 12
) -> float:
    """ממוצע חודשי של ההוצאה לפי חיפוש התנועות (``cost.query``) — נגזר מהתנועות
    התואמות; 0 אם אין שאילתה/התאמה."""
    query = str(getattr(cost, "query", "") or "").strip()
    if not query or not movements:
        return 0.0
    matched = match_movements(movements, vendor_query=query, include_transfers=False)
    return average_monthly(matched, months=months)[0]


def cost_total_amount(cost: CostItem, movements: Optional[list] = None) -> float:
    """הסכום הכולל (המתוכנן) של שורת עלות — לחישוב עלות הרכישה. אם הוזן סכום
    מתוכנן משתמשים בו; אחרת נופלים לסכום ששולם בפועל (כשהוגדר רק חיפוש תנועות).
    בניגוד ל'שולם בפועל', זה אינו מתכווץ לפי מה ששולם עד כה."""
    planned = float(cost.amount)
    if planned > 0:
        return planned
    return cost_paid_amount(cost, movements)


def query_paid_amount(
    query: str, movements: Optional[list] = None, *, include_transfers: bool = False
) -> float:
    """כמו cost_paid_amount אך מקבל טקסט חיפוש ישירות (להון עצמי)."""
    return cost_paid_amount(
        CostItem(query=str(query or "")),
        movements,
        include_transfers=include_transfers,
    )


def query_received_amount(
    query: str, movements: Optional[list] = None, *, include_transfers: bool = False
) -> float:
    """סכום התנועות הנכנסות (הכנסה) התואמות לטקסט החיפוש — למקורות מימון.
    זהה ל-``query_paid_amount`` פרט לכיוון (הכנסה במקום הוצאה)."""
    return cost_paid_amount(
        CostItem(query=str(query or "")),
        movements,
        include_transfers=include_transfers,
        match_income=True,
    )


def purchase_summary(
    mortgage: Mortgage,
    assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
    movements: Optional[list] = None,
) -> PurchaseSummary:
    price = float(mortgage.property_price or 0.0)
    # המשכנתא נקבעת ע"י המשתמש = סכום המסלולים (התמהיל), לא מחושבת כיתרה.
    tracks_total = float(mortgage.original_principal)
    mortgage_amount = tracks_total
    # עלויות חד-פעמיות — הסכום הכולל המתוכנן (לא מתכווץ לפי מה ששולם בפועל).
    one_time_total = float(
        sum(cost_total_amount(c, movements) for c in mortgage.one_time_costs)
    )
    # עלות הרכישה = מחיר הדירה + העלויות החד-פעמיות (מה שיוצא בפועל).
    acquisition_cost = price + one_time_total
    # סך המימון העצמי = סכום מקורות המימון המוקצים (לא כולל משכנתא וחשבון הבנק).
    funding_total = float(sum(float(f.amount) for f in mortgage.funding_sources))
    # היתרה שחשבון "בנק" צריך לכסות (יכול להיות שלילי = עודף מימון).
    residual_from_bank = acquisition_cost - mortgage_amount - funding_total
    ltv = (mortgage_amount / price) if price > 0 else 0.0
    # עלויות חודשיות נשארות מתוכננות (סכום חודשי — לא מסכמים תנועות רבות).
    monthly_costs_total = float(
        sum(float(c.amount) for c in mortgage.monthly_costs)
    )
    mortgage_monthly = mortgage_initial_monthly(mortgage, assumptions)
    total_interest = mortgage_total_interest(mortgage, assumptions)
    return PurchaseSummary(
        property_price=price,
        required_mortgage=mortgage_amount,
        tracks_total=tracks_total,
        ltv=ltv,
        one_time_total=one_time_total,
        monthly_costs_total=monthly_costs_total,
        mortgage_monthly=mortgage_monthly,
        upfront_cash=acquisition_cost - mortgage_amount,
        monthly_total=mortgage_monthly + monthly_costs_total,
        total_interest=total_interest,
        total_cost=acquisition_cost + total_interest,
        acquisition_cost=acquisition_cost,
        funding_total=funding_total,
        residual_from_bank=residual_from_bank,
        ltv_exceeds_75=bool(ltv > 0.75),
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


# ─────────────────────── פירוק תשלום: ריבית מול קרן ───────────────────────


@dataclass(frozen=True)
class PaymentSplitPoint:
    """פירוק התשלום בתקופה מסוימת: כמה ריבית וכמה קרן (סכום כל המסלולים)."""

    period: int  # מספר התשלום (1-based)
    interest: float
    principal: float


def payment_split_projection(
    mortgage: Mortgage,
    *,
    months: int,
    step: int = 1,
    assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
) -> List[PaymentSplitPoint]:
    """פירוק התשלום החודשי לריבית מול קרן, לאורך חיי ההלוואה (סכום מסלולים)."""
    schedules: Dict[str, List[ScheduleRow]] = {
        t.id: track_schedule(t, assumptions) for t in mortgage.tracks
    }
    points: List[PaymentSplitPoint] = []
    step = max(1, int(step))
    for period in range(1, int(months) + 1, step):
        interest = principal = 0.0
        for t in mortgage.tracks:
            sched = schedules.get(t.id, [])
            if period - 1 < len(sched):
                interest += float(sched[period - 1].interest_part)
                principal += float(sched[period - 1].principal_part)
        points.append(
            PaymentSplitPoint(period=period, interest=interest, principal=principal)
        )
    return points


# ─────────────────────── חשיפה למדד / ריבית ממוצעת ───────────────────────


# ─────────────────────── רגישות להנחות (פריים / מדד) ───────────────────────


@dataclass(frozen=True)
class SensitivityResult:
    """השפעת שינוי בהנחות על התשלום החודשי ההתחלתי וסך הריבית."""

    prime_delta: float  # שינוי הפריים שנבדק (נק' אחוז)
    cpi_delta: float  # שינוי המדד שנבדק (נק' אחוז)
    prime_monthly_delta: float  # שינוי בתשלום החודשי בעקבות עליית הפריים
    prime_interest_delta: float  # שינוי בסך הריבית בעקבות עליית הפריים
    cpi_monthly_delta: float
    cpi_interest_delta: float


def assumptions_sensitivity(
    mortgage: Mortgage,
    base: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
    *,
    prime_delta: float = 1.0,
    cpi_delta: float = 1.0,
) -> SensitivityResult:
    """כמה משתנים התשלום החודשי וסך הריבית אם הפריים/המדד יעלו ב-delta."""
    base_monthly = mortgage_initial_monthly(mortgage, base)
    base_interest = mortgage_total_interest(mortgage, base)
    prime_up = replace(base, prime_rate=float(base.prime_rate) + float(prime_delta))
    cpi_up = replace(base, cpi_annual=float(base.cpi_annual) + float(cpi_delta))
    return SensitivityResult(
        prime_delta=float(prime_delta),
        cpi_delta=float(cpi_delta),
        prime_monthly_delta=mortgage_initial_monthly(mortgage, prime_up) - base_monthly,
        prime_interest_delta=mortgage_total_interest(mortgage, prime_up) - base_interest,
        cpi_monthly_delta=mortgage_initial_monthly(mortgage, cpi_up) - base_monthly,
        cpi_interest_delta=mortgage_total_interest(mortgage, cpi_up) - base_interest,
    )


# ─────────────────────── אבני-דרך: סיום מסלולים ───────────────────────


@dataclass(frozen=True)
class TrackMilestone:
    """סיום מסלול — הנקודה שבה התשלום החודשי יורד (המסלול נגמר)."""

    period: int  # מספר החודש שבו המסלול מסתיים
    track_name: str
    payment_drop: float  # התשלום הראשוני של המסלול (~גובה הירידה בתשלום)


def track_end_milestones(
    mortgage: Mortgage, assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS
) -> List[TrackMilestone]:
    """אבני-דרך: מתי כל מסלול מסתיים ובכמה יירד התשלום החודשי בקירוב."""
    out: List[TrackMilestone] = []
    for t in mortgage.tracks:
        sched = track_schedule(t, assumptions)
        if not sched:
            continue
        out.append(
            TrackMilestone(
                period=len(sched),
                track_name=str(t.name),
                payment_drop=float(sched[0].payment),
            )
        )
    out.sort(key=lambda m: m.period)
    return out


# ─────────────────────── סימולציית פירעון מוקדם ───────────────────────


@dataclass(frozen=True)
class EarlyPayoffResult:
    """תוצאת תרחיש פירעון חלקי חד-פעמי, מחושבת על לוח הסילוקין האמיתי.

    תשלום חד-פעמי מופנה למסלול היקר ביותר (avalanche, מתגלגל הלאה). התשלום
    החודשי נשאר כשהיה — הקטנת הקרן מקצרת את התקופה. הבסיס עקבי עם שאר המסך."""

    lump_sum: float
    baseline_months: int
    new_months: int
    months_saved: int
    baseline_interest: float
    new_interest: float
    interest_saved: float


@dataclass
class _TrackSim:
    """מצב מסלול בסימולציית הפירעון המוקדם (מבנה פנימי בלבד)."""

    balance: float
    r: float  # ריבית חודשית
    linkage: float  # מקדם הצמדה חודשי
    sched: List[ScheduleRow]
    rate: float  # ריבית שנתית אפקטיבית (לבחירת מסלול לתשלום)
    idx: int = 0


def _simulate_with_lump(
    mortgage: Mortgage,
    assumptions: MortgageAssumptions,
    lump_sum: float,
) -> tuple[int, float]:
    """סימולציית סילוקין לאחר תשלום חד-פעמי אחד לקרן.

    ה-``lump_sum`` מופחת פעם אחת מהקרן (מהמסלול היקר ביותר, מתגלגל הלאה),
    ואז כל מסלול ממשיך לשלם את התשלום שבלוח הסילוקין שלו — כך שהתקופה
    מתקצרת. מחזיר (מספר חודשים עד סילוק מלא, סך ריבית). ב-``lump_sum == 0``
    התוצאה זהה ללוח המקורי.
    """
    states: List[_TrackSim] = []
    for t in mortgage.tracks:
        sched = track_schedule(t, assumptions)
        if not sched:
            continue
        states.append(
            _TrackSim(
                balance=float(t.principal),
                r=_monthly_rate(effective_annual_rate(t, assumptions)),
                linkage=_monthly_linkage_factor(t, assumptions),
                sched=sched,
                rate=effective_annual_rate(t, assumptions),
            )
        )
    if not states:
        return 0, 0.0

    # תשלום חד-פעמי — פעם אחת, למסלול שמסתיים אחרון (הכי ארוך) כדי לקצר את
    # תקופת המשכנתא בפועל; שוויון-אורך מוכרע לפי הריבית הגבוהה (חיסכון ריבית).
    remaining = float(lump_sum)
    for s in sorted(states, key=lambda x: (len(x.sched), x.rate), reverse=True):
        if remaining <= 0.0:
            break
        pay = min(remaining, s.balance)
        s.balance -= pay
        remaining -= pay

    total_interest = 0.0
    month = 0
    cap = max(len(s.sched) for s in states) + 12  # backstop against loops
    while month < cap and any(s.balance > 0.5 for s in states):
        month += 1
        for s in states:
            if s.balance <= 0.5:
                continue
            if s.linkage != 1.0:
                s.balance *= s.linkage
            interest = s.balance * s.r
            # התשלום מלוח הסילוקין; אחרי הסוף — כסה את מה שנשאר.
            payment = (
                s.sched[s.idx].payment
                if s.idx < len(s.sched)
                else interest + s.balance
            )
            principal_part = payment - interest
            if principal_part < 0.0:
                principal_part = 0.0
            if principal_part > s.balance:
                principal_part = s.balance
            s.balance -= principal_part
            total_interest += interest
            s.idx += 1
        for s in states:
            if s.balance < 0.5:
                s.balance = 0.0
    return month, total_interest


def early_payoff_savings(
    mortgage: Mortgage,
    lump_sum: float,
    assumptions: MortgageAssumptions = DEFAULT_ASSUMPTIONS,
) -> Optional[EarlyPayoffResult]:
    """חיסכון מתשלום חד-פעמי לקרן, מול לוח הסילוקין האמיתי.

    הבסיס = התקופה (המסלול הארוך) וסך הריבית האמיתי — עקבי עם שאר המסך.
    מחזיר ``None`` כשאין קרן/מסלולים.
    """
    baseline_months = max((int(t.term_months) for t in mortgage.tracks), default=0)
    if baseline_months <= 0 or float(mortgage.original_principal) <= 0:
        return None
    baseline_interest = float(mortgage_total_interest(mortgage, assumptions))
    new_months, new_interest = _simulate_with_lump(
        mortgage, assumptions, float(lump_sum)
    )
    return EarlyPayoffResult(
        lump_sum=float(lump_sum),
        baseline_months=int(baseline_months),
        new_months=int(new_months),
        months_saved=int(baseline_months - new_months),
        baseline_interest=float(baseline_interest),
        new_interest=float(new_interest),
        interest_saved=float(baseline_interest - new_interest),
    )


def equity_split(value: float, outstanding: float) -> tuple[float, float]:
    """Equity and its fraction of value for an asset worth ``value`` carrying
    ``outstanding`` debt: ``(value − outstanding, equity ⁄ value)``. The
    fraction is 0 when the value is non-positive."""
    equity = float(value) - float(outstanding)
    frac = (equity / value) if value > 0 else 0.0
    return equity, frac
