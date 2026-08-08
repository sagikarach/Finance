"""Central logging configuration.

Without a configured sink, replacing ``except Exception: pass`` with logging
would be meaningless — the records would go nowhere. This wires a console
handler plus a rotating file in the app-data dir, so swallowed-but-logged
errors (see :mod:`finance.utils.safe`) are actually discoverable.

Level comes from the ``FINANCE_LOG_LEVEL`` env var (default ``INFO``); set it to
``DEBUG`` to surface everything the ``swallow`` helper catches.
"""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler

_CONFIGURED = False

_FORMAT = "%(asctime)s %(levelname)s %(name)s: %(message)s"


def setup_logging(*, force: bool = False) -> None:
    """Configure the ``finance`` logger tree once. Idempotent unless ``force``."""
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    level_name = str(os.environ.get("FINANCE_LOG_LEVEL", "INFO")).upper()
    level = getattr(logging, level_name, logging.INFO)

    root = logging.getLogger("finance")
    root.setLevel(level)
    for h in list(root.handlers):
        root.removeHandler(h)

    fmt = logging.Formatter(_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(fmt)
    root.addHandler(console)

    # File logging is best-effort: if the app-data dir is unavailable we still
    # have the console handler. Narrow to OSError so a real bug here isn't hidden.
    try:
        from .app_paths import app_data_dir

        log_dir = app_data_dir() / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            log_dir / "finance.log",
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)
    except OSError:
        root.warning("file logging unavailable; console only", exc_info=True)

    root.propagate = False
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """A namespaced child of the ``finance`` logger (e.g. ``get_logger('data')``)."""
    name = str(name or "").strip()
    if not name or name == "finance":
        return logging.getLogger("finance")
    return logging.getLogger(name if name.startswith("finance.") else f"finance.{name}")
