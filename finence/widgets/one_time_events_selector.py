from __future__ import annotations

from typing import Callable, List, Optional

from ..models.one_time_event import OneTimeEvent
from ..qt import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QMenu,
    QSizePolicy,
    QToolButton,
    Qt,
    QWidget,
    QWidgetAction,
)


class OneTimeEventsSelector(QWidget):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        on_selected: Optional[Callable[[str], None]] = None,
        on_add_event: Optional[Callable[[], None]] = None,
        on_delete_event: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._on_selected = on_selected
        self._on_add_event = on_add_event
        self._on_delete_event = on_delete_event

        self._events: List[OneTimeEvent] = []
        self._selected_event_id: Optional[str] = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._btn = QToolButton(self)
        self._btn.setObjectName("EventSelectorButton")
        self._btn.setToolTip("בחירת אירוע")
        self._btn.setText("בחר אירוע  ▾")
        try:
            self._btn.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass
        try:
            mode = None
            try:
                mode = QToolButton.ToolButtonPopupMode.InstantPopup
            except Exception:
                try:
                    mode = getattr(QToolButton, "InstantPopup", None)
                except Exception:
                    mode = None
            if mode is not None:
                self._btn.setPopupMode(mode)
        except Exception:
            pass
        try:
            self._btn.setSizePolicy(
                QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed
            )
        except Exception:
            pass

        self._menu = QMenu(self)
        try:
            self._menu.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass
        self._apply_menu_style()
        try:
            self._btn.setMenu(self._menu)
        except Exception:
            pass

        lay.addWidget(self._btn, 1)

    def set_events(
        self, events: List[OneTimeEvent], selected_event_id: Optional[str]
    ) -> None:
        self._events = list(events)
        self._selected_event_id = selected_event_id
        self._rebuild_menu()
        self._update_button_text()

    def clear(self) -> None:
        self.set_events([], None)

    def set_enabled_actions(self, enabled: bool) -> None:
        try:
            self._btn.setEnabled(bool(enabled))
        except Exception:
            pass

    def _apply_menu_style(self) -> None:
        try:
            theme = "light"
            app = QApplication.instance()
            if app is not None:
                try:
                    theme = str(app.property("theme") or "light")
                except Exception:
                    theme = "light"

            is_dark = theme == "dark"
            bg = "#020617" if is_dark else "#dbeafe"
            fg = "#e5e7eb" if is_dark else "#111827"
            border = "#334155" if is_dark else "#cbd5e1"
            sel = "rgba(255,255,255,0.08)" if is_dark else "rgba(37, 99, 235, 0.12)"

            self._menu.setStyleSheet(
                f"""
                QMenu {{
                    background: {bg};
                    color: {fg};
                    border: 1px solid {border};
                    padding: 6px;
                    min-width: 220px;
                }}
                QMenu::item {{
                    padding: 6px 10px;
                    border-radius: 6px;
                    background: transparent;
                    text-align: center;
                }}
                QMenu::item:selected {{
                    background: {sel};
                }}
                QWidget#EventMenuRow QLabel {{
                    color: {fg};
                    background: transparent;
                }}
                QWidget#EventMenuRow:hover {{
                    background: {sel};
                    border-radius: 6px;
                }}
                QMenu::separator {{
                    height: 1px;
                    background: {border};
                    margin: 6px 6px;
                }}
                """
            )
        except Exception:
            pass

    def _update_button_text(self) -> None:
        name = "בחר אירוע"
        for e in self._events:
            if e.id == self._selected_event_id:
                name = e.name or name
                break
        try:
            self._btn.setText(f"{name}  ▾")
        except Exception:
            pass

    def _rebuild_menu(self) -> None:
        try:
            self._menu.clear()
        except Exception:
            return

        def add_center_row(
            *,
            label_text: str,
            icon_text: str,
            on_click: Callable[[], None],
            enabled: bool = True,
        ) -> None:
            wa = QWidgetAction(self._menu)
            wa.setEnabled(bool(enabled))
            row = QWidget(self._menu)
            row.setObjectName("EventMenuRow")
            try:
                row.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
            except Exception:
                pass
            row_l = QHBoxLayout(row)
            row_l.setContentsMargins(10, 6, 10, 6)
            row_l.setSpacing(8)

            left = QLabel("", row)
            left.setFixedWidth(14)
            name = QLabel(label_text, row)
            try:
                name.setAlignment(
                    Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
                )
            except Exception:
                pass
            icon = QLabel(icon_text, row)
            try:
                icon.setAlignment(
                    Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
                )
            except Exception:
                pass
            icon.setFixedWidth(14)

            row_l.addWidget(left)
            row_l.addWidget(name, 1)
            row_l.addWidget(icon)

            wa.setDefaultWidget(row)
            self._menu.addAction(wa)

            if not enabled:
                try:
                    row.setEnabled(False)
                except Exception:
                    pass
                return

            setattr(row, "mousePressEvent", lambda _evt: on_click())

        for ev in self._events:
            try:
                wa = QWidgetAction(self._menu)
                row = QWidget(self._menu)
                row.setObjectName("EventMenuRow")
                try:
                    row.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
                except Exception:
                    pass
                row_l = QHBoxLayout(row)
                row_l.setContentsMargins(10, 6, 10, 6)
                row_l.setSpacing(8)

                left = QLabel("", row)
                left.setFixedWidth(14)
                name = QLabel(ev.name, row)
                try:
                    name.setAlignment(
                        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
                    )
                except Exception:
                    pass
                right = QLabel("✓" if ev.id == self._selected_event_id else "", row)
                try:
                    right.setAlignment(
                        Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight
                    )
                except Exception:
                    pass
                right.setFixedWidth(14)

                row_l.addWidget(left)
                row_l.addWidget(name, 1)
                row_l.addWidget(right)

                wa.setDefaultWidget(row)
                self._menu.addAction(wa)

                def make_cb(eid: str) -> Callable[[], None]:
                    def _cb() -> None:
                        self._selected_event_id = eid
                        self._update_button_text()
                        if self._on_selected is not None:
                            self._on_selected(eid)

                    return _cb

                setattr(row, "mousePressEvent", lambda _evt, cb=make_cb(ev.id): cb())
            except Exception:
                continue

        try:
            self._menu.addSeparator()
        except Exception:
            pass

        if self._on_add_event is not None:
            try:
                add_center_row(
                    label_text="אירוע חדש",
                    icon_text="➕",
                    on_click=self._on_add_event,
                    enabled=True,
                )
            except Exception:
                pass

        if self._on_delete_event is not None:
            try:
                add_center_row(
                    label_text="מחיקת אירוע נבחר",
                    icon_text="🗑",
                    on_click=self._on_delete_event,
                    enabled=bool(self._selected_event_id),
                )
            except Exception:
                pass
