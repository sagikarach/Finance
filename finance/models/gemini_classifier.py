from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple

from .bank_movement import MovementType
from .keychain_passwords import delete_password, get_password, set_password

_KEYCHAIN_ACCOUNT = "gemini_api_key"
_MODEL = "gemini-2.5-flash"
_CONFIDENCE = 0.85

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
            response = client.models.generate_content(
                model=_MODEL,
                contents=prompt,
            )
            raw = (response.text or "").strip()
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


# Singleton for reuse
_classifier: Optional[GeminiClassifier] = None


def get_gemini_classifier() -> GeminiClassifier:
    global _classifier
    if _classifier is None:
        _classifier = GeminiClassifier()
    return _classifier
