from __future__ import annotations

from typing import Dict, Optional, List, Callable

from ..qt import (
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    Qt,
    QSizePolicy,
    QApplication,
    QToolButton,
)
from ..data.provider import AccountsProvider
from ..models.accounts_service import AccountsService
from ..models.overview import AccountsOverview
from ..widgets.accounts_pie_chart import AccountsPieChart
from .base_page import BasePage


class HomePage(BasePage):
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
            page_title="לוח בקרה",
            current_route="home",
        )
        self._accounts_service = AccountsService(self._provider)

    def _build_header_left_buttons(self) -> List[QToolButton]:
        buttons = []
        settings_btn = QToolButton(self)
        settings_btn.setObjectName("IconButton")
        settings_btn.setText("⚙")
        settings_btn.setToolTip("הגדרות")
        if self._navigate is not None:
            settings_btn.clicked.connect(lambda: self._navigate("settings"))  # type: ignore[arg-type]
        buttons.append(settings_btn)
        return buttons

    def _build_content(self, main_col: QVBoxLayout) -> None:
        # DEBUG: Add green card and put both in cards_row layout
        overview = AccountsOverview.for_home(self._accounts)
        total_all = overview.total_all
        total_liquid = overview.total_liquid

        # Get parent widget from layout to ensure proper cleanup
        parent_widget = main_col.parentWidget()
        if parent_widget is None:
            parent_widget = self

        total_all_card = QWidget(parent_widget)
        total_all_card.setObjectName("StatCardGreen")
        try:
            total_all_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        total_all_card_layout = QVBoxLayout(total_all_card)
        total_all_card_layout.setContentsMargins(14, 14, 14, 14)
        total_all_card_layout.setSpacing(6)
        try:
            total_all_card.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass
        total_all_title = QLabel("סה״כ כסף", total_all_card)
        total_all_title.setObjectName("StatTitle")
        total_all_label = QLabel(format_currency(total_all), total_all_card)
        total_all_label.setObjectName("StatValueLarge")
        total_all_card_layout.addStretch(1)
        total_all_card_layout.addWidget(
            total_all_title, 0, Qt.AlignmentFlag.AlignHCenter
        )
        total_all_card_layout.addWidget(
            total_all_label, 0, Qt.AlignmentFlag.AlignHCenter
        )
        total_all_card_layout.addStretch(1)

        total_liquid_card = QWidget(parent_widget)
        total_liquid_card.setObjectName("StatCardPurple")
        try:
            total_liquid_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        total_liquid_card_layout = QVBoxLayout(total_liquid_card)
        total_liquid_card_layout.setContentsMargins(14, 14, 14, 14)
        total_liquid_card_layout.setSpacing(6)
        try:
            total_liquid_card.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass
        total_liquid_title = QLabel("סכום נזיל", total_liquid_card)
        total_liquid_title.setObjectName("StatTitle")
        total_liquid_label = QLabel(format_currency(total_liquid), total_liquid_card)
        total_liquid_label.setObjectName("StatValueLarge")
        total_liquid_card_layout.addStretch(1)
        total_liquid_card_layout.addWidget(
            total_liquid_title, 0, Qt.AlignmentFlag.AlignHCenter
        )
        total_liquid_card_layout.addWidget(
            total_liquid_label, 0, Qt.AlignmentFlag.AlignHCenter
        )
        total_liquid_card_layout.addStretch(1)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)
        cards_row.addWidget(total_all_card, 1)
        cards_row.addWidget(total_liquid_card, 1)
        main_col.addLayout(cards_row, 0)

        chart = AccountsPieChart(accounts=overview.accounts, parent=parent_widget)

        chart_card = QWidget(parent_widget)
        chart_card.setObjectName("Sidebar")
        try:
            chart_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        chart_card_layout = QVBoxLayout(chart_card)
        chart_card_layout.setContentsMargins(4, 4, 4, 4)
        chart_card_layout.setSpacing(0)
        chart_card_layout.addWidget(chart, 1)

        chart_side_card = QWidget(parent_widget)
        chart_side_card.setObjectName("Sidebar")
        try:
            chart_side_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        chart_side_layout = QVBoxLayout(chart_side_card)
        chart_side_layout.setContentsMargins(12, 12, 12, 12)
        chart_side_layout.setSpacing(0)

        chart_row = QHBoxLayout()
        chart_row.setSpacing(16)
        chart_row.addWidget(chart_card, 2)
        chart_row.addWidget(chart_side_card, 1)

        main_col.addLayout(chart_row, 1)

    def on_route_activated(self) -> None:
        try:
            self._accounts = self._accounts_service.load_accounts()
        except Exception:
            pass

        if self._sidebar is not None and hasattr(self._sidebar, "update_accounts"):
            try:
                self._sidebar.update_accounts(self._accounts)  # type: ignore[arg-type]
            except Exception:
                pass

        if isinstance(self._content_col, QVBoxLayout):
            layout = self._content_col
            # Remove all items and widgets immediately
            widgets_to_delete = []
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widgets_to_delete.append(widget)
                layout_item = item.layout()
                if layout_item is not None:
                    # Recursively collect widgets from nested layouts
                    while layout_item.count():
                        nested_item = layout_item.takeAt(0)
                        nested_widget = nested_item.widget()
                        if nested_widget is not None:
                            widgets_to_delete.append(nested_widget)
            # Delete all collected widgets
            for widget in widgets_to_delete:
                widget.setParent(None)
                widget.deleteLater()
            # Force Qt to process the deletions before rebuilding
            QApplication.processEvents()
            self._build_content(layout)


def format_currency(value: float) -> str:
    try:
        return f"₪{value:,.2f}"
    except Exception:
        return f"₪{value}"
