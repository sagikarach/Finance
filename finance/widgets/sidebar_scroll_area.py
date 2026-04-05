from __future__ import annotations

from typing import Callable

from ..qt import QApplication, QFrame, QScrollArea, QTimer, QVBoxLayout, QWidget, Qt


class SidebarScrollArea:
    def __init__(self, parent: QWidget) -> None:
        self.scroll = QScrollArea(parent)
        self.scroll.setObjectName("SidebarScrollArea")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        self.content = QWidget(self.scroll)
        self.layout = QVBoxLayout(self.content)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)
        self.scroll.setWidget(self.content)

        sb = self.scroll.verticalScrollBar()
        try:
            sb.rangeChanged.connect(lambda _a, _b: self.sync_scrollbar_visual_state())
        except Exception:
            pass
        self.sync_scrollbar_visual_state()

    def schedule_style_update(
        self, apply_style: Callable[[], None], *, delay_ms: int = 0
    ) -> None:
        try:
            QTimer.singleShot(delay_ms, apply_style)
        except Exception:
            apply_style()

    def sync_scrollbar_visual_state(self) -> None:
        try:
            sb = self.scroll.verticalScrollBar()
            has_scroll = bool(sb.maximum() > 0)
            sb.setProperty("hasScroll", "true" if has_scroll else "false")
            st = sb.style()
            st.unpolish(sb)
            st.polish(sb)
            sb.update()
        except Exception:
            pass

    def apply_scrollbar_style(self) -> None:
        is_dark = False
        try:
            app = QApplication.instance()
            if app is not None:
                is_dark = str(app.property("theme") or "light") == "dark"
        except Exception:
            is_dark = False

        handle = "#1e3a5f" if is_dark else "#93c5fd"
        handle_hover = "#2d5a8e" if is_dark else "#60a5fa"

        try:
            self.scroll.setStyleSheet(
                f"""
                QScrollArea#SidebarScrollArea QScrollBar:vertical {{
                    background: transparent;
                    width: 8px;
                    margin: 8px 2px 8px 2px;
                    border: none;
                }}
                QScrollArea#SidebarScrollArea QScrollBar::handle:vertical {{
                    background: {handle};
                    border-radius: 999px;
                    min-height: 24px;
                }}
                QScrollArea#SidebarScrollArea QScrollBar:vertical[hasScroll="false"]::handle:vertical {{
                    background: transparent;
                }}
                QScrollArea#SidebarScrollArea QScrollBar::handle:vertical:hover {{
                    background: {handle_hover};
                }}
                QScrollArea#SidebarScrollArea QScrollBar::add-line:vertical,
                QScrollArea#SidebarScrollArea QScrollBar::sub-line:vertical {{
                    background: transparent;
                    border: none;
                    height: 0px;
                    width: 0px;
                }}
                QScrollArea#SidebarScrollArea QScrollBar::up-arrow,
                QScrollArea#SidebarScrollArea QScrollBar::down-arrow {{
                    background: none;
                    border: none;
                    width: 0px;
                    height: 0px;
                }}
                QScrollArea#SidebarScrollArea QScrollBar:horizontal {{
                    height: 0px;
                }}
                QScrollArea#SidebarScrollArea::corner {{
                    background: transparent;
                }}
                """
            )
        except Exception:
            pass
