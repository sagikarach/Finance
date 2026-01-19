from __future__ import annotations

from typing import List

from .firebase_client import FirestoreClient


def pull_ml_seed_best_effort(
    *, workspace_id: str, ensure_in_firebase: bool = False
) -> None:
    if not str(workspace_id or "").strip():
        return
    try:
        from .workspace_ml_trainer import WorkspaceMLTrainer

        t = WorkspaceMLTrainer()
        t.pull_seed_to_cache()
        if bool(ensure_in_firebase):
            t.ensure_seed_in_firebase()
    except Exception:
        pass


def pull_events_to_local_cache(
    *, fs: FirestoreClient, workspace_id: str, id_token: str
) -> None:
    workspace_id = str(workspace_id or "").strip()
    if not workspace_id:
        return
    try:
        from ..data.one_time_event_provider import JsonFileOneTimeEventProvider
        from ..models.one_time_event import (
            OneTimeEvent,
            OneTimeEventStatus,
            parse_one_time_event_status,
        )

        docs_events = fs.list_collection(
            collection_path=f"workspaces/{workspace_id}/events",
            id_token=id_token,
        )
        events: List[OneTimeEvent] = []
        for d in docs_events:
            try:
                doc_id, parsed = fs.parse_any_doc(d)
                if bool(parsed.get("deleted", False)):
                    continue
                eid = str(parsed.get("id") or doc_id).strip()
                name = str(parsed.get("name") or "").strip()
                budget = float(parsed.get("budget") or 0.0)
                status = parse_one_time_event_status(
                    parsed.get("status") or OneTimeEventStatus.ACTIVE.value
                )
                start_date = parsed.get("start_date")
                end_date = parsed.get("end_date")
                notes = parsed.get("notes")
                events.append(
                    OneTimeEvent(
                        id=eid,
                        name=name,
                        budget=budget,
                        status=status,
                        start_date=str(start_date)
                        if isinstance(start_date, str) and str(start_date).strip()
                        else None,
                        end_date=str(end_date)
                        if isinstance(end_date, str) and str(end_date).strip()
                        else None,
                        notes=str(notes)
                        if isinstance(notes, str) and str(notes).strip()
                        else None,
                    )
                )
            except Exception:
                continue
        JsonFileOneTimeEventProvider().save_events(events)
    except Exception:
        pass


def pull_installment_plans_to_local_cache(
    *, fs: FirestoreClient, workspace_id: str, id_token: str
) -> None:
    workspace_id = str(workspace_id or "").strip()
    if not workspace_id:
        return
    try:
        from ..data.installment_plan_provider import JsonFileInstallmentPlanProvider
        from ..models.installment_plan import InstallmentPlan

        docs_plans = fs.list_collection(
            collection_path=f"workspaces/{workspace_id}/installment_plans",
            id_token=id_token,
        )
        plans: List[InstallmentPlan] = []
        for d in docs_plans:
            try:
                doc_id, parsed = fs.parse_any_doc(d)
                if bool(parsed.get("deleted", False)):
                    continue
                pid = str(parsed.get("id") or doc_id).strip()
                name = str(parsed.get("name") or "").strip()
                vendor_query = str(parsed.get("vendor_query") or "").strip()
                account_name = str(parsed.get("account_name") or "").strip()
                start_date = str(parsed.get("start_date") or "").strip()
                payments_count = int(parsed.get("payments_count") or 0)
                original_amount = float(parsed.get("original_amount") or 0.0)
                excluded_raw = parsed.get("excluded_movement_ids") or []
                excluded: list[str] = []
                if isinstance(excluded_raw, list):
                    excluded = [str(x) for x in excluded_raw if str(x).strip()]
                archived = bool(parsed.get("archived", False))
                plans.append(
                    InstallmentPlan(
                        id=pid,
                        name=name,
                        vendor_query=vendor_query,
                        account_name=account_name,
                        start_date=start_date,
                        payments_count=payments_count,
                        original_amount=original_amount,
                        excluded_movement_ids=excluded,
                        archived=archived,
                    )
                )
            except Exception:
                continue
        JsonFileInstallmentPlanProvider().save_plans(plans)
    except Exception:
        pass


def pull_notifications_to_local_cache(
    *, fs: FirestoreClient, workspace_id: str, id_token: str
) -> None:
    workspace_id = str(workspace_id or "").strip()
    if not workspace_id:
        return
    try:
        from ..data.notifications_provider import JsonFileNotificationsProvider
        from ..models.notifications import (
            Notification,
            NotificationSeverity,
            NotificationStatus,
            NotificationType,
        )

        docs = fs.list_collection(
            collection_path=f"workspaces/{workspace_id}/notifications",
            id_token=id_token,
        )

        prov = JsonFileNotificationsProvider()
        local = list(prov.list_notifications())
        by_key = {n.key: n for n in local if getattr(n, "key", "")}

        for d in docs:
            try:
                doc_id, parsed = fs.parse_any_doc(d)
                nid = str(parsed.get("id") or "").strip() or str(doc_id or "").strip()
                key = str(parsed.get("key") or "").strip() or str(doc_id or "").strip()
                if not key:
                    continue

                status = NotificationStatus(str(parsed.get("status") or "unread"))
                existing = by_key.get(key)
                if existing is not None and existing.status in (
                    NotificationStatus.RESOLVED,
                    NotificationStatus.DISMISSED,
                ):
                    continue

                # If remote is resolved/dismissed, remove locally and skip.
                if status in (
                    NotificationStatus.RESOLVED,
                    NotificationStatus.DISMISSED,
                ):
                    if key in by_key:
                        by_key.pop(key, None)
                    continue

                notif = Notification(
                    id=nid or key,
                    key=key,
                    type=NotificationType(str(parsed.get("type") or "")),
                    title=str(parsed.get("title") or ""),
                    message=str(parsed.get("message") or ""),
                    severity=NotificationSeverity(
                        str(parsed.get("severity") or "info")
                    ),
                    created_at=str(parsed.get("created_at") or ""),
                    status=status,
                    due_at=str(parsed["due_at"])
                    if parsed.get("due_at") is not None
                    else None,
                    source=str(parsed.get("source") or "system"),
                    context=dict(parsed.get("context") or {}),
                )
                by_key[key] = notif
            except Exception:
                continue

        merged = list(by_key.values())
        merged.sort(key=lambda x: str(getattr(x, "created_at", "") or ""), reverse=True)
        prov.save_notifications(merged)
    except Exception:
        pass


def pull_notifications_meta_to_local_cache(
    *, fs: FirestoreClient, workspace_id: str, id_token: str
) -> None:
    workspace_id = str(workspace_id or "").strip()
    if not workspace_id:
        return
    try:
        from ..data.notifications_provider import JsonFileNotificationsProvider
        from ..models.notifications import NotificationRule, RuleType

        doc = fs.get_document(
            document_path=f"workspaces/{workspace_id}/meta/notifications",
            id_token=id_token,
        )
        _, parsed = fs.parse_any_doc(doc) if isinstance(doc, dict) else ("", {})
        enabled = bool(parsed.get("enabled", True))
        rules_raw = parsed.get("rules", []) or []
        rules: list[NotificationRule] = []
        if isinstance(rules_raw, list):
            for r in rules_raw:
                if not isinstance(r, dict):
                    continue
                try:
                    rules.append(
                        NotificationRule(
                            id=str(r.get("id", "") or ""),
                            type=RuleType(str(r.get("type", "") or "")),
                            enabled=bool(r.get("enabled", True)),
                            schedule=str(r.get("schedule", "daily") or "daily"),
                            params=dict(r.get("params", {}) or {}),
                        )
                    )
                except Exception:
                    continue
        prov = JsonFileNotificationsProvider()
        prov.set_enabled(bool(enabled))
        if rules:
            prov.save_rules(rules)
    except Exception:
        return


def pull_user_profile_to_local_cache(
    *, fs: FirestoreClient, workspace_id: str, uid: str, id_token: str
) -> None:
    workspace_id = str(workspace_id or "").strip()
    uid = str(uid or "").strip()
    if not workspace_id or not uid:
        return
    try:
        from ..utils.app_paths import user_profile_path
        import json

        doc = fs.get_document(
            document_path=f"workspaces/{workspace_id}/users/{uid}",
            id_token=id_token,
        )
        _, parsed = fs.parse_any_doc(doc) if isinstance(doc, dict) else ("", {})
        full_name = str(parsed.get("full_name", "") or "")
        lock_enabled = bool(parsed.get("lock_enabled", False))

        path = user_profile_path()
        local = {}
        if path.exists():
            try:
                local = json.loads(path.read_text(encoding="utf-8") or "{}")
            except Exception:
                local = {}
        if not isinstance(local, dict):
            local = {}
        if full_name:
            local["full_name"] = full_name
        local["lock_enabled"] = bool(lock_enabled)
        # Intentionally keep local-only: password, avatar_path.
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(local, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        return
