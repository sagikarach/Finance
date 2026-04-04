from __future__ import annotations

from typing import Callable, List, Optional

from ..models.installment_plan import InstallmentPlan
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


class InstallmentsSelector(QWidget):
    def __init__(
        self,
        parent: Optional[QWidget] = None,
        *,
        on_selected: Optional[Callable[[str], None]] = None,
        on_add_plan: Optional[Callable[[], None]] = None,
        on_delete_plan: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self._on_selected = on_selected
        self._on_add_plan = on_add_plan
        self._on_delete_plan = on_delete_plan

        self._plans: List[InstallmentPlan] = []
        self._selected_plan_id: Optional[str] = None

        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        self._btn = QToolButton(self)
        self._btn.setObjectName("EventSelectorButton")
        self._btn.setToolTip("בחירת תכנית תשלומים")
        self._btn.setText("בחר תכנית  ▾")
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

    def set_plans(
        self, plans: List[InstallmentPlan], selected_plan_id: Optional[str]
    ) -> None:
        self._plans = list(plans)
        self._selected_plan_id = selected_plan_id
        self._rebuild_menu()
        self._update_button_text()

    def clear(self) -> None:
        self.set_plans([], None)

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
        name = "בחר תכנית"
        for p in self._plans:
            if p.id == self._selected_plan_id:
                name = p.name or name
                break
        try:
            self._btn.setText(f"{name}  ▾")
        except Exception:
            pass

    def _rebuild_menu(self) -> None:
        try:
            self._menu.clear()
        except Exception:
            pass

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

        for plan in self._plans:
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
                name = QLabel(plan.name, row)
                try:
                    name.setAlignment(
                        Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter
                    )
                except Exception:
                    pass
                right = QLabel("✓" if plan.id == self._selected_plan_id else "", row)
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

                def make_cb(pid: str) -> Callable[[], None]:
                    def _cb() -> None:
                        self._selected_plan_id = pid
                        self._update_button_text()
                        self._rebuild_menu()
                        if self._on_selected is not None:
                            self._on_selected(pid)

                    return _cb

                setattr(row, "mousePressEvent", lambda _evt, cb=make_cb(plan.id): cb())
            except Exception:
                continue

        try:
            self._menu.addSeparator()
        except Exception:
            pass

        if self._on_add_plan is not None:
            try:
                add_center_row(
                    label_text="תכנית חדשה",
                    icon_text="➕",
                    on_click=self._on_add_plan,
                    enabled=True,
                )
            except Exception:
                pass

        if self._on_delete_plan is not None:
            try:
                add_center_row(
                    label_text="מחיקת תכנית נבחרת",
                    icon_text="🗑",
                    on_click=self._on_delete_plan,
                    enabled=bool(self._selected_plan_id),
                )
            except Exception:
                pass
