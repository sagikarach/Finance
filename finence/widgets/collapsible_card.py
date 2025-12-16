from __future__ import annotations

from typing import Optional

from ..qt import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget, QSizePolicy, Qt


class CollapsibleCard(QWidget):
    def __init__(
        self,
        title: str,
        parent: Optional[QWidget] = None,
        *,
        expanded: bool = False,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        try:
            self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass

        self._expanded = expanded

        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        header = QWidget(self)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)

        self._toggle = QPushButton("▲" if self._expanded else "▼", header)
        self._toggle.setObjectName("SidebarNavToggle")
        self._toggle.setCheckable(True)
        self._toggle.setChecked(self._expanded)
        self._toggle.setFixedWidth(32)
        try:
            self._toggle.setSizePolicy(
                QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed
            )
        except Exception:
            pass

        self._title = QLabel(title, header)
        self._title.setObjectName("Subtitle")
        try:
            self._title.setAlignment(
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )
        except Exception:
            pass

        header_layout.addWidget(self._toggle, 0)
        header_layout.addWidget(self._title, 1)

        self._content = QWidget(self)
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(12)

        root.addWidget(header, 0)
        root.addWidget(self._content, 1)

        self._apply_visibility()

        self._toggle.clicked.connect(self.toggle)

    def set_content(self, widget: QWidget) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.setParent(None)
                w.deleteLater()
        self._content_layout.addWidget(widget, 1)
        self._apply_visibility()

    def set_expanded(self, expanded: bool) -> None:
        if self._expanded == expanded:
            return
        self._expanded = expanded
        self._apply_visibility()

    def is_expanded(self) -> bool:
        return self._expanded

    def toggle(self) -> None:
        self._expanded = not self._expanded
        self._apply_visibility()

    def _apply_visibility(self) -> None:
        self._content.setVisible(self._expanded)
        self._toggle.setChecked(self._expanded)
        self._toggle.setText("▲" if self._expanded else "▼")
