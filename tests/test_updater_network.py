"""Update check networking: a GitHub hiccup is retried once, and an HTTP
error is never mistaken for "no releases published"."""

from __future__ import annotations

import subprocess
import sys

import pytest

from finance.utils import updater


def _fake_once(outcomes):
    calls = []

    def once(url, timeout):
        calls.append(url)
        item = outcomes.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return once, calls


def test_server_error_then_success_is_retried(monkeypatch):
    once, calls = _fake_once([updater._HttpStatusError(504), b"[]"])
    monkeypatch.setattr(updater, "_http_get_once", once)
    assert updater._http_get("https://x") == b"[]"
    assert len(calls) == 2


def test_timeouts_give_up_after_one_retry(monkeypatch):
    err = RuntimeError("curl error 28: ")
    once, calls = _fake_once([err, err, b"never"])
    monkeypatch.setattr(updater, "_http_get_once", once)
    with pytest.raises(RuntimeError, match="curl error 28"):
        updater._http_get("https://x")
    assert len(calls) == 2


def test_permanent_errors_are_not_retried(monkeypatch):
    once, calls = _fake_once([RuntimeError("curl error 6: bad host"), b"never"])
    monkeypatch.setattr(updater, "_http_get_once", once)
    with pytest.raises(RuntimeError):
        updater._http_get("https://x")
    assert len(calls) == 1


def test_only_404_means_no_release(monkeypatch):
    monkeypatch.setattr(updater, "_http_get_once",
                        _fake_once([updater._HttpStatusError(404)])[0])
    with pytest.raises(updater._NoReleaseFound):
        updater._github_latest_release("o/r")
    monkeypatch.setattr(updater, "_http_get_once",
                        _fake_once([updater._HttpStatusError(504)] * 2)[0])
    with pytest.raises(updater._HttpStatusError):  # an outage is an error, not "up to date"
        updater._github_latest_release("o/r")


def test_curl_status_code_is_parsed(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")

    def run(args, capture_output, timeout):
        body = b'{"ok": 1}' if "good" in args[-1] else b"<html>Unicorn</html>"
        status = b"200" if "good" in args[-1] else b"504"
        return subprocess.CompletedProcess(args, 0, body + b"\n__HTTP_STATUS__:" + status, b"")

    monkeypatch.setattr(subprocess, "run", run)
    assert updater._http_get_once("https://good", 5) == b'{"ok": 1}'
    with pytest.raises(updater._HttpStatusError) as info:
        updater._http_get_once("https://bad", 5)
    assert info.value.status == 504
