from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime, timedelta
from typing import Callable, List, Optional
import uuid

from ..utils.rtl import unwrap_rtl
from ..data.action_history_provider import ActionHistoryProvider
from ..data.bank_movement_provider import BankMovementProvider
from ..data.notifications_provider import (
    JsonFileNotificationsProvider,
    NotificationsProvider,
)
from ..data.provider import AccountsProvider
from ..models.accounts import SavingsAccount, parse_iso_date
from ..models.action_history import ActionHistory
from ..models.bank_movement import BankMovement, MovementType
from ..data.one_time_event_provider import JsonFileOneTimeEventProvider
from ..models.one_time_event import OneTimeEvent
from .notifications import (
    CLOSED_BY_SYSTEM,
    CLOSED_BY_USER,
    Notification,
    NotificationRule,
    NotificationSeverity,
    NotificationStatus,
    NotificationType,
    RuleType,
)
from ..data.installment_plan_provider import (
    InstallmentPlanProvider,
    JsonFileInstallmentPlanProvider,
)
from ..data.mortgage_provider import JsonFileMortgageProvider, MortgageProvider
from ..data.one_time_event_provider import OneTimeEventProvider
from .movement_matching import match_movements
from .mortgage_math import cost_matched_movements
from .mortgage import CostItem
from .unusual_expense_detector import (
    DEFAULT_CONFIG,
    CandidateDecision,
    UnusualExpenseConfig,
    YearMonth,
    decision_context,
    DetectionIndex,
    decision_title,
    evaluate_month,
    format_unusual_expense_message,
    outcome_counts,
    movement_month,
    shift_month,
)
from ..utils.logging_setup import get_logger
from ..utils.safe import PARSE_ERRORS, swallow

_log = get_logger("notifications")

# Unusual-expense alerts are keyed ``unexpected_expense:<movement id>``; the
# duplicate-charge alerts share the type but live under ``…:duplicate:``.
_UNEXPECTED_PREFIX = "unexpected_expense:"
_DUPLICATE_INFIX = "duplicate:"
def _is_unusual_expense_key(key: str) -> bool:
    key = str(key or "")
    return key.startswith(_UNEXPECTED_PREFIX) and not key.startswith(
        _UNEXPECTED_PREFIX + _DUPLICATE_INFIX
    )


def _today_iso() -> str:
    try:
        return date.today().isoformat()
    except PARSE_ERRORS:
        return ""


class NotificationsService:
    def __init__(
        self,
        *,
        provider: Optional[NotificationsProvider] = None,
        accounts_provider: Optional[AccountsProvider] = None,
        movement_provider: Optional[BankMovementProvider] = None,
        history_provider: Optional[ActionHistoryProvider] = None,
        installment_provider: Optional[InstallmentPlanProvider] = None,
        mortgage_provider: Optional[MortgageProvider] = None,
        event_provider: Optional[OneTimeEventProvider] = None,
        unusual_expense_config: Optional[UnusualExpenseConfig] = None,
        today: Optional[Callable[[], date]] = None,
    ) -> None:
        self._provider = provider or JsonFileNotificationsProvider()
        self._accounts_provider = accounts_provider
        self._movement_provider = movement_provider
        self._history_provider = history_provider
        # Plan/asset/event providers are resolved lazily so the JSON defaults
        # always follow the *current* workspace.
        self._installment_override = installment_provider
        self._mortgage_override = mortgage_provider
        self._event_override = event_provider
        self._unusual_config = unusual_expense_config or DEFAULT_CONFIG
        self._today: Callable[[], date] = today or date.today
        # Outcome counts of the last evaluated month (diagnostics: how many
        # expenses got no statistical decision and why). Counts only.
        self.last_unusual_outcomes: dict[str, int] = {}

    def _installment_provider(self) -> InstallmentPlanProvider:
        return self._installment_override or JsonFileInstallmentPlanProvider()

    def _mortgage_provider(self) -> MortgageProvider:
        return self._mortgage_override or JsonFileMortgageProvider()

    def _event_provider(self) -> OneTimeEventProvider:
        return self._event_override or JsonFileOneTimeEventProvider()

    def ensure_defaults(self) -> None:
        try:
            rules = list(self._provider.list_rules())
        except PARSE_ERRORS:
            rules = []
        by_id = {r.id: r for r in rules if getattr(r, "id", None)}

        defaults: List[NotificationRule] = [
            NotificationRule(
                id="unexpected_expense",
                type=RuleType.UNEXPECTED_EXPENSE,
                enabled=True,
                params={},
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
            NotificationRule(
                id="event_over_budget",
                type=RuleType.EVENT_OVER_BUDGET,
                enabled=True,
                params={},
            ),
        ]
        changed = False
        merged: List[NotificationRule] = list(rules)
        for d in defaults:
            if d.id not in by_id:
                merged.append(d)
                changed = True
        if changed or not rules:
            self._provider.save_rules(merged)

    def is_enabled(self) -> bool:
        getter = getattr(self._provider, "is_enabled", None)
        if callable(getter):
            try:
                return bool(getter())
            except PARSE_ERRORS:
                return True
        return True

    def set_enabled(self, enabled: bool) -> None:
        setter = getattr(self._provider, "set_enabled", None)
        if callable(setter):
            try:
                setter(bool(enabled))
            except PARSE_ERRORS:
                pass

    def list_rules(self) -> List[NotificationRule]:
        self.ensure_defaults()
        try:
            return list(self._provider.list_rules())
        except PARSE_ERRORS:
            return []

    def list_notifications(self) -> List[Notification]:
        if not self.is_enabled():
            return []
        try:
            items = list(self._provider.list_notifications())
        except PARSE_ERRORS:
            items = []
        visible = self._filter_by_enabled_rules(items)
        return [
            n
            for n in visible
            if n.status
            not in (NotificationStatus.RESOLVED, NotificationStatus.DISMISSED)
        ]

    def set_rule_enabled(self, rule_id: str, enabled: bool) -> None:
        self.ensure_defaults()
        try:
            rules = self._provider.list_rules()
        except PARSE_ERRORS:
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
            except PARSE_ERRORS:
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

        # Each rule type maps to its evaluator (data-driven dispatch instead of
        # an if/elif type switch — adding a rule type is a one-line registry
        # entry). Each evaluator returns the notifications it produced.
        def _eval_unexpected(rule):
            notes = self._rule_unexpected_expense(rule, movements, existing_by_key)
            active_keys.update(
                n.key for n in notes if n.type == NotificationType.UNEXPECTED_EXPENSE
            )
            return notes

        evaluators = {
            RuleType.UNEXPECTED_EXPENSE: _eval_unexpected,
            RuleType.MISSING_MONTHLY_UPLOAD: lambda rule: (
                self._rule_missing_monthly_upload(
                    rule, history, existing_by_key, active_keys
                )
            ),
            RuleType.MISSING_SAVINGS_UPDATE: lambda rule: (
                self._rule_missing_savings_update(
                    rule, history, existing_by_key, active_keys
                )
            ),
            RuleType.EVENT_OVER_BUDGET: lambda rule: (
                self._rule_event_over_budget(rule, existing_by_key, active_keys)
            ),
        }

        for rule in rules:
            evaluator = evaluators.get(rule.type)
            if evaluator is not None:
                created.extend(evaluator(rule))

        for n in created:
            self._provider.upsert(n)
            with swallow(msg="firebase sync in refresh"):
                from ..models.firebase_workspace_writer import FirebaseWorkspaceWriter

                FirebaseWorkspaceWriter().upsert_notification(n)

        self._resolve_stale(active_keys=active_keys)
        try:
            items = list(self._provider.list_notifications())
        except PARSE_ERRORS:
            items = []
        visible = self._filter_by_enabled_rules(items)
        return [
            n
            for n in visible
            if n.status
            not in (NotificationStatus.RESOLVED, NotificationStatus.DISMISSED)
        ]

    def get_movement_by_id(self, movement_id: str) -> Optional[BankMovement]:
        movement_id = str(movement_id or "").strip()
        if not movement_id:
            return None
        if self._movement_provider is None:
            return None
        try:
            items = list(self._movement_provider.list_movements())
        except PARSE_ERRORS:
            items = []
        for m in items:
            try:
                if str(getattr(m, "id", "") or "") == movement_id:
                    return m
            except PARSE_ERRORS:
                continue
        return None

    def get_movements_by_ids(self, movement_ids: List[str]) -> List[BankMovement]:
        ids = [str(x or "").strip() for x in list(movement_ids or [])]
        want = {x for x in ids if x}
        if not want or self._movement_provider is None:
            return []
        try:
            items = list(self._movement_provider.list_movements())
        except PARSE_ERRORS:
            items = []
        out: List[BankMovement] = []
        for m in items:
            try:
                mid = str(getattr(m, "id", "") or "")
            except PARSE_ERRORS:
                continue
            if mid in want:
                out.append(m)
        return out

    def unread_count(self) -> int:
        if not self.is_enabled():
            return 0
        items = self.list_notifications()
        return sum(1 for n in items if n.status == NotificationStatus.UNREAD)

    def mark_read(self, key: str) -> None:
        self._provider.update_status(key=key, status=NotificationStatus.READ)
        self._best_effort_push_status(key=key)

    def mark_unread(self, key: str) -> None:
        self._provider.update_status(key=key, status=NotificationStatus.UNREAD)
        self._best_effort_push_status(key=key)

    def resolve(self, key: str) -> None:
        """The user marked the alert as handled — never reopened automatically."""
        self._provider.update_status(
            key=key, status=NotificationStatus.RESOLVED, closed_by=CLOSED_BY_USER
        )
        self._best_effort_push_status(key=key)

    def _best_effort_push_status(self, *, key: str) -> None:
        key = str(key or "").strip()
        if not key:
            return
        try:
            items = list(self._provider.list_notifications())
        except PARSE_ERRORS:
            items = []
        notif = None
        for n in items:
            try:
                if str(getattr(n, "key", "") or "") == key:
                    notif = n
                    break
            except PARSE_ERRORS:
                continue
        if notif is None:
            return
        with swallow(msg="firebase sync in _best_effort_push_status"):
            from ..models.sync_gate import allow_firebase_push

            if not allow_firebase_push():
                return
            from ..models.firebase_workspace_writer import FirebaseWorkspaceWriter

            FirebaseWorkspaceWriter().upsert_notification(notif)

    def _enabled_rule_ids(self) -> set[str]:
        try:
            rules = self._provider.list_rules()
        except PARSE_ERRORS:
            return set()
        return {r.id for r in rules if bool(getattr(r, "enabled", False))}

    def _filter_by_enabled_rules(self, items: List[Notification]) -> List[Notification]:
        enabled_rule_ids = self._enabled_rule_ids()

        out: List[Notification] = []
        for n in items:
            try:
                source = str(getattr(n, "source", "") or "")
                if source.startswith("rule:"):
                    if not enabled_rule_ids:
                        continue
                    rule_id = source.split(":", 1)[1].strip()
                    if rule_id and rule_id not in enabled_rule_ids:
                        continue
                out.append(n)
            except PARSE_ERRORS:
                continue
        return out

    def _resolve_stale(self, *, active_keys: set[str]) -> None:
        items = self._provider.list_notifications()
        for n in items:
            if n.type in (
                NotificationType.MISSING_MONTHLY_UPLOAD,
                NotificationType.MISSING_SAVINGS_UPDATE,
                NotificationType.EVENT_OVER_BUDGET,
            ):
                if n.key not in active_keys and n.status not in (
                    NotificationStatus.DISMISSED,
                    NotificationStatus.RESOLVED,
                ):
                    self._provider.update_status(
                        key=n.key, status=NotificationStatus.RESOLVED
                    )
                    self._best_effort_push_status(key=n.key)

    def _rule_event_over_budget(
        self,
        rule: NotificationRule,
        existing_by_key: dict[str, Notification],
        active_keys: set[str],
    ) -> List[Notification]:
        out: List[Notification] = []
        try:
            events = self._event_provider().list_events()
        except PARSE_ERRORS:
            events = []

        movements = (
            self._movement_provider.list_movements() if self._movement_provider else []
        )

        for event in events:
            try:
                key = f"event_over_budget:{event.id}"
                spent = self._event_spent(event, movements)
                budget = float(getattr(event, "budget", 0.0) or 0.0)
                if budget <= 0:
                    continue
                if spent <= budget:
                    continue
                active_keys.add(key)

                existing = existing_by_key.get(key)
                if existing is not None:
                    # If the user resolved this notification, keep it resolved (tombstone)
                    # and do not recreate/re-open it while the condition is still active.
                    continue

                over = spent - budget
                title = "חריגה מתקציב אירוע"
                name = str(getattr(event, "name", "") or "").strip() or "אירוע"
                msg = (
                    f"האירוע {unwrap_rtl(name)} חרג מהתקציב.\n"
                    f"תקציב: {budget:,.0f} | הוצאות: {spent:,.0f} | חריגה: {over:,.0f}"
                )

                out.append(
                    Notification(
                        id=str(uuid.uuid4()),
                        key=key,
                        type=NotificationType.EVENT_OVER_BUDGET,
                        title=title,
                        message=msg,
                        severity=NotificationSeverity.CRITICAL,
                        created_at=_today_iso(),
                        status=NotificationStatus.UNREAD,
                        due_at=None,
                        source=f"rule:{rule.id}",
                        context={
                            "event_id": str(event.id),
                            "event_name": name,
                            "budget": budget,
                            "spent": spent,
                            "over": over,
                        },
                    )
                )
            except PARSE_ERRORS:
                continue

        return out

    def _event_spent(self, event: OneTimeEvent, movements: List[BankMovement]) -> float:
        spent = 0.0
        for m in movements:
            try:
                if getattr(m, "type", None) != MovementType.ONE_TIME:
                    continue
            except PARSE_ERRORS:
                continue
            try:
                if getattr(m, "event_id", None) != event.id:
                    continue
            except PARSE_ERRORS:
                continue

            try:
                if not self._event_in_range(event, m):
                    continue
            except PARSE_ERRORS:
                pass

            try:
                amt = float(getattr(m, "amount", 0.0))
            except PARSE_ERRORS:
                continue
            if amt < 0:
                spent += abs(amt)
        return float(spent)

    def _event_in_range(self, event: OneTimeEvent, movement: BankMovement) -> bool:
        try:
            start = getattr(event, "start_date", None)
            end = getattr(event, "end_date", None)
        except PARSE_ERRORS:
            start, end = None, None
        if not start and not end:
            return True
        dt = parse_iso_date(getattr(movement, "date", ""))
        if start:
            if dt < parse_iso_date(str(start)):
                return False
        if end:
            if dt > parse_iso_date(str(end)):
                return False
        return True

    def _rule_unexpected_expense(
        self,
        rule: NotificationRule,
        movements: List[BankMovement],
        existing_by_key: dict[str, Notification],
    ) -> List[Notification]:
        """Duplicate charges + unusual expenses for the previous calendar month."""
        target_year, target_month = shift_month(
            (self._today().year, self._today().month), -1
        )
        out = self._duplicate_charge_notifications(
            rule, movements, existing_by_key, target_year, target_month
        )
        out.extend(
            self._unusual_expense_notifications(
                rule, movements, existing_by_key, (target_year, target_month)
            )
        )
        return out

    def _duplicate_charge_notifications(
        self,
        rule: NotificationRule,
        movements: List[BankMovement],
        existing_by_key: dict[str, Notification],
        target_year: int,
        target_month: int,
    ) -> List[Notification]:
        groups: dict[tuple[str, float, str], List[BankMovement]] = {}
        for m in movements:
            try:
                amt = float(getattr(m, "amount", 0.0))
                if amt >= 0:
                    continue
                dt = parse_iso_date(getattr(m, "date", ""))
                if dt.year != target_year or dt.month != target_month:
                    continue
                desc_raw = getattr(m, "description", "") or ""
                desc = unwrap_rtl(str(desc_raw)).strip().lower()
                key_t = (str(getattr(m, "date", "")), abs(float(amt)), desc)
                groups.setdefault(key_t, []).append(m)
            except PARSE_ERRORS:
                continue

        out: List[Notification] = []
        for (date_str, abs_amt, desc), items in groups.items():
            if len(items) < 2:
                continue
            safe_desc = desc if desc else "ללא תיאור"
            group_key = (
                f"{_UNEXPECTED_PREFIX}{_DUPLICATE_INFIX}"
                f"{date_str}:{abs_amt:.2f}:{safe_desc}"
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
        return out

    # ── unusual expenses (local, conservative detector) ──────────────────

    def _unusual_expense_notifications(
        self,
        rule: NotificationRule,
        movements: List[BankMovement],
        existing_by_key: dict[str, Notification],
        evaluated: YearMonth,
    ) -> List[Notification]:
        """Create, update, close and reopen unusual-expense alerts.

        * New alerts are created only for the evaluated (previous) month.
        * Every existing alert that is open — or was closed *automatically* — is
          re-checked against its own month: open + no longer qualifies → closed
          automatically (``closed_by=system``); system-closed + qualifies again
          → the same record is reopened with a fresh explanation.
        * Alerts closed by the user, or legacy closed records whose reason is
          unknown, are never touched.
        * On any detector error nothing is created, closed or reopened — there
          is deliberately no looser fallback.
        """
        try:
            planned = self._planned_movement_ids(movements)
            # Parsed once per refresh; every month evaluated below reuses it.
            index = DetectionIndex(movements)
            alerts_by_month: dict[YearMonth, dict[str, CandidateDecision]] = {}

            def alerts_for(ym: YearMonth) -> dict[str, CandidateDecision]:
                if ym not in alerts_by_month:
                    decisions = evaluate_month(
                        movements,
                        evaluated_month=ym,
                        planned_movement_ids=planned,
                        config=self._unusual_config,
                        index=index,
                    )
                    if ym == evaluated:
                        self.last_unusual_outcomes = outcome_counts(decisions)
                        _log.info(
                            "unusual-expense outcomes %04d-%02d: %s",
                            ym[0], ym[1], self.last_unusual_outcomes,
                        )
                    alerts_by_month[ym] = {
                        d.movement_id: d for d in decisions if d.is_alert
                    }
                return alerts_by_month[ym]

            alerts_for(evaluated)

            by_id = {str(getattr(m, "id", "") or ""): m for m in movements}
            to_close: List[str] = []
            to_refresh: dict[str, CandidateDecision] = {}  # open or reopen
            for key, n in existing_by_key.items():
                if not _is_unusual_expense_key(key):
                    continue
                if n.is_closed and not n.is_system_closed:
                    continue  # user-handled / legacy: keep the decision
                movement_id = key[len(_UNEXPECTED_PREFIX):]
                mv = by_id.get(movement_id)
                ym = movement_month(mv) if mv is not None else None
                decision = alerts_for(ym).get(movement_id) if ym is not None else None
                if decision is not None:
                    to_refresh[key] = decision
                elif not n.is_closed:
                    to_close.append(key)
        except Exception as exc:  # noqa: BLE001 - detector must never fall back
            _log.warning(
                "unusual-expense detector failed; no alert changes: %s",
                type(exc).__name__,
            )
            return []

        for key in to_close:
            self._provider.update_status(
                key=key,
                status=NotificationStatus.RESOLVED,
                closed_by=CLOSED_BY_SYSTEM,
            )
            self._best_effort_push_status(key=key)

        out: List[Notification] = []
        for key, decision in to_refresh.items():
            existing = existing_by_key[key]
            message = format_unusual_expense_message(decision)
            context = decision_context(decision)
            reopened = existing.is_system_closed
            if (
                not reopened
                and existing.message == message
                and dict(existing.context) == context
            ):
                continue
            out.append(
                replace(
                    existing,
                    title=decision_title(decision),
                    message=message,
                    context=context,
                    source=f"rule:{rule.id}",
                    status=NotificationStatus.UNREAD if reopened else existing.status,
                    closed_by=None if reopened else existing.closed_by,
                )
            )

        for decision in alerts_for(evaluated).values():
            key = f"{_UNEXPECTED_PREFIX}{decision.movement_id}"
            if key in existing_by_key:
                continue  # handled above (or a user/legacy closure)
            out.append(
                Notification(
                    id=str(uuid.uuid4()),
                    key=key,
                    type=NotificationType.UNEXPECTED_EXPENSE,
                    title=decision_title(decision),
                    message=format_unusual_expense_message(decision),
                    severity=NotificationSeverity.WARNING,
                    created_at=_today_iso(),
                    source=f"rule:{rule.id}",
                    context=decision_context(decision),
                )
            )
        return out

    def _planned_movement_ids(self, movements: List[BankMovement]) -> set[str]:
        """Ids of movements explicitly tied to something the user planned:
        installment plans and direct debits, mortgage payments/prepayments,
        an asset's purchase-price payments and recurring/annual/one-time cost
        items, and budgeted events.
        Every link here is one the user configured and can see (and exclude)
        in the app — nothing is inferred from description text by itself."""
        planned: set[str] = set()

        plans = list(self._installment_provider().list_plans())
        for plan in plans:
            if plan.is_direct_debit:
                prefix = f"dd-{plan.id}-"
                planned.update(
                    str(m.id) for m in movements if str(m.id).startswith(prefix)
                )
            else:
                planned.update(str(m.id) for m in plan.matches(movements))

        for asset in list(self._mortgage_provider().list_mortgages()):
            planned.update(
                str(m.id)
                for m in match_movements(
                    movements,
                    vendor_query=asset.vendor_query,
                    account_name=asset.account_name,
                    start_date=str(asset.start_date or ""),
                    excluded_ids=list(asset.excluded_movement_ids or []),
                )
            )
            planned.update(str(x) for x in (asset.prepayment_movement_ids or []))
            # Payments to the seller, linked by the asset's price search text.
            price_query = str(getattr(asset, "price_query", "") or "").strip()
            if price_query:
                planned.update(
                    str(m.id)
                    for m in cost_matched_movements(
                        CostItem(query=price_query), movements
                    )
                )
            for cost in (
                list(asset.monthly_costs or [])
                + list(asset.yearly_costs or [])
                + list(asset.one_time_costs or [])
            ):
                planned.update(
                    str(m.id) for m in cost_matched_movements(cost, movements)
                )

        budgeted_events = {
            str(e.id)
            for e in self._event_provider().list_events()
            if float(getattr(e, "budget", 0.0) or 0.0) > 0
        }
        if budgeted_events:
            planned.update(
                str(m.id)
                for m in movements
                if str(getattr(m, "event_id", "") or "") in budgeted_events
            )
        return planned

    def _rule_missing_monthly_upload(
        self,
        rule: NotificationRule,
        history: List[ActionHistory],
        existing_by_key: dict[str, Notification],
        active_keys: set[str],
    ) -> List[Notification]:
        today = date.today()
        # Alert only after enough time has passed since the missing month.
        # User expectation example: if October (10) was missed, alert only after December (12) ended.
        # That means we alert in January -> target month is 3 months back.
        delay_months = 3

        def _add_months(y: int, m: int, delta: int) -> tuple[int, int]:
            total = (int(y) * 12 + (int(m) - 1)) + int(delta)
            ny = total // 12
            nm = (total % 12) + 1
            return int(ny), int(nm)

        target_year, target_month = _add_months(today.year, today.month, -delay_months)
        ym = f"{target_year:04d}-{target_month:02d}"
        key = f"missing_upload:{ym}"

        has_upload = False
        for h in history:
            try:
                if getattr(h.action, "action_name", "") != "upload_outcome_file":
                    continue
                if not getattr(h.action, "success", True):
                    continue
                ts = parse_iso_date(getattr(h, "timestamp", ""))
                if ts.year == target_year and ts.month == target_month:
                    has_upload = True
                    break
            except PARSE_ERRORS:
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
                message="לא העלה קובץ הוצאות חודשי.",
                severity=NotificationSeverity.INFO,
                created_at=_today_iso(),
                source=f"rule:{rule.id}",
                context={"year": target_year, "month": target_month},
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
        except PARSE_ERRORS:
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
                except PARSE_ERRORS:
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
            except PARSE_ERRORS:
                continue
        return out
