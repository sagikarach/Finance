from __future__ import annotations

from typing import List, Optional

from .firebase_client import FirestoreClient
from ..data.provider import JsonFileAccountsProvider
from ..models.accounts_service import AccountsService
from ..models.accounts import BudgetAccount, MoneySnapshot


def pull_accounts_meta_to_local_cache(
    *,
    fs: FirestoreClient,
    workspace_id: str,
    id_token: str,
    accounts_provider: Optional[JsonFileAccountsProvider] = None,
    accounts_service: Optional[AccountsService] = None,
) -> None:
    workspace_id = str(workspace_id or "").strip()
    if not workspace_id:
        return

    try:
        from ..models.accounts import (
            BankAccount,
            Savings,
            SavingsAccount,
        )

        doc = fs.get_document(
            document_path=f"workspaces/{workspace_id}/meta/accounts",
            id_token=id_token,
        )
        _, parsed = fs.parse_any_doc(doc) if isinstance(doc, dict) else ("", {})
        remote_bank = parsed.get("bank_accounts", [])
        remote_savings = parsed.get("savings_accounts", [])

        provider = accounts_provider or JsonFileAccountsProvider()
        svc = accounts_service or AccountsService(provider)
        local_accounts = svc.load_accounts()
        local_bank_by_name = {
            a.name: a for a in local_accounts if isinstance(a, BankAccount)
        }
        local_budget_by_name = {
            a.name: a for a in local_accounts if isinstance(a, BudgetAccount)
        }

        bank_accounts: List[BankAccount] = []
        budget_accounts: List[BudgetAccount] = []
        if isinstance(remote_bank, list):
            for row in remote_bank:
                if not isinstance(row, dict):
                    continue
                name = str(row.get("name", "") or "").strip()
                if not name:
                    continue
                kind = str(row.get("kind", "") or "").strip().lower()
                is_liquid = bool(row.get("is_liquid", False))
                active = bool(row.get("active", False))
                if kind == "budget":
                    try:
                        mb = float(row.get("monthly_budget", 0.0) or 0.0)
                    except Exception:
                        mb = 0.0
                    try:
                        rd = int(row.get("reset_day", 1) or 1)
                    except Exception:
                        rd = 1
                    last_period = str(row.get("last_reset_period", "") or "").strip()
                    try:
                        bal = float(row.get("total_amount", 0.0) or 0.0)
                    except Exception:
                        bal = 0.0
                    hist_rows = row.get("history", [])
                    hist: List[MoneySnapshot] = []
                    if isinstance(hist_rows, list):
                        for h in hist_rows:
                            if not isinstance(h, dict):
                                continue
                            ds = str(h.get("date", "") or "").strip()
                            if not ds:
                                continue
                            try:
                                ha = float(h.get("amount", 0.0) or 0.0)
                            except Exception:
                                ha = 0.0
                            hist.append(MoneySnapshot(date=ds, amount=ha))
                    existing_b = local_budget_by_name.get(name)
                    if isinstance(existing_b, BudgetAccount) and not hist:
                        hist = list(existing_b.history)
                        bal = float(existing_b.total_amount)
                        last_period = (
                            str(existing_b.last_reset_period or "") or last_period
                        )
                        rd = int(existing_b.reset_day or rd)
                        mb = float(existing_b.monthly_budget or mb)
                    budget_accounts.append(
                        BudgetAccount(
                            name=name,
                            total_amount=bal,
                            is_liquid=False,
                            history=hist,
                            active=active,
                            monthly_budget=float(mb),
                            reset_day=int(rd),
                            last_reset_period=last_period,
                        )
                    )
                    continue

                existing = local_bank_by_name.get(name)
                if isinstance(existing, BankAccount):
                    bank_accounts.append(
                        BankAccount(
                            name=name,
                            total_amount=float(existing.total_amount),
                            is_liquid=is_liquid,
                            history=list(existing.history),
                            active=active,
                        )
                    )
                else:
                    bank_accounts.append(
                        BankAccount(
                            name=name,
                            total_amount=0.0,
                            is_liquid=is_liquid,
                            history=[],
                            active=active,
                        )
                    )

        savings_accounts: List[SavingsAccount] = []
        if isinstance(remote_savings, list):
            for row in remote_savings:
                if not isinstance(row, dict):
                    continue
                name = str(row.get("name", "") or "").strip()
                if not name:
                    continue
                is_liquid = bool(row.get("is_liquid", False))
                savings_rows = row.get("savings", [])
                savings: List[Savings] = []
                if isinstance(savings_rows, list):
                    for srow in savings_rows:
                        if not isinstance(srow, dict):
                            continue
                        sname = str(srow.get("name", "") or "").strip()
                        if not sname:
                            continue
                        history_rows = srow.get("history", [])
                        shist: List[MoneySnapshot] = []
                        if isinstance(history_rows, list):
                            for h in history_rows:
                                if not isinstance(h, dict):
                                    continue
                                date_str = str(h.get("date", "") or "").strip()
                                try:
                                    amt = float(h.get("amount", 0.0) or 0.0)
                                except Exception:
                                    amt = 0.0
                                if date_str:
                                    shist.append(
                                        MoneySnapshot(date=date_str, amount=amt)
                                    )
                        try:
                            amt = float(srow.get("amount", 0.0) or 0.0)
                        except Exception:
                            amt = 0.0
                        savings.append(Savings(name=sname, amount=amt, history=shist))

                savings_accounts.append(
                    SavingsAccount(
                        name=name,
                        total_amount=0.0,
                        is_liquid=is_liquid,
                        savings=savings,
                    )
                )

        provider.save_bank_accounts(list(bank_accounts) + list(budget_accounts))
        provider.save_savings_accounts(savings_accounts)
    except Exception:
        pass
