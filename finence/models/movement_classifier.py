from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Tuple
import json
import re

from .bank_movement import BankMovement, MovementType
from ..utils.app_paths import app_data_dir
from .firebase_session import current_firebase_uid, current_firebase_workspace_id


@dataclass
class SimilarityBasedClassifier:
    SIMILARITY_THRESHOLD: ClassVar[float] = 0.3
    DEFAULT_CATEGORY: ClassVar[str] = "שונות"
    DEFAULT_TYPE: ClassVar[MovementType] = MovementType.MONTHLY
    DEFAULT_CONFIDENCE: ClassVar[float] = 0.3
    MAX_SIMILAR_EXPENSES: ClassVar[int] = 5
    _NOISE_WORDS: ClassVar[set[str]] = {
        "בעמ",
        'בע"מ',
        "בע׳מ",
        "בע״מ",
        "בע?מ",
        "חברה",
        "ישראלי",
        "ישראל",
        "תשלום",
        "תשלומים",
        "דמי",
        "כרטיס",
        "ויזה",
        "לאומי",
        "בנק",
        "העברה",
        "העברות",
        "מפעולות",
        "ישיר",
    }

    TYPE_MAPPING: ClassVar[Dict[str, MovementType]] = {
        "חודשית": MovementType.MONTHLY,
        "חודשי": MovementType.MONTHLY,
        "שנתי": MovementType.YEARLY,
        "שנתית": MovementType.YEARLY,
        "חד פעמי": MovementType.ONE_TIME,
        "חד פעמית": MovementType.ONE_TIME,
        "חד-פעמי": MovementType.ONE_TIME,
        "חד-פעמית": MovementType.ONE_TIME,
        "חד־פעמי": MovementType.ONE_TIME,
        "חד־פעמית": MovementType.ONE_TIME,
    }

    training_data_path: Path = field(default_factory=lambda: _default_training_path())
    _training_data: List[Dict[str, Any]] = field(default_factory=list, init=False)
    _is_initialized: bool = field(default=False, init=False)

    def initialize(self) -> None:
        if self._is_initialized:
            return

        candidate_paths = [
            self.training_data_path,
            Path.cwd() / "data" / "expenses.json",
        ]

        loaded = False
        for candidate_path in candidate_paths:
            try:
                if candidate_path.exists():
                    with candidate_path.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                        if isinstance(data, list):
                            self._training_data = data
                            loaded = True
                            break
            except Exception:
                continue

        if not loaded:
            try:
                self.training_data_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            self._training_data = []

        self._is_initialized = True

    def reload(self) -> None:
        self._training_data = []
        self._is_initialized = False
        self.initialize()

    def set_training_data(self, training: List[Dict[str, Any]]) -> None:
        self._training_data = list(training)
        self._is_initialized = True
        try:
            self.training_data_path.parent.mkdir(parents=True, exist_ok=True)
            with self.training_data_path.open("w", encoding="utf-8") as f:
                json.dump(self._training_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def classify_outcome(
        self,
        movement: BankMovement,
        allowed_categories: Optional[List[str]] = None,
    ) -> Tuple[str, MovementType, float]:
        if not self._is_initialized:
            self.initialize()

        if not self._training_data:
            return (
                self.DEFAULT_CATEGORY,
                self.DEFAULT_TYPE,
                self.DEFAULT_CONFIDENCE,
            )

        similar_expenses = self._find_similar_expenses(movement)

        if not similar_expenses:
            return (
                self.DEFAULT_CATEGORY,
                self.DEFAULT_TYPE,
                self.DEFAULT_CONFIDENCE,
            )

        top_similarity = (
            float(similar_expenses[0].get("similarity", 0.0))
            if similar_expenses
            else 0.0
        )
        is_exact_match = top_similarity > 0.9

        if is_exact_match:
            category = similar_expenses[0].get("category", "") or self.DEFAULT_CATEGORY
            expense_type_str = similar_expenses[0].get("expenseType", "") or "חודשית"
        else:
            category = (
                self._weighted_pick(similar_expenses, field="category")
                or self.DEFAULT_CATEGORY
            )
            expense_type_str = (
                self._weighted_pick(similar_expenses, field="expenseType") or "חודשית"
            )

        movement_type = self.TYPE_MAPPING.get(expense_type_str, self.DEFAULT_TYPE)

        base_similarity = top_similarity

        matching_categories = sum(
            1 for e in similar_expenses if e.get("category", "") == category
        )
        category_agreement = (
            matching_categories / len(similar_expenses) if similar_expenses else 0.0
        )

        if is_exact_match:
            if category_agreement >= 0.6:
                confidence = 0.6 + (0.1 * category_agreement)
            else:
                confidence = 0.5 + (0.1 * category_agreement)
        else:
            confidence = base_similarity * (0.4 + 0.4 * category_agreement)

        if len(similar_expenses) >= 3:
            confidence = min(0.7, confidence * 1.1)
        elif len(similar_expenses) == 1:
            confidence = confidence * 0.75

        confidence = min(0.7, max(0.0, confidence))

        if allowed_categories and category not in allowed_categories:
            category = self._match_category_to_allowed(category, allowed_categories)

        return (category, movement_type, confidence)

    def _match_category_to_allowed(
        self, category: str, allowed_categories: List[str]
    ) -> str:
        for cat in allowed_categories:
            if cat in category or category in cat:
                return cat
        return ""

    def _find_similar_expenses(self, movement: BankMovement) -> List[Dict[str, Any]]:
        similar = []
        for train_expense in self._training_data:
            similarity = self._calculate_similarity(movement, train_expense)
            if similarity > self.SIMILARITY_THRESHOLD:
                similar.append({**train_expense, "similarity": similarity})

        similar.sort(key=lambda x: x.get("similarity", 0.0), reverse=True)
        return similar[: self.MAX_SIMILAR_EXPENSES]

    def _normalize_text(self, s: str) -> str:
        s = s.lower()
        s = re.sub(r"[^0-9a-zא-ת]+", " ", s, flags=re.IGNORECASE)
        s = re.sub(r"\s+", " ", s).strip()
        return s

    def _tokens(self, s: str) -> set[str]:
        s = self._normalize_text(s)
        toks: set[str] = set()
        for w in s.split():
            if len(w) <= 1:
                continue
            if w.isdigit():
                continue
            if w in self._NOISE_WORDS:
                continue
            toks.add(w)
        return toks

    def _token_overlap(self, a: str, b: str) -> float:
        t1 = self._tokens(a)
        t2 = self._tokens(b)
        if not t1 or not t2:
            return 0.0
        inter = len(t1 & t2)
        union = len(t1 | t2)
        if union <= 0:
            return 0.0
        return float(inter) / float(union)

    def _weighted_pick(self, rows: List[Dict[str, Any]], *, field: str) -> str:
        scores: Dict[str, float] = {}
        for r in rows:
            try:
                v = str(r.get(field, "") or "").strip()
                if not v:
                    continue
                sim = float(r.get("similarity", 0.0) or 0.0)
                scores[v] = scores.get(v, 0.0) + max(0.0, sim)
            except Exception:
                continue
        if not scores:
            return ""
        return max(scores.items(), key=lambda x: x[1])[0]

    def _calculate_similarity(
        self, expense1: BankMovement, expense2: Dict[str, Any]
    ) -> float:
        desc_score = 0.0
        amount_score = 0.0

        desc1 = str(expense1.description or "")
        desc2 = str(expense2.get("description", "") or "")

        n1 = self._normalize_text(desc1)
        n2 = self._normalize_text(desc2)

        if n1 and n2 and n1 == n2:
            desc_score += 0.6
        elif n1 and n2 and (n1 in n2 or n2 in n1):
            desc_score += 0.4
        else:
            overlap = self._token_overlap(desc1, desc2)
            if overlap >= 0.5:
                desc_score += 0.6
            elif overlap >= 0.25:
                desc_score += 0.4
            elif overlap >= 0.12:
                desc_score += 0.3

        if desc_score <= 0.0:
            return 0.0

        try:
            amount1 = abs(expense1.amount)
            amount2 = abs(float(expense2.get("amount", 0)))
            amount_diff = abs(amount1 - amount2)

            if amount_diff < 10:
                amount_score += 0.4
            elif amount_diff < 50:
                amount_score += 0.3
            elif amount_diff < 100:
                amount_score += 0.2
        except (ValueError, TypeError):
            pass

        return desc_score + amount_score

    def _has_common_words(self, str1: str, str2: str) -> bool:
        return bool(self._tokens(str1) & self._tokens(str2))

    def _get_most_common(self, array: List[str]) -> Optional[str]:
        if not array:
            return None

        counts: Dict[str, int] = {}
        for value in array:
            counts[value] = counts.get(value, 0) + 1

        if not counts:
            return None

        return max(counts.items(), key=lambda x: x[1])[0]

    def learn(self, confirmed_expense: Dict[str, Any]) -> None:
        if not self._is_initialized:
            self.initialize()

        description = str(confirmed_expense.get("description", ""))
        amount = float(confirmed_expense.get("amount", 0))

        is_duplicate = any(
            str(e.get("description", "")) == description
            and abs(float(e.get("amount", 0)) - amount) < 0.01
            for e in self._training_data
        )

        if not is_duplicate:
            self._training_data.append(confirmed_expense)

            try:
                self.training_data_path.parent.mkdir(parents=True, exist_ok=True)
                with self.training_data_path.open("w", encoding="utf-8") as f:
                    json.dump(self._training_data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass


def _default_training_path() -> Path:
    key = (current_firebase_workspace_id() or current_firebase_uid() or "").strip()
    suffix = f"_{key}" if key else ""
    return app_data_dir() / "training" / f"expenses{suffix}.json"
