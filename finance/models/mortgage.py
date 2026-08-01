from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import List, Optional
import uuid

from .accounts import MoneyAccount, SavingsAccount


def endpoint_balance(
    accounts: List[MoneyAccount], account_name: str, saving_name: str = ""
) -> float:
    """Balance of a transfer endpoint: a specific saving inside a savings account
    (when ``saving_name`` is given), otherwise the account's own balance."""
    account_name = str(account_name or "").strip()
    saving_name = str(saving_name or "").strip()
    for a in accounts:
        if str(getattr(a, "name", "") or "").strip() != account_name:
            continue
        if saving_name and isinstance(a, SavingsAccount):
            for sv in a.savings:
                if str(getattr(sv, "name", "") or "").strip() == saving_name:
                    return float(getattr(sv, "amount", 0.0) or 0.0)
            return 0.0
        return float(getattr(a, "total_amount", 0.0) or 0.0)
    return 0.0


def account_transferred_out(
    movements: list, account_name: str, saving_name: str = ""
) -> float:
    """Total outgoing transfers from a given account/saving (transfers only,
    negative amounts) — money funneled from the source toward the purchase."""
    name = str(account_name or "").strip()
    if not name:
        return 0.0
    sv = str(saving_name or "").strip()
    target = f"{name} -- {sv}" if sv else name
    total = 0.0
    for m in movements:
        try:
            if (
                bool(getattr(m, "is_transfer", False))
                and float(getattr(m, "amount", 0.0) or 0.0) < 0
                and str(getattr(m, "account_name", "") or "").strip() == target
            ):
                total += abs(float(m.amount))
        except Exception:
            continue
    return float(total)


class AmortizationType(StrEnum):
    """שיטת החזר ההלוואה."""

    SPITZER = "שפיצר"  # תשלום חודשי קבוע (אנונה)
    EQUAL_PRINCIPAL = "קרן שווה"  # החזר קרן קבוע, תשלום יורד


class TrackKind(StrEnum):
    """סוג מסלול במשכנתא (תמהיל)."""

    PRIME = "פריים"
    FIXED_UNLINKED = "קבועה לא צמודה"
    FIXED_LINKED = "קבועה צמודה"
    VARIABLE_UNLINKED = "משתנה לא צמודה"
    VARIABLE_LINKED = "משתנה צמודה"


class AssetKind(StrEnum):
    """סוג הנכס. נדל״ן = נכס נדל״ן שנרכש (משכנתא/תמהיל + עלויות). רכב = רכב מתפחת
    עם עלויות שנתיות. אחר = החזקה פשוטה.

    הערך ההיסטורי של נדל״ן היה ``"רכישה"``; ראה ``_parse_asset_kind`` הממפה
    רשומות ישנות."""

    PURCHASE = "נדל״ן"
    CAR = "רכב"
    OTHER = "אחר"


def generate_mortgage_id() -> str:
    return str(uuid.uuid4())


def generate_track_id() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class CostItem:
    """שורת עלות בתרחיש רכישת דירה (חד-פעמית או חודשית).

    ``amount`` הוא הסכום המתוכנן/ידני. ``query`` (אופציונלי, לעלויות חד-פעמיות)
    הוא טקסט לשיוך תנועות בנק — אם הוא תואם תנועות, הסכום בפועל מחושב מסכומן.
    """

    name: str = ""
    amount: float = 0.0
    query: str = ""
    renewal_month: int = 0  # 1-12: חודש חידוש שנתי (לעלויות רכב); 0 = לא הוגדר


class FundingKind(StrEnum):
    """מקור מימון לרכישה (צד ההכנסות)."""

    ACCOUNT = "חשבון קיים"  # מתוך חשבון בנק/חיסכון קיים
    MOVEMENTS = "תנועות"  # שיוך תנועות נכנסות (מתנה, תמורת מכירה)
    FUTURE = "עתידי"  # כסף שצפוי להתקבל בעתיד


@dataclass(frozen=True)
class FundingSource:
    """מקור מימון. ``amount`` = הסכום המוקצה/הצפוי. לפי ``kind``:
    ACCOUNT → ``account_name`` (+``saving_name`` לחיסכון ספציפי בתוך חשבון
    חיסכון, ברמת ההעברות); MOVEMENTS → ``query``; FUTURE → ``amount`` בלבד."""

    name: str = ""
    amount: float = 0.0
    kind: FundingKind = FundingKind.FUTURE
    query: str = ""
    account_name: str = ""
    saving_name: str = ""

    def available(self, *, movements: list, accounts: List[MoneyAccount]) -> float:
        """How much of this source is currently available/received."""
        if self.kind == FundingKind.ACCOUNT:
            return endpoint_balance(accounts, self.account_name, self.saving_name)
        if self.kind == FundingKind.MOVEMENTS:
            from .mortgage_math import query_received_amount

            return query_received_amount(self.query, movements, include_transfers=True)
        return 0.0  # FUTURE — not yet received

    def spent(self, movements: list) -> Optional[float]:
        """How much of this source has actually been used (None for FUTURE)."""
        if self.kind == FundingKind.ACCOUNT:
            return account_transferred_out(
                movements, self.account_name, self.saving_name
            )
        if self.kind == FundingKind.MOVEMENTS:
            from .mortgage_math import query_received_amount

            return query_received_amount(self.query, movements, include_transfers=True)
        return None  # FUTURE


@dataclass(frozen=True)
class MortgageTrack:
    """מסלול בודד בתוך תמהיל המשכנתא.

    הריבית האפקטיבית נגזרת לפי סוג המסלול:
      - PRIME: ריבית הפריים (הנחה) + ``prime_spread``.
      - שאר המסלולים: ``annual_rate``.
    הצמדה למדד מופעלת דרך ``cpi_linked`` ומחושבת לפי הנחת מדד שנתי.
    """

    id: str = field(default_factory=generate_track_id)
    name: str = ""
    kind: TrackKind = TrackKind.FIXED_UNLINKED
    principal: float = 0.0  # קרן מקורית של המסלול
    annual_rate: float = 0.0  # ריבית נומינלית שנתית באחוזים
    term_months: int = 0
    amortization: AmortizationType = AmortizationType.SPITZER
    cpi_linked: bool = False  # הצמדה למדד
    prime_spread: float = 0.0  # למסלול פריים: P + spread (יכול להיות שלילי)
    reset_months: int = 0  # למסלול משתנה: תקופת עדכון ריבית (0 = ללא)


@dataclass(frozen=True)
class Mortgage:
    """נכס. עבור ``kind == PURCHASE`` הרשומה מחזיקה את נתוני הרכישה והמשכנתא
    (מסלולים, מחיר, הון עצמי, עלויות). עבור ``kind == OTHER`` היא החזקה פשוטה
    עם ``current_value`` בלבד. (השם ההיסטורי ``Mortgage`` נשמר פנימית.)"""

    id: str = field(default_factory=generate_mortgage_id)
    name: str = ""
    account_name: str = ""  # החשבון שממנו יורד התשלום (לשיוך תנועות אמיתיות)
    vendor_query: str = ""  # טקסט לזיהוי תנועות בנק של המשכנתא
    start_date: str = ""  # תאריך תחילת ההלוואה (YYYY-MM-DD)
    tracks: list[MortgageTrack] = field(default_factory=list)
    excluded_movement_ids: list[str] = field(default_factory=list)
    archived: bool = False
    # תרחיש רכישת דירה (אופציונלי) — אפס/ריק כשלא מולא.
    property_price: float = 0.0  # מחיר הדירה
    price_query: str = ""  # טקסט לשיוך תנועות התשלום למוכר (לחישוב ששולם בפועל)
    one_time_costs: list[CostItem] = field(default_factory=list)  # מס רכישה, עו"ד...
    monthly_costs: list[CostItem] = field(default_factory=list)  # ארנונה, ועד, ביטוח
    yearly_costs: list[CostItem] = field(default_factory=list)  # ביטוח, טסט, אגרה (רכב)
    funding_sources: list[FundingSource] = field(default_factory=list)  # צד ההכנסות
    kind: AssetKind = AssetKind.PURCHASE  # סוג הנכס
    current_value: float = 0.0  # שווי נוכחי — לנכס מסוג "אחר"
    expense_category: str = ""  # קטגוריית תנועות לחישוב ממוצע חודשי (רכב)
    sold: bool = False  # האם הנכס נמכר
    sale_price: float = 0.0  # מחיר המכירה (השווי שמומש)
    sale_date: str = ""  # תאריך המכירה (YYYY-MM-DD)
    # מזהי תנועות (הוצאות חד-פעמיות) שקושרו כפירעון חלקי לקרן (קיצור תקופה).
    prepayment_movement_ids: list[str] = field(default_factory=list)

    @property
    def original_principal(self) -> float:
        return float(sum(float(t.principal) for t in self.tracks))
