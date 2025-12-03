"""Button positioning utilities for sidebar components."""


def update_dashboard_button_width(
    sidebar: object,
    sidebar_width: int,
    button_container: object,
    dashboard_btn: object,
) -> None:
    """Update dashboard button container and button to full width."""
    if not button_container or not button_container.isVisible():
        return

    container_rect = button_container.geometry()
    if container_rect.height() > 0:
        button_container.setGeometry(
            -16, container_rect.y(), sidebar_width + 32, container_rect.height()
        )
        if dashboard_btn:
            dashboard_btn.setGeometry(
                0, container_rect.y(), sidebar_width, container_rect.height()
            )
            try:
                dashboard_btn.raise_()
                dashboard_btn.update()
                dashboard_btn.repaint()
            except Exception:
                pass


def update_savings_button_width(
    sidebar: object,
    sidebar_width: int,
    savings_button_container: object,
    savings_btn: object,
    savings_toggle_btn: object,
) -> None:
    """Update savings button container, button, and toggle to full width."""
    if not savings_button_container or not savings_button_container.isVisible():
        return

    savings_rect = savings_button_container.geometry()
    if savings_rect.height() > 0:
        savings_button_container.setGeometry(
            -16, savings_rect.y(), sidebar_width + 32, savings_rect.height()
        )
        if savings_btn:
            savings_btn.setGeometry(
                0, savings_rect.y(), sidebar_width, savings_rect.height()
            )
            try:
                savings_btn.raise_()
                savings_btn.update()
                savings_btn.repaint()
            except Exception:
                pass
        if savings_toggle_btn:
            savings_toggle_btn.setGeometry(
                0, savings_rect.y(), 32, savings_rect.height()
            )
            try:
                savings_toggle_btn.raise_()
            except Exception:
                pass


def update_savings_accounts_container_width(
    sidebar: object,
    sidebar_width: int,
    savings_accounts_container: object,
) -> None:
    """Update savings accounts container to full width."""
    if not savings_accounts_container or not savings_accounts_container.isVisible():
        return

    accounts_rect = savings_accounts_container.geometry()
    if accounts_rect.height() > 0:
        savings_accounts_container.setGeometry(
            -16, accounts_rect.y(), sidebar_width + 32, accounts_rect.height()
        )
