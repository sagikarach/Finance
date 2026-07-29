from __future__ import annotations

from typing import Callable, Dict, List, Optional

from ..data.bank_movement_provider import JsonFileBankMovementProvider
from ..data.action_history_provider import JsonFileActionHistoryProvider
from ..data.one_time_event_provider import JsonFileOneTimeEventProvider
from ..models.one_time_event import OneTimeEvent
from ..models.one_time_events_service import OneTimeEventsService
from ..qt import (
    QLabel,
    QHBoxLayout,
    QMessageBox,
    QProgressBar,
    QSizePolicy,
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
            history_provider=JsonFileActionHistoryProvider(),
        )
        self._events: List[OneTimeEvent] = []
        self._selected_event_id: Optional[str] = None

        self._selector: Optional[OneTimeEventsSelector] = None
        self._assign_btn: Optional[QToolButton] = None
        self._edit_btn: Optional[QToolButton] = None
        self._cards: Optional[OneTimeEventStatCards] = None
        self._pie: Optional[OneTimeEventPieChart] = None
        self._expenses_chart: Optional[OneTimeEventExpensesOverTimeChart] = None
        self._name_lbl: Optional[QLabel] = None
        self._status_badge: Optional[QLabel] = None
        self._range_lbl: Optional[QLabel] = None
        self._range_sep: Optional[QLabel] = None
        self._count_lbl: Optional[QLabel] = None
        self._count_sep: Optional[QLabel] = None
        self._budget_wrap: Optional[QWidget] = None
        self._budget_lead: Optional[QLabel] = None
        self._budget_rem: Optional[QLabel] = None
        self._budget_bar: Optional[QProgressBar] = None
        self._budget_max_lbl: Optional[QLabel] = None
        self._legend_layout: Optional[QVBoxLayout] = None

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
        try:
            from ..utils.icons import apply_icon
            apply_icon(settings_btn, "gear", size=20, is_dark=self._is_dark_theme())
        except Exception:
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
        lay.setSpacing(16)

        lay.addWidget(self._build_hero(panel), 0)

        self._cards = OneTimeEventStatCards(panel)
        lay.addWidget(self._cards, 0)

        lay.addWidget(self._build_charts_row(panel), 1)

        return panel

    # ------------------------------------------------------------------ hero
    def _build_hero(self, parent: QWidget) -> QWidget:
        hero = QWidget(parent)
        hero.setObjectName("ContentPanel")
        try:
            hero.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        hero_l = QVBoxLayout(hero)
        hero_l.setContentsMargins(24, 22, 24, 22)
        hero_l.setSpacing(18)

        # ── identity (right) + actions (left) ──
        top = QHBoxLayout()
        top.setSpacing(16)

        id_col = QVBoxLayout()
        id_col.setSpacing(8)
        self._name_lbl = QLabel("", hero)
        self._name_lbl.setObjectName("EventName")
        id_col.addWidget(self._name_lbl)

        meta = QHBoxLayout()
        meta.setSpacing(10)
        self._status_badge = QLabel("", hero)
        self._status_badge.setObjectName("EventBadge")
        self._range_lbl = QLabel("", hero)
        self._range_lbl.setObjectName("Subtitle")
        self._range_sep = self._make_dot(hero)
        self._count_lbl = QLabel("", hero)
        self._count_lbl.setObjectName("Subtitle")
        self._count_sep = self._make_dot(hero)
        meta.addWidget(self._status_badge, 0)
        meta.addWidget(self._range_sep, 0)
        meta.addWidget(self._range_lbl, 0)
        meta.addWidget(self._count_sep, 0)
        meta.addWidget(self._count_lbl, 0)
        meta.addStretch(1)
        id_col.addLayout(meta)

        id_wrap = QWidget(hero)
        id_wrap.setLayout(id_col)
        top.addWidget(id_wrap, 1)

        actions = QWidget(hero)
        actions_l = QHBoxLayout(actions)
        actions_l.setContentsMargins(0, 0, 0, 0)
        actions_l.setSpacing(8)
        self._selector = OneTimeEventsSelector(
            actions,
            on_selected=self._on_event_selected,
            on_add_event=self._on_add_event,
            on_delete_event=self._on_delete_event,
        )
        actions_l.addWidget(self._selector, 0)

        self._assign_btn = QToolButton(actions)
        self._assign_btn.setObjectName("HeroAddButton")
        try:
            from ..utils.icons import apply_icon
            apply_icon(self._assign_btn, "plus", size=18, is_dark=self._is_dark_theme())
        except Exception:
            self._assign_btn.setText("＋")
        self._assign_btn.setToolTip("שיוך תנועות לאירוע")
        self._assign_btn.clicked.connect(self._open_assign_dialog)
        actions_l.addWidget(self._assign_btn)

        self._edit_btn = QToolButton(actions)
        self._edit_btn.setObjectName("IconButton")
        try:
            from ..utils.icons import apply_icon
            apply_icon(self._edit_btn, "edit", size=18, is_dark=self._is_dark_theme())
        except Exception:
            self._edit_btn.setText("✎")
        self._edit_btn.setToolTip("עריכת אירוע")
        self._edit_btn.clicked.connect(self._open_edit_selected_event)
        actions_l.addWidget(self._edit_btn)
        top.addWidget(actions, 0, Qt.AlignmentFlag.AlignTop)

        hero_l.addLayout(top)

        # ── budget-usage bar ──
        self._budget_wrap = QWidget(hero)
        bwl = QVBoxLayout(self._budget_wrap)
        bwl.setContentsMargins(0, 0, 0, 0)
        bwl.setSpacing(9)

        brow = QHBoxLayout()
        brow.setSpacing(12)
        self._budget_lead = QLabel("", self._budget_wrap)
        self._budget_lead.setObjectName("Subtitle")
        self._budget_rem = QLabel("", self._budget_wrap)
        self._budget_rem.setObjectName("BudgetRemain")
        brow.addWidget(self._budget_lead, 0)
        brow.addStretch(1)
        brow.addWidget(self._budget_rem, 0)
        bwl.addLayout(brow)

        self._budget_bar = QProgressBar(self._budget_wrap)
        self._budget_bar.setObjectName("BudgetBar")
        self._budget_bar.setRange(0, 100)
        self._budget_bar.setTextVisible(False)
        try:
            self._budget_bar.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            self._budget_bar.setFixedHeight(14)
            self._budget_bar.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
            )
        except Exception:
            pass
        bwl.addWidget(self._budget_bar)

        ticks = QHBoxLayout()
        ticks.setSpacing(8)
        self._budget_max_lbl = QLabel("", self._budget_wrap)
        self._budget_max_lbl.setObjectName("TickLabel")
        tick0 = QLabel("₪0", self._budget_wrap)
        tick0.setObjectName("TickLabel")
        # RTL: ₪0 sits at the right (the bar's fill origin), budget cap at left.
        ticks.addWidget(tick0, 0)
        ticks.addStretch(1)
        ticks.addWidget(self._budget_max_lbl, 0)
        bwl.addLayout(ticks)

        hero_l.addWidget(self._budget_wrap)
        return hero

    @staticmethod
    def _make_dot(parent: QWidget) -> QLabel:
        dot = QLabel("•", parent)
        dot.setObjectName("MetaDot")
        return dot

    # ---------------------------------------------------------------- charts
    def _build_charts_row(self, parent: QWidget) -> QWidget:
        charts_row = QWidget(parent)
        charts_row_l = QHBoxLayout(charts_row)
        charts_row_l.setContentsMargins(0, 0, 0, 0)
        charts_row_l.setSpacing(16)

        # expenses over time (right in RTL)
        line_card = QWidget(charts_row)
        line_card.setObjectName("ContentPanel")
        try:
            line_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        line_card_l = QVBoxLayout(line_card)
        line_card_l.setContentsMargins(20, 18, 20, 18)
        line_card_l.setSpacing(10)
        line_title = QLabel("הוצאות לאורך זמן", line_card)
        line_title.setObjectName("PanelTitle")
        line_card_l.addWidget(line_title)
        self._expenses_chart = OneTimeEventExpensesOverTimeChart(line_card)
        line_card_l.addWidget(self._expenses_chart, 1)

        # expense breakdown: donut + legend (left in RTL)
        pie_card = QWidget(charts_row)
        pie_card.setObjectName("ContentPanel")
        try:
            pie_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        pie_card_l = QVBoxLayout(pie_card)
        pie_card_l.setContentsMargins(20, 18, 20, 18)
        pie_card_l.setSpacing(10)
        pie_title = QLabel("פילוח הוצאות", pie_card)
        pie_title.setObjectName("PanelTitle")
        pie_card_l.addWidget(pie_title)
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
            donut_row = QHBoxLayout()
            donut_row.setSpacing(20)
            self._pie = OneTimeEventPieChart(pie_card)
            try:
                self._pie.setMinimumWidth(150)
            except Exception:
                pass
            donut_row.addWidget(self._pie, 0)

            self._legend_host = QWidget(pie_card)
            self._legend_layout = QVBoxLayout(self._legend_host)
            self._legend_layout.setContentsMargins(0, 0, 0, 0)
            self._legend_layout.setSpacing(12)
            self._legend_layout.addStretch(1)
            donut_row.addWidget(self._legend_host, 1)
            pie_card_l.addLayout(donut_row, 1)

        charts_row_l.addWidget(line_card, 1)
        charts_row_l.addWidget(pie_card, 1)
        return charts_row

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
        if self._name_lbl is not None:
            self._name_lbl.setText("אין אירועים")
        for lbl in (self._status_badge, self._range_lbl, self._count_lbl):
            if lbl is not None:
                lbl.setText("")
                lbl.setVisible(False)
        for sep in (self._range_sep, self._count_sep):
            if sep is not None:
                sep.setVisible(False)
        if self._budget_wrap is not None:
            self._budget_wrap.setVisible(False)
        if self._cards is not None:
            self._cards.clear()
        if self._pie is not None:
            self._pie.clear()
        self._rebuild_legend({}, 0.0)
        if self._expenses_chart is not None:
            self._expenses_chart.clear()

    def _fill_ui(self, event: OneTimeEvent) -> None:
        if self._assign_btn is not None:
            self._assign_btn.setEnabled(True)
        if self._edit_btn is not None:
            self._edit_btn.setEnabled(True)

        totals = self._service.event_totals(event)
        assigned, _unassigned = self._service.movements_for_event(event)

        # ── identity ──
        if self._name_lbl is not None:
            self._name_lbl.setText((event.name or "ללא שם").strip() or "ללא שם")
        if self._status_badge is not None:
            status_text = getattr(event.status, "value", str(event.status))
            self._status_badge.setText(str(status_text))
            self._status_badge.setStyleSheet(self._badge_style(str(status_text)))
            self._status_badge.setVisible(True)

        date_range = self._format_date_range(event.start_date, event.end_date)
        if self._range_lbl is not None:
            self._range_lbl.setText(date_range)
            self._range_lbl.setVisible(bool(date_range))
        if self._range_sep is not None:
            self._range_sep.setVisible(bool(date_range))

        count_text = f"{len(assigned)} תנועות משויכות" if assigned else ""
        if self._count_lbl is not None:
            self._count_lbl.setText(count_text)
            self._count_lbl.setVisible(bool(count_text))
        if self._count_sep is not None:
            self._count_sep.setVisible(bool(count_text) and bool(date_range))

        # ── budget-usage bar ──
        self._fill_budget_bar(event, totals)

        # ── stat tiles ──
        if self._cards is not None:
            self._cards.set_values(
                budget=format_currency(float(event.budget), use_compact=True),
                remaining=format_currency(float(totals.remaining), use_compact=True),
                expenses=format_currency(float(totals.expenses), use_compact=True),
                income=format_currency(float(totals.income), use_compact=True),
            )

        # ── expense breakdown ──
        if self._pie is not None:
            self._pie.set_breakdown(totals.by_category_expense)
        self._rebuild_legend(totals.by_category_expense, float(totals.expenses))

        # ── expenses over time ──
        if self._expenses_chart is not None:
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

    # ---------------------------------------------------------- fill helpers
    def _fill_budget_bar(self, event: OneTimeEvent, totals) -> None:
        budget = float(event.budget or 0.0)
        if self._budget_wrap is not None:
            self._budget_wrap.setVisible(budget > 0)
        if budget <= 0:
            return

        spent = float(totals.expenses)
        remaining = float(totals.remaining)
        pct = totals.percent_used
        pct = (spent / budget) if pct is None else float(pct)
        pct = max(0.0, pct)
        over = pct > 1.0
        pct_int = int(round(min(pct, 1.0) * 100))

        spent_s = format_currency(spent, use_compact=True)
        budget_s = format_currency(budget, use_compact=True)
        if self._budget_lead is not None:
            self._budget_lead.setText(
                f"נוצלו <b>{spent_s}</b> מתוך תקציב של "
                f"<b>{budget_s}</b> · <b>{int(round(pct * 100))}%</b>"
            )
        if self._budget_rem is not None:
            if over:
                self._budget_rem.setText(
                    f"חריגה {format_currency(abs(remaining), use_compact=True)}"
                )
                self._budget_rem.setStyleSheet("color:#d66a4e;font-weight:800;")
            else:
                self._budget_rem.setText(
                    f"נותרו {format_currency(remaining, use_compact=True)}"
                )
                self._budget_rem.setStyleSheet("color:#2f9e68;font-weight:800;")
        if self._budget_max_lbl is not None:
            self._budget_max_lbl.setText(f"תקציב {budget_s}")
        if self._budget_bar is not None:
            self._budget_bar.setValue(pct_int)
            chunk = (
                "qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 #e9a491,stop:1 #d66a4e)"
                if over
                else "qlineargradient(x1:0,y1:0,x2:1,y2:0,"
                "stop:0 #8FBF9F,stop:1 #2f9e68)"
            )
            self._budget_bar.setStyleSheet(
                "QProgressBar#BudgetBar{background:#eef1ea;border:none;"
                "border-radius:7px;}"
                "QProgressBar#BudgetBar::chunk{border-radius:7px;background:"
                f"{chunk};}}"
            )

    def _rebuild_legend(self, by_category: Dict[str, float], total: float) -> None:
        layout = self._legend_layout
        if layout is None:
            return
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)  # detach now; deleteLater alone lingers visually
                w.deleteLater()
        palette = [
            "#B9B6F0", "#C6D3B4", "#F2D06B", "#E9A491",
            "#9BB4E6", "#8FBF9F", "#E0B0D8", "#F7E2A6",
        ]
        for idx, (cat, amount) in enumerate(by_category.items()):
            row = QWidget(self._legend_host)
            row_l = QHBoxLayout(row)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(10)

            sw = QLabel(row)
            sw.setFixedSize(12, 12)
            sw.setStyleSheet(
                f"background:{palette[idx % len(palette)]};border-radius:4px;"
            )
            name = QLabel(str(cat), row)
            name.setObjectName("LegendName")
            pct = (float(amount) / total * 100.0) if total > 0 else 0.0
            val = QLabel(
                f"{format_currency(float(amount), use_compact=True)} · {pct:.0f}%",
                row,
            )
            val.setObjectName("LegendVal")

            row_l.addWidget(sw, 0)
            row_l.addWidget(name, 1)
            row_l.addWidget(val, 0)
            layout.addWidget(row)
        layout.addStretch(1)

    @staticmethod
    def _badge_style(status_text: str) -> str:
        palette = {
            "פעיל": ("#eaf5ef", "#2f9e68"),
            "מתוכנן": ("#ecebfb", "#4a3f9e"),
            "הסתיים": ("#eef1ea", "#5b5f57"),
            "בארכיון": ("#f0eee6", "#8a8d83"),
        }
        bg, fg = palette.get(status_text, ("#eef1ea", "#5b5f57"))
        return (
            f"QLabel#EventBadge{{background:{bg};color:{fg};font-size:12px;"
            "font-weight:800;padding:4px 12px;border-radius:999px;}}"
        )

    @staticmethod
    def _format_date_range(start: Optional[str], end: Optional[str]) -> str:
        months = [
            "ינואר", "פברואר", "מרץ", "אפריל", "מאי", "יוני",
            "יולי", "אוגוסט", "ספטמבר", "אוקטובר", "נובמבר", "דצמבר",
        ]

        def parse(s: Optional[str]):
            if not s:
                return None
            try:
                from datetime import datetime
                return datetime.strptime(str(s)[:10], "%Y-%m-%d")
            except Exception:
                return None

        d1, d2 = parse(start), parse(end)
        if d1 and d2:
            if d1.year == d2.year and d1.month == d2.month:
                return f"{d1.day}–{d2.day} ב{months[d1.month - 1]} {d1.year}"
            if d1.year == d2.year:
                return (
                    f"{d1.day} ב{months[d1.month - 1]} – "
                    f"{d2.day} ב{months[d2.month - 1]} {d1.year}"
                )
            return (
                f"{d1.day} ב{months[d1.month - 1]} {d1.year} – "
                f"{d2.day} ב{months[d2.month - 1]} {d2.year}"
            )
        if d1:
            return f"מ־{d1.day} ב{months[d1.month - 1]} {d1.year}"
        if d2:
            return f"עד {d2.day} ב{months[d2.month - 1]} {d2.year}"
        return ""

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
        try:
            ans = QMessageBox.question(
                self,
                "מחיקת אירוע",
                "האם אתה בטוח שברצונך למחוק את האירוע?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                return
        except Exception:
            pass
        self._service.delete_event(self._selected_event_id)
        self._selected_event_id = None
        self._refresh()
        self._render_selected_event()
