from __future__ import annotations

import os
import webbrowser

from ...qt import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
    Qt,
)
from ...models.update_service import UpdateService


class UpdatesCard(QWidget):
    def __init__(self, *, parent: QWidget, app_version: str) -> None:
        super().__init__(parent)
        self.setObjectName("Sidebar")
        self._app_version = str(app_version or "").strip()
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
        updates_layout = QVBoxLayout(self)
        updates_layout.setContentsMargins(24, 24, 24, 24)
        updates_layout.setSpacing(12)

        updates_title = QLabel("עדכונים", self)
        try:
            updates_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        except Exception:
            pass
        updates_layout.addWidget(updates_title)

        ver_lbl = QLabel(f"גרסה נוכחית: {self._app_version}", self)
        updates_layout.addWidget(ver_lbl)

        repo = str(os.environ.get("FINENCE_UPDATE_REPO", "") or "").strip()
        repo_lbl = QLabel(
            f"מקור עדכון: {repo if repo else 'לא הוגדר (FINENCE_UPDATE_REPO)'}",
            self,
        )
        repo_lbl.setObjectName("Subtitle")
        updates_layout.addWidget(repo_lbl)

        status_lbl = QLabel("", self)
        status_lbl.setObjectName("Subtitle")
        updates_layout.addWidget(status_lbl)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        check_btn = QPushButton("בדוק עדכונים", self)
        check_btn.setObjectName("SaveButton")
        open_btn = QPushButton("פתח דף הורדה", self)
        btn_row.addWidget(check_btn)
        btn_row.addWidget(open_btn)
        btn_row.addStretch(1)
        updates_layout.addLayout(btn_row)

        def open_download_page() -> None:
            if repo:
                webbrowser.open(f"https://github.com/{repo}/releases")
            else:
                webbrowser.open("https://github.com/")

        def check_updates() -> None:
            status_lbl.setText("בודק עדכונים...")
            QApplication.processEvents()
            if not repo:
                status_lbl.setText("כדי לאפשר בדיקת עדכונים, הגדר FINENCE_UPDATE_REPO.")
                return
            svc = UpdateService(repo=repo)
            latest = svc.latest_release()
            if latest is None:
                status_lbl.setText("לא ניתן לבדוק עדכונים כרגע.")
                return
            if svc.is_newer(current=self._app_version, latest=latest.version):
                status_lbl.setText(f"גרסה חדשה זמינה: {latest.version}")
                webbrowser.open(latest.html_url)
            else:
                status_lbl.setText("אתה על הגרסה העדכנית.")

        open_btn.clicked.connect(open_download_page)
        check_btn.clicked.connect(check_updates)
        updates_layout.addStretch(1)
