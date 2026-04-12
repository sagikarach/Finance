from __future__ import annotations

import json
import re
import socket
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


def _is_network_error(exc: Exception) -> bool:
    """Return True for genuine no-internet / DNS failures (NOT timeouts).

    Timeouts (httpx.ConnectTimeout, TimeoutError, etc.) mean the server is
    slow or overloaded — they are NOT treated as connectivity failures so the
    retry logic can try the next model instead.
    """
    _NETWORK_PHRASES = (
        "network is unreachable",
        "failed to establish a new connection",
        "name or service not known",
        "getaddrinfo failed",
        "nodename nor servname provided",
        "no route to host",
        "temporary failure in name resolution",
    )
    err_lower = str(exc).lower()
    if any(phrase in err_lower for phrase in _NETWORK_PHRASES):
        return True
    # OSError with ENETUNREACH / EHOSTUNREACH / ENOTCONN errno values
    if isinstance(exc, (ConnectionError, OSError, socket.gaierror)):
        errno_val = getattr(exc, "errno", None)
        if errno_val in (51, 65, 101, 111, 113):  # ENETUNREACH / EHOSTUNREACH / ECONNREFUSED
            return True
    # httpx ConnectError = server actively refused / unreachable (not timeout)
    try:
        import httpx  # noqa: PLC0415
        if isinstance(exc, (httpx.ConnectError, httpx.NetworkError)):
            return True
    except ImportError:
        pass
    # Recursively check wrapped cause
    cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
    if cause and cause is not exc:
        return _is_network_error(cause)
    return False


def _is_timeout_error(exc: Exception) -> bool:
    """Return True for API-level timeouts (server slow, not no-internet)."""
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return True
    try:
        import httpx  # noqa: PLC0415
        if isinstance(exc, httpx.TimeoutException):
            return True
    except ImportError:
        pass
    try:
        import httpcore  # noqa: PLC0415
        if isinstance(exc, httpcore.TimeoutException):
            return True
    except ImportError:
        pass
    cause = getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
    if cause and cause is not exc:
        return _is_timeout_error(cause)
    return False


def _check_connectivity() -> None:
    """Fail immediately (< 200 ms) when there is no internet connection.

    Tries a raw TCP connection to Google's public DNS (8.8.8.8:53).
    The OS returns ENETUNREACH / EHOSTUNREACH in milliseconds when offline.
    """
    try:
        s = socket.create_connection(("8.8.8.8", 53), timeout=2)
        s.close()
    except OSError as _e:
        raise RuntimeError("אין חיבור לאינטרנט. בדוק את חיבור הרשת ונסה שוב.") from _e


def _generate_with_retry(client: Any, prompt: str, retries: int = 2) -> str:
    """Call Gemini with fallback models and smart retry.

    Per-model strategy:
    - 429 daily quota exhausted  → skip immediately to next model
    - 429 RPM (per-minute) limit → wait *retryDelay* seconds, then retry same
      model once more before moving on
    - 503 UNAVAILABLE            → exponential backoff, then next model
    - other errors               → skip to next model
    """
    # Fast offline check — raises in < 200 ms if there is no internet.
    _check_connectivity()

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

                # Hard network failure (ENETUNREACH, DNS failure, etc.) —
                # no point trying other models, raise immediately.
                if _is_network_error(exc):
                    raise RuntimeError(
                        "אין חיבור לאינטרנט. בדוק את חיבור הרשת ונסה שוב."
                    ) from exc

                # API-level timeout (slow server, not offline) → skip to next model
                if _is_timeout_error(exc):
                    break

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
            client = genai.Client(api_key=api_key, http_options={"timeout": 30_000})
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
            client = genai.Client(api_key=api_key, http_options={"timeout": 30_000})
            raw = _generate_with_retry(client, prompt)
        except Exception:
            return {}

        return self._parse_filter_response(raw, id_map)

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
