from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ..data.action_history_provider import ActionHistoryProvider
from ..data.provider import AccountsProvider, JsonFileAccountsProvider
from .accounts import (
    BankAccount,
    BudgetAccount,
    MoneyAccount,
    MoneySnapshot,
    SavingsAccount,
)
from .action_history import (
    ActionHistory,
    ActivateBankAccountAction,
    AddSavingAction,
    AddSavingsAccountAction,
    DeactivateBankAccountAction,
    DeleteSavingAction,
    DeleteSavingsAccountAction,
    EditSavingAction,
    EditSavingsAccountAction,
    SetStarterAmountAction,
    TransferAction,
    generate_action_id,
    get_current_timestamp,
)
from .bank_settings import BankSettingsRowInput, apply_bank_settings
from .savings_dialogs import (
    SavingsAccountForm,
    form_to_new_savings_account,
    form_to_updated_savings_account,
    remove_savings_account,
)
from .transfers import TransferRequest, TransferResult, apply_transfer


@dataclass
class AccountsService:
    provider: AccountsProvider
    history_provider: Optional[ActionHistoryProvider] = None

    def load_accounts(self) -> List[MoneyAccount]:
        accounts = self.provider.list_accounts()
        updated = self._apply_budget_account_resets(accounts)

        # Migration / rule: "בנק" is always liquid (counts in totals).
        # This keeps behavior consistent even if old snapshots had is_liquid=false.
        changed = False
        enforced: List[MoneyAccount] = []
        for acc in updated:
            if (
                isinstance(acc, BankAccount)
                and str(acc.name) == "בנק"
                and not bool(getattr(acc, "is_liquid", False))
            ):
                enforced.append(
                    BankAccount(
                        name=acc.name,
                        total_amount=float(acc.total_amount),
                        is_liquid=True,
                        history=list(acc.history),
                        active=bool(getattr(acc, "active", False)),
                        baseline_amount=float(
                            getattr(acc, "baseline_amount", 0.0) or 0.0
                        ),
                    )
                )
                changed = True
            else:
                enforced.append(acc)

        if (updated is not accounts or changed) and isinstance(
            self.provider, JsonFileAccountsProvider
        ):
            try:
                self.save_all(enforced)
            except Exception:
                pass
        return enforced

    def _apply_budget_account_resets(
        self, accounts: List[MoneyAccount]
    ) -> List[MoneyAccount]:
        from datetime import date as _date

        if not accounts:
            return accounts
        today = _date.today()

        def _prev_year_month(y: int, m: int) -> tuple[int, int]:
            if m <= 1:
                return y - 1, 12
            return y, m - 1

        out: List[MoneyAccount] = []
        changed = False
        for acc in accounts:
            if not isinstance(acc, BudgetAccount):
                out.append(acc)
                continue

            reset_day = int(acc.reset_day)
            if reset_day < 1:
                reset_day = 1
            if reset_day > 28:
                reset_day = 28

            if today.day >= reset_day:
                period_y, period_m = today.year, today.month
            else:
                period_y, period_m = _prev_year_month(today.year, today.month)
            period = f"{period_y:04d}-{period_m:02d}"

            if str(acc.last_reset_period or "").strip() == period:
                out.append(acc)
                continue

            try:
                reset_date = _date(period_y, period_m, reset_day).isoformat()
            except Exception:
                reset_date = today.isoformat()
            new_history = list(acc.history) + [
                MoneySnapshot(date=reset_date, amount=float(acc.monthly_budget))
            ]
            out.append(
                BudgetAccount(
                    name=acc.name,
                    total_amount=float(acc.monthly_budget),
                    is_liquid=False,
                    history=new_history,
                    active=bool(acc.active),
                    monthly_budget=float(acc.monthly_budget),
                    reset_day=int(reset_day),
                    last_reset_period=period,
                )
            )
            changed = True

        return out if changed else accounts

    def add_savings_account(
        self,
        accounts: List[MoneyAccount],
        form: SavingsAccountForm,
    ) -> List[MoneyAccount]:
        new_acc = form_to_new_savings_account(form)
        updated_accounts = accounts + [new_acc]

        if self.history_provider is not None:
            try:
                action = AddSavingsAccountAction(
                    action_name="add_savings_account",
                    account_name=new_acc.name,
                    is_liquid=new_acc.is_liquid,
                )
                history_entry = ActionHistory(
                    id=generate_action_id(),
                    timestamp=get_current_timestamp(),
                    action=action,
                )
                self.history_provider.add_action(history_entry)
            except Exception:
                pass

        return updated_accounts

    def edit_savings_account(
        self,
        accounts: List[MoneyAccount],
        original: SavingsAccount,
        form: SavingsAccountForm,
    ) -> List[MoneyAccount]:
        updated = form_to_updated_savings_account(original, form)
        out: List[MoneyAccount] = []
        replaced = False
        for acc in accounts:
            if acc is original and not replaced:
                out.append(updated)
                replaced = True
            else:
                out.append(acc)
        if not replaced:
            name = original.name
            out = [
                updated if isinstance(acc, SavingsAccount) and acc.name == name else acc
                for acc in out
            ]

        if self.history_provider is not None:
            try:
                old_name = original.name if original.name != updated.name else None
                new_name = updated.name if original.name != updated.name else None
                old_is_liquid = (
                    original.is_liquid
                    if original.is_liquid != updated.is_liquid
                    else None
                )
                new_is_liquid = (
                    updated.is_liquid
                    if original.is_liquid != updated.is_liquid
                    else None
                )
                action = EditSavingsAccountAction(
                    action_name="edit_savings_account",
                    account_name=updated.name,
                    old_name=old_name,
                    new_name=new_name,
                    old_is_liquid=old_is_liquid,
                    new_is_liquid=new_is_liquid,
                )
                history_entry = ActionHistory(
                    id=generate_action_id(),
                    timestamp=get_current_timestamp(),
                    action=action,
                )
                self.history_provider.add_action(history_entry)
            except Exception:
                pass

        return out

    def delete_savings_account(
        self,
        accounts: List[MoneyAccount],
        selected: SavingsAccount,
    ) -> List[MoneyAccount]:
        from .accounts import compute_savings_account_total_amount

        account_total_amount = compute_savings_account_total_amount([selected])

        updated_accounts = remove_savings_account(accounts, selected)

        if self.history_provider is not None:
            try:
                action = DeleteSavingsAccountAction(
                    action_name="delete_savings_account",
                    account_name=selected.name,
                    account_total_amount=account_total_amount,
                )
                history_entry = ActionHistory(
                    id=generate_action_id(),
                    timestamp=get_current_timestamp(),
                    action=action,
                )
                self.history_provider.add_action(history_entry)
            except Exception:
                pass

        return updated_accounts

    def add_saving(
        self,
        accounts: List[MoneyAccount],
        account: SavingsAccount,
        saving_name: str,
        saving_amount: float,
        date_str: Optional[str] = None,
    ) -> List[MoneyAccount]:
        from .accounts import MoneySnapshot, Savings
        from datetime import date as _date

        if date_str is None:
            try:
                date_str = _date.today().isoformat()
            except Exception:
                date_str = ""

        updated_accounts: List[MoneyAccount] = []
        for acc in accounts:
            if isinstance(acc, SavingsAccount) and acc.name == account.name:
                snap = MoneySnapshot(date=date_str, amount=saving_amount)
                new_saving = Savings(
                    name=saving_name, amount=saving_amount, history=[snap]
                )
                new_savings = list(acc.savings) + [new_saving]
                updated_account = SavingsAccount(
                    name=acc.name,
                    total_amount=0.0,
                    is_liquid=acc.is_liquid,
                    savings=new_savings,
                )
                updated_accounts.append(updated_account)
            else:
                updated_accounts.append(acc)

        if self.history_provider is not None:
            try:
                action = AddSavingAction(
                    action_name="add_saving",
                    account_name=account.name,
                    saving_name=saving_name,
                    saving_amount=saving_amount,
                )
                history_entry = ActionHistory(
                    id=generate_action_id(),
                    timestamp=get_current_timestamp(),
                    action=action,
                )
                self.history_provider.add_action(history_entry)
            except Exception:
                pass

        return updated_accounts

    def edit_saving(
        self,
        accounts: List[MoneyAccount],
        account: SavingsAccount,
        saving_name: str,
        new_amount: float,
        date_str: Optional[str] = None,
    ) -> List[MoneyAccount]:
        from .accounts import MoneySnapshot, Savings
        from datetime import date as _date

        old_amount = 0.0
        for saving in account.savings:
            if saving.name == saving_name:
                old_amount = saving.amount
                break

        if date_str is None:
            try:
                date_str = _date.today().isoformat()
            except Exception:
                date_str = ""

        updated_accounts: List[MoneyAccount] = []
        for acc in accounts:
            if isinstance(acc, SavingsAccount) and acc.name == account.name:
                new_savings: List = []
                for s in acc.savings:
                    if s.name == saving_name:
                        new_history = list(s.history) + [
                            MoneySnapshot(date=date_str, amount=new_amount)
                        ]
                        new_savings.append(
                            Savings(name=s.name, amount=new_amount, history=new_history)
                        )
                    else:
                        new_savings.append(s)
                updated_account = SavingsAccount(
                    name=acc.name,
                    total_amount=0.0,
                    is_liquid=acc.is_liquid,
                    savings=new_savings,
                )
                updated_accounts.append(updated_account)
            else:
                updated_accounts.append(acc)

        if self.history_provider is not None:
            try:
                action = EditSavingAction(
                    action_name="edit_saving",
                    account_name=account.name,
                    saving_name=saving_name,
                    old_amount=old_amount,
                    new_amount=new_amount,
                )
                history_entry = ActionHistory(
                    id=generate_action_id(),
                    timestamp=get_current_timestamp(),
                    action=action,
                )
                self.history_provider.add_action(history_entry)
            except Exception:
                pass

        return updated_accounts

    def delete_saving(
        self,
        accounts: List[MoneyAccount],
        account: SavingsAccount,
        saving_name: str,
    ) -> List[MoneyAccount]:
        saving_amount = 0.0

        for saving in account.savings:
            if saving.name == saving_name:
                saving_amount = saving.amount
                break

        updated_accounts: List[MoneyAccount] = []
        for acc in accounts:
            if isinstance(acc, SavingsAccount) and acc.name == account.name:
                new_savings = [s for s in acc.savings if s.name != saving_name]
                updated_account = SavingsAccount(
                    name=acc.name,
                    total_amount=0.0,
                    is_liquid=acc.is_liquid,
                    savings=new_savings,
                )
                updated_accounts.append(updated_account)
            else:
                updated_accounts.append(acc)

        if self.history_provider is not None:
            try:
                action = DeleteSavingAction(
                    action_name="delete_saving",
                    account_name=account.name,
                    saving_name=saving_name,
                    saving_amount=saving_amount,
                )
                history_entry = ActionHistory(
                    id=generate_action_id(),
                    timestamp=get_current_timestamp(),
                    action=action,
                )
                self.history_provider.add_action(history_entry)
            except Exception:
                pass

        return updated_accounts

    def apply_transfer_request(
        self,
        accounts: List[MoneyAccount],
        request: TransferRequest,
    ) -> TransferResult:
        result = apply_transfer(accounts, request)

        if self.history_provider is not None and result.error is None:
            try:
                src_acc = accounts[request.source.account_index]
                dst_acc = accounts[request.target.account_index]

                src_name = src_acc.name
                dst_name = dst_acc.name
                src_type = "bank" if request.source.kind == "bank" else "saving"
                dst_type = "bank" if request.target.kind == "bank" else "saving"

                if request.source.kind == "saving" and isinstance(
                    src_acc, SavingsAccount
                ):
                    try:
                        src_saving = src_acc.savings[request.source.savings_index]
                        src_name = f"{src_acc.name} -- {src_saving.name}"
                    except Exception:
                        pass

                if request.target.kind == "saving" and isinstance(
                    dst_acc, SavingsAccount
                ):
                    try:
                        dst_saving = dst_acc.savings[request.target.savings_index]
                        dst_name = f"{dst_acc.name} -- {dst_saving.name}"
                    except Exception:
                        pass

                action = TransferAction(
                    action_name="transfer",
                    amount=request.amount,
                    source_name=src_name,
                    target_name=dst_name,
                    source_type=src_type,
                    target_type=dst_type,
                )
                history_entry = ActionHistory(
                    id=generate_action_id(),
                    timestamp=get_current_timestamp(),
                    action=action,
                )
                self.history_provider.add_action(history_entry)
            except Exception:
                pass

        return result

    def apply_bank_settings_rows(
        self,
        rows: List[BankSettingsRowInput],
    ) -> List[MoneyAccount]:
        updated_bank_accounts = apply_bank_settings(rows)
        existing = self.provider.list_accounts()
        savings_only = [acc for acc in existing if isinstance(acc, SavingsAccount)]
        merged: List[MoneyAccount] = []
        merged.extend(updated_bank_accounts)
        merged.extend(savings_only)

        if self.history_provider is not None:
            try:
                existing_bank_accounts = {
                    acc.name: acc for acc in existing if isinstance(acc, BankAccount)
                }

                for row in rows:
                    current_account = row.current_account
                    is_active = row.is_active
                    amount_text = row.starter_amount_text.strip()

                    prev_baseline = None
                    if current_account is not None:
                        try:
                            prev_baseline = float(
                                getattr(current_account, "baseline_amount", 0.0) or 0.0
                            )
                        except Exception:
                            prev_baseline = None
                    else:
                        existing_acc = existing_bank_accounts.get(row.name)
                        if existing_acc is not None:
                            try:
                                prev_baseline = float(
                                    getattr(existing_acc, "baseline_amount", 0.0) or 0.0
                                )
                            except Exception:
                                prev_baseline = None

                    if current_account is not None:
                        was_inactive = not current_account.active
                        is_being_activated = is_active and was_inactive
                        is_being_deactivated = not is_active and current_account.active
                    else:
                        existing_acc = existing_bank_accounts.get(row.name)
                        if existing_acc is not None:
                            was_inactive = not existing_acc.active
                            is_being_activated = is_active and was_inactive
                            is_being_deactivated = not is_active and existing_acc.active
                        else:
                            is_being_activated = is_active
                            is_being_deactivated = False

                    if is_being_activated:
                        starter_amount = None
                        if amount_text:
                            try:
                                starter_amount = float(amount_text)
                            except Exception:
                                starter_amount = None

                        activate_action = ActivateBankAccountAction(
                            action_name="activate_bank_account",
                            account_name=row.name,
                            starter_amount=starter_amount,
                        )
                        history_entry = ActionHistory(
                            id=generate_action_id(),
                            timestamp=get_current_timestamp(),
                            action=activate_action,
                        )
                        self.history_provider.add_action(history_entry)
                    elif is_being_deactivated:
                        deactivate_action = DeactivateBankAccountAction(
                            action_name="deactivate_bank_account",
                            account_name=row.name,
                        )
                        history_entry = ActionHistory(
                            id=generate_action_id(),
                            timestamp=get_current_timestamp(),
                            action=deactivate_action,
                        )
                        self.history_provider.add_action(history_entry)
                    elif is_active and amount_text:
                        starter_amount = None
                        try:
                            starter_amount = float(amount_text)
                        except Exception:
                            starter_amount = None

                        if (
                            starter_amount is not None
                            and starter_amount >= 0
                            and not is_being_activated
                            and not is_being_deactivated
                        ):
                            baseline_changed = (
                                prev_baseline is None
                                or abs(starter_amount - float(prev_baseline)) > 1e-9
                            )
                            if baseline_changed:
                                set_amount_action = SetStarterAmountAction(
                                    action_name="set_starter_amount",
                                    account_name=row.name,
                                    starter_amount=starter_amount,
                                )
                                history_entry = ActionHistory(
                                    id=generate_action_id(),
                                    timestamp=get_current_timestamp(),
                                    action=set_amount_action,
                                )
                                self.history_provider.add_action(history_entry)
            except Exception:
                pass

        return merged

    def save_all(self, accounts: List[MoneyAccount]) -> None:
        if not isinstance(self.provider, JsonFileAccountsProvider):
            return

        savings_accounts = [acc for acc in accounts if isinstance(acc, SavingsAccount)]
        bank_accounts: List[MoneyAccount] = [
            acc for acc in accounts if isinstance(acc, (BankAccount, BudgetAccount))
        ]

        try:
            self.provider.save_savings_accounts(savings_accounts)
        except Exception:
            pass
        try:
            self.provider.save_bank_accounts(bank_accounts)
        except Exception:
            pass

        try:
            from ..models.sync_gate import allow_firebase_push

            if not allow_firebase_push():
                return
            from ..models.firebase_workspace_writer import FirebaseWorkspaceWriter

            FirebaseWorkspaceWriter().upsert_accounts_snapshot(accounts)
        except Exception:
            pass
