from __future__ import annotations

from dataclasses import dataclass

from .firebase_client import FirestoreClient
from .firebase_session import FirebaseSessionStore
from .firebase_session_manager import FirebaseSessionManager


@dataclass
class FirebaseWorkspaceService:
    session_store: FirebaseSessionStore = FirebaseSessionStore()

    def _load_session_refresh_if_needed(self):
        return FirebaseSessionManager(store=self.session_store).get_valid_session()

    def _fs(self, project_id: str) -> FirestoreClient:
        return FirestoreClient(project_id=project_id)

    def validate_workspace_exists(self, *, workspace_id: str) -> None:
        workspace_id = str(workspace_id or "").strip()
        if not workspace_id:
            raise RuntimeError("Workspace ID is empty")
        s = self._load_session_refresh_if_needed()
        fs = self._fs(s.project_id)
        fs.get_document(document_path=f"workspaces/{workspace_id}", id_token=s.id_token)

    def create_workspace(self, *, workspace_id: str, name: str = "Workspace") -> None:
        workspace_id = str(workspace_id or "").strip()
        if not workspace_id:
            raise RuntimeError("Workspace ID is empty")

        s = self._load_session_refresh_if_needed()
        fs = self._fs(s.project_id)

        fs.upsert_document(
            document_path=f"workspaces/{workspace_id}",
            id_token=s.id_token,
            fields={"created_by": s.uid, "name": name, "version": 1},
        )
        fs.upsert_document(
            document_path=f"workspaces/{workspace_id}/members/{s.uid}",
            id_token=s.id_token,
            fields={"role": "owner"},
        )
        fs.upsert_document(
            document_path=f"users/{s.uid}",
            id_token=s.id_token,
            fields={"active_workspace_id": workspace_id},
        )

        s.workspace_id = workspace_id
        self.session_store.save(s)

    def join_workspace(self, *, workspace_id: str, role: str = "editor") -> None:
        workspace_id = str(workspace_id or "").strip()
        if not workspace_id:
            raise RuntimeError("Workspace ID is empty")

        s = self._load_session_refresh_if_needed()
        fs = self._fs(s.project_id)

        fs.get_document(document_path=f"workspaces/{workspace_id}", id_token=s.id_token)

        fs.upsert_document(
            document_path=f"workspaces/{workspace_id}/members/{s.uid}",
            id_token=s.id_token,
            fields={"role": str(role or "editor")},
        )
        fs.upsert_document(
            document_path=f"users/{s.uid}",
            id_token=s.id_token,
            fields={"active_workspace_id": workspace_id},
        )

        s.workspace_id = workspace_id
        self.session_store.save(s)

    def disconnect_workspace_local(self) -> None:
        s = self.session_store.load()
        if not s.is_logged_in:
            return
        s.workspace_id = ""
        self.session_store.save(s)
