from __future__ import annotations

from typing import List

from .firebase_client import FirestoreClient


def pull_ml_seed_best_effort(*, workspace_id: str) -> None:
    if not str(workspace_id or "").strip():
        return
    try:
        from .workspace_ml_trainer import WorkspaceMLTrainer

        t = WorkspaceMLTrainer()
        t.pull_seed_to_cache()
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
        from ..models.one_time_event import OneTimeEvent, OneTimeEventStatus

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
                status_raw = str(
                    parsed.get("status") or OneTimeEventStatus.ACTIVE.value
                )
                try:
                    status = OneTimeEventStatus(status_raw)
                except Exception:
                    status = OneTimeEventStatus.ACTIVE
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
