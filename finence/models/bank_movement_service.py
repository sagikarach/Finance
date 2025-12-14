from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Union, Dict
import csv
import re
from io import StringIO

from ..data.bank_movement_provider import BankMovementProvider
from ..data.action_history_provider import ActionHistoryProvider
from .accounts import MoneyAccount, BankAccount, MoneySnapshot
from .bank_movement import BankMovement, MovementType
from .movement_classifier import MovementClassifier
from .classified_expense import ClassifiedExpense
from .parsed_expense import ParsedExpense
from .action_history import (
    ActionHistory,
    AddIncomeMovementAction,
    AddOutcomeMovementAction,
    generate_action_id,
    get_current_timestamp,
)


@dataclass
class CsvExpenseParser:
    """
    Improved CSV parser based on JavaScript ExpenseParser logic.
    Uses regex-based header detection and handles quoted fields properly.
    """

    @staticmethod
    def clean_description(description: str) -> str:
        """Clean description: remove quotes and backslashes"""
        if not description:
            return ""
        return (
            description.replace('"', "")
            .replace("'", "")
            .replace('"', "")
            .replace("\\", "")
            .strip()
        )

    @staticmethod
    def _normalize(s: str) -> str:
        """Remove BOM, quotes, commas, and whitespace for pattern matching"""
        return (
            s.replace("\ufeff", "").replace('"', "").replace(",", "").replace(" ", "")
        )

    def parse(self, csv_text: str) -> List[ParsedExpense]:
        """
        Parse CSV file and extract expense rows.

        Returns list of ParsedExpense objects
        """
        expenses = []
        lines = csv_text.split("\n")

        # Regex pattern to match Hebrew header: תאריך העסקה, שם בית העסק, סכום העסקה/חיוב
        # Pattern matches variations: תאריךעסק[אה]?שםביתה?עסקסכוםה?עסקה
        header_pattern = re.compile(
            r"תאריך\s*עסק[אה]?\s*שם\s*בית\s*העסק\s*סכום\s*[הח]?עסקה"
        )

        # Also match header with "סכום חיוב" which is the preferred format
        preferred_header_pattern = re.compile(
            r"תאריך\s*עסק[אה]?\s*שם\s*בית\s*העסק.*סכום\s*חיוב"
        )

        # Find header row - prefer headers with "סכום חיוב"
        header_idx = -1
        column_map: Dict[str, int] = {"date": 0, "desc": 1, "amount": 2}  # defaults
        preferred_header_idx = -1

        # First pass: find preferred headers (with "סכום חיוב")
        for i, line in enumerate(lines):
            normalized = self._normalize(line)
            if preferred_header_pattern.search(normalized):
                preferred_header_idx = i
                break

        # Second pass: find any matching header if no preferred one found
        if preferred_header_idx == -1:
            for i, line in enumerate(lines):
                normalized = self._normalize(line)
                if header_pattern.search(normalized):
                    preferred_header_idx = i
                    break

        if preferred_header_idx != -1:
            header_idx = preferred_header_idx
            # Parse header to map column indices
            line = lines[header_idx]
            parts = line.replace("\ufeff", "").split(",")
            parts = [p.strip() for p in parts]

            for idx, header in enumerate(parts):
                header_clean = header.strip().replace('"', "")
                if "תאריך" in header_clean and "עסקה" in header_clean:
                    column_map["date"] = idx
                elif "שם בית העסק" in header_clean:
                    column_map["desc"] = idx
                elif "סכום חיוב" in header_clean:
                    column_map["amount"] = idx
                elif (
                    "סכום העסקה" in header_clean
                    and "amount" not in column_map
                    or column_map.get("amount") == 2
                ):
                    # Use סכום העסקה as fallback, but prefer סכום חיוב
                    column_map["amount"] = idx

        # Fallback: find first line with date pattern DD/MM/YYYY or DD.MM.YY
        if header_idx == -1:
            date_regex = re.compile(r"\d{2}[/.]\d{2}[/.]\d{2,4}")
            for i, line in enumerate(lines):
                if date_regex.search(line):
                    header_idx = i - 1 if i > 0 else 0
                    break
            if header_idx < 0:
                header_idx = 0

        # Extract expense rows
        for i in range(header_idx + 1, len(lines)):
            raw_line = lines[i].strip()
            if not raw_line or 'סה"כ' in raw_line or 'סה"כ' in raw_line:
                continue

            # Use csv.reader to properly handle quoted fields with commas
            try:
                reader = csv.reader(StringIO(raw_line))
                parts = next(reader)
            except Exception:
                # Fallback: simple split if csv.reader fails
                parts = raw_line.split(",")

            if len(parts) < 3:
                continue

            # Get date
            date_idx = column_map.get("date", 0)
            if date_idx >= len(parts):
                continue
            date_str = parts[date_idx].strip()

            # Validate date format (should contain / or .)
            if "/" not in date_str and "." not in date_str:
                continue

            # Get description
            desc_idx = column_map.get("desc", 1)
            if desc_idx >= len(parts):
                continue
            description = self.clean_description(parts[desc_idx])

            # Skip if description looks like a time (HH:MM or H:MM format)
            if description and re.match(r"^\d{1,2}:\d{2}$", description.strip()):
                # This is likely a time column, try to find the actual description
                # Look for the next column that has text and isn't a time
                for alt_idx in range(desc_idx + 1, min(desc_idx + 3, len(parts))):
                    alt_desc = self.clean_description(parts[alt_idx])
                    if alt_desc and not re.match(r"^\d{1,2}:\d{2}$", alt_desc.strip()):
                        description = alt_desc
                        break
                else:
                    # If we can't find a better description, skip this row
                    continue

            if not description:
                continue

            # Get amount - try סכום חיוב first, then סכום העסקה
            amount = None
            amount_idx = column_map.get("amount", len(parts) - 1)

            # Try to find amount column (prefer last numeric column)
            for idx in range(len(parts) - 1, max(0, len(parts) - 3), -1):
                cell = parts[idx].strip() if idx < len(parts) else ""
                if not cell:
                    continue

                # Remove quotes, commas, spaces, = prefix
                amount_clean = (
                    cell.replace('"', "")
                    .replace(",", "")
                    .replace(" ", "")
                    .replace("=", "")
                )
                if not amount_clean:
                    continue

                try:
                    amount_value = float(amount_clean)
                    amount = -abs(amount_value)  # Expenses are negative
                    break
                except ValueError:
                    continue

            if amount is None:
                # Try the mapped amount column
                if amount_idx < len(parts):
                    amount_str = (
                        parts[amount_idx]
                        .strip()
                        .replace('"', "")
                        .replace(",", "")
                        .replace(" ", "")
                        .replace("=", "")
                    )
                    try:
                        amount = -abs(float(amount_str))
                    except ValueError:
                        continue
                else:
                    continue

            expenses.append(
                ParsedExpense(date=date_str, description=description, amount=amount)
            )

        return expenses


@dataclass
class BankMovementService:
    movement_provider: BankMovementProvider
    history_provider: ActionHistoryProvider
    classifier: Optional[MovementClassifier] = None
    _pending_reviews: List[ClassifiedExpense] = field(default_factory=list)
    min_confidence: float = 0.3
    csv_parser: CsvExpenseParser = field(default_factory=CsvExpenseParser)
    _imported_for_last_csv: List[BankMovement] = field(default_factory=list)

    def apply_movement(
        self,
        accounts: List[MoneyAccount],
        movement: BankMovement,
        is_income_hint: Optional[bool] = None,
        record_history: bool = True,
    ) -> List[MoneyAccount]:
        movement = self._classify_if_needed(movement, is_income_hint)
        # 1) Persist the movement itself
        try:
            self.movement_provider.add_movement(movement)
        except Exception:
            # Movement persistence is best-effort; continue even if it fails.
            pass

        # 2) Record the movement in the global history (unless suppressed for bulk imports)
        if record_history:
            try:
                try:
                    is_income_movement = movement.amount > 0
                except Exception:
                    is_income_movement = bool(is_income_hint)

                if is_income_movement:
                    action_obj: object = AddIncomeMovementAction(
                        action_name="add_income_movement",
                        movement_id=movement.id,
                    )
                else:
                    action_obj = AddOutcomeMovementAction(
                        action_name="add_outcome_movement",
                        movement_id=movement.id,
                    )

                history_entry = ActionHistory(
                    id=generate_action_id(),
                    timestamp=get_current_timestamp(),
                    action=action_obj,  # type: ignore[arg-type]
                )
                self.history_provider.add_action(history_entry)
            except Exception:
                # History is also best-effort; a UI failure should not break the app.
                pass

        # 3) Apply the movement to the target bank account balance in-memory
        if not accounts:
            return accounts

        updated_accounts: List[MoneyAccount] = []
        account_updated = False

        for acc in accounts:
            if isinstance(acc, BankAccount) and acc.name == movement.account_name:
                # Compute new total based on current total_amount and the
                # signed movement amount (positive for income, negative for outcome).
                try:
                    current_total = float(acc.total_amount)
                except Exception:
                    current_total = 0.0
                try:
                    new_total = current_total + float(movement.amount)
                except Exception:
                    new_total = current_total

                # Use the movement date for the snapshot; fall back to today if empty.
                try:
                    date_str = movement.date
                except Exception:
                    date_str = ""
                if not date_str:
                    try:
                        from datetime import date as _date

                        date_str = _date.today().isoformat()
                    except Exception:
                        date_str = ""

                snap = MoneySnapshot(date=date_str, amount=new_total)
                new_history = list(acc.history) + [snap]

                updated_acc = BankAccount(
                    name=acc.name,
                    total_amount=0.0,  # recomputed from history in __post_init__
                    is_liquid=acc.is_liquid,
                    history=new_history,
                    active=acc.active,
                )
                updated_accounts.append(updated_acc)
                account_updated = True
            else:
                updated_accounts.append(acc)

        if not account_updated:
            # No matching bank account found; return the original list unchanged.
            return accounts

        return updated_accounts

    def _classify_if_needed(
        self, movement: BankMovement, is_income_hint: Optional[bool]
    ) -> BankMovement:
        return movement

    def import_outcome_csv(
        self,
        accounts: List[MoneyAccount],
        account_name: str,
        csv_path: Union[str, Path],
    ) -> List[MoneyAccount]:
        if not accounts:
            return accounts
        self._imported_for_last_csv.clear()
        allowed_categories: List[str] = []
        try:
            provider = self.movement_provider
            if hasattr(provider, "list_categories_for_type"):
                allowed_categories = provider.list_categories_for_type(False)  # type: ignore[attr-defined]
            elif hasattr(provider, "list_categories"):
                allowed_categories = provider.list_categories()  # type: ignore[attr-defined]
        except Exception:
            allowed_categories = []

        path = Path(csv_path)
        if not path.exists() or not path.is_file():
            return accounts

        # Read CSV content
        try:
            csv_text = path.read_text(encoding="utf-8-sig")
        except Exception:
            return accounts

        # Parse CSV using improved parser (based on JavaScript ExpenseParser)
        expenses = self.csv_parser.parse(csv_text)

        # Process extracted expenses
        all_classified: List[ClassifiedExpense] = []

        for parsed_expense in expenses:
            try:
                # Convert ParsedExpense to BankMovement
                movement = parsed_expense.to_bank_movement(account_name)
            except Exception:
                continue

            if self.classifier is not None:
                # Classify the movement
                classified = self._classify_movement(movement, allowed_categories)
                all_classified.append(classified)
            else:
                # No classifier - apply movement as-is
                accounts = self.apply_movement(
                    accounts,
                    movement,
                    is_income_hint=False,
                    record_history=False,
                )
                self._imported_for_last_csv.append(movement)

        # After classifying all, sort by confidence and handle accordingly
        if all_classified:
            # Sort by confidence (lowest first)
            all_classified_sorted = sorted(all_classified, key=lambda x: x.confidence)

            # The 3 lowest confidence ones go to pending reviews for user feedback
            top_3_lowest = all_classified_sorted[:3]
            self._pending_reviews.extend(top_3_lowest)

            # Auto-apply the rest if they have high confidence
            for classified in all_classified_sorted[3:]:
                if (
                    classified.suggested_category
                    and classified.confidence >= self.min_confidence
                ):
                    try:
                        movement = classified.to_bank_movement()
                        accounts = self.apply_movement(
                            accounts,
                            movement,
                            is_income_hint=False,
                            record_history=False,
                        )
                        self._imported_for_last_csv.append(movement)
                    except Exception:
                        continue
                else:
                    # Even if not in top 3, if low confidence, add to pending
                    if classified not in top_3_lowest:
                        self._pending_reviews.append(classified)

        return accounts

    def _classify_movement(
        self,
        movement: BankMovement,
        allowed_categories: List[str],
    ) -> ClassifiedExpense:
        """
        Classify a movement using the classifier and match category to allowed list.

        Returns:
            ClassifiedExpense with the classification result
        """
        if self.classifier is None:
            return ClassifiedExpense(
                movement=movement,
                suggested_category=None,
                suggested_type=MovementType.ONE_TIME,
                confidence=0.0,
            )

        try:
            category, mtype, confidence = self.classifier.classify_outcome(
                movement, allowed_categories
            )
        except Exception:
            return ClassifiedExpense(
                movement=movement,
                suggested_category=None,
                suggested_type=MovementType.ONE_TIME,
                confidence=0.0,
            )

        # Match category to allowed categories if needed
        if category and allowed_categories and category not in allowed_categories:
            category = self._match_category_to_allowed(category, allowed_categories)

        return ClassifiedExpense(
            movement=movement,
            suggested_category=category or None,
            suggested_type=mtype,
            confidence=confidence,
        )

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
        normalized = category.strip()
        for cat in allowed_categories:
            if cat in normalized or normalized in cat:
                return cat
        return ""

    def pop_pending_reviews(self) -> List[ClassifiedExpense]:
        """
        Get and clear all pending expense reviews.

        Returns:
            List of ClassifiedExpense objects that need user review
        """
        pending = list(self._pending_reviews)
        self._pending_reviews.clear()
        return pending

    def pop_imported_for_last_csv(self) -> List[BankMovement]:
        out = list(self._imported_for_last_csv)
        self._imported_for_last_csv.clear()
        return out
