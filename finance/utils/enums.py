from __future__ import annotations

from enum import Enum
from typing import Any, Mapping, Optional, Type, TypeVar

E = TypeVar("E", bound=Enum)


def coerce_enum(
    enum_cls: Type[E],
    value: Any,
    default: E,
    *,
    aliases: Optional[Mapping[str, E]] = None,
) -> E:
    """Coerce ``value`` (usually a raw string from JSON) into a member of
    ``enum_cls``, falling back to ``default`` when it is ``None`` or not a
    recognized value. ``aliases`` maps legacy/alternate strings to a member and
    is consulted before the plain enum lookup (e.g. a renamed historical value).
    """
    if value is None:
        return default
    key = str(value)
    if aliases and key in aliases:
        return aliases[key]
    try:
        return enum_cls(key)
    except (ValueError, KeyError):
        return default
