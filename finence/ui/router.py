from __future__ import annotations

from typing import Callable, Dict, Optional

from ..qt import QStackedWidget, QWidget


class Router:
    def __init__(self, stacked_widget: QStackedWidget) -> None:
        self._stack: QStackedWidget = stacked_widget
        self._route_name_to_factory: Dict[str, Callable[[], QWidget]] = {}
        self._route_name_to_index: Dict[str, int] = {}

    def register(self, route_name: str, factory: Callable[[], QWidget]) -> None:
        self._route_name_to_factory[route_name] = factory

    def navigate(self, route_name: str) -> None:
        if route_name not in self._route_name_to_index:
            self._ensure_created(route_name)

        index = self._route_name_to_index[route_name]
        self._stack.setCurrentIndex(index)

    def _ensure_created(self, route_name: str) -> None:
        factory = self._route_name_to_factory.get(route_name)
        if factory is None:
            raise KeyError(f"Route not registered: {route_name!r}")

        widget = factory()
        index = self._stack.addWidget(widget)
        self._route_name_to_index[route_name] = index

    def current_route(self) -> Optional[str]:
        current_index = self._stack.currentIndex()
        for name, idx in self._route_name_to_index.items():
            if idx == current_index:
                return name
        return None
