"""Styling utilities for sidebar components."""


def get_toggle_style_expanded(is_dark: bool) -> str:
    """Get toggle button style when expanded."""
    if is_dark:
        return """
            QPushButton#SidebarNavToggle {
                background: #020617 !important;
                color: #e5e7eb;
                border-top: 2px solid #1f2937 !important;
                border-bottom: none;
                border-left: none;
                border-right: none;
                padding: 8px 6px;
            }
            QPushButton#SidebarNavToggle:hover {
                background: #1f2937;
            }
            QPushButton#SidebarNavToggle:checked {
                background: #020617 !important;
                border-top: 2px solid #1f2937 !important;
                border-bottom: none;
            }
        """
    else:
        return """
            QPushButton#SidebarNavToggle {
                background: #dcecff;
                color: #0f172a;
                border-top: 2px solid #a0bce2;
                border-bottom: none;
                border-left: none;
                border-right: none;
                padding: 8px 6px;
            }
            QPushButton#SidebarNavToggle:hover {
                background: #c9e1fe;
            }
            QPushButton#SidebarNavToggle:checked {
                background: #dcecff !important;
                border-top: 2px solid #a0bce2 !important;
                border-bottom: none;
            }
        """


def get_toggle_style_checked(is_dark: bool) -> str:
    """Get toggle button style when savings button is checked but not expanded."""
    if is_dark:
        return """
            QPushButton#SidebarNavToggle {
                background: #1e3a5f !important;
                color: #e5e7eb;
                border-top: 2px solid #3b82f6 !important;
                border-bottom: 2px solid #3b82f6 !important;
                border-left: none;
                border-right: none;
                padding: 8px 6px;
            }
            QPushButton#SidebarNavToggle:hover {
                background: #1f2937;
            }
        """
    else:
        return """
            QPushButton#SidebarNavToggle {
                background: #dcecff;
                color: #0f172a;
                border-top: 2px solid #a0bce2;
                border-bottom: 2px solid #a0bce2;
                border-left: none;
                border-right: none;
                padding: 8px 6px;
            }
            QPushButton#SidebarNavToggle:hover {
                background: #c9e1fe;
            }
        """


def get_toggle_style_normal(is_dark: bool) -> str:
    """Get toggle button style when savings button is not checked."""
    if is_dark:
        return """
            QPushButton#SidebarNavToggle {
                background: #020617 !important;
                color: #e5e7eb;
                border-top: 2px solid #1f2937 !important;
                border-bottom: 2px solid #1f2937 !important;
                border-left: none;
                border-right: none;
                padding: 8px 6px;
            }
            QPushButton#SidebarNavToggle:hover {
                background: #1f2937;
            }
        """
    else:
        return """
            QPushButton#SidebarNavToggle {
                background: #dcecff;
                color: #0f172a;
                border-top: 2px solid #a0bce2;
                border-bottom: 2px solid #a0bce2;
                border-left: none;
                border-right: none;
                padding: 8px 6px;
            }
            QPushButton#SidebarNavToggle:hover {
                background: #c9e1fe;
            }
        """


def apply_toggle_button_style(
    toggle_btn,
    savings_btn,
    is_expanded: bool,
) -> None:
    """Apply styling to toggle button to match savings button state."""
    if not toggle_btn or not savings_btn:
        return

    try:
        from PySide6.QtWidgets import QApplication  # type: ignore
    except Exception:
        try:
            from PyQt6.QtWidgets import QApplication  # type: ignore
        except Exception:
            return

    app = QApplication.instance()
    if app is None:
        return

    theme = app.property("theme")
    is_dark = theme == "dark"

    if is_expanded:
        style = get_toggle_style_expanded(is_dark)
    else:
        style = get_toggle_style_normal(is_dark)

    toggle_btn.setStyleSheet("")
    toggle_btn.setStyleSheet(style)
    try:
        toggle_btn.update()
        toggle_btn.repaint()
    except Exception:
        pass

    if not is_expanded:
        savings_btn.setStyleSheet("")
        return

    if is_dark:
        savings_style = """
            QPushButton#SidebarNavButtonSavings {
                border-bottom-color: transparent;
            }
        """
    else:
        savings_style = """
            QPushButton#SidebarNavButtonSavings {
                border-bottom-color: transparent;
            }
        """

    savings_btn.setStyleSheet("")
    savings_btn.setStyleSheet(savings_style)
    try:
        savings_btn.update()
        savings_btn.repaint()
    except Exception:
        pass
