from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..data.action_history_provider import ActionHistoryProvider
from ..data.bank_movement_provider import BankMovementProvider
from .accounts import BankAccount, BudgetAccount, MoneyAccount, MoneySnapshot
from .action_history import (
    Action,
    ActionHistory,
    AddIncomeMovementAction,
    AddOutcomeMovementAction,
    DeleteMovementAction,
    generate_action_id,
    get_current_timestamp,
)
from .bank_movement import BankMovement, MovementType
from .budget_period import budget_period_end_key, current_budget_period_end_key
from .classified_expense import ClassifiedExpense
from .csv_expense_parser import CsvExpenseParser
from .movement_classifier import SimilarityBasedClassifier


class OverBudgetError(ValueError):
    """Raised when an expense exceeds the remaining monthly budget."""

    def __init__(self, message: str, over_by: float = 0.0) -> None:
        super().__init__(message)
        self.over_by = over_by


@dataclass
class BankMovementService:
    movement_provider: BankMovementProvider
    history_provider: ActionHistoryProvider
    classifier: Optional[SimilarityBasedClassifier] = None
    _pending_reviews: List[ClassifiedExpense] = field(default_factory=list)
    min_confidence: float = 0.3
    csv_parser: CsvExpenseParser = field(default_factory=CsvExpenseParser)
    _imported_for_last_csv: List[BankMovement] = field(default_factory=list)

    def list_movements(self) -> List[BankMovement]:
        try:
            return list(self.movement_provider.list_movements())
        except Exception:
            return []

    def list_categories(self, is_income: bool) -> List[str]:
        p = self.movement_provider
        try:
            if hasattr(p, "list_categories_for_type"):
                return list(p.list_categories_for_type(is_income))
            if hasattr(p, "list_categories"):
                return list(p.list_categories())
        except Exception:
            return []
        return []

    def save_movements(
        self,
        all_movements: List[BankMovement],
        *,
        changed_movements: Optional[List[BankMovement]] = None,
    ) -> None:
        """
        Persist a full movement snapshot locally.
        Firebase push happens only when the user presses Sync.
        """
        try:
            self.movement_provider.save_movements(list(all_movements))
        except Exception:
            return

        try:
            from ..models.sync_gate import allow_firebase_push

            if not allow_firebase_push():
                return
        except Exception:
            return

        to_push = changed_movements if changed_movements is not None else all_movements
        try:
            from ..models.firebase_workspace_writer import FirebaseWorkspaceWriter

            w = FirebaseWorkspaceWriter()
            for m in to_push:
                try:
                    w.upsert_movement(m)
                except Exception:
                    continue
        except Exception:
            return

    def apply_movement(
        self,
        accounts: List[MoneyAccount],
        movement: BankMovement,
        is_income_hint: Optional[bool] = None,
        record_history: bool = True,
        allow_over_budget: bool = False,
    ) -> List[MoneyAccount]:
        target_acc: Optional[MoneyAccount] = None
        try:
            for acc in accounts:
                if getattr(acc, "name", None) == getattr(
                    movement, "account_name", None
                ):
                    target_acc = acc
                    break
        except Exception:
            target_acc = None

        movement_period_key: Optional[tuple[int, int]] = None
        current_period_key: Optional[tuple[int, int]] = None
        if isinstance(target_acc, BudgetAccount):
            try:
                amt = float(movement.amount)
            except Exception:
                amt = 0.0
            if amt > 0:
                raise ValueError("לא ניתן להוסיף הכנסה לחשבון תקציב")

            reset_day = int(getattr(target_acc, "reset_day", 1) or 1)
            if reset_day < 1:
                reset_day = 1
            if reset_day > 28:
                reset_day = 28

            current_period_key = current_budget_period_end_key(reset_day)
            movement_period_key = budget_period_end_key(
                str(getattr(movement, "date", "") or ""), reset_day
            )
            if movement_period_key is None:
                movement_period_key = current_period_key

            try:
                budget = float(getattr(target_acc, "monthly_budget", 0.0) or 0.0)
            except Exception:
                budget = 0.0

            spent_by_period: Dict[tuple[int, int], float] = {}
            try:
                existing = list(self.movement_provider.list_movements())
            except Exception:
                existing = []
            for m in existing:
                try:
                    if (
                        str(getattr(m, "account_name", "") or "").strip()
                        != str(getattr(target_acc, "name", "") or "").strip()
                    ):
                        continue
                    if bool(getattr(m, "is_transfer", False)):
                        continue
                    a = float(getattr(m, "amount", 0.0) or 0.0)
                    if a >= 0:
                        continue
                    k = budget_period_end_key(
                        str(getattr(m, "date", "") or ""), reset_day
                    )
                    if k is None:
                        continue
                    spent_by_period[k] = float(spent_by_period.get(k, 0.0)) + abs(a)
                except Exception:
                    continue

            already_spent = float(spent_by_period.get(movement_period_key, 0.0))
            remaining = float(budget) - float(already_spent)
            over_by = abs(float(amt)) - remaining
            if over_by > 0 and not allow_over_budget:
                raise OverBudgetError(
                    f"ההוצאה חורגת מהתקציב החודשי של חשבון {target_acc.name} "
                    f"ב-{over_by:.2f} ₪.",
                    over_by=over_by,
                )

        try:
            self.movement_provider.add_movement(movement)
        except Exception:
            return list(accounts)

        try:
            from ..models.sync_gate import allow_firebase_push

            if allow_firebase_push():
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

        updated_accounts: List[MoneyAccount] = []
        account_updated = False

        _movement_acc_name = str(getattr(movement, "account_name", "") or "").strip()
        for acc in accounts:
            if (
                isinstance(acc, (BankAccount, BudgetAccount))
                and str(getattr(acc, "name", "") or "").strip() == _movement_acc_name
            ):
                try:
                    current_total = float(acc.total_amount)
                except Exception:
                    current_total = 0.0
                try:
                    move_amt = float(movement.amount)
                except Exception:
                    move_amt = 0.0

                if isinstance(acc, BudgetAccount):
                    reset_day = int(getattr(acc, "reset_day", 1) or 1)
                    if reset_day < 1:
                        reset_day = 1
                    if reset_day > 28:
                        reset_day = 28
                    cur_key = current_period_key or current_budget_period_end_key(
                        reset_day
                    )
                    mov_key = movement_period_key or budget_period_end_key(
                        str(getattr(movement, "date", "") or ""), reset_day
                    )
                    if mov_key is not None and mov_key == cur_key:
                        new_total = current_total + float(move_amt)
                    else:
                        new_total = current_total
                else:
                    new_total = current_total + float(move_amt)

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

                new_history = list(getattr(acc, "history", []) or [])
                if not (isinstance(acc, BudgetAccount) and new_total == current_total):
                    new_history = new_history + [
                        MoneySnapshot(date=date_str, amount=new_total)
                    ]

                updated_acc: MoneyAccount
                if isinstance(acc, BudgetAccount):
                    updated_acc = BudgetAccount(
                        name=acc.name,
                        total_amount=new_total,
                        is_liquid=False,
                        history=new_history,
                        active=acc.active,
                        monthly_budget=float(acc.monthly_budget),
                        reset_day=int(acc.reset_day),
                        last_reset_period=str(acc.last_reset_period or ""),
                    )
                else:
                    updated_acc = BankAccount(
                        name=acc.name,
                        total_amount=new_total,
                        is_liquid=acc.is_liquid,
                        history=new_history,
                        active=acc.active,
                        baseline_amount=float(
                            getattr(acc, "baseline_amount", 0.0) or 0.0
                        ),
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
                try:
                    calculated_balance += float(
                        getattr(acc, "baseline_amount", 0.0) or 0.0
                    )
                except Exception:
                    pass

                new_history = list(acc.history)
                try:
                    from datetime import date as _date

                    date_str = _date.today().isoformat()
                except Exception:
                    date_str = ""

                if date_str:
                    try:
                        if new_history and str(new_history[-1].date) == str(date_str):
                            new_history[-1] = MoneySnapshot(
                                date=date_str, amount=calculated_balance
                            )
                        else:
                            new_history.append(
                                MoneySnapshot(date=date_str, amount=calculated_balance)
                            )
                    except Exception:
                        new_history.append(
                            MoneySnapshot(date=date_str, amount=calculated_balance)
                        )

                updated_acc = BankAccount(
                    name=acc.name,
                    total_amount=calculated_balance,
                    is_liquid=acc.is_liquid,
                    history=new_history,
                    active=acc.active,
                    baseline_amount=float(getattr(acc, "baseline_amount", 0.0) or 0.0),
                )
                updated_accounts.append(updated_acc)
            elif isinstance(acc, BudgetAccount):
                reset_day = int(getattr(acc, "reset_day", 1) or 1)
                if reset_day < 1:
                    reset_day = 1
                if reset_day > 28:
                    reset_day = 28

                cur_key = current_budget_period_end_key(reset_day)
                spent = 0.0
                for m in all_movements:
                    try:
                        if (
                            str(getattr(m, "account_name", "") or "").strip()
                            != str(getattr(acc, "name", "") or "").strip()
                        ):
                            continue
                        if bool(getattr(m, "is_transfer", False)):
                            continue
                        a = float(getattr(m, "amount", 0.0) or 0.0)
                        if a >= 0:
                            continue
                        k = budget_period_end_key(
                            str(getattr(m, "date", "") or ""), reset_day
                        )
                        if k is None or k != cur_key:
                            continue
                        spent += abs(a)
                    except Exception:
                        continue

                try:
                    budget = float(getattr(acc, "monthly_budget", 0.0) or 0.0)
                except Exception:
                    budget = 0.0
                remaining = float(budget) - float(spent)
                if remaining < 0:
                    remaining = 0.0

                new_history = list(getattr(acc, "history", []) or [])
                try:
                    from datetime import date as _date

                    date_str = _date.today().isoformat()
                except Exception:
                    date_str = ""
                if date_str:
                    try:
                        if new_history and str(
                            getattr(new_history[-1], "date", "")
                        ) == str(date_str):
                            new_history[-1] = MoneySnapshot(
                                date=date_str, amount=remaining
                            )
                        else:
                            new_history.append(
                                MoneySnapshot(date=date_str, amount=remaining)
                            )
                    except Exception:
                        new_history.append(
                            MoneySnapshot(date=date_str, amount=remaining)
                        )

                updated_accounts.append(
                    BudgetAccount(
                        name=acc.name,
                        total_amount=float(remaining),
                        is_liquid=False,
                        history=new_history,
                        active=bool(getattr(acc, "active", False)),
                        monthly_budget=float(
                            getattr(acc, "monthly_budget", 0.0) or 0.0
                        ),
                        reset_day=int(getattr(acc, "reset_day", 1) or 1),
                        last_reset_period=str(
                            getattr(acc, "last_reset_period", "") or ""
                        ),
                    )
                )
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
            from ..models.firebase_session import (
                current_firebase_uid,
                current_firebase_workspace_id,
            )
            from ..models.firebase_sync_state import add_pending_delete
            from ..models.sync_gate import allow_firebase_push

            key = (
                current_firebase_workspace_id() or current_firebase_uid() or ""
            ).strip()
            if key:
                add_pending_delete(key=key, kind="movement", item_id=movement_id)

            if allow_firebase_push():
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
                        baseline_amount=float(
                            getattr(acc, "baseline_amount", 0.0) or 0.0
                        ),
                    )
                )
            elif isinstance(acc, BudgetAccount) and str(
                getattr(acc, "name", "")
            ) == str(getattr(target, "account_name", "")):
                reset_day = int(getattr(acc, "reset_day", 1) or 1)
                if reset_day < 1:
                    reset_day = 1
                if reset_day > 28:
                    reset_day = 28
                cur_key = current_budget_period_end_key(reset_day)
                target_key = budget_period_end_key(
                    str(getattr(target, "date", "") or ""), reset_day
                )

                restored_total = float(getattr(acc, "total_amount", 0.0) or 0.0)
                if target_key is not None and target_key == cur_key:
                    try:
                        restored_total = float(acc.total_amount) + abs(
                            float(target.amount)
                        )
                    except Exception:
                        restored_total = float(getattr(acc, "total_amount", 0.0) or 0.0)
                new_history = list(getattr(acc, "history", []) or [])
                if today:
                    new_history.append(MoneySnapshot(date=today, amount=restored_total))
                out.append(
                    BudgetAccount(
                        name=acc.name,
                        total_amount=restored_total,
                        is_liquid=False,
                        history=new_history,
                        active=acc.active,
                        monthly_budget=float(acc.monthly_budget),
                        reset_day=int(acc.reset_day),
                        last_reset_period=str(acc.last_reset_period or ""),
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
