from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ..data.bank_movement_provider import JsonFileBankMovementProvider
from ..data.one_time_event_provider import JsonFileOneTimeEventProvider
from ..models.one_time_event import OneTimeEvent
from ..models.one_time_events_service import OneTimeEventsService
from ..qt import (
    QLabel,
    QHBoxLayout,
    QToolButton,
    QVBoxLayout,
    QWidget,
    Qt,
    charts_available,
)
from ..ui.one_time_event_assign_dialog import OneTimeEventAssignDialog
from ..ui.one_time_event_edit_dialog import OneTimeEventEditDialog
from ..utils.formatting import format_currency
from ..widgets.one_time_event_expenses_chart import (
    ExpensePoint,
    OneTimeEventExpensesOverTimeChart,
)
from ..widgets.one_time_event_pie_chart import OneTimeEventPieChart
from ..widgets.one_time_event_stat_cards import OneTimeEventStatCards
from ..widgets.one_time_events_selector import OneTimeEventsSelector
from .base_page import BasePage


class OneTimeEventsPage(BasePage):
    def __init__(
        self,
        app_context: Optional[Dict[str, str]] = None,
        parent: Optional[QWidget] = None,
        navigate: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._service = OneTimeEventsService(
            events_provider=JsonFileOneTimeEventProvider(),
            movements_provider=JsonFileBankMovementProvider(),
        )
        self._events: List[OneTimeEvent] = []
        self._selected_event_id: Optional[str] = None

        self._selector: Optional[OneTimeEventsSelector] = None
        self._assign_btn: Optional[QToolButton] = None
        self._edit_btn: Optional[QToolButton] = None
        self._cards: Optional[OneTimeEventStatCards] = None
        self._pie: Optional[OneTimeEventPieChart] = None
        self._expenses_chart: Optional[OneTimeEventExpensesOverTimeChart] = None

        self._refresh()

        super().__init__(
            app_context=app_context,
            parent=parent,
            provider=None,
            navigate=navigate,
            page_title="אירועים",
            current_route="one_time_events",
        )

    def _build_header_left_buttons(self) -> List[QToolButton]:
        buttons: List[QToolButton] = []
        settings_btn = QToolButton(self)
        settings_btn.setObjectName("IconButton")
        settings_btn.setText("⚙")
        settings_btn.setToolTip("הגדרות")
        if self._navigate is not None:
            settings_btn.clicked.connect(lambda: self._navigate("settings"))
        buttons.append(settings_btn)
        return buttons

    def on_route_activated(self) -> None:
        super().on_route_activated()
        self._refresh()
        if isinstance(self._content_col, QVBoxLayout):
            self._build_content(self._content_col)

    def _refresh(self) -> None:
        self._events = self._service.list_events()
        if self._selected_event_id and not any(
            e.id == self._selected_event_id for e in self._events
        ):
            self._selected_event_id = None
        if self._selected_event_id is None and self._events:
            self._selected_event_id = self._events[0].id

    def _selected_event(self) -> Optional[OneTimeEvent]:
        for e in self._events:
            if e.id == self._selected_event_id:
                return e
        return None

    def _build_content(self, main_col: QVBoxLayout) -> None:
        self._clear_content_layout(main_col)

        root = QWidget(self)
        try:
            root.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        right = self._build_event_details_panel(root)
        layout.addWidget(right, 1)

        main_col.addWidget(root, 1)
        self._render_selected_event()

    def _build_event_details_panel(self, parent: QWidget) -> QWidget:
        panel = QWidget(parent)
        lay = QVBoxLayout(panel)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        header_card = QWidget(panel)
        header_card.setObjectName("Sidebar")
        try:
            header_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        header_card_l = QVBoxLayout(header_card)
        header_card_l.setContentsMargins(16, 14, 16, 14)
        header_card_l.setSpacing(0)

        header_row = QHBoxLayout()
        header_row.setSpacing(8)

        self._selector = OneTimeEventsSelector(
            header_card,
            on_selected=self._on_event_selected,
            on_add_event=self._on_add_event,
            on_delete_event=self._on_delete_event,
        )
        header_row.addWidget(self._selector, 0)
        header_row.addStretch(1)

        self._assign_btn = QToolButton(header_card)
        self._assign_btn.setObjectName("IconButton")
        self._assign_btn.setText("➕")
        self._assign_btn.setToolTip("שיוך תנועות לאירוע")
        self._assign_btn.clicked.connect(self._open_assign_dialog)
        header_row.addWidget(self._assign_btn)

        self._edit_btn = QToolButton(header_card)
        self._edit_btn.setObjectName("IconButton")
        self._edit_btn.setText("✎")
        self._edit_btn.setToolTip("עריכת אירוע")
        self._edit_btn.clicked.connect(self._open_edit_selected_event)
        header_row.addWidget(self._edit_btn)

        header_card_l.addLayout(header_row)
        lay.addWidget(header_card, 0)

        cards_wrap = QWidget(panel)
        cards_wrap_l = QVBoxLayout(cards_wrap)
        cards_wrap_l.setContentsMargins(16, 0, 16, 0)
        cards_wrap_l.setSpacing(0)
        self._cards = OneTimeEventStatCards(cards_wrap)
        cards_wrap_l.addWidget(self._cards, 0)
        lay.addWidget(cards_wrap, 0)

        charts_row = QWidget(panel)
        charts_row_l = QHBoxLayout(charts_row)
        charts_row_l.setContentsMargins(0, 0, 0, 0)
        charts_row_l.setSpacing(12)

        pie_card = QWidget(charts_row)
        pie_card.setObjectName("Sidebar")
        try:
            pie_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        pie_card_l = QVBoxLayout(pie_card)
        pie_card_l.setContentsMargins(16, 16, 16, 16)
        pie_card_l.setSpacing(8)
        if not charts_available:
            lbl = QLabel(
                "Charts are unavailable on this backend. Install QtCharts.", pie_card
            )
            lbl.setObjectName("Subtitle")
            try:
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            except Exception:
                pass
            pie_card_l.addWidget(lbl, 1)
        else:
            self._pie = OneTimeEventPieChart(pie_card)
            pie_card_l.addWidget(self._pie, 1)

        line_card = QWidget(charts_row)
        line_card.setObjectName("Sidebar")
        try:
            line_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        line_card_l = QVBoxLayout(line_card)
        line_card_l.setContentsMargins(16, 16, 16, 16)
        line_card_l.setSpacing(8)
        self._expenses_chart = OneTimeEventExpensesOverTimeChart(line_card)
        line_card_l.addWidget(self._expenses_chart, 1)

        charts_row_l.addWidget(pie_card, 1)
        charts_row_l.addWidget(line_card, 1)
        lay.addWidget(charts_row, 1)

        return panel

    def _render_selected_event(self) -> None:
        if self._selector is not None:
            self._selector.set_events(self._events, self._selected_event_id)

        event = self._selected_event()
        if event is None:
            self._clear_ui()
            return

        self._fill_ui(event)

    def _clear_ui(self) -> None:
        if self._assign_btn is not None:
            self._assign_btn.setEnabled(False)
        if self._edit_btn is not None:
            self._edit_btn.setEnabled(False)
        if self._cards is not None:
            self._cards.clear()
        if self._pie is not None:
            self._pie.clear()
        if self._expenses_chart is not None:
            self._expenses_chart.clear()

    def _fill_ui(self, event: OneTimeEvent) -> None:
        if self._assign_btn is not None:
            self._assign_btn.setEnabled(True)
        if self._edit_btn is not None:
            self._edit_btn.setEnabled(True)

        totals = self._service.event_totals(event)
        if self._cards is not None:
            self._cards.set_values(
                budget=format_currency(float(event.budget), use_compact=True),
                remaining=format_currency(float(totals.remaining), use_compact=True),
                expenses=format_currency(float(totals.expenses), use_compact=True),
                income=format_currency(float(totals.income), use_compact=True),
            )

        if self._pie is not None:
            self._pie.set_breakdown(totals.by_category_expense)

        if self._expenses_chart is not None:
            assigned, _unassigned = self._service.movements_for_event(event)
            pts: List[ExpensePoint] = []
            for m in assigned:
                try:
                    amt = float(getattr(m, "amount", 0.0))
                    date_iso = str(getattr(m, "date", "") or "")
                except Exception:
                    continue
                if amt < 0 and date_iso:
                    pts.append(ExpensePoint(date_iso=date_iso, amount=abs(amt)))
            self._expenses_chart.set_expenses(pts)

    def _on_event_selected(self, event_id: str) -> None:
        self._selected_event_id = event_id
        self._render_selected_event()

    def _open_edit_selected_event(self) -> None:
        event = self._selected_event()
        if event is None:
            return
        self._open_edit_event(event)

    def _open_edit_event(self, event: OneTimeEvent) -> None:
        try:
            dlg = OneTimeEventEditDialog(event=event, parent=None)
            dlg.exec()
            updated = dlg.result_event()
            if updated is None:
                return
            self._service.upsert_event(updated)
            self._selected_event_id = updated.id
            self._refresh()
            self._render_selected_event()
        except Exception:
            return

    def _open_assign_dialog(self) -> None:
        event = self._selected_event()
        if event is None:
            return
        try:
            dlg = OneTimeEventAssignDialog(
                service=self._service, event=event, parent=None
            )
            dlg.exec()
        except Exception:
            return
        self._refresh()
        self._render_selected_event()

    def _on_add_event(self) -> None:
        draft = OneTimeEventsService.default_event(name="")
        try:
            dlg = OneTimeEventEditDialog(
                event=draft,
                parent=None,
                require_name=True,
                title="יצירת אירוע חדש",
            )
            dlg.exec()
            created = dlg.result_event()
            if created is None:
                return
            if not (created.name or "").strip():
                return
            self._service.upsert_event(created)
            self._selected_event_id = created.id
            self._refresh()
            self._render_selected_event()
        except Exception:
            return

    def _on_delete_event(self) -> None:
        if not self._selected_event_id:
            return
        self._service.delete_event(self._selected_event_id)
        self._selected_event_id = None
        self._refresh()
        self._render_selected_event()
