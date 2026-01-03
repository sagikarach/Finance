from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _sanitize_rows(raw: Any) -> Tuple[List[Dict[str, Any]], int]:
    if not isinstance(raw, list):
        return [], 0

    out: List[Dict[str, Any]] = []
    skipped = 0
    seen: set[tuple[str, float, str, str]] = set()

    for it in raw:
        if not isinstance(it, dict):
            skipped += 1
            continue

        desc = str(it.get("description", "") or "").strip()
        cat = str(it.get("category", "") or "").strip()
        if not desc or not cat:
            skipped += 1
            continue

        et = str(it.get("expenseType", "") or "חודשית").strip() or "חודשית"

        try:
            amt = float(it.get("amount", 0.0) or 0.0)
        except Exception:
            skipped += 1
            continue

        amt = float(abs(amt))
        key = (desc, round(amt, 2), cat, et)
        if key in seen:
            continue
        seen.add(key)

        out.append(
            {
                "description": desc,
                "amount": amt,
                "category": cat,
                "expenseType": et,
            }
        )

    return out, skipped


def main() -> int:
    if str(_REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(_REPO_ROOT))

    from finance.models.firebase_workspace_writer import FirebaseWorkspaceWriter
    from finance.models.firebase_session import FirebaseSessionStore

    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--file",
        default="data/expenses.json",
        help="Path to JSON list of training examples (default: data/expenses.json)",
    )
    args = ap.parse_args()

    session = FirebaseSessionStore().load()
    if not session.is_logged_in:
        raise SystemExit(
            "Not logged in. Open the desktop app, login to Firebase, and set/join a workspace first."
        )
    if not str(getattr(session, "workspace_id", "") or "").strip():
        raise SystemExit(
            "Workspace not set. Open the desktop app and join/create a workspace first."
        )

    p = Path(args.file)
    if not p.exists():
        raise SystemExit(f"File not found: {p}")

    raw = json.loads(p.read_text(encoding="utf-8"))
    examples, skipped = _sanitize_rows(raw)
    if not examples:
        raise SystemExit("No valid examples found to upload.")

    FirebaseWorkspaceWriter().upsert_ml_seed(examples=examples)
    print(f"Uploaded ml_seed examples: {len(examples)} (skipped {skipped})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
