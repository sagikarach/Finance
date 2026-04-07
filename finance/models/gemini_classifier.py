from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

from .bank_movement import MovementType
from .keychain_passwords import delete_password, get_password, set_password

_KEYCHAIN_ACCOUNT = "gemini_api_key"
# Ordered list of models to try; first available / not quota-exhausted wins.
_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash-lite",
    "gemini-flash-lite-latest",
]
_CONFIDENCE = 0.85


def _parse_retry_delay(err_str: str) -> Optional[int]:
    """Extract retryDelay seconds from a Gemini 429 error string, if present."""
    m = re.search(r"['\"]retryDelay['\"]:\s*['\"](\d+)s['\"]", err_str)
    return int(m.group(1)) if m else None


def _is_daily_quota(err_str: str) -> bool:
    """Return True when the 429 means the *daily* quota is exhausted (skip model)."""
    return "PerDay" in err_str or "Per1Day" in err_str or "limit: 0" in err_str


def _generate_with_retry(client: Any, prompt: str, retries: int = 2) -> str:
    """Call Gemini with fallback models and smart retry.

    Per-model strategy:
    - 429 daily quota exhausted  → skip immediately to next model
    - 429 RPM (per-minute) limit → wait *retryDelay* seconds, then retry same
      model once more before moving on
    - 503 UNAVAILABLE            → exponential backoff, then next model
    - other errors               → skip to next model
    """
    last_err: Optional[Exception] = None
    for model in _MODELS:
        rpm_waited = False  # only wait once per model for RPM
        for attempt in range(retries + 1):
            try:
                response = client.models.generate_content(
                    model=model, contents=prompt
                )
                return (response.text or "").strip()
            except Exception as exc:
                last_err = exc
                err_str = str(exc)

                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    if _is_daily_quota(err_str):
                        break  # daily quota gone → next model
                    if not rpm_waited:
                        # RPM limit: wait the suggested delay, then retry once
                        delay = _parse_retry_delay(err_str) or 62
                        delay = min(delay + 2, 70)  # small buffer, cap at 70 s
                        time.sleep(delay)
                        rpm_waited = True
                        continue  # retry same model after waiting
                    break  # already waited once, move to next model

                if "503" in err_str or "UNAVAILABLE" in err_str:
                    if attempt < retries:
                        time.sleep(2 ** attempt)
                    else:
                        break
                else:
                    break  # unexpected error → try next model

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
    # Monthly net cash-flow prediction (for annual overview chart)
    # ------------------------------------------------------------------

    def predict_monthly_net(
        self,
        history: List[Tuple[str, float]],
        horizon: int = 6,
    ) -> List[float]:
        """Predict net cash-flow (income - expenses) for the next *horizon* months.

        Args:
            history: list of (label, net_amount) pairs, oldest first.
            horizon: number of future months to predict.

        Returns list[float] of length *horizon*, or [] on failure.
        """
        if not history:
            return []
        api_key = get_gemini_api_key()
        if not api_key:
            return []
        try:
            import google.genai as genai  # type: ignore[import]
        except ImportError:
            return []

        from datetime import date as _date

        today = _date.today()
        future_months: List[str] = []
        y, m = today.year, today.month
        for _ in range(horizon):
            m += 1
            if m > 12:
                m = 1
                y += 1
            future_months.append(f"{y}-{m:02d}")

        hist_lines = "\n".join(
            f"  {label}: {net:+,.0f}₪" for label, net in history[-24:]
        )

        prompt = (
            "אתה יועץ פיננסי אישי. מטה מופיע תזרים המזומנים החודשי הנטו (הכנסות פחות הוצאות) "
            "לאורך הזמן:\n\n"
            + hist_lines
            + "\n\nחזה את יתרת הנטו החודשית לחודשים הבאים: "
            + ", ".join(future_months)
            + "\n\nהנחות: שמור על מגמה שנצפתה. הסתמך על הנתונים בלבד.\n\n"
            "החזר אך ורק JSON array תקין:\n"
            '[{"month": "YYYY-MM", "net": 5000}, ...]\n'
            f"מספר האלמנטים: {horizon}."
        )

        try:
            client = genai.Client(api_key=api_key)
            raw = _generate_with_retry(client, prompt)
        except Exception:
            return []

        return self._parse_monthly_net_response(raw, future_months)

    def _parse_monthly_net_response(
        self, raw: str, future_months: List[str]
    ) -> List[float]:
        cleaned = re.sub(r"```[a-z]*\n?", "", raw).strip()
        try:
            data = json.loads(cleaned)
        except Exception:
            m = re.search(r"\[.*\]", cleaned, re.DOTALL)
            if not m:
                return []
            try:
                data = json.loads(m.group(0))
            except Exception:
                return []

        if not isinstance(data, list):
            return []

        month_to_net: Dict[str, float] = {}
        for item in data:
            if not isinstance(item, dict):
                continue
            try:
                month_to_net[str(item["month"])] = float(item["net"])
            except Exception:
                continue

        result: List[float] = []
        last = 0.0
        for fm in future_months:
            val = month_to_net.get(fm)
            if val is not None:
                last = val
            result.append(last)

        return result if any(v != 0.0 for v in result) else []

    # ------------------------------------------------------------------
    # Category trend prediction (for category trends chart)
    # ------------------------------------------------------------------

    def predict_category_trends(
        self,
        category_history: Dict[str, List[float]],
        month_labels: List[str],
        horizon: int = 6,
        max_categories: int = 8,
    ) -> Dict[str, List[float]]:
        """Predict per-category monthly totals for the next *horizon* months.

        Args:
            category_history: category → list of monthly amounts (oldest first).
            month_labels: labels for each history month (for context in prompt).
            horizon: future months to predict.
            max_categories: limit prompt size by only predicting top N categories.

        Returns dict mapping category name → list[float] of length *horizon*.
        """
        if not category_history:
            return {}
        api_key = get_gemini_api_key()
        if not api_key:
            return {}
        try:
            import google.genai as genai  # type: ignore[import]
        except ImportError:
            return {}

        from datetime import date as _date

        today = _date.today()
        future_months: List[str] = []
        y, m = today.year, today.month
        for _ in range(horizon):
            m += 1
            if m > 12:
                m = 1
                y += 1
            future_months.append(f"{y}-{m:02d}")

        # Keep only top-N categories by total amount
        top_cats = sorted(
            category_history.items(), key=lambda kv: -sum(kv[1])
        )[:max_categories]

        hist_lines: List[str] = []
        for cat_name, vals in top_cats:
            row = ", ".join(f"{v:,.0f}" for v in vals[-12:])
            hist_lines.append(f'  "{cat_name}": [{row}]')

        prompt = (
            "אתה יועץ פיננסי אישי. מטה מופיעים סכומי ההוצאה החודשיים לפי קטגוריה "
            f"(חודשים: {', '.join(month_labels[-12:])}):\n\n"
            + "\n".join(hist_lines)
            + "\n\nחזה את הסכום החודשי לכל קטגוריה לחודשים: "
            + ", ".join(future_months)
            + "\n\nהנחות: שמור על מגמה שנצפתה. הסתמך על הנתונים בלבד.\n\n"
            "החזר אך ורק JSON array תקין:\n"
            '[{"category": "שם", "projections": [1234, 2345, ...]}, ...]\n'
            f"מספר ה-projections בכל אובייקט: {horizon}."
        )

        try:
            client = genai.Client(api_key=api_key)
            raw = _generate_with_retry(client, prompt)
        except Exception:
            return {}

        return self._parse_category_trends_response(raw, top_cats, horizon)

    def _parse_category_trends_response(
        self,
        raw: str,
        top_cats: List[Tuple[str, List[float]]],
        horizon: int,
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

        known = {str(cat): vals for cat, vals in top_cats}
        result: Dict[str, List[float]] = {}

        for item in data:
            if not isinstance(item, dict):
                continue
            name = str(item.get("category") or "").strip()
            if not name:
                continue
            matched = name if name in known else next(
                (k for k in known if k in name or name in k), name
            )
            projs = item.get("projections") or []
            if not isinstance(projs, list):
                continue
            vals = []
            for p in projs[:horizon]:
                try:
                    vals.append(float(p))
                except Exception:
                    vals.append(0.0)
            while len(vals) < horizon:
                vals.append(vals[-1] if vals else 0.0)
            if any(v > 0 for v in vals):
                result[matched] = vals

        return result

    # ------------------------------------------------------------------
    # Savings balance projection
    # ------------------------------------------------------------------

    def predict_savings_balances(
        self,
        savings_input: List[Dict[str, Any]],
        monthly_net_savings: float,
        today_year: int,
        today_month: int,
        horizon: int = 6,
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
