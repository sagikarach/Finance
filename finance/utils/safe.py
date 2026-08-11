"""A discoverable replacement for ``try: ... except Exception: pass``.

The bare idiom silences *every* error, so real bugs (a latent corruption, a
shadowed style) hide next to the expected best-effort failures. ``swallow`` keeps
the graceful degradation but routes the exception through the logger, and lets
callers narrow the caught types — so a logic error of the wrong type still
propagates. Flip ``FINANCE_LOG_LEVEL=DEBUG`` and everything swallowed surfaces.
"""

from __future__ import annotations

import functools
import logging
from contextlib import contextmanager
from typing import Callable, Iterator, Type, TypeVar

_log = logging.getLogger("finance.safe")

_T = TypeVar("_T")

# Exceptions expected when parsing untrusted on-disk / remote data into models.
# Catch these for resilience; anything else is a bug and should propagate.
PARSE_ERRORS: tuple[type[Exception], ...] = (
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
    IndexError,
)

# Exceptions a Qt widget call realistically raises: a wrapped C++ object already
# deleted (RuntimeError), a missing/None widget (AttributeError), a bad argument
# (TypeError/ValueError), or a stale index/key. Catch these at the Qt boundary so
# a truly unexpected error (SystemExit, MemoryError, KeyboardInterrupt) still
# propagates instead of vanishing.
QT_ERRORS: tuple[type[Exception], ...] = (
    RuntimeError,
    AttributeError,
    TypeError,
    ValueError,
    KeyError,
    IndexError,
    OSError,
)


@contextmanager
def swallow(
    *exc_types: Type[BaseException],
    msg: str = "",
    level: int = logging.DEBUG,
) -> Iterator[None]:
    """Run a block, logging and suppressing the given exception types.

    Defaults to ``Exception`` when no types are given, but prefer naming the
    specific types you expect (e.g. ``swallow(RuntimeError)`` for a possibly-deleted
    Qt object) so unexpected errors keep propagating.
    """
    types: tuple[Type[BaseException], ...] = exc_types or (Exception,)
    try:
        yield
    except types as exc:
        _log.log(level, "swallowed %s: %s", msg or type(exc).__name__, exc, exc_info=True)


def best_effort(
    *exc_types: Type[BaseException],
    msg: str = "",
    level: int = logging.DEBUG,
) -> Callable[[Callable[..., _T]], Callable[..., _T | None]]:
    """Decorator form of :func:`swallow`: the wrapped function returns ``None``
    instead of raising one of ``exc_types``."""

    def decorator(fn: Callable[..., _T]) -> Callable[..., _T | None]:
        @functools.wraps(fn)
        def wrapper(*args: object, **kwargs: object) -> _T | None:
            with swallow(*exc_types, msg=msg or fn.__name__, level=level):
                return fn(*args, **kwargs)
            return None

        return wrapper

    return decorator
