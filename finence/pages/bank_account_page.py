from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ..qt import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    Qt,
    QToolButton,
)
from ..data.provider import AccountsProvider
from ..models.accounts import BankAccount
from ..models.accounts_service import AccountsService
from ..widgets.bank_history_chart import create_bank_history_chart_card
from .base_page import BasePage
from .savings_page import format_currency


class BankAccountPage(BasePage):
    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
        provider: Optional[AccountsProvider] = None,
        navigate: Optional[Callable[[str], None]] = None,
    ) -> None:
        super().__init__(
            app_context=app_context,
            parent=parent,
            provider=provider,
            navigate=navigate,
            page_title="פרטי חשבון בנק",
            current_route="bank_account",
        )
        self._accounts_service = AccountsService(
            self._provider, history_provider=self._history_provider
        )

    def _build_header_left_buttons(self) -> List[QToolButton]:
        buttons: List[QToolButton] = []
        settings_btn = QToolButton(self)
        settings_btn.setObjectName("IconButton")
        settings_btn.setText("⚙")
        settings_btn.setToolTip("הגדרות")
        if self._navigate is not None:
            settings_btn.clicked.connect(lambda: self._navigate("settings"))  # type: ignore[arg-type]
        buttons.append(settings_btn)
        return buttons

    def _build_content(self, main_col: QVBoxLayout) -> None:
        while main_col.count():
            item = main_col.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        selected_name = ""
        try:
            selected_name = str(self._app_context.get("selected_bank_account", ""))
        except Exception:
            selected_name = ""

        target: Optional[BankAccount] = None
        for acc in self._accounts:
            if isinstance(acc, BankAccount) and acc.name == selected_name:
                target = acc
                break

        if target is None:
            placeholder = QLabel("לא נבחר חשבון בנק", self)
            placeholder.setObjectName("Title")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            main_col.addWidget(placeholder, 1)
            return

        top_card = QWidget(self)
        top_card.setObjectName("Sidebar")
        try:
            top_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        top_layout = QHBoxLayout(top_card)
        top_layout.setContentsMargins(16, 16, 16, 16)
        top_layout.setSpacing(16)

        summary_col = QVBoxLayout()
        summary_col.setSpacing(4)

        name_label = QLabel(target.name, top_card)
        name_label.setObjectName("HeaderTitle")
        total_label = QLabel(format_currency(target.total_amount), top_card)
        total_label.setObjectName("StatValueLarge")
        liquid_text = "נזיל" if target.is_liquid else "לא נזיל"
        liquid_label = QLabel(liquid_text, top_card)
        liquid_label.setObjectName("StatTitle")

        name_liquid_row = QHBoxLayout()
        name_liquid_row.setSpacing(8)
        name_liquid_row.addWidget(liquid_label, 0, Qt.AlignmentFlag.AlignRight)
        name_liquid_row.addStretch(1)
        name_liquid_row.addWidget(name_label, 0, Qt.AlignmentFlag.AlignLeft)

        summary_col.addLayout(name_liquid_row)
        summary_col.addWidget(total_label, 0, Qt.AlignmentFlag.AlignRight)

        top_layout.addStretch(1)
        top_layout.addLayout(summary_col, 1)

        chart_card = create_bank_history_chart_card(self, target, format_currency)

        main_col.addWidget(top_card, 1)
        main_col.addWidget(chart_card, 2)

    def on_route_activated(self) -> None:
        try:
            self._accounts = self._accounts_service.load_accounts()
        except Exception:
            pass
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)

    def _on_theme_changed(self, is_dark: bool) -> None:
        super()._on_theme_changed(is_dark)
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)
