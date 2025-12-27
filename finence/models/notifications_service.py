from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional
import uuid

from ..ui.dialog_utils import unwrap_rtl
from ..data.action_history_provider import ActionHistoryProvider
from ..data.bank_movement_provider import BankMovementProvider
from ..data.notifications_provider import (
    JsonFileNotificationsProvider,
    NotificationsProvider,
)
from ..data.provider import AccountsProvider
from ..models.accounts import SavingsAccount, parse_iso_date
from ..models.action_history import ActionHistory
from ..models.bank_movement import BankMovement
from .notifications import (
    Notification,
    NotificationRule,
    NotificationSeverity,
    NotificationStatus,
    NotificationType,
    RuleType,
)


def _today_iso() -> str:
    try:
        return date.today().isoformat()
    except Exception:
        return ""


class NotificationsService:
    def __init__(
        self,
        *,
        provider: Optional[NotificationsProvider] = None,
        accounts_provider: Optional[AccountsProvider] = None,
        movement_provider: Optional[BankMovementProvider] = None,
        history_provider: Optional[ActionHistoryProvider] = None,
    ) -> None:
        self._provider = provider or JsonFileNotificationsProvider()
        self._accounts_provider = accounts_provider
        self._movement_provider = movement_provider
        self._history_provider = history_provider

    def ensure_defaults(self) -> None:
        rules = self._provider.list_rules()
        if rules:
            return
        defaults: List[NotificationRule] = [
            NotificationRule(
                id="unexpected_expense",
                type=RuleType.UNEXPECTED_EXPENSE,
                enabled=True,
                params={"percentile": 0.8},
            ),
            NotificationRule(
                id="missing_monthly_upload",
                type=RuleType.MISSING_MONTHLY_UPLOAD,
                enabled=True,
                params={"day_of_month": 5},
            ),
            NotificationRule(
                id="missing_savings_update",
                type=RuleType.MISSING_SAVINGS_UPDATE,
                enabled=True,
                params={"days_since_update": 30},
            ),
        ]
        self._provider.save_rules(defaults)

    def is_enabled(self) -> bool:
        getter = getattr(self._provider, "is_enabled", None)
        if callable(getter):
            try:
                return bool(getter())
            except Exception:
                return True
        return True

    def set_enabled(self, enabled: bool) -> None:
        setter = getattr(self._provider, "set_enabled", None)
        if callable(setter):
            try:
                setter(bool(enabled))
            except Exception:
                pass

    def list_rules(self) -> List[NotificationRule]:
        self.ensure_defaults()
        try:
            return list(self._provider.list_rules())
        except Exception:
            return []

    def list_notifications(self) -> List[Notification]:
        if not self.is_enabled():
            return []
        try:
            items = list(self._provider.list_notifications())
        except Exception:
            items = []
        return self._filter_by_enabled_rules(items)

    def set_rule_enabled(self, rule_id: str, enabled: bool) -> None:
        self.ensure_defaults()
        try:
            rules = self._provider.list_rules()
        except Exception:
            return
        changed = False
        updated: List[NotificationRule] = []
        for r in rules:
            if r.id == rule_id and bool(r.enabled) != bool(enabled):
                r = NotificationRule(
                    id=r.id,
                    type=r.type,
                    enabled=bool(enabled),
                    schedule=r.schedule,
                    params=dict(r.params),
                )
                changed = True
            updated.append(r)
        if changed:
            try:
                self._provider.save_rules(updated)
            except Exception:
                pass

    def refresh(self) -> List[Notification]:
        self.ensure_defaults()
        if not self.is_enabled():
            return []
        rules = [r for r in self._provider.list_rules() if r.enabled]

        existing = self._provider.list_notifications()
        existing_by_key = {n.key: n for n in existing}

        history = (
            self._history_provider.list_history() if self._history_provider else []
        )
        movements = (
            self._movement_provider.list_movements() if self._movement_provider else []
        )

        created: List[Notification] = []
        active_keys: set[str] = set()

        for rule in rules:
            if rule.type == RuleType.UNEXPECTED_EXPENSE:
                created.extend(
                    self._rule_unexpected_expense(rule, movements, existing_by_key)
                )
                active_keys.update(
                    n.key
                    for n in created
                    if n.type == NotificationType.UNEXPECTED_EXPENSE
                )
            elif rule.type == RuleType.MISSING_MONTHLY_UPLOAD:
                created.extend(
                    self._rule_missing_monthly_upload(
                        rule, history, existing_by_key, active_keys
                    )
                )
            elif rule.type == RuleType.MISSING_SAVINGS_UPDATE:
                created.extend(
                    self._rule_missing_savings_update(
                        rule, history, existing_by_key, active_keys
                    )
                )

        for n in created:
            self._provider.upsert(n)

        self._resolve_stale(active_keys=active_keys)
        try:
            items = list(self._provider.list_notifications())
        except Exception:
            items = []
        return self._filter_by_enabled_rules(items)

    def unread_count(self) -> int:
        if not self.is_enabled():
            return 0
        items = self.list_notifications()
        return sum(1 for n in items if n.status == NotificationStatus.UNREAD)

    def mark_read(self, key: str) -> None:
        self._provider.update_status(key=key, status=NotificationStatus.READ)

    def dismiss(self, key: str) -> None:
        self._provider.update_status(key=key, status=NotificationStatus.DISMISSED)

    def _enabled_rule_ids(self) -> set[str]:
        try:
            rules = self._provider.list_rules()
        except Exception:
            return set()
        return {r.id for r in rules if bool(getattr(r, "enabled", False))}

    def _filter_by_enabled_rules(self, items: List[Notification]) -> List[Notification]:
        enabled_rule_ids = self._enabled_rule_ids()
        if not enabled_rule_ids:
            return []

        out: List[Notification] = []
        for n in items:
            try:
                source = str(getattr(n, "source", "") or "")
                if source.startswith("rule:"):
                    rule_id = source.split(":", 1)[1].strip()
                    if rule_id and rule_id not in enabled_rule_ids:
                        continue
                out.append(n)
            except Exception:
                continue
        return out

    def _resolve_stale(self, *, active_keys: set[str]) -> None:
        items = self._provider.list_notifications()
        for n in items:
            if n.type in (
                NotificationType.MISSING_MONTHLY_UPLOAD,
                NotificationType.MISSING_SAVINGS_UPDATE,
            ):
                if n.key not in active_keys and n.status not in (
                    NotificationStatus.DISMISSED,
                    NotificationStatus.RESOLVED,
                ):
                    self._provider.update_status(
                        key=n.key, status=NotificationStatus.RESOLVED
                    )

    def _rule_unexpected_expense(
        self,
        rule: NotificationRule,
        movements: List[BankMovement],
        existing_by_key: dict[str, Notification],
    ) -> List[Notification]:
        percentile = float(rule.params.get("percentile", 0.8))
        try:
            percentile = max(0.0, min(1.0, percentile))
        except Exception:
            percentile = 0.8

        today = date.today()
        if today.month == 1:
            target_year, target_month = today.year - 1, 12
        else:
            target_year, target_month = today.year, today.month - 1

        prev_month_expenses: List[float] = []
        movement_dt: dict[str, datetime] = {}
        for m in movements:
            try:
                amt = float(getattr(m, "amount", 0.0))
                if amt >= 0:
                    continue
                dt = parse_iso_date(getattr(m, "date", ""))
                movement_dt[m.id] = dt
                if dt.year == target_year and dt.month == target_month:
                    prev_month_expenses.append(abs(amt))
            except Exception:
                continue

        if not prev_month_expenses:
            return []

        prev_month_expenses.sort()
        idx = int((len(prev_month_expenses) - 1) * percentile)
        idx = max(0, min(len(prev_month_expenses) - 1, idx))
        cutoff_amount = float(prev_month_expenses[idx])

        out: List[Notification] = []

        # Duplicate detection (same date + amount + description) in previous month
        groups: dict[tuple[str, float, str], List[BankMovement]] = {}
        for m in movements:
            try:
                amt = float(getattr(m, "amount", 0.0))
                if amt >= 0:
                    continue
                dt = movement_dt.get(m.id) or parse_iso_date(getattr(m, "date", ""))
                if dt.year != target_year or dt.month != target_month:
                    continue
                desc_raw = getattr(m, "description", "") or ""
                desc = unwrap_rtl(str(desc_raw)).strip().lower()
                key_t = (str(getattr(m, "date", "")), abs(float(amt)), desc)
                groups.setdefault(key_t, []).append(m)
            except Exception:
                continue

        for (date_str, abs_amt, desc), items in groups.items():
            if len(items) < 2:
                continue
            safe_desc = desc if desc else "ללא תיאור"
            group_key = (
                f"unexpected_expense:duplicate:{date_str}:{abs_amt:.2f}:{safe_desc}"
            )
            if group_key in existing_by_key:
                continue
            out.append(
                Notification(
                    id=str(uuid.uuid4()),
                    key=group_key,
                    type=NotificationType.UNEXPECTED_EXPENSE,
                    title="הוצאה כפולה",
                    message=f"זוהו {len(items)} הוצאות זהות באותו יום (₪{abs_amt:.2f}).",
                    severity=NotificationSeverity.WARNING,
                    created_at=_today_iso(),
                    source=f"rule:{rule.id}",
                    context={
                        "date": date_str,
                        "amount": -abs_amt,
                        "description": safe_desc,
                        "movement_ids": [m.id for m in items],
                        "target_year": target_year,
                        "target_month": target_month,
                    },
                )
            )

        for m in movements:
            try:
                amt = float(getattr(m, "amount", 0.0))
                if amt >= 0:
                    continue
                dt = movement_dt.get(m.id) or parse_iso_date(getattr(m, "date", ""))
                if dt.year != target_year or dt.month != target_month:
                    continue

                abs_amt = abs(float(amt))
                if abs_amt < cutoff_amount:
                    continue

                key = f"unexpected_expense:{m.id}"
                if key in existing_by_key:
                    continue

                title = "הוצאה חריגה"
                msg = f"הוצאה חריגה (טופ {int((1.0 - percentile) * 100)}%) בסכום ₪{abs_amt:.2f}"
                out.append(
                    Notification(
                        id=str(uuid.uuid4()),
                        key=key,
                        type=NotificationType.UNEXPECTED_EXPENSE,
                        title=title,
                        message=msg,
                        severity=NotificationSeverity.WARNING,
                        created_at=_today_iso(),
                        source=f"rule:{rule.id}",
                        context={
                            "movement_id": m.id,
                            "date": getattr(m, "date", ""),
                            "amount": float(amt),
                            "percentile": percentile,
                            "cutoff_amount": cutoff_amount,
                            "target_year": target_year,
                            "target_month": target_month,
                        },
                    )
                )
            except Exception:
                continue
        return out

    def _rule_missing_monthly_upload(
        self,
        rule: NotificationRule,
        history: List[ActionHistory],
        existing_by_key: dict[str, Notification],
        active_keys: set[str],
    ) -> List[Notification]:
        day_of_month = int(rule.params.get("day_of_month", 5))
        today = date.today()
        if today.day < day_of_month:
            return []

        ym = f"{today.year:04d}-{today.month:02d}"
        key = f"missing_upload:{ym}"

        has_upload = False
        for h in history:
            try:
                if getattr(h.action, "action_name", "") != "upload_outcome_file":
                    continue
                if not getattr(h.action, "success", True):
                    continue
                ts = parse_iso_date(getattr(h, "timestamp", ""))
                if ts.year == today.year and ts.month == today.month:
                    has_upload = True
                    break
            except Exception:
                continue

        if has_upload:
            return []

        active_keys.add(key)
        if key in existing_by_key:
            return []

        return [
            Notification(
                id=str(uuid.uuid4()),
                key=key,
                type=NotificationType.MISSING_MONTHLY_UPLOAD,
                title="חסרה העלאת קובץ הוצאות",
                message="נראה שעדיין לא העלית קובץ הוצאות לחודש הנוכחי.",
                severity=NotificationSeverity.INFO,
                created_at=_today_iso(),
                source=f"rule:{rule.id}",
                context={"year": today.year, "month": today.month},
            )
        ]

    def _rule_missing_savings_update(
        self,
        rule: NotificationRule,
        history: List[ActionHistory],
        existing_by_key: dict[str, Notification],
        active_keys: set[str],
    ) -> List[Notification]:
        days_since_update = int(rule.params.get("days_since_update", 30))
        cutoff = datetime.now() - timedelta(days=days_since_update)

        if self._accounts_provider is None:
            return []
        try:
            accounts = self._accounts_provider.list_accounts()
        except Exception:
            accounts = []
        savings_accounts = [a for a in accounts if isinstance(a, SavingsAccount)]
        if not savings_accounts:
            return []

        relevant_actions = {
            "add_savings_account",
            "edit_savings_account",
            "add_saving",
            "edit_saving",
            "delete_saving",
        }

        def last_update_for(name: str) -> Optional[datetime]:
            latest: Optional[datetime] = None
            for h in history:
                try:
                    an = getattr(h.action, "action_name", "")
                    if an not in relevant_actions:
                        continue
                    if getattr(h.action, "account_name", "") != name:
                        continue
                    ts = parse_iso_date(getattr(h, "timestamp", ""))
                    if latest is None or ts > latest:
                        latest = ts
                except Exception:
                    continue
            return latest

        out: List[Notification] = []
        for acc in savings_accounts:
            try:
                name = getattr(acc, "name", "")
                if not name:
                    continue
                last = last_update_for(name)
                if last is not None and last >= cutoff:
                    continue
                key = f"missing_savings_update:{name}"
                active_keys.add(key)
                if key in existing_by_key:
                    continue
                out.append(
                    Notification(
                        id=str(uuid.uuid4()),
                        key=key,
                        type=NotificationType.MISSING_SAVINGS_UPDATE,
                        title="עדכון חסכונות חסר",
                        message=f"שכחת לעדכן את החסכונות בחשבון: {name}",
                        severity=NotificationSeverity.INFO,
                        created_at=_today_iso(),
                        source=f"rule:{rule.id}",
                        context={
                            "account_name": name,
                            "days_since_update": days_since_update,
                        },
                    )
                )
            except Exception:
                continue
        return out
