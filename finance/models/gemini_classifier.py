from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from .bank_movement import MovementType
from .keychain_passwords import delete_password, get_password, set_password

_KEYCHAIN_ACCOUNT = "gemini_api_key"
_MODEL = "gemini-2.0-flash"
_CONFIDENCE = 0.85

def _generate_with_retry(client: Any, prompt: str, retries: int = 2) -> str:
    """Call Gemini with simple exponential-backoff retry on 503."""
    last_err: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            response = client.models.generate_content(model=_MODEL, contents=prompt)
            return (response.text or "").strip()
        except Exception as exc:
            last_err = exc
            if attempt < retries:
                time.sleep(2 ** attempt)
    raise last_err  # type: ignore[misc]


_TYPE_MAP: Dict[str, MovementType] = {
    "חודשי": MovementType.MONTHLY,
    "חודשית": MovementType.MONTHLY,
    "שנתי": MovementType.YEARLY,
    "שנתית": MovementType.YEARLY,
    "חד פעמי": MovementType.ONE_TIME,
    "חד פעמית": MovementType.ONE_TIME,
    "חד-פעמי": MovementType.ONE_TIME,
    "חד-פעמית": MovementType.ONE_TIME,
}


# ---------------------------------------------------------------------------
# API key helpers (stored in macOS Keychain)
# ---------------------------------------------------------------------------

def get_gemini_api_key() -> Optional[str]:
    return get_password(account=_KEYCHAIN_ACCOUNT)


def set_gemini_api_key(key: str) -> None:
    key = str(key or "").strip()
    if key:
        set_password(account=_KEYCHAIN_ACCOUNT, password=key)
    else:
        delete_password(account=_KEYCHAIN_ACCOUNT)


def has_gemini_api_key() -> bool:
    k = get_gemini_api_key()
    return bool(k)


# ---------------------------------------------------------------------------
# Batch classifier
# ---------------------------------------------------------------------------

class GeminiClassifier:
    """Batch-classify bank transaction descriptions using Gemini.

    Designed to be used as a fallback when the similarity-based classifier
    returns low confidence.  All low-confidence items are sent in a single
    API call to minimise quota usage.
    """

    def classify_batch(
        self,
        expenses: List[Tuple[str, float]],
        allowed_categories: List[str],
    ) -> Dict[int, Tuple[str, MovementType]]:
        """Classify a batch of expenses via Gemini.

        Args:
            expenses: list of (description, amount) tuples.
            allowed_categories: categories the user has defined.

        Returns:
            dict mapping expense index → (category, MovementType).
            Indices whose classification failed are absent from the result.
        """
        if not expenses:
            return {}

        api_key = get_gemini_api_key()
        if not api_key:
            return {}

        try:
            import google.genai as genai  # type: ignore[import]
        except ImportError:
            return {}

        cats = ", ".join(allowed_categories) if allowed_categories else "שונות"
        types_str = "חודשי, שנתי, חד פעמי"

        lines = []
        for i, (desc, amount) in enumerate(expenses, start=1):
            lines.append(f'{i}. "{desc}" {amount:+.0f}₪')

        prompt = (
            "אתה מסווג פעולות בנקאיות בעברית.\n"
            f"קטגוריות מותרות: {cats}\n"
            f"סוגי תשלום מותרים: {types_str}\n\n"
            "עבור כל פעולה, החזר אובייקט JSON עם שתי שדות:\n"
            '  "category": אחד מהקטגוריות המותרות\n'
            '  "type": אחד מסוגי התשלום המותרים\n\n'
            "החזר אך ורק מערך JSON תקין, ללא הסברים נוספים.\n"
            "מספר האובייקטים חייב להיות זהה למספר הפעולות.\n\n"
            "פעולות:\n"
            + "\n".join(lines)
        )

        try:
            client = genai.Client(api_key=api_key)
            raw = _generate_with_retry(client, prompt)
        except Exception:
            return {}

        return self._parse_response(raw, len(expenses), allowed_categories)

    # ------------------------------------------------------------------

    def _parse_response(
        self,
        raw: str,
        expected: int,
        allowed_categories: List[str],
    ) -> Dict[int, Tuple[str, MovementType]]:
        # Strip markdown code fences if present
        cleaned = re.sub(r"```[a-z]*\n?", "", raw).strip()

        try:
            data = json.loads(cleaned)
        except Exception:
            # Try to extract a JSON array from the middle of the text
            m = re.search(r"\[.*\]", cleaned, re.DOTALL)
            if not m:
                return {}
            try:
                data = json.loads(m.group(0))
            except Exception:
                return {}

        if not isinstance(data, list):
            return {}

        result: Dict[int, Tuple[str, MovementType]] = {}
        for i, item in enumerate(data):
            if i >= expected:
                break
            if not isinstance(item, dict):
                continue
            raw_cat = str(item.get("category", "") or "").strip()
            raw_type = str(item.get("type", "") or "").strip()

            cat = self._match_category(raw_cat, allowed_categories)
            mtype = _TYPE_MAP.get(raw_type, MovementType.ONE_TIME)
            result[i] = (cat, mtype)

        return result

    def _match_category(self, category: str, allowed: List[str]) -> str:
        if not category:
            return "שונות"
        if not allowed:
            return category
        # Exact match
        if category in allowed:
            return category
        # Partial match
        for cat in allowed:
            if cat in category or category in cat:
                return cat
        return "שונות"


    # ------------------------------------------------------------------
    # Notification filter
    # ------------------------------------------------------------------

    def filter_unexpected_expenses(
        self,
        candidates: List[Dict[str, Any]],
        category_context: str,
    ) -> Dict[str, Tuple[bool, str]]:
        """Filter candidate 'unexpected expense' notifications through Gemini.

        Gemini decides whether each transaction is *genuinely* unusual given
        the user's spending history, and provides a Hebrew explanation.

        Args:
            candidates: list of dicts with keys:
                movement_id, description, amount (negative float),
                category, date
            category_context: formatted string of per-category monthly
                averages over the past 6 months.

        Returns:
            dict mapping movement_id → (is_genuinely_unusual, reason_hebrew).
            Missing entries mean the movement was not evaluated (treat as
            unusual = True to preserve the original behaviour as fallback).
        """
        if not candidates:
            return {}

        api_key = get_gemini_api_key()
        if not api_key:
            return {}

        try:
            import google.genai as genai  # type: ignore[import]
        except ImportError:
            return {}

        # Use sequential indices in the prompt — UUIDs risk being mangled by the LLM.
        # We map back from index → movement_id after parsing.
        id_map: Dict[int, str] = {}
        lines = []
        for i, c in enumerate(candidates):
            desc = str(c.get("description") or "")
            amt = abs(float(c.get("amount") or 0))
            cat = str(c.get("category") or "")
            dt = str(c.get("date") or "")
            mid = str(c.get("movement_id") or "")
            id_map[i] = mid
            lines.append(f'  {i}. {dt} | {cat} | "{desc}" | {amt:,.0f}₪')

        prompt = (
            "אתה מנתח דפוסי הוצאות אישיות.\n\n"
            "להלן ממוצעי ההוצאות החודשיים לפי קטגוריה בחצי השנה האחרונה:\n"
            f"{category_context}\n\n"
            "עבור כל עסקה להלן, קבע אם היא באמת חריגה ובלתי צפויה.\n"
            "חשוב: תשלומים שנתיים ידועים (ביטוח, ארנונה), חינוך קבוע, "
            "תשלומים חוזרים — אינם חריגים גם אם הסכום גבוה.\n"
            "חריגה אמיתית = עלייה פתאומית בקטגוריה שרגילה להיות נמוכה, "
            "חיוב כפול, סכום שגבוה משמעותית מהממוצע ללא סיבה צפויה.\n\n"
            "החזר אך ורק מערך JSON תקין, ללא הסברים נוספים.\n"
            'כל אובייקט: {"index": <מספר העסקה>, "is_unusual": true/false, '
            '"reason": "הסבר קצר בעברית (משפט אחד)"}\n\n'
            "עסקאות:\n"
            + "\n".join(lines)
        )

        try:
            client = genai.Client(api_key=api_key)
            raw = _generate_with_retry(client, prompt)
        except Exception:
            return {}

        return self._parse_filter_response(raw, id_map)

    # ------------------------------------------------------------------
    # Savings balance projection
    # ------------------------------------------------------------------

    def predict_savings_balances(
        self,
        savings_input: List[Dict[str, Any]],
        monthly_net_savings: float,
        today_year: int,
        today_month: int,
        horizon: int = 12,
    ) -> Dict[str, List[float]]:
        """Predict savings balances for the next *horizon* months.

        Args:
            savings_input: list of dicts, each with:
                - name: str
                - current: float  (latest known balance)
                - history: list of {"month": "YYYY-MM", "balance": float}
            monthly_net_savings: average monthly net savings (income-expenses)
                computed from the last 6 months of movements data.
            today_year / today_month: current date for the prompt context.
            horizon: how many months to project (default 12).

        Returns:
            dict mapping saving name → list[float] of length *horizon*.
            Missing entries mean the prediction failed for that saving.
        """
        if not savings_input:
            return {}

        api_key = get_gemini_api_key()
        if not api_key:
            return {}

        try:
            import google.genai as genai  # type: ignore[import]
        except ImportError:
            return {}

        # Build future month labels for the prompt
        future_months: List[str] = []
        y, m = today_year, today_month
        for _ in range(horizon):
            m += 1
            if m > 12:
                m = 1
                y += 1
            future_months.append(f"{y}-{m:02d}")

        # Format each saving's history (last 12 snapshots)
        savings_lines: List[str] = []
        for s in savings_input:
            name = str(s.get("name") or "")
            current = float(s.get("current") or 0.0)
            hist = list(s.get("history") or [])
            hist_sorted = sorted(hist, key=lambda h: str(h.get("month") or ""))
            hist_recent = hist_sorted[-12:]
            hist_str = ", ".join(
                f'{h["month"]}: {float(h["balance"]):,.0f}₪' for h in hist_recent
            )
            savings_lines.append(
                f'  - "{name}" | יתרה נוכחית: {current:,.0f}₪'
                + (f' | היסטוריה: {hist_str}' if hist_str else "")
            )

        prompt = (
            "אתה יועץ פיננסי אישי. חזה את יתרת כל חסכון לכל אחד מהחודשים הבאים.\n\n"
            f"קצב חיסכון נטו חודשי ממוצע (הכנסות פחות הוצאות, 6 חודשים אחרונים): "
            f"{monthly_net_savings:,.0f}₪\n\n"
            "חסכונות:\n"
            + "\n".join(savings_lines)
            + "\n\n"
            f"חודש נוכחי: {today_year}-{today_month:02d}\n"
            f"חזה עבור חודשים: {', '.join(future_months)}\n\n"
            "הנחות:\n"
            "- שמור על קצב הצמיחה שנצפה בכל חסכון בפועל (מהנתונים ההיסטוריים).\n"
            "- אם אין מספיק היסטוריה, הניח קצב יציב.\n"
            "- אל תמציא תשואות — הסתמך רק על הנתונים שסופקו.\n\n"
            "החזר אך ורק JSON array תקין (ללא הסברים):\n"
            '[{"name": "שם החסכון", '
            '"projections": [{"month": "YYYY-MM", "balance": 12345}, ...]}, ...]\n'
            "מספר האובייקטים = מספר החסכונות. "
            "מספר ה-projections בכל אובייקט = " + str(horizon) + "."
        )

        try:
            client = genai.Client(api_key=api_key)
            raw = _generate_with_retry(client, prompt)
        except Exception:
            return {}

        return self._parse_projection_response(raw, savings_input, future_months)

    def _parse_projection_response(
        self,
        raw: str,
        savings_input: List[Dict[str, Any]],
        future_months: List[str],
    ) -> Dict[str, List[float]]:
        cleaned = re.sub(r"```[a-z]*\n?", "", raw).strip()

        try:
            data = json.loads(cleaned)
        except Exception:
            m = re.search(r"\[.*\]", cleaned, re.DOTALL)
            if not m:
                return {}
            try:
                data = json.loads(m.group(0))
            except Exception:
                return {}

        if not isinstance(data, list):
            return {}

        known_names = {str(s.get("name") or "") for s in savings_input}
        result: Dict[str, List[float]] = {}

        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            # Fuzzy match: allow partial name overlap
            matched_name = name if name in known_names else next(
                (n for n in known_names if n in name or name in n), name
            )
            projections = item.get("projections") or []
            if not isinstance(projections, list):
                continue

            # Build ordered list aligned to future_months
            month_to_bal: Dict[str, float] = {}
            for p in projections:
                if not isinstance(p, dict):
                    continue
                try:
                    month_to_bal[str(p["month"])] = float(p["balance"])
                except Exception:
                    continue

            balances: List[float] = []
            last = 0.0
            for fm in future_months:
                val = month_to_bal.get(fm)
                if val is not None:
                    last = val
                balances.append(last)

            if any(b > 0 for b in balances):
                result[matched_name] = balances

        return result

    def _parse_filter_response(
        self, raw: str, id_map: Optional[Dict[int, str]] = None
    ) -> Dict[str, Tuple[bool, str]]:
        cleaned = re.sub(r"```[a-z]*\n?", "", raw).strip()

        try:
            data = json.loads(cleaned)
        except Exception:
            m = re.search(r"\[.*\]", cleaned, re.DOTALL)
            if not m:
                return {}
            try:
                data = json.loads(m.group(0))
            except Exception:
                return {}

        if not isinstance(data, list):
            return {}

        result: Dict[str, Tuple[bool, str]] = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            is_unusual = bool(item.get("is_unusual", True))
            reason = str(item.get("reason") or "").strip()

            # Prefer index-based lookup (new format)
            if id_map is not None and "index" in item:
                try:
                    idx = int(item["index"])
                    mid = id_map.get(idx)
                    if mid:
                        result[mid] = (is_unusual, reason)
                        continue
                except Exception:
                    pass

            # Fallback: movement_id field (old format)
            mid = str(item.get("movement_id") or "").strip()
            if mid:
                result[mid] = (is_unusual, reason)

        return result


# Singleton for reuse
_classifier: Optional[GeminiClassifier] = None


def get_gemini_classifier() -> GeminiClassifier:
    global _classifier
    if _classifier is None:
        _classifier = GeminiClassifier()
    return _classifier
