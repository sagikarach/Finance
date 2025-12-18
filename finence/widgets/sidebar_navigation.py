from __future__ import annotations

from typing import Optional, Callable

from ..qt import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QSizePolicy, Qt


class SidebarHeaderButton(QPushButton):
    def nextCheckState(self) -> None:
        return


class SidebarNavigation:
    def __init__(
        self,
        parent: QWidget,
        layout: QVBoxLayout,
        navigate: Optional[Callable[[str], None]],
        current_route: Optional[str],
    ) -> None:
        self._parent = parent
        self._layout = layout
        self._navigate = navigate
        self._current_route = current_route

        self._dashboard_btn: Optional[QPushButton] = None
        self._button_container: Optional[QWidget] = None
        self._bank_btn: Optional[QPushButton] = None
        self._bank_button_container: Optional[QWidget] = None
        self._savings_btn: Optional[QPushButton] = None
        self._savings_button_container: Optional[QWidget] = None
        self._monthly_data_btn: Optional[QPushButton] = None
        self._monthly_data_container: Optional[QWidget] = None
        self._yearly_summary_btn: Optional[QPushButton] = None
        self._yearly_summary_container: Optional[QWidget] = None

        self._setup_dashboard_button()
        self._setup_bank_button()
        self._setup_savings_button()
        self._setup_monthly_data_button()
        self._setup_yearly_summary_button()

    def _setup_dashboard_button(self) -> None:
        button_container = QWidget(self._parent)
        button_container_layout = QHBoxLayout(button_container)
        button_container_layout.setContentsMargins(0, 0, 0, 0)
        button_container_layout.setSpacing(0)

        self._dashboard_btn = QPushButton("לוח בקרה", button_container)
        self._dashboard_btn.setObjectName("SidebarNavButton")
        self._dashboard_btn.setCheckable(True)
        try:
            self._dashboard_btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        except Exception:
            pass

        if self._navigate is not None:
            self._dashboard_btn.clicked.connect(lambda: self._navigate("home"))

        self._dashboard_btn.setMinimumHeight(40)
        button_container_layout.addWidget(self._dashboard_btn)

        self._button_container = button_container
        self._layout.addWidget(button_container)

    def _setup_bank_button(self) -> None:
        button_container = QWidget(self._parent)
        button_container_layout = QHBoxLayout(button_container)
        button_container_layout.setContentsMargins(0, 0, 0, 0)
        button_container_layout.setSpacing(0)

        is_bank = self._current_route == "bank_accounts"
        self._bank_btn = SidebarHeaderButton("חשבונות", button_container)
        self._bank_btn.setObjectName("SidebarNavButton")
        self._bank_btn.setCheckable(True)
        self._bank_btn.setChecked(is_bank)
        self._bank_btn.setEnabled(True)
        try:
            self._bank_btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        except Exception:
            pass

        if self._navigate is not None:
            self._bank_btn.clicked.connect(lambda: self._navigate("bank_accounts"))

        self._bank_btn.setMinimumHeight(40)
        button_container_layout.addWidget(self._bank_btn)

        self._bank_button_container = button_container
        self._layout.addWidget(button_container)

    def _setup_savings_button(self) -> None:
        savings_button_container = QWidget(self._parent)
        try:
            savings_button_container.setAttribute(
                Qt.WidgetAttribute.WA_NoSystemBackground, True
            )
        except Exception:
            pass

        savings_button_layout = QHBoxLayout(savings_button_container)
        savings_button_layout.setContentsMargins(0, 0, 0, 0)
        savings_button_layout.setSpacing(0)

        is_savings = self._current_route == "savings"
        self._savings_btn = SidebarHeaderButton("חסכונות", savings_button_container)
        self._savings_btn.setObjectName("SidebarNavButtonSavings")
        self._savings_btn.setCheckable(True)
        self._savings_btn.setChecked(is_savings)
        self._savings_btn.setEnabled(True)
        try:
            self._savings_btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        except Exception:
            pass

        self._savings_btn.setMinimumHeight(40)
        savings_button_layout.addWidget(self._savings_btn)

        self._savings_button_container = savings_button_container
        self._layout.addWidget(savings_button_container)

    def _setup_monthly_data_button(self) -> None:
        button_container = QWidget(self._parent)
        button_container_layout = QHBoxLayout(button_container)
        button_container_layout.setContentsMargins(0, 0, 0, 0)
        button_container_layout.setSpacing(0)

        is_monthly_data = self._current_route == "monthly_data"
        self._monthly_data_btn = QPushButton("סיכום חודשי", button_container)
        self._monthly_data_btn.setObjectName("SidebarNavButton")
        self._monthly_data_btn.setCheckable(True)
        self._monthly_data_btn.setChecked(is_monthly_data)
        self._monthly_data_btn.setEnabled(not is_monthly_data)
        try:
            self._monthly_data_btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        except Exception:
            pass

        if self._navigate is not None:
            self._monthly_data_btn.clicked.connect(
                lambda: self._navigate("monthly_data")
            )

        self._monthly_data_btn.setMinimumHeight(40)
        button_container_layout.addWidget(self._monthly_data_btn)

        self._monthly_data_container = button_container
        self._layout.addWidget(button_container)

    def _setup_yearly_summary_button(self) -> None:
        button_container = QWidget(self._parent)
        button_container_layout = QHBoxLayout(button_container)
        button_container_layout.setContentsMargins(0, 0, 0, 0)
        button_container_layout.setSpacing(0)

        is_yearly_section = self._current_route in (
            "yearly_overview",
            "yearly_data",
            "yearly_category_trends",
        )
        self._yearly_summary_btn = SidebarHeaderButton("סיכום שנתי", button_container)
        self._yearly_summary_btn.setObjectName("SidebarNavButton")
        self._yearly_summary_btn.setCheckable(True)
        self._yearly_summary_btn.setChecked(is_yearly_section)
        self._yearly_summary_btn.setEnabled(True)
        try:
            self._yearly_summary_btn.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
            )
        except Exception:
            pass

        self._yearly_summary_btn.setMinimumHeight(40)
        button_container_layout.addWidget(self._yearly_summary_btn)

        self._yearly_summary_container = button_container
        self._layout.addWidget(button_container)

    def get_dashboard_button(self) -> Optional[QPushButton]:
        return self._dashboard_btn

    def get_dashboard_container(self) -> Optional[QWidget]:
        return self._button_container

    def get_bank_button(self) -> Optional[QPushButton]:
        return self._bank_btn

    def get_bank_container(self) -> Optional[QWidget]:
        return self._bank_button_container

    def get_savings_button(self) -> Optional[QPushButton]:
        return self._savings_btn

    def get_savings_container(self) -> Optional[QWidget]:
        return self._savings_button_container

    def get_monthly_data_button(self) -> Optional[QPushButton]:
        return self._monthly_data_btn

    def get_monthly_data_container(self) -> Optional[QWidget]:
        return self._monthly_data_container

    def get_yearly_summary_button(self) -> Optional[QPushButton]:
        return self._yearly_summary_btn

    def get_yearly_summary_container(self) -> Optional[QWidget]:
        return self._yearly_summary_container
