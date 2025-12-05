from __future__ import annotations

from .base import (
    load_base_light_styles as _load_base_light,
    load_base_dark_styles as _load_base_dark,
)
from .menus import load_menus_light_styles, load_menus_dark_styles
from .typography import load_typography_light_styles, load_typography_dark_styles
from .cards import load_cards_light_styles, load_cards_dark_styles
from .sidebar import load_sidebar_light_styles, load_sidebar_dark_styles
from .buttons import load_buttons_light_styles, load_buttons_dark_styles
from .date_picker import load_date_picker_light_styles, load_date_picker_dark_styles


def load_base_light_styles() -> str:
    return (
        _load_base_light()
        + load_menus_light_styles()
        + load_typography_light_styles()
        + load_cards_light_styles()
        + load_sidebar_light_styles()
        + load_buttons_light_styles()
        + load_date_picker_light_styles()
    )


def load_base_dark_styles() -> str:
    return (
        _load_base_dark()
        + load_menus_dark_styles()
        + load_typography_dark_styles()
        + load_cards_dark_styles()
        + load_sidebar_dark_styles()
        + load_buttons_dark_styles()
        + load_date_picker_dark_styles()
    )
