from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Protocol, Tuple
import json

from .bank_movement import BankMovement, MovementType


class MovementClassifier(Protocol):
    def classify_outcome(
        self,
        movement: BankMovement,
        allowed_categories: Optional[List[str]] = None,
    ) -> Tuple[str, MovementType, float]:
        """
        Classify an outcome movement.

        Returns:
            category: suggested category name (empty string if unknown)
            type: MovementType suggestion
            confidence: float in [0.0, 1.0]
        """


# Removed AIMovementClassifier - using SimilarityBasedClassifier instead


@dataclass
class SimilarityBasedClassifier:
    """
    Similarity-based movement classifier that learns from historical expenses.

    Based on the JavaScript ExpenseClassifier logic:
    - Finds similar expenses based on description and amount
    - Returns most common category/type from similar expenses
    - Learns from confirmed expenses to improve over time
    """

    # Class constants (not dataclass fields)
    SIMILARITY_THRESHOLD: ClassVar[float] = 0.3
    DEFAULT_CATEGORY: ClassVar[str] = "שונות"
    DEFAULT_TYPE: ClassVar[MovementType] = MovementType.MONTHLY
    DEFAULT_CONFIDENCE: ClassVar[float] = 0.3
    MAX_SIMILAR_EXPENSES: ClassVar[int] = 5

    # Type mapping from Hebrew strings to MovementType enum (class constant)
    TYPE_MAPPING: ClassVar[Dict[str, MovementType]] = {
        "חודשית": MovementType.MONTHLY,
        "חודשי": MovementType.MONTHLY,
        "שנתי": MovementType.YEARLY,
        "שנתית": MovementType.YEARLY,
        "חד פעמי": MovementType.ONE_TIME,
    }

    training_data_path: Path = field(
        default_factory=lambda: Path.cwd() / "data" / "expenses.json"
    )
    _training_data: List[Dict[str, Any]] = field(default_factory=list, init=False)
    _is_initialized: bool = field(default=False, init=False)

    def initialize(self) -> None:
        """Load training data from JSON file."""
        if self._is_initialized:
            return

        # Try multiple candidate paths (similar to JavaScript version)
        candidate_paths = [
            self.training_data_path,  # Default: cwd/data/expenses.json
            Path.cwd() / "data" / "expenses.json",  # Current working directory
            Path.home() / "Desktop" / "data" / "expenses.json",  # Desktop location
            Path("/Users/sagikarach/Desktop/data/expenses.json"),  # Absolute path
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
            # If no file found, create directory for default path
            try:
                self.training_data_path.parent.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
            self._training_data = []

        self._is_initialized = True

    def classify_outcome(
        self,
        movement: BankMovement,
        allowed_categories: Optional[List[str]] = None,
    ) -> Tuple[str, MovementType, float]:
        """
        Classify an outcome movement using similarity-based matching.

        Returns:
            category: suggested category name (empty string if unknown)
            type: MovementType suggestion
            confidence: float in [0.0, 1.0]
        """
        if not self._is_initialized:
            self.initialize()

        if not self._training_data:
            return (
                self.DEFAULT_CATEGORY,
                self.DEFAULT_TYPE,
                self.DEFAULT_CONFIDENCE,
            )

        # Find similar expenses
        similar_expenses = self._find_similar_expenses(movement)

        if not similar_expenses:
            return (
                self.DEFAULT_CATEGORY,
                self.DEFAULT_TYPE,
                self.DEFAULT_CONFIDENCE,
            )

        # Get most common category and type from similar expenses
        # Weight by similarity: if top match has very high similarity (>0.9), prefer it
        top_similarity = (
            float(similar_expenses[0].get("similarity", 0.0))
            if similar_expenses
            else 0.0
        )
        is_exact_match = top_similarity > 0.9

        if is_exact_match:
            # For very high similarity, use the top match directly
            category = similar_expenses[0].get("category", "") or self.DEFAULT_CATEGORY
            expense_type_str = similar_expenses[0].get("expenseType", "") or "חודשית"
        else:
            # For lower similarity, use most common from all similar expenses
            categories = [
                e.get("category", "") for e in similar_expenses if e.get("category")
            ]
            types = [
                e.get("expenseType", "")
                for e in similar_expenses
                if e.get("expenseType")
            ]

            category = self._get_most_common(categories) or self.DEFAULT_CATEGORY
            expense_type_str = self._get_most_common(types) or "חודשית"

        # Map Hebrew type strings to MovementType enum
        movement_type = self.TYPE_MAPPING.get(expense_type_str, self.DEFAULT_TYPE)

        # Calculate confidence based on:
        # 1. Similarity score (how similar the expense is)
        # 2. Category agreement (how many similar expenses agree on the category)
        # 3. Number of similar expenses (more = more confident)
        base_similarity = top_similarity

        # Calculate category agreement ratio
        matching_categories = sum(
            1 for e in similar_expenses if e.get("category", "") == category
        )
        category_agreement = (
            matching_categories / len(similar_expenses) if similar_expenses else 0.0
        )

        # Calculate confidence more conservatively
        if is_exact_match:
            # Very high similarity (exact or near-exact match)
            # For exact matches, trust the top match but still consider agreement
            if category_agreement >= 0.6:  # 60%+ of similar expenses agree
                # Good agreement with exact match = moderate-high confidence
                confidence = 0.6 + (0.1 * category_agreement)  # 60-70% range
            else:
                # Lower agreement - reduce confidence even for exact matches
                confidence = 0.5 + (0.1 * category_agreement)  # 50-60% range
        else:
            # Lower similarity - be more conservative
            # Weight by both similarity and category agreement
            confidence = base_similarity * (0.4 + 0.4 * category_agreement)

        # Adjust based on number of similar expenses
        if len(similar_expenses) >= 3:
            # Multiple matches increase confidence (more data points = more reliable)
            confidence = min(0.7, confidence * 1.1)
        elif len(similar_expenses) == 1:
            # Single match is less reliable - reduce confidence
            confidence = confidence * 0.75

        # Cap confidence to prevent overconfidence
        # Even perfect matches shouldn't exceed 0.7 (70%) to always leave room for user review
        confidence = min(0.7, max(0.0, confidence))

        # Filter by allowed categories if provided
        if allowed_categories and category not in allowed_categories:
            category = self._match_category_to_allowed(category, allowed_categories)

        return (category, movement_type, confidence)

    def _match_category_to_allowed(
        self, category: str, allowed_categories: List[str]
    ) -> str:
        """
        Try to match a category to the allowed categories list using substring matching.

        Args:
            category: The category to match
            allowed_categories: List of allowed category names

        Returns:
            Matched category name or empty string if no match found
        """
        for cat in allowed_categories:
            if cat in category or category in cat:
                return cat
        return ""

    def _find_similar_expenses(self, movement: BankMovement) -> List[Dict[str, Any]]:
        """Find similar expenses from training data."""
        similar = []
        for train_expense in self._training_data:
            similarity = self._calculate_similarity(movement, train_expense)
            if similarity > self.SIMILARITY_THRESHOLD:
                similar.append({**train_expense, "similarity": similarity})

        # Sort by similarity (descending) and take top N
        similar.sort(key=lambda x: x.get("similarity", 0.0), reverse=True)
        return similar[: self.MAX_SIMILAR_EXPENSES]

    def _calculate_similarity(
        self, expense1: BankMovement, expense2: Dict[str, Any]
    ) -> float:
        """Calculate similarity score between two expenses."""
        score = 0.0

        # Compare descriptions
        desc1 = (expense1.description or "").lower()
        desc2 = str(expense2.get("description", "")).lower()

        # Exact match
        if desc1 == desc2:
            score += 0.6
        # Contains each other
        elif desc1 in desc2 or desc2 in desc1:
            score += 0.4
        # Has common words
        elif self._has_common_words(desc1, desc2):
            score += 0.3

        # Compare amounts
        try:
            amount1 = abs(expense1.amount)
            amount2 = abs(float(expense2.get("amount", 0)))
            amount_diff = abs(amount1 - amount2)

            if amount_diff < 10:
                score += 0.4
            elif amount_diff < 50:
                score += 0.3
            elif amount_diff < 100:
                score += 0.2
        except (ValueError, TypeError):
            pass

        return score

    def _has_common_words(self, str1: str, str2: str) -> bool:
        """Check if two strings have common words."""
        words1 = set(str1.split())
        words2 = set(str2.split())
        return bool(words1 & words2)  # Intersection

    def _get_most_common(self, array: List[str]) -> Optional[str]:
        """Get the most common value from an array."""
        if not array:
            return None

        counts: Dict[str, int] = {}
        for value in array:
            counts[value] = counts.get(value, 0) + 1

        if not counts:
            return None

        return max(counts.items(), key=lambda x: x[1])[0]

    def learn(self, confirmed_expense: Dict[str, Any]) -> None:
        """
        Learn from a confirmed expense by adding it to training data.

        Args:
            confirmed_expense: Dictionary with keys: description, amount, category, expenseType
        """
        if not self._is_initialized:
            self.initialize()

        # Check for duplicates
        description = str(confirmed_expense.get("description", ""))
        amount = float(confirmed_expense.get("amount", 0))

        is_duplicate = any(
            str(e.get("description", "")) == description
            and abs(float(e.get("amount", 0)) - amount) < 0.01
            for e in self._training_data
        )

        if not is_duplicate:
            self._training_data.append(confirmed_expense)

            # Save updated training data
            try:
                self.training_data_path.parent.mkdir(parents=True, exist_ok=True)
                with self.training_data_path.open("w", encoding="utf-8") as f:
                    json.dump(self._training_data, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
