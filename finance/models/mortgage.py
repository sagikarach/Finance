from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import uuid


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
    """סוג הנכס. רכישה = הנכס נרכש (משכנתא/תמהיל + עלויות). אחר = החזקה פשוטה."""

    PURCHASE = "רכישה"
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
    equity: float = 0.0  # הון עצמי (מתוכנן)
    equity_query: str = ""  # טקסט לשיוך תנועות ההון העצמי (אופציונלי)
    one_time_costs: list[CostItem] = field(default_factory=list)  # מס רכישה, עו"ד...
    monthly_costs: list[CostItem] = field(default_factory=list)  # ארנונה, ועד, ביטוח
    kind: AssetKind = AssetKind.PURCHASE  # סוג הנכס
    current_value: float = 0.0  # שווי נוכחי — לנכס מסוג "אחר"

    @property
    def original_principal(self) -> float:
        return float(sum(float(t.principal) for t in self.tracks))
