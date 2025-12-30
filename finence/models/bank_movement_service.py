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
from .movement_classifier import SimilarityBasedClassifier
from .classified_expense import ClassifiedExpense
from .parsed_expense import ParsedExpense
from .action_history import (
    ActionHistory,
    Action,
    AddIncomeMovementAction,
    AddOutcomeMovementAction,
    DeleteMovementAction,
    generate_action_id,
    get_current_timestamp,
)


@dataclass
class CsvExpenseParser:
    @staticmethod
    def clean_description(description: str) -> str:
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
        return (
            s.replace("\ufeff", "").replace('"', "").replace(",", "").replace(" ", "")
        )

    def parse(self, csv_text: str) -> List[ParsedExpense]:
        expenses = []
        lines = csv_text.split("\n")

        header_pattern = re.compile(
            r"תאריך\s*עסק[אה]?\s*שם\s*בית\s*העסק\s*סכום\s*[הח]?עסקה"
        )

        preferred_header_pattern = re.compile(
            r"תאריך\s*עסק[אה]?\s*שם\s*בית\s*העסק.*סכום\s*חיוב"
        )

        header_idx = -1
        column_map: Dict[str, int] = {"date": 0, "desc": 1, "amount": 2}
        preferred_header_idx = -1

        for i, line in enumerate(lines):
            normalized = self._normalize(line)
            if preferred_header_pattern.search(normalized):
                preferred_header_idx = i
                break

        if preferred_header_idx == -1:
            for i, line in enumerate(lines):
                normalized = self._normalize(line)
                if header_pattern.search(normalized):
                    preferred_header_idx = i
                    break

        if preferred_header_idx != -1:
            header_idx = preferred_header_idx
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
                    column_map["amount"] = idx

        if header_idx == -1:
            date_regex = re.compile(r"\d{2}[/.]\d{2}[/.]\d{2,4}")
            for i, line in enumerate(lines):
                if date_regex.search(line):
                    header_idx = i - 1 if i > 0 else 0
                    break
            if header_idx < 0:
                header_idx = 0

        for i in range(header_idx + 1, len(lines)):
            raw_line = lines[i].strip()
            if not raw_line or 'סה"כ' in raw_line or 'סה"כ' in raw_line:
                continue

            try:
                reader = csv.reader(StringIO(raw_line))
                parts = next(reader)
            except Exception:
                parts = raw_line.split(",")

            if len(parts) < 3:
                continue

            date_idx = column_map.get("date", 0)
            if date_idx >= len(parts):
                continue
            date_str = parts[date_idx].strip()

            if "/" not in date_str and "." not in date_str:
                continue

            desc_idx = column_map.get("desc", 1)
            if desc_idx >= len(parts):
                continue
            description = self.clean_description(parts[desc_idx])

            if description and re.match(r"^\d{1,2}:\d{2}$", description.strip()):
                for alt_idx in range(desc_idx + 1, min(desc_idx + 3, len(parts))):
                    alt_desc = self.clean_description(parts[alt_idx])
                    if alt_desc and not re.match(r"^\d{1,2}:\d{2}$", alt_desc.strip()):
                        description = alt_desc
                        break
                else:
                    continue

            if not description:
                continue

            amount = None
            amount_idx = column_map.get("amount", len(parts) - 1)

            for idx in range(len(parts) - 1, max(0, len(parts) - 3), -1):
                cell = parts[idx].strip() if idx < len(parts) else ""
                if not cell:
                    continue

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
                    amount = -abs(amount_value)
                    break
                except ValueError:
                    continue

            if amount is None:
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
    classifier: Optional[SimilarityBasedClassifier] = None
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
        try:
            self.movement_provider.add_movement(movement)
        except Exception:
            pass

        # Immediate push-on-write (desktop -> Firebase workspace).
        try:
            from ..models.firebase_workspace_writer import FirebaseWorkspaceWriter

            FirebaseWorkspaceWriter().upsert_movement(movement)
        except Exception:
            pass

        if record_history:
            try:
                try:
                    is_income_movement = movement.amount > 0
                except Exception:
                    is_income_movement = bool(is_income_hint)

                if is_income_movement:
                    action_obj: Action = AddIncomeMovementAction(
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
                    action=action_obj,
                )
                self.history_provider.add_action(history_entry)
            except Exception:
                pass

        if not accounts:
            return accounts

        updated_accounts: List[MoneyAccount] = []
        account_updated = False

        for acc in accounts:
            if isinstance(acc, BankAccount) and acc.name == movement.account_name:
                try:
                    current_total = float(acc.total_amount)
                except Exception:
                    current_total = 0.0
                try:
                    new_total = current_total + float(movement.amount)
                except Exception:
                    new_total = current_total

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
                    total_amount=new_total,
                    is_liquid=acc.is_liquid,
                    history=new_history,
                    active=acc.active,
                )
                updated_accounts.append(updated_acc)
                account_updated = True
            else:
                updated_accounts.append(acc)

        if not account_updated:
            return accounts

        return updated_accounts

    def recalculate_account_balances(
        self, accounts: List[MoneyAccount]
    ) -> List[MoneyAccount]:
        if not accounts:
            return accounts

        try:
            all_movements = self.movement_provider.list_movements()
        except Exception:
            return accounts

        balance_by_account: Dict[str, float] = {}
        for movement in all_movements:
            account_name = movement.account_name
            if account_name not in balance_by_account:
                balance_by_account[account_name] = 0.0
            try:
                balance_by_account[account_name] += float(movement.amount)
            except Exception:
                pass

        updated_accounts: List[MoneyAccount] = []
        for acc in accounts:
            if isinstance(acc, BankAccount):
                calculated_balance = balance_by_account.get(acc.name, 0.0)

                new_history = list(acc.history)
                try:
                    from datetime import date as _date

                    date_str = _date.today().isoformat()
                except Exception:
                    date_str = ""

                new_history.append(
                    MoneySnapshot(date=date_str, amount=calculated_balance)
                )

                updated_acc = BankAccount(
                    name=acc.name,
                    total_amount=calculated_balance,
                    is_liquid=acc.is_liquid,
                    history=new_history,
                    active=acc.active,
                )
                updated_accounts.append(updated_acc)
            else:
                updated_accounts.append(acc)

        return updated_accounts

    def delete_movement(
        self,
        accounts: List[MoneyAccount],
        *,
        movement_id: str,
        record_history: bool = True,
    ) -> List[MoneyAccount]:
        movement_id = str(movement_id or "").strip()
        if not movement_id:
            return accounts

        try:
            all_movements = list(self.movement_provider.list_movements())
        except Exception:
            return accounts

        target: Optional[BankMovement] = None
        for m in all_movements:
            if str(getattr(m, "id", "") or "") == movement_id:
                target = m
                break
        if target is None:
            return accounts

        # baseline = current_total - sum(all movements)
        sum_by_account: Dict[str, float] = {}
        for m in all_movements:
            try:
                name = str(m.account_name or "").strip()
                if not name:
                    continue
                sum_by_account[name] = sum_by_account.get(name, 0.0) + float(m.amount)
            except Exception:
                continue

        baseline_by_account: Dict[str, float] = {}
        for acc in accounts:
            if isinstance(acc, BankAccount):
                try:
                    baseline_by_account[acc.name] = float(acc.total_amount) - float(
                        sum_by_account.get(acc.name, 0.0)
                    )
                except Exception:
                    baseline_by_account[acc.name] = 0.0

        updated_movements = [m for m in all_movements if str(m.id) != movement_id]
        try:
            self.movement_provider.save_movements(updated_movements)
        except Exception:
            return accounts

        try:
            from .firebase_workspace_writer import FirebaseWorkspaceWriter

            FirebaseWorkspaceWriter().delete_movement(movement_id=movement_id)
        except Exception:
            pass

        if record_history:
            try:
                action = DeleteMovementAction(
                    action_name="delete_movement",
                    movement_id=movement_id,
                    account_name=str(target.account_name),
                    amount=float(target.amount),
                    date=str(target.date),
                )
                self.history_provider.add_action(
                    ActionHistory(
                        id=generate_action_id(),
                        timestamp=get_current_timestamp(),
                        action=action,
                    )
                )
            except Exception:
                pass

        new_sum_by_account: Dict[str, float] = {}
        for m in updated_movements:
            try:
                name = str(m.account_name or "").strip()
                if not name:
                    continue
                new_sum_by_account[name] = new_sum_by_account.get(name, 0.0) + float(
                    m.amount
                )
            except Exception:
                continue

        try:
            from datetime import date as _date

            today = _date.today().isoformat()
        except Exception:
            today = ""

        out: List[MoneyAccount] = []
        for acc in accounts:
            if isinstance(acc, BankAccount):
                base = float(baseline_by_account.get(acc.name, 0.0))
                total = base + float(new_sum_by_account.get(acc.name, 0.0))
                new_history = list(acc.history)
                if today:
                    new_history.append(MoneySnapshot(date=today, amount=total))
                out.append(
                    BankAccount(
                        name=acc.name,
                        total_amount=total,
                        is_liquid=acc.is_liquid,
                        history=new_history,
                        active=acc.active,
                    )
                )
            else:
                out.append(acc)
        return out

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
                allowed_categories = provider.list_categories_for_type(False)
            elif hasattr(provider, "list_categories"):
                allowed_categories = provider.list_categories()
        except Exception:
            allowed_categories = []

        path = Path(csv_path)
        if not path.exists() or not path.is_file():
            return accounts

        try:
            csv_text = path.read_text(encoding="utf-8-sig")
        except Exception:
            return accounts

        expenses = self.csv_parser.parse(csv_text)

        all_classified: List[ClassifiedExpense] = []

        for parsed_expense in expenses:
            try:
                movement = parsed_expense.to_bank_movement(account_name)
            except Exception:
                continue

            if self.classifier is not None:
                classified = self._classify_movement(movement, allowed_categories)
                all_classified.append(classified)
            else:
                accounts = self.apply_movement(
                    accounts,
                    movement,
                    is_income_hint=False,
                    record_history=False,
                )
                self._imported_for_last_csv.append(movement)

        if all_classified:
            all_classified_sorted = sorted(all_classified, key=lambda x: x.confidence)

            top_3_lowest = all_classified_sorted[:3]
            self._pending_reviews.extend(top_3_lowest)

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
                    if classified not in top_3_lowest:
                        self._pending_reviews.append(classified)

        return accounts

    def _classify_movement(
        self,
        movement: BankMovement,
        allowed_categories: List[str],
    ) -> ClassifiedExpense:
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
        normalized = category.strip()
        for cat in allowed_categories:
            if cat in normalized or normalized in cat:
                return cat
        return ""

    def pop_pending_reviews(self) -> List[ClassifiedExpense]:
        pending = list(self._pending_reviews)
        self._pending_reviews.clear()
        return pending

    def pop_imported_for_last_csv(self) -> List[BankMovement]:
        out = list(self._imported_for_last_csv)
        self._imported_for_last_csv.clear()
        return out
