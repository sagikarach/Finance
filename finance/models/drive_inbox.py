"""Drive-inbox importer: pull bank-statement files a Gmail rule dropped into a
Drive folder, and feed them through the normal expenses-import pipeline.

Once a file is imported it's trashed on Drive (recoverable ~30 days) so the
folder stays clean. A small local ledger also records imported file ids as a
fallback: if trashing ever fails, the ledger still stops a re-import. The ledger
and the configured folder id live in one JSON file under the accounts data dir
(so the sandbox override isolates them too).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Set
import json

from .google_drive_client import DriveFile, GoogleDriveClient
from .spreadsheet_reader import bytes_to_csv_text
from ..utils.app_paths import accounts_data_dir
from ..utils.logging_setup import get_logger

_log = get_logger(__name__)

# The expense file types the importer understands.
SUPPORTED_SUFFIXES = (".csv", ".xls", ".xlsx")

_STATE_FILENAME = "drive_inbox_state.json"


def _state_path() -> Path:
    return accounts_data_dir() / _STATE_FILENAME


@dataclass
class DriveInboxState:
    """Persisted config + import history for the Drive inbox."""

    folder_id: str = ""
    processed_ids: Set[str] = field(default_factory=set)

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "DriveInboxState":
        p = path or _state_path()
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cls()
        if not isinstance(data, dict):
            return cls()
        ids = data.get("processed_ids", [])
        return cls(
            folder_id=str(data.get("folder_id", "") or "").strip(),
            processed_ids={str(i) for i in ids if isinstance(i, (str, int))},
        )

    def save(self, path: Optional[Path] = None) -> None:
        p = path or _state_path()
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(
                json.dumps(
                    {
                        "folder_id": self.folder_id,
                        "processed_ids": sorted(self.processed_ids),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        except OSError as exc:
            _log.warning("could not save Drive inbox state: %s", exc)

    def is_processed(self, file_id: str) -> bool:
        return str(file_id) in self.processed_ids

    def mark_processed(self, file_id: str) -> None:
        self.processed_ids.add(str(file_id))


def is_supported(file: DriveFile) -> bool:
    return file.suffix in SUPPORTED_SUFFIXES


@dataclass
class DriveInboxService:
    """Lists and reads statement files from the configured Drive folder.

    Applying the expenses to an account (with the classify/review flow) is the
    caller's job — this service only surfaces *what* to import and remembers
    *what has been* imported.
    """

    client: GoogleDriveClient
    state: DriveInboxState

    def pending_files(self, folder_id: Optional[str] = None) -> List[DriveFile]:
        """Supported statement files in the folder that haven't been imported yet,
        oldest first."""
        fid = str(folder_id or self.state.folder_id or "").strip()
        if not fid:
            return []
        files = [
            f
            for f in self.client.list_folder(fid)
            if is_supported(f) and not self.state.is_processed(f.id)
        ]
        return files

    def csv_text_for(self, file: DriveFile) -> str:
        """Download a Drive file and normalize it to CSV text for the parser."""
        raw = self.client.download(file.id)
        return bytes_to_csv_text(raw, suffix=file.suffix)

    def complete_import(self, file: DriveFile, *, delete: bool = True) -> None:
        """Finish a file: record it in the ledger and (by default) trash it on
        Drive so the folder stays clean. Trashing is best-effort — if it fails,
        the ledger still prevents a re-import."""
        self.state.mark_processed(file.id)
        self.state.save()
        if delete:
            try:
                self.client.trash(file.id)
            except Exception as exc:  # noqa: BLE001 - trashing is best-effort
                _log.warning("could not trash Drive file %s: %s", file.name, exc)
