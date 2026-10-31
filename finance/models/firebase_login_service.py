from __future__ import annotations

from dataclasses import dataclass, field

from .firebase_client import FirebaseAuthClient, FirestoreClient
from .firebase_workspace_membership import (
    create_workspace,
    ensure_workspace_membership,
    get_active_workspace_id,
    join_workspace,
    set_active_workspace_id,
)
from .firebase_session import FirebaseSession, FirebaseSessionStore
from ..utils.time_utils import now_ts
from ..firebase_defaults import API_KEY as DEFAULT_API_KEY, PROJECT_ID as DEFAULT_PROJECT_ID
from ..utils.safe import swallow


def _last_local_workspace_for(email: str) -> str:
    """Budget this email last used on this computer (older desktop versions
    never stored the active budget in the cloud)."""
    try:
        from .firebase_workspace_profiles import FirebaseWorkspaceProfilesStore

        e = str(email or "").strip().casefold()
        for p in FirebaseWorkspaceProfilesStore().list_profiles():  # newest first
            if str(p.email or "").strip().casefold() == e and p.workspace_id:
                return str(p.workspace_id).strip()
    except (ImportError, OSError, ValueError, AttributeError):
        return ""
    return ""


@dataclass
class OnboardingResult:
    session: FirebaseSession
    created_workspace: bool  # a brand-new, empty budget was made for this account
    joined_workspace: bool  # joined someone else's budget via a share code


@dataclass
class FirebaseLoginService:
    session_store: FirebaseSessionStore = field(default_factory=FirebaseSessionStore)

    def _project(self) -> tuple[str, str]:
        current = self.session_store.load()
        api_key = str(getattr(current, "api_key", "") or "").strip()
        project_id = str(getattr(current, "project_id", "") or "").strip()
        if not api_key:
            api_key = str(DEFAULT_API_KEY or "").strip()
        if not project_id:
            project_id = str(DEFAULT_PROJECT_ID or "").strip()
        if not api_key or not project_id:
            raise RuntimeError("חובה להגדיר פרויקט (API key + project id) לפני התחברות")
        return api_key, project_id

    def sign_in_or_up(
        self,
        *,
        email: str,
        password: str,
        create_account: bool,
        share_code: str = "",
    ) -> OnboardingResult:
        """The whole new-user / returning-user flow in one call — nothing for
        the user to figure out:

        1. sign in (or create the Firebase account),
        2. pick the budget: the share code if given, else the one this account
           last used (shared with mobile), else create a fresh private one,
        3. remember it as the account's active budget and save the session.
        """
        api_key, project_id = self._project()
        email = str(email or "").strip()
        password = str(password or "")
        if not email or not password:
            raise RuntimeError("חובה למלא אימייל וסיסמה")

        auth = FirebaseAuthClient(api_key=api_key)
        if create_account:
            res = auth.sign_up_with_password(email=email, password=password)
        else:
            res = auth.sign_in_with_password(email=email, password=password)

        fs = FirestoreClient(project_id=project_id)
        created = joined = False
        code = str(share_code or "").strip()
        if code:
            wid = join_workspace(
                fs=fs, project_id=project_id, workspace_id=code,
                uid=res.uid, id_token=res.id_token,
            )
            joined = True
        else:
            wid = "" if create_account else (
                get_active_workspace_id(fs, uid=res.uid, id_token=res.id_token)
                or _last_local_workspace_for(email)
            )
            if wid:
                ensure_workspace_membership(
                    fs=fs, project_id=project_id, workspace_id=wid,
                    uid=res.uid, id_token=res.id_token,
                )
            else:
                wid = create_workspace(
                    fs=fs, project_id=project_id, uid=res.uid, id_token=res.id_token
                )
                created = True
        set_active_workspace_id(fs, uid=res.uid, workspace_id=wid, id_token=res.id_token)

        s = FirebaseSession(
            api_key=api_key,
            project_id=project_id,
            email=email,
            uid=res.uid,
            workspace_id=wid,
            refresh_token=res.refresh_token,
            id_token=res.id_token,
            expires_at=now_ts() + float(res.expires_in),
        )
        self.session_store.save(s)
        return OnboardingResult(session=s, created_workspace=created, joined_workspace=joined)

    def send_password_reset(self, *, email: str) -> None:
        api_key, _ = self._project()
        email = str(email or "").strip()
        if not email:
            raise RuntimeError("הזן את האימייל שלך כדי לאפס סיסמה")
        FirebaseAuthClient(api_key=api_key).send_password_reset_email(email=email)

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
        if not api_key:
            api_key = str(DEFAULT_API_KEY or "").strip()
        if not project_id:
            project_id = str(DEFAULT_PROJECT_ID or "").strip()
        if not api_key or not project_id:
            raise RuntimeError("חובה להגדיר פרויקט (API key + project id) לפני התחברות")

        email = str(email or "").strip()
        password = str(password or "")
        if not email or not password:
            raise RuntimeError("חובה למלא אימייל וסיסמה")

        auth = FirebaseAuthClient(api_key=api_key)
        res = auth.sign_in_with_password(email=email, password=password)

        wid = str(workspace_id or "").strip()
        if wid:
            # Join (or create) the workspace before switching to it, so an
            # account the server refuses never becomes the active session.
            try:
                ensure_workspace_membership(
                    fs=FirestoreClient(project_id=project_id),
                    project_id=project_id,
                    workspace_id=wid,
                    uid=res.uid,
                    id_token=res.id_token,
                )
            except RuntimeError as exc:
                if "PERMISSION_DENIED" in str(exc):
                    raise RuntimeError("אין לחשבון הזה גישה ל-Workspace הזה") from exc
                raise
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

        with swallow(msg="login_with_email_password"):
            from .firebase_movements_sync import FirebaseMovementsSyncService

            key = (
                str(getattr(s, "workspace_id", "") or "").strip()
                or str(res.uid or "").strip()
            )
            if key:
                FirebaseMovementsSyncService().ensure_user_local_file(key)

        return s
