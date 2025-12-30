from __future__ import annotations

from typing import Optional

from ..qt import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    Qt,
)


class LockDialog(QDialog):
    def __init__(
        self, expected_password: str, parent: Optional[QDialog] = None
    ) -> None:
        super().__init__(parent)
        self._expected_password = expected_password or ""

        self.setWindowTitle("נעילת אפליקציה")
        self.setModal(True)
        try:
            self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        except Exception:
            pass

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(16)

        title = QLabel("הזן סיסמה כדי לפתוח את האפליקציה", self)
        title.setObjectName("HeaderTitle")
        try:
            title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass

        password_edit = QLineEdit(self)
        try:
            password_edit.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            try:
                password_edit.setLayoutDirection(Qt.RightToLeft)
            except Exception:
                pass
        try:
            password_edit.setAlignment(Qt.AlignmentFlag.AlignRight)
        except Exception:
            pass
        try:
            password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        except Exception:
            try:
                password_edit.setEchoMode(QLineEdit.Password)
            except Exception:
                pass

        error_label = QLabel("", self)
        error_label.setStyleSheet("color: #b91c1c;")
        try:
            error_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass

        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(12)

        cancel_btn = QPushButton("יציאה", self)
        unlock_btn = QPushButton("פתח", self)
        unlock_btn.setDefault(True)

        buttons_row.addWidget(cancel_btn)
        buttons_row.addStretch(1)
        buttons_row.addWidget(unlock_btn)

        layout.addWidget(title)
        layout.addWidget(password_edit)
        layout.addWidget(error_label)
        layout.addLayout(buttons_row)

        def try_unlock() -> None:
            if password_edit.text() == self._expected_password:
                self.accept()
            else:
                error_label.setText("סיסמה שגויה, נסה שוב")
                password_edit.selectAll()
                password_edit.setFocus()

        unlock_btn.clicked.connect(try_unlock)
        cancel_btn.clicked.connect(self.reject)
        try:
            password_edit.returnPressed.connect(try_unlock)
        except Exception:
            pass
