from __future__ import annotations

from dataclasses import dataclass
import json
import re
import urllib.request
from typing import Optional, Tuple


def _parse_semver(s: str) -> Optional[Tuple[int, int, int]]:
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", s)
    if not m:
        return None
    try:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    except Exception:
        return None


@dataclass(frozen=True)
class UpdateInfo:
    version: str
    html_url: str
    name: str
    body: str


class UpdateService:
    def __init__(self, *, repo: str) -> None:
        self._repo = repo.strip()

    def latest_release(self) -> Optional[UpdateInfo]:
        if not self._repo:
            return None
        url = f"https://api.github.com/repos/{self._repo}/releases/latest"
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "Finance",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=6) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
        except Exception:
            return None
        if not isinstance(data, dict):
            return None

        tag = str(data.get("tag_name", "") or "")
        html = str(data.get("html_url", "") or "")
        name = str(data.get("name", "") or tag)
        body = str(data.get("body", "") or "")
        if not tag or not html:
            return None
        return UpdateInfo(version=tag, html_url=html, name=name, body=body)

    @staticmethod
    def is_newer(*, current: str, latest: str) -> bool:
        c = _parse_semver(current) or (0, 0, 0)
        latest_v = _parse_semver(latest) or (0, 0, 0)
        return latest_v > c
