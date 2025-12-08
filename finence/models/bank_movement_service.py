from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..data.bank_movement_provider import BankMovementProvider
from ..data.action_history_provider import ActionHistoryProvider
from .accounts import MoneyAccount, BankAccount, MoneySnapshot
from .bank_movement import BankMovement
from .action_history import (
    ActionHistory,
    AddIncomeMovementAction,
    AddOutcomeMovementAction,
    generate_action_id,
    get_current_timestamp,
)


@dataclass
class BankMovementService:
    """
    Domain service responsible for applying bank movements to accounts and
    recording them in the global action history.

    This class has no UI or Qt dependencies – it only works with models and
    providers, keeping the view layer (pages/dialogs) thin.
    """

    movement_provider: BankMovementProvider
    history_provider: ActionHistoryProvider

    def apply_movement(
        self,
        accounts: List[MoneyAccount],
        movement: BankMovement,
        is_income_hint: Optional[bool] = None,
    ) -> List[MoneyAccount]:
        """
        Persist the movement, create a matching history entry, and return an
        updated accounts list where the target BankAccount reflects the new
        balance.
        """
        # 1) Persist the movement itself
        try:
            self.movement_provider.add_movement(movement)
        except Exception:
            # Movement persistence is best-effort; continue even if it fails.
            pass

        # 2) Record the movement in the global action history
        try:
            try:
                is_income_movement = movement.amount > 0
            except Exception:
                is_income_movement = bool(is_income_hint)

            if is_income_movement:
                action_obj: object = AddIncomeMovementAction(
                    action_name="add_income_movement",
                    account_name=movement.account_name,
                    amount=movement.amount,
                    category=movement.category,
                    type=str(
                        movement.type.value
                        if hasattr(movement.type, "value")
                        else movement.type
                    ),
                    description=movement.description,
                )
            else:
                action_obj = AddOutcomeMovementAction(
                    action_name="add_outcome_movement",
                    account_name=movement.account_name,
                    amount=movement.amount,
                    category=movement.category,
                    type=str(
                        movement.type.value
                        if hasattr(movement.type, "value")
                        else movement.type
                    ),
                    description=movement.description,
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
