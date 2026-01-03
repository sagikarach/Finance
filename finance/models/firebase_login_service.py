from __future__ import annotations

from dataclasses import dataclass

from .firebase_client import FirebaseAuthClient
from .firebase_session import FirebaseSession, FirebaseSessionStore
from ..utils.time_utils import now_ts


@dataclass
class FirebaseLoginService:
    session_store: FirebaseSessionStore = FirebaseSessionStore()

    def login_with_email_password(
        self,
        *,
        email: str,
        password: str,
        workspace_id: str = "",
    ) -> FirebaseSession:
        current = self.session_store.load()
        api_key = str(getattr(current, "api_key", "") or "").strip()
        project_id = str(getattr(current, "project_id", "") or "").strip()
        if not api_key or not project_id:
            raise RuntimeError("חובה להגדיר פרויקט (API key + project id) לפני התחברות")

        email = str(email or "").strip()
        password = str(password or "")
        if not email or not password:
            raise RuntimeError("חובה למלא אימייל וסיסמה")

        auth = FirebaseAuthClient(api_key=api_key)
        res = auth.sign_in_with_password(email=email, password=password)
        s = FirebaseSession(
            api_key=api_key,
            project_id=project_id,
            email=email,
            uid=res.uid,
            workspace_id=str(workspace_id or "").strip(),
            refresh_token=res.refresh_token,
            id_token=res.id_token,
            expires_at=now_ts() + float(res.expires_in),
        )
        self.session_store.save(s)

        try:
            from .firebase_movements_sync import FirebaseMovementsSyncService

            key = (
                str(getattr(s, "workspace_id", "") or "").strip()
                or str(res.uid or "").strip()
            )
            if key:
                FirebaseMovementsSyncService().ensure_user_local_file(key)
        except Exception:
            pass

        return s
