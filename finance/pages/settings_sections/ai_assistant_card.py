from __future__ import annotations

from ...qt import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    Qt,
    QVBoxLayout,
    QWidget,
)
from ...models.gemini_classifier import get_gemini_api_key, has_gemini_api_key, set_gemini_api_key


class AiAssistantCard(QWidget):
    """Settings card for configuring the Gemini AI assistant API key."""

    def __init__(self, *, parent: object) -> None:
        super().__init__(parent)
        self.setObjectName("ContentPanel")
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
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(12)

        title = QLabel("עוזר AI (Gemini)", self)
        try:
            title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        layout.addWidget(title)
        layout.addSpacing(4)

        desc = QLabel(
            "הוסף מפתח Gemini API כדי לאפשר סיווג חכם של הוצאות בעת ייבוא קובץ.\n"
            "כאשר הסיווג האוטומטי אינו בטוח, Gemini יסווג את הפעולות בצורה מדויקת יותר.",
            self,
        )
        desc.setObjectName("StatTitle")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        layout.addSpacing(4)

        # Status row
        status_text = "✓ מפתח API מוגדר" if has_gemini_api_key() else "✗ מפתח API לא מוגדר"
        self._status_label = QLabel(status_text, self)
        self._status_label.setObjectName("StatValue")
        layout.addWidget(self._status_label)

        layout.addSpacing(8)

        # API key input
        key_label = QLabel("מפתח Gemini API:", self)
        key_label.setObjectName("StatTitle")
        layout.addWidget(key_label)

        self._key_input = QLineEdit(self)
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("AIzaSy...")
        existing = get_gemini_api_key()
        if existing:
            self._key_input.setText(existing)
        layout.addWidget(self._key_input)

        hint = QLabel(
            'קבל מפתח חינמי בכתובת aistudio.google.com ← "Get API key"',
            self,
        )
        hint.setObjectName("StatTitle")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        layout.addSpacing(8)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(12)

        save_btn = QPushButton("שמור מפתח", self)
        save_btn.setObjectName("SaveButton")
        btn_row.addWidget(save_btn)

        clear_btn = QPushButton("מחק מפתח", self)
        clear_btn.setObjectName("SecondaryButton")
        btn_row.addWidget(clear_btn)

        btn_row.addStretch(1)
        layout.addLayout(btn_row)

        layout.addStretch(1)

        def _save() -> None:
            key = self._key_input.text().strip()
            set_gemini_api_key(key)
            if key:
                self._status_label.setText("✓ מפתח API מוגדר")
            else:
                self._status_label.setText("✗ מפתח API לא מוגדר")

        def _clear() -> None:
            self._key_input.clear()
            set_gemini_api_key("")
            self._status_label.setText("✗ מפתח API לא מוגדר")

        save_btn.clicked.connect(_save)
        clear_btn.clicked.connect(_clear)
