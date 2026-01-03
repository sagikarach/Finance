from __future__ import annotations

from .base_theme import load_base_light_styles, load_base_dark_styles
from .home_page_theme import load_home_page_light_styles, load_home_page_dark_styles
from .settings_page_theme import (
    load_settings_page_light_styles,
    load_settings_page_dark_styles,
)
from .savings_page_theme import (
    load_savings_page_light_styles,
    load_savings_page_dark_styles,
)


def load_default_stylesheet() -> str:
    return (
        load_base_light_styles()
        + load_home_page_light_styles()
        + load_settings_page_light_styles()
        + load_savings_page_light_styles()
    )


def load_dark_stylesheet() -> str:
    return (
        load_base_dark_styles()
        + load_home_page_dark_styles()
        + load_settings_page_dark_styles()
        + load_savings_page_dark_styles()
    )
