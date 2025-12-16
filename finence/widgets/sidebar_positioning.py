from typing import Any


def update_dashboard_button_width(
    sidebar: Any,
    sidebar_width: int,
    button_container: Any,
    dashboard_btn: Any,
) -> None:
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


def update_bank_button_width(
    sidebar: Any,
    sidebar_width: int,
    bank_button_container: Any,
    bank_btn: Any,
    bank_toggle_btn: Any,
) -> None:
    if not bank_button_container or not bank_button_container.isVisible():
        return

    container_rect = bank_button_container.geometry()
    if container_rect.height() > 0:
        bank_button_container.setGeometry(
            -16, container_rect.y(), sidebar_width + 32, container_rect.height()
        )
        if bank_btn:
            bank_btn.setGeometry(
                0, container_rect.y(), sidebar_width, container_rect.height()
            )
            try:
                bank_btn.raise_()
                bank_btn.update()
                bank_btn.repaint()
            except Exception:
                pass
        if bank_toggle_btn:
            bank_toggle_btn.setGeometry(
                0, container_rect.y(), 32, container_rect.height()
            )
            try:
                bank_toggle_btn.raise_()
            except Exception:
                pass


def update_savings_button_width(
    sidebar: Any,
    sidebar_width: int,
    savings_button_container: Any,
    savings_btn: Any,
    savings_toggle_btn: Any,
) -> None:
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


def update_monthly_data_button_width(
    sidebar: Any,
    sidebar_width: int,
    monthly_data_container: Any,
    monthly_data_btn: Any,
) -> None:
    if not monthly_data_container or not monthly_data_container.isVisible():
        return

    container_rect = monthly_data_container.geometry()
    if container_rect.height() > 0:
        monthly_data_container.setGeometry(
            -16, container_rect.y(), sidebar_width + 32, container_rect.height()
        )
        if monthly_data_btn:
            monthly_data_btn.setGeometry(
                0, container_rect.y(), sidebar_width, container_rect.height()
            )
            try:
                monthly_data_btn.raise_()
                monthly_data_btn.update()
                monthly_data_btn.repaint()
            except Exception:
                pass


def update_savings_accounts_container_width(
    sidebar: Any,
    sidebar_width: int,
    savings_accounts_container: Any,
) -> None:
    if not savings_accounts_container or not savings_accounts_container.isVisible():
        return

    accounts_rect = savings_accounts_container.geometry()
    if accounts_rect.height() > 0:
        savings_accounts_container.setGeometry(
            -16, accounts_rect.y(), sidebar_width + 32, accounts_rect.height()
        )
