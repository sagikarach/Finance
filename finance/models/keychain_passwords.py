from __future__ import annotations

import subprocess
from typing import Optional


SERVICE_NAME = "Finance"


def _run_security(args: list[str]) -> subprocess.CompletedProcess:
    """
    Uses macOS `security` CLI. This will prompt the user if Keychain access requires it.
    """
    return subprocess.run(
        ["security", *args],
        check=True,
        capture_output=True,
        text=True,
    )


def set_password(*, account: str, password: str, service: str = SERVICE_NAME) -> None:
    account = str(account or "").strip()
    if not account:
        return
    password = str(password or "")
    # -U updates item if it exists
    _run_security(
        ["add-generic-password", "-U", "-a", account, "-s", service, "-w", password]
    )


def get_password(*, account: str, service: str = SERVICE_NAME) -> Optional[str]:
    account = str(account or "").strip()
    if not account:
        return None
    try:
        res = _run_security(
            ["find-generic-password", "-a", account, "-s", service, "-w"]
        )
        pw = (res.stdout or "").rstrip("\n")
        return pw if pw else None
    except Exception:
        return None


def delete_password(*, account: str, service: str = SERVICE_NAME) -> None:
    account = str(account or "").strip()
    if not account:
        return
    try:
        _run_security(["delete-generic-password", "-a", account, "-s", service])
    except Exception:
        return
