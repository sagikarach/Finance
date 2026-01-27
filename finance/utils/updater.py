from __future__ import annotations

import base64
import json
import os
import pathlib
import shutil
import tempfile
import urllib.request
from typing import Optional, Tuple

from nacl.signing import VerifyKey

from ..__version__ import __version__
from ..appcast_key import PUBLIC_KEY_B64

PUBLIC_KEY_ENV = "FINANCE_ED25519_PUBKEY"
DEFAULT_PUBLIC_KEY = PUBLIC_KEY_B64


def _parse_version(v: str) -> Tuple[int, ...]:
    """Convert semantic-ish version string to tuple of ints for comparison."""
    v = v.lstrip("v").strip()
    parts = []
    for part in v.split("."):
        try:
            parts.append(int(part))
        except Exception:
            parts.append(0)
    return tuple(parts)


def _is_newer(latest: str, current: str) -> bool:
    return _parse_version(latest) > _parse_version(current)


def _github_latest_release(repo: str) -> dict:
    url = f"https://api.github.com/repos/{repo}/releases/latest"
    with urllib.request.urlopen(url) as resp:
        return json.load(resp)


def _find_asset(release: dict, name: str) -> Optional[dict]:
    for asset in release.get("assets", []) or []:
        if asset.get("name") == name:
            return asset
    return None


def _download(url: str, dest_path: pathlib.Path) -> pathlib.Path:
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as resp, open(dest_path, "wb") as fh:
        fh.write(resp.read())
    return dest_path


def _get_public_key() -> Optional[VerifyKey]:
    raw = os.environ.get(PUBLIC_KEY_ENV, DEFAULT_PUBLIC_KEY)
    if not raw:
        return None
    try:
        data = base64.b64decode(raw.strip())
        return VerifyKey(data)
    except Exception:
        return None


def _verify_signature(path: pathlib.Path, signature_b64: str) -> Optional[str]:
    vk = _get_public_key()
    if not vk:
        return "Missing or invalid public key for update verification."
    try:
        sig = base64.b64decode(signature_b64)
        vk.verify(path.read_bytes(), sig)
        return None
    except Exception as exc:  # noqa: BLE001
        return f"Signature verification failed: {exc}"


def _extract_zip(zip_path: pathlib.Path, dest_dir: pathlib.Path) -> pathlib.Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.unpack_archive(str(zip_path), str(dest_dir))
    return dest_dir


def check_for_updates_mac(repo: Optional[str] = None) -> Tuple[bool, str, Optional[pathlib.Path], Optional[str]]:
    """
    Check GitHub Releases for a newer macOS build.

    Returns: (is_update_available, latest_version, extracted_app_path or None, error_message or None)
    """
    repo = repo or os.environ.get("FINANCE_UPDATE_REPO", "sagikarach/Finance")
    try:
        release = _github_latest_release(repo)
        latest_tag = str(release.get("tag_name", "")).lstrip("v")

        appcast_asset = _find_asset(release, "appcast.json")
        if not appcast_asset:
            return False, latest_tag, None, "No appcast.json found in latest release."

        with urllib.request.urlopen(appcast_asset["browser_download_url"]) as resp:
            appcast = json.load(resp)

        latest_version = str(appcast.get("version", latest_tag)).lstrip("v")
        if not _is_newer(latest_version, __version__):
            return False, latest_version, None, None

        zip_url = appcast.get("url")
        sig = appcast.get("signature")
        if not zip_url or not sig:
            return False, latest_version, None, "Appcast missing url or signature."

        zip_dest = pathlib.Path(tempfile.gettempdir()) / "Finance-mac-latest.zip"
        _download(zip_url, zip_dest)

        sig_error = _verify_signature(zip_dest, sig)
        if sig_error:
            return False, latest_version, None, sig_error

        extract_dir = pathlib.Path(tempfile.mkdtemp(prefix="finance-update-"))
        extracted = _extract_zip(zip_dest, extract_dir)
        return True, latest_version, extracted, None
    except Exception as exc:  # noqa: BLE001
        return False, "", None, f"Update check failed: {exc}"

