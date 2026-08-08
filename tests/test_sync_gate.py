"""The push safety gate: the app only writes to Firebase inside an explicit
Sync action. These lock that policy so a stray background write can't slip out."""

from finance.models.sync_gate import allow_firebase_push, is_syncing, sync_context


def test_push_blocked_by_default():
    assert is_syncing() is False
    assert allow_firebase_push() is False


def test_push_allowed_only_inside_sync_context():
    with sync_context():
        assert allow_firebase_push() is True
    assert allow_firebase_push() is False  # restored on exit


def test_nested_sync_context_restores_previous_state():
    with sync_context():
        with sync_context():
            assert allow_firebase_push() is True
        # leaving the inner context keeps us inside the outer one
        assert allow_firebase_push() is True
    assert allow_firebase_push() is False
