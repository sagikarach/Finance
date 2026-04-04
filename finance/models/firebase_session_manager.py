from __future__ import annotations

from dataclasses import dataclass

from .firebase_client import FirebaseAuthClient
from .firebase_session import FirebaseSession, FirebaseSessionStore
from ..utils.time_utils import now_ts


@dataclass
class FirebaseSessionManager:
    store: FirebaseSessionStore = FirebaseSessionStore()

    def get_valid_session(self) -> FirebaseSession:
        session = self.store.load()
        if not session.is_logged_in or not session.id_token:
            raise RuntimeError("Not logged in")

        if not session.is_id_token_valid():
            auth = FirebaseAuthClient(api_key=session.api_key)
            id_token, refresh_token, expires_in = auth.refresh_id_token(
                refresh_token=session.refresh_token
            )
            session.id_token = id_token
            session.refresh_token = refresh_token
            session.expires_at = now_ts() + float(expires_in)
            self.store.save(session)

        return session
