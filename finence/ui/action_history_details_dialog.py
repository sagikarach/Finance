from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Optional

from ..qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    Qt,
)
from ..models.action_history import ActionHistory, Action


class ActionHistoryDetailsDialog(QDialog):
    def __init__(self, entry: ActionHistory, parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self._entry = entry

        self.setWindowTitle("פרטי פעולה")
        self.setModal(True)
        try:
            self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        except Exception:
            pass

        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                self.setLayoutDirection(Qt.RightToLeft)  # type: ignore[attr-defined]
            except Exception:
                pass

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(12)

        title_label = QLabel("פרטי פעולה", self)
        title_label.setObjectName("HeaderTitle")
        try:
            title_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        layout.addWidget(title_label)

        meta_layout = QVBoxLayout()

        date_label = QLabel(f"תאריך: {entry.timestamp}", self)

        action_name_map = {
            "transfer": "העברת כסף",
            "add_savings_account": "הוספת חסכון",
            "edit_savings_account": "עריכת חסכון",
            "delete_savings_account": "מחיקת חסכון",
            "add_saving": "הוספת סוג חסכון",
            "edit_saving": "עריכת סוג חסכון",
            "delete_saving": "מחיקת סוג חסכון",
            "activate_bank_account": "הפעלת חשבון",
            "deactivate_bank_account": "ביטול חשבון",
            "set_starter_amount": "הגדרת סכום התחלתי",
            "add_income_movement": "הוספת הכנסה",
            "add_outcome_movement": "הוספת הוצאה",
        }
        action_key = entry.action.action_name
        action_title = action_name_map.get(action_key, action_key)
        type_label = QLabel(f"סוג פעולה: {action_title}", self)

        meta_layout.addWidget(date_label)
        meta_layout.addWidget(type_label)

        layout.addLayout(meta_layout)

        action = entry.action
        details_layout = QVBoxLayout()

        if isinstance(action, Action) and is_dataclass(action):
            field_labels = {
                "amount": "סכום",
                "source_name": "חשבון מקור",
                "target_name": "חשבון יעד",
                "source_type": "סוג מקור",
                "target_type": "סוג יעד",
                "account_name": "שם חשבון",
                "is_liquid": "נזיל",
                "old_name": "שם קודם",
                "new_name": "שם חדש",
                "old_is_liquid": "נזיל קודם",
                "new_is_liquid": "נזיל חדש",
                "account_total_amount": "סכום בחשבון",
                "saving_name": "שם חסכון",
                "saving_amount": "סכום חסכון",
                "old_amount": "סכום קודם",
                "new_amount": "סכום חדש",
                "starter_amount": "סכום התחלתי",
                "category": "קטגוריה",
                "type": "סוג",
                "description": "תיאור",
            }
            for field_info in fields(action):
                name = field_info.name
                if name in ("action_name", "success", "error_message"):
                    continue
                value = getattr(action, name, None)
                if value is None:
                    continue
                label_text = field_labels.get(name, name)
                details_label = QLabel(f"{label_text}: {value}", self)
                details_layout.addWidget(details_label)

            if getattr(action, "error_message", None):
                error_label = QLabel(f"שגיאה: {action.error_message}", self)
                details_layout.addWidget(error_label)

        layout.addLayout(details_layout)

        buttons_row = QHBoxLayout()
        buttons_row.addStretch(1)
        close_btn = QPushButton("סגור", self)
        buttons_row.addWidget(close_btn)
        layout.addLayout(buttons_row)

        close_btn.clicked.connect(self.accept)  # type: ignore[arg-type]
