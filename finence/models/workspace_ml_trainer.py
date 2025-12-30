from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import json

from ..utils.app_paths import app_data_dir
from .bank_movement import BankMovement, MovementType
from .firebase_session import FirebaseSessionStore
from .firebase_client import FirestoreClient
from .firebase_session_manager import FirebaseSessionManager
from .movement_classifier import SimilarityBasedClassifier


def _training_dir() -> Path:
    p = app_data_dir() / "training"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _seed_cache_path(key: str) -> Path:
    key = str(key or "").strip()
    suffix = f"_{key}" if key else ""
    return _training_dir() / f"ml_seed{suffix}.json"


def _seed_from_repo_file() -> List[Dict[str, Any]]:
    p = Path.cwd() / "data" / "expenses.json"
    if not p.exists():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
    except Exception:
        return []
    return []


def _movement_to_training_row(m: BankMovement) -> Optional[Dict[str, Any]]:
    try:
        desc = str(m.description or "").strip()
        cat = str(m.category or "").strip()
        if not desc or not cat:
            return None
        if cat in ("שונות", "אחר", "אחרים"):
            return None
        if float(m.amount) >= 0:
            return None
        mt = m.type
        type_mapping = {
            MovementType.MONTHLY: "חודשית",
            MovementType.YEARLY: "שנתית",
            MovementType.ONE_TIME: "חד פעמי",
        }
        expense_type_str = type_mapping.get(mt, "חודשית")
        return {
            "description": desc,
            "amount": float(abs(float(m.amount))),
            "category": cat,
            "expenseType": expense_type_str,
            "source": "history",
        }
    except Exception:
        return None


@dataclass
class WorkspaceMLTrainer:
    def _session(self):
        try:
            s = FirebaseSessionManager(store=FirebaseSessionStore()).get_valid_session()
        except Exception:
            return None
        wid = str(getattr(s, "workspace_id", "") or "").strip()
        if not wid:
            return None
        return s

    def pull_seed_to_cache(self) -> None:
        s = self._session()
        if s is None:
            return
        wid = str(getattr(s, "workspace_id", "") or "").strip()
        fs = FirestoreClient(project_id=s.project_id)
        try:
            doc = fs.get_document(
                document_path=f"workspaces/{wid}/meta/ml_seed", id_token=s.id_token
            )
            _id, parsed = fs.parse_any_doc(doc) if isinstance(doc, dict) else ("", {})
            raw = parsed.get("examples", [])
            if not isinstance(raw, list):
                raw = []
            cleaned: List[Dict[str, Any]] = []
            for it in raw:
                if isinstance(it, dict):
                    cleaned.append(it)
            _seed_cache_path(wid).write_text(
                json.dumps(cleaned, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception:
            pass

    def ensure_seed_in_firebase(self) -> None:
        s = self._session()
        if s is None:
            return
        wid = str(getattr(s, "workspace_id", "") or "").strip()
        fs = FirestoreClient(project_id=s.project_id)

        try:
            fs.get_document(
                document_path=f"workspaces/{wid}/meta/ml_seed", id_token=s.id_token
            )
            return
        except Exception:
            pass

        seed = _seed_from_repo_file()
        if not seed:
            return
        try:
            fs.upsert_document(
                document_path=f"workspaces/{wid}/meta/ml_seed",
                id_token=s.id_token,
                fields={"examples": seed, "version": 1},
            )
        except Exception:
            pass

    def _load_seed_cached_or_default(self) -> List[Dict[str, Any]]:
        s = FirebaseSessionStore().load()
        wid = str(getattr(s, "workspace_id", "") or "").strip()
        key = wid or str(getattr(s, "uid", "") or "").strip()
        p = _seed_cache_path(key)
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return [x for x in data if isinstance(x, dict)]
            except Exception:
                pass
        return _seed_from_repo_file()

    def rebuild_training_file(
        self,
        *,
        movements: List[BankMovement],
        classifier: SimilarityBasedClassifier,
    ) -> Tuple[int, int]:
        seed = self._load_seed_cached_or_default()
        seed_rows: List[Dict[str, Any]] = []
        for it in seed:
            try:
                desc = str(it.get("description", "") or "").strip()
                cat = str(it.get("category", "") or "").strip()
                if not desc or not cat:
                    continue
                amt = it.get("amount", 0.0)
                try:
                    amt_f = float(abs(float(amt)))
                except Exception:
                    amt_f = 0.0
                et = str(it.get("expenseType", "חודשית") or "חודשית")
                seed_rows.append(
                    {
                        "description": desc,
                        "amount": amt_f,
                        "category": cat,
                        "expenseType": et,
                        "source": "seed",
                    }
                )
            except Exception:
                continue

        history_rows: List[Dict[str, Any]] = []
        for m in movements:
            row = _movement_to_training_row(m)
            if row is not None:
                history_rows.append(row)

        combined = seed_rows + history_rows
        classifier.set_training_data(combined)
        return len(seed_rows), len(history_rows)
