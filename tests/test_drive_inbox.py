import json

import pytest

from finance.models.drive_inbox import (
    DriveInboxService,
    DriveInboxState,
    is_supported,
)
from finance.models.google_drive_client import (
    DriveError,
    DriveFile,
    GoogleDriveClient,
)


# ── a fake Drive: an in-memory transport driven by (method, url) ──────────────
class FakeDrive:
    def __init__(self, files):
        # files: list of dicts with id/name + raw bytes payloads
        self._meta = [
            {
                "id": f["id"],
                "name": f["name"],
                "mimeType": f.get("mimeType", ""),
                "modifiedTime": f.get("modifiedTime", ""),
                "size": str(len(f.get("raw", b""))),
            }
            for f in files
        ]
        self._raw = {f["id"]: f.get("raw", b"") for f in files}
        self.trashed = []

    def transport(self, method, url, headers, body):
        assert headers.get("Authorization") == "Bearer tok"
        if method == "GET" and "alt=media" in url:
            fid = url.split("/files/")[1].split("?")[0]
            return 200, self._raw.get(fid, b"")
        if method == "GET":
            return 200, json.dumps({"files": self._meta}).encode()
        if method == "PATCH":
            fid = url.split("/files/")[1].split("?")[0]
            self.trashed.append(fid)
            return 200, json.dumps({"id": fid, "trashed": True}).encode()
        return 404, b"{}"


def _client(fake):
    return GoogleDriveClient(token_provider=lambda: "tok", transport=fake.transport)


def test_is_supported_by_extension():
    assert is_supported(DriveFile(id="1", name="x.xlsx"))
    assert is_supported(DriveFile(id="2", name="x.CSV"))
    assert is_supported(DriveFile(id="3", name="x.xls"))
    assert not is_supported(DriveFile(id="4", name="x.pdf"))
    assert not is_supported(DriveFile(id="5", name="noext"))


def test_list_folder_maps_fields():
    fake = FakeDrive([{"id": "a", "name": "leumi.xls", "raw": b"<html></html>"}])
    files = _client(fake).list_folder("FOLDER")
    assert files[0].id == "a" and files[0].name == "leumi.xls"
    assert files[0].size == len(b"<html></html>")


def test_missing_token_raises():
    c = GoogleDriveClient(token_provider=lambda: "", transport=FakeDrive([]).transport)
    with pytest.raises(DriveError):
        c.list_folder("FOLDER")


def test_pending_excludes_unsupported_and_already_processed(tmp_path):
    fake = FakeDrive([
        {"id": "a", "name": "jan.csv", "raw": b"h\n"},
        {"id": "b", "name": "note.pdf", "raw": b"%PDF"},
        {"id": "c", "name": "feb.xlsx", "raw": b"PK\x03\x04"},
    ])
    state = DriveInboxState(folder_id="FOLDER", processed_ids={"c"})
    svc = DriveInboxService(client=_client(fake), state=state)

    pending = svc.pending_files()
    assert [f.name for f in pending] == ["jan.csv"]  # pdf skipped, feb already done


def test_csv_text_for_downloads_and_parses_html_xls():
    # A Leumi-style HTML table saved as .xls, fetched from Drive.
    html = (
        "<table><tr><th>תאריך העסקה</th>"
        "<th>שם בית העסק</th>"
        "<th>סכום חיוב</th></tr>"
        "<tr><td>16/07/2026</td><td>רמי לוי</td><td>50.00</td></tr>"
        "</table>"
    )
    fake = FakeDrive([{"id": "a", "name": "leumi.xls", "raw": html.encode()}])
    svc = DriveInboxService(
        client=_client(fake), state=DriveInboxState(folder_id="FOLDER")
    )
    text = svc.csv_text_for(DriveFile(id="a", name="leumi.xls"))
    assert "16/07/2026" in text and "50.00" in text


def test_complete_import_records_ledger_and_trashes(tmp_path):
    fake = FakeDrive([{"id": "a", "name": "jan.csv", "raw": b"h\n"}])
    state = DriveInboxState(folder_id="FOLDER")
    svc = DriveInboxService(client=_client(fake), state=state)

    f = DriveFile(id="a", name="jan.csv")
    svc.complete_import(f)

    assert state.is_processed("a")
    assert fake.trashed == ["a"]  # trashed on Drive
    # And it no longer shows as pending.
    assert svc.pending_files() == []


def test_complete_import_without_delete_keeps_file(tmp_path):
    fake = FakeDrive([{"id": "a", "name": "jan.csv", "raw": b"h\n"}])
    svc = DriveInboxService(
        client=_client(fake), state=DriveInboxState(folder_id="FOLDER")
    )
    svc.complete_import(DriveFile(id="a", name="jan.csv"), delete=False)
    assert fake.trashed == []


def test_state_round_trips_through_disk(tmp_path):
    p = tmp_path / "drive_inbox_state.json"
    DriveInboxState(folder_id="FID", processed_ids={"x", "y"}).save(p)
    loaded = DriveInboxState.load(p)
    assert loaded.folder_id == "FID"
    assert loaded.processed_ids == {"x", "y"}


def test_state_load_tolerates_missing_or_bad_file(tmp_path):
    assert DriveInboxState.load(tmp_path / "nope.json").folder_id == ""
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    assert DriveInboxState.load(bad).processed_ids == set()
