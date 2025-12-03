from __future__ import annotations

backend: str

try:
    from PySide6.QtWidgets import (  # type: ignore
        QApplication,
        QMainWindow,
        QWidget,
        QStackedWidget,
        QFrame,
        QSizePolicy,
        QHBoxLayout,
        QVBoxLayout,
        QLabel,
        QToolButton,
        QPushButton,
        QLineEdit,
        QCheckBox,
        QDialog,
        QListWidget,
        QComboBox,
        QMenu,
        QMenuBar,
        QGraphicsDropShadowEffect,
        QToolTip,
    )
    from PySide6.QtGui import (
        QAction,
        QPainter,
        QColor,
        QFont,
        QCursor,
        QIcon,
        QPixmap,
        QImage,
    )  # type: ignore
    from PySide6.QtCore import Signal, Slot, Qt, QMarginsF  # type: ignore

    backend = "PySide6"
    # QtCharts (available in modern PySide6 wheels)
    try:
        from PySide6.QtCharts import (  # type: ignore
            QChart,
            QChartView,
            QPieSeries,
            QPieSlice,
            QLegend,
            QLegendMarker,
        )

        charts_available = True  # type: ignore[assignment]
    except Exception:
        charts_available = False  # type: ignore[assignment]
except Exception:  # noqa: BLE001 - deliberate broad import fallback guard
    from PyQt6.QtWidgets import (  # type: ignore
        QApplication,
        QMainWindow,
        QWidget,
        QStackedWidget,
        QFrame,
        QSizePolicy,
        QHBoxLayout,
        QVBoxLayout,
        QLabel,
        QToolButton,
        QPushButton,
        QLineEdit,
        QCheckBox,
        QDialog,
        QListWidget,
        QComboBox,
        QMenu,
        QMenuBar,
        QGraphicsDropShadowEffect,
        QToolTip,
    )
    from PyQt6.QtGui import (
        QAction,
        QPainter,
        QColor,
        QFont,
        QCursor,
        QIcon,
        QPixmap,
        QImage,
    )  # type: ignore
    from PyQt6.QtCore import pyqtSignal as Signal, pyqtSlot as Slot, Qt, QMarginsF  # type: ignore

    backend = "PyQt6"
    # QtCharts (may require separate wheel in PyQt6)
    try:
        from PyQt6.QtCharts import (  # type: ignore
            QChart,
            QChartView,
            QPieSeries,
            QPieSlice,
            QLegend,
            QLegendMarker,
        )

        charts_available = True  # type: ignore[assignment]
    except Exception:
        charts_available = False  # type: ignore[assignment]

__all__ = [
    "backend",
    "QApplication",
    "QMainWindow",
    "QWidget",
    "QStackedWidget",
    "QFrame",
    "QSizePolicy",
    "QHBoxLayout",
    "QVBoxLayout",
    "QLabel",
    "QToolButton",
    "QPushButton",
    "QLineEdit",
    "QCheckBox",
    "QDialog",
    "QListWidget",
    "QComboBox",
    "QMenu",
    "QMenuBar",
    "QAction",
    "Signal",
    "Slot",
    "Qt",
    "QPainter",
    "QColor",
    "QGraphicsDropShadowEffect",
    "QMarginsF",
    "QFont",
    "QToolTip",
    "QCursor",
    "QIcon",
    "QPixmap",
    "QImage",
    # Charts
    "charts_available",
    "QChart",
    "QChartView",
    "QPieSeries",
    "QLegend",
    "QLegendMarker",
    "QPieSlice",
]
