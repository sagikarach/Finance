from __future__ import annotations

from typing import Optional

from ..qt import (
    QCheckBox,
    QComboBox,
    QDate,
    QDateEdit,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    Qt,
)
from ..models.one_time_event import OneTimeEvent, OneTimeEventStatus
from .dialog_utils import create_standard_buttons_row, setup_standard_rtl_dialog, setup_calendar_popup


class OneTimeEventEditDialog(QDialog):
    def __init__(
        self,
        *,
        event: OneTimeEvent,
        parent: Optional[QDialog] = None,
        require_name: bool = False,
        title: str = "עריכת אירוע",
    ) -> None:
        super().__init__(parent)
        self._event = event
        self._result: Optional[OneTimeEvent] = None
        self._require_name = bool(require_name)

        layout = setup_standard_rtl_dialog(
            self,
            title=title,
            margins=(24, 20, 24, 20),
            spacing=12,
        )
        self.setMinimumWidth(520)

        header = QLabel("עריכת פרטי אירוע", self)
        header.setObjectName("Subtitle")
        try:
            header.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        layout.addWidget(header)

        self._name = QLineEdit(self)
        self._name.setPlaceholderText("שם אירוע")
        self._name.setText(event.name)
        self._name_error = QLabel("", self)
        self._name_error.setObjectName("Subtitle")
        try:
            self._name_error.setObjectName("ErrorLabel")
        except Exception:
            pass
        self._name_error.setVisible(False)

        self._budget = QLineEdit(self)
        self._budget.setPlaceholderText("תקציב")
        self._budget.setText(str(float(event.budget)))

        self._status = QComboBox(self)
        for st in OneTimeEventStatus:
            self._status.addItem(str(st.value), st)
        for i in range(self._status.count()):
            if self._status.itemData(i) == event.status:
                self._status.setCurrentIndex(i)
                break

        row1 = QHBoxLayout()
        row1.setSpacing(8)
        row1.addWidget(QLabel("שם:", self))
        row1.addWidget(self._name, 1)
        layout.addLayout(row1)
        layout.addWidget(self._name_error)

        row2 = QHBoxLayout()
        row2.setSpacing(8)
        row2.addWidget(QLabel("סטטוס:", self))
        row2.addWidget(self._status, 1)
        row2.addWidget(QLabel("תקציב:", self))
        row2.addWidget(self._budget, 1)
        layout.addLayout(row2)

        self._use_range = QCheckBox("טווח תאריכים", self)
        self._use_range.setChecked(bool(event.start_date or event.end_date))
        layout.addWidget(self._use_range)

        self._start = QDateEdit(self)
        self._end = QDateEdit(self)
        try:
            self._start.setCalendarPopup(True)
            setup_calendar_popup(self._start)
            self._end.setCalendarPopup(True)
            setup_calendar_popup(self._end)
        except Exception:
            pass

        if event.start_date:
            try:
                self._start.setDate(QDate.fromString(event.start_date, "yyyy-MM-dd"))
            except Exception:
                pass
        if event.end_date:
            try:
                self._end.setDate(QDate.fromString(event.end_date, "yyyy-MM-dd"))
            except Exception:
                pass

        dates_row = QHBoxLayout()
        dates_row.setSpacing(8)
        dates_row.addWidget(QLabel("מתאריך:", self))
        dates_row.addWidget(self._start, 1)
        dates_row.addWidget(QLabel("עד תאריך:", self))
        dates_row.addWidget(self._end, 1)
        layout.addLayout(dates_row)

        self._notes = QLineEdit(self)
        self._notes.setPlaceholderText("הערות (אופציונלי)")
        self._notes.setText(event.notes or "")
        layout.addWidget(self._notes)

        def apply_range_enabled(enabled: bool) -> None:
            self._start.setEnabled(bool(enabled))
            self._end.setEnabled(bool(enabled))

        apply_range_enabled(self._use_range.isChecked())
        self._use_range.toggled.connect(apply_range_enabled)

        buttons_row, save_btn, cancel_btn = create_standard_buttons_row(
            self, primary_text="שמור", cancel_text="ביטול"
        )
        layout.addLayout(buttons_row)
        cancel_btn.clicked.connect(self.reject)
        save_btn.clicked.connect(self._on_save)

    def result_event(self) -> Optional[OneTimeEvent]:
        return self._result

    def _on_save(self) -> None:
        name = (self._name.text() or "").strip()
        if self._require_name and not name:
            self._name_error.setText("חובה להזין שם לאירוע.")
            self._name_error.setVisible(True)
            try:
                self._name.setFocus()
            except Exception:
                pass
            return
        if not name:
            name = self._event.name or "אירוע"
        budget = self._event.budget
        try:
            budget = float((self._budget.text() or "").strip() or 0.0)
        except Exception:
            budget = self._event.budget
        if budget < 0:
            QMessageBox.warning(self, "שגיאה", "התקציב לא יכול להיות שלילי.")
            return

        status = self._event.status
        data = self._status.currentData()
        if isinstance(data, OneTimeEventStatus):
            status = data

        start_date = None
        end_date = None
        if self._use_range.isChecked():
            try:
                start_date = self._start.date().toString("yyyy-MM-dd")
                end_date = self._end.date().toString("yyyy-MM-dd")
                if self._end.date() < self._start.date():
                    QMessageBox.warning(
                        self,
                        "טווח תאריכים שגוי",
                        "תאריך הסיום חייב להיות לאחר תאריך ההתחלה.",
                    )
                    return
            except Exception:
                start_date = self._event.start_date
                end_date = self._event.end_date

        notes = (self._notes.text() or "").strip() or None

        self._result = OneTimeEvent(
            id=self._event.id,
            name=name,
            budget=float(budget),
            status=status,
            start_date=start_date,
            end_date=end_date,
            notes=notes,
        )
        self.accept()
