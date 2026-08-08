"""שיוך תנועות בנק אמיתיות לפי טקסט ספק + חשבון.

הלוגיקה הזו הופקה מ-``InstallmentsService._match_movements`` כדי שגם
תכניות תשלומים וגם משכנתאות ישתמשו באותו מנגנון זיהוי (נרמול Unicode + סינון
לפי חשבון/סכום/תאריך/החרגות). שמירה על התנהגות זהה לקוד המקורי.
"""

from __future__ import annotations

from typing import Iterable, List, Optional
import unicodedata

from .accounts import parse_iso_date
from .bank_movement import BankMovement
from ..utils.safe import PARSE_ERRORS


# איחוד גרסאות מרכאות/גרש לצורה אחת — בנקים משתמשים בגרשיים (״) ובגרש (׳)
# בעוד שמשתמשים מקלידים מרכאות/אפוסטרוף רגילים. ממירים הכל לצורה אחידה כדי
# שהשיוך יעבוד ללא תלות בצורת הסימן.
_QUOTE_MAP = {
    "״": '"',  # gershayim U+05F4
    "“": '"',  # U+201C
    "”": '"',  # U+201D
    "″": '"',  # double prime U+2033
    "׳": "'",  # geresh U+05F3
    "‘": "'",  # U+2018
    "’": "'",  # U+2019
    "′": "'",  # prime U+2032
}
_QUOTE_TRANSLATION = {ord(k): v for k, v in _QUOTE_MAP.items()}


# תווי כיווניות / רוחב-אפס שיש להסיר לפני השוואה.
_DROP_CHARS = {
    "‎",
    "‏",
    "‪",
    "‫",
    "‬",
    "‭",
    "‮",
    "⁦",
    "⁧",
    "⁨",
    "⁩",
    "​",
    "‌",
    "‍",
    "﻿",
}


def normalize_text(value: str) -> str:
    """נרמול טקסט להשוואה: NFKC, הסרת תווי כיווניות וניקוד, וכיווץ רווחים."""
    value = str(value or "")
    try:
        value = unicodedata.normalize("NFKC", value)
    except PARSE_ERRORS:
        pass
    try:
        value = "".join(ch for ch in value if ch not in _DROP_CHARS)
    except PARSE_ERRORS:
        pass
    try:
        value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    except PARSE_ERRORS:
        pass
    try:
        value = value.translate(_QUOTE_TRANSLATION)
    except PARSE_ERRORS:
        pass
    value = " ".join(value.split())
    return value


def match_movements(
    movements: Iterable[BankMovement],
    *,
    vendor_query: str,
    account_name: str = "",
    start_date: str = "",
    excluded_ids: Iterable[str] = (),
    max_count: Optional[int] = None,
    include_transfers: bool = False,
    match_income: bool = False,
) -> List[BankMovement]:
    """החזר את התנועות (הוצאות) התואמות לשאילתת הטקסט.

    תנועה תואמת אם: אינה העברה, סכומה שלילי (הוצאה), אינה מוחרגת, תיאורה מכיל
    את טקסט החיפוש (לאחר נרמול), ותאריכה אינו לפני ``start_date``. אם נמסר
    ``account_name`` — מסונן גם לפי חשבון; אם ריק — נסרקים כל החשבונות (שימושי
    לשיוך עלויות רכישה חד-פעמיות). ממוין לפי תאריך; ``max_count`` חותך לראשונים.
    """
    vendor_query_norm = normalize_text(vendor_query).strip()
    account_key = str(account_name or "").strip().casefold()
    if not vendor_query_norm:
        return []
    vendor_norm = normalize_text(vendor_query_norm).casefold()
    start_dt = (
        parse_iso_date(str(start_date or "").strip())
        if str(start_date or "").strip()
        else None
    )
    excluded = set(str(x) for x in excluded_ids if str(x or "").strip())

    out: List[BankMovement] = []
    for m in movements:
        try:
            if account_key and (
                str(getattr(m, "account_name", "") or "").strip().casefold()
                != account_key
            ):
                continue
            if not include_transfers and bool(getattr(m, "is_transfer", False)):
                continue
            amt = float(getattr(m, "amount", 0.0) or 0.0)
            if match_income:
                if amt <= 0:  # רק תנועות נכנסות (הכנסה)
                    continue
            elif amt >= 0:  # ברירת מחדל: רק הוצאות
                continue
            if str(getattr(m, "id", "") or "") in excluded:
                continue
            desc = str(getattr(m, "description", "") or "")
            if not desc:
                continue
            if vendor_norm not in normalize_text(desc).casefold():
                continue
            if start_dt is not None:
                if parse_iso_date(str(getattr(m, "date", "") or "")) < start_dt:
                    continue
            out.append(m)
        except PARSE_ERRORS:
            continue

    out.sort(key=lambda x: parse_iso_date(str(getattr(x, "date", "") or "")))
    if max_count is not None and int(max_count) > 0:
        out = out[: int(max_count)]
    return out
