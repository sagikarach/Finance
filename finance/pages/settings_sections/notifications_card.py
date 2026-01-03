from __future__ import annotations

from typing import Callable, Optional

from ...qt import (
    QCheckBox,
    QCursor,
    QLabel,
    QToolTip,
    QVBoxLayout,
    QWidget,
    Qt,
)
from ...models.notifications import RuleType


class NotificationsCard(QWidget):
    def __init__(
        self,
        *,
        parent: QWidget,
        notifications_service,
        on_refreshed: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                self.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass
        self._svc = notifications_service
        self._on_refreshed = on_refreshed
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title_label = QLabel("התראות", self)
        try:
            title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        layout.addWidget(title_label)
        layout.addSpacing(8)

        try:
            self._svc.ensure_defaults()
        except Exception:
            pass

        master_cb = QCheckBox("הפעל התראות", self)
        try:
            master_cb.setChecked(bool(self._svc.is_enabled()))
        except Exception:
            master_cb.setChecked(True)
        layout.addWidget(master_cb)
        layout.addSpacing(6)

        rule_label_map: dict[RuleType, str] = {
            RuleType.UNEXPECTED_EXPENSE: "הוצאות חריגות / כפולות",
            RuleType.MISSING_MONTHLY_UPLOAD: "תזכורת העלאת קובץ הוצאות חודשי",
            RuleType.MISSING_SAVINGS_UPDATE: "תזכורת עדכון חסכונות",
            RuleType.EVENT_OVER_BUDGET: "חריגה מתקציב אירוע",
        }

        rules = []
        try:
            rules = self._svc.list_rules()
        except Exception:
            rules = []

        rule_checkboxes: dict[str, QCheckBox] = {}
        for r in rules:
            label = rule_label_map.get(r.type, r.id)
            cb = QCheckBox(label, self)
            cb.setObjectName("NotificationRuleToggle")
            cb.setChecked(bool(r.enabled))
            rule_checkboxes[r.id] = cb
            layout.addWidget(cb)

            def make_rule_toggle(rule_id: str):
                def _handler(checked: bool) -> None:
                    try:
                        self._svc.set_rule_enabled(rule_id, bool(checked))
                        self._svc.refresh()
                        if self._on_refreshed is not None:
                            self._on_refreshed()
                        QToolTip.showText(QCursor.pos(), "הגדרות התראות נשמרו")
                    except Exception:
                        pass

                return _handler

            cb.toggled.connect(make_rule_toggle(r.id))

        def apply_enabled_state(enabled: bool) -> None:
            for cb in rule_checkboxes.values():
                cb.setEnabled(bool(enabled))

        def on_master_toggled(checked: bool) -> None:
            try:
                self._svc.set_enabled(bool(checked))
                apply_enabled_state(bool(checked))
                self._svc.refresh()
                if self._on_refreshed is not None:
                    self._on_refreshed()
                QToolTip.showText(QCursor.pos(), "הגדרות התראות נשמרו")
            except Exception:
                pass

        master_cb.toggled.connect(on_master_toggled)
        apply_enabled_state(master_cb.isChecked())
        layout.addStretch(1)
