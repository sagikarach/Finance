from __future__ import annotations

backend: str

try:
    from PySide6.QtWidgets import (
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
        QDateEdit,
        QTableWidget,
        QTableWidgetItem,
        QHeaderView,
        QScrollArea,
        QProgressBar,
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
        QPainterPath,
        QLinearGradient,
    )
    from PySide6.QtCore import (
        Signal,
        Slot,
        Qt,
        QMarginsF,
        QDate,
        QLocale,
        QPointF,
    )

    backend = "PySide6"
    try:
        from PySide6.QtCharts import (
            QChart,
            QChartView,
            QPieSeries,
            QPieSlice,
            QLegend,
            QLegendMarker,
            QLineSeries,
            QValueAxis,
            QCategoryAxis,
        )

        charts_available = True
    except Exception:
        charts_available = False
except Exception:
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
        QDateEdit,
        QTableWidget,
        QTableWidgetItem,
        QHeaderView,
        QScrollArea,
        QProgressBar,
    )
    from PyQt6.QtGui import (  # type: ignore
        QAction,
        QPainter,
        QColor,
        QFont,
        QCursor,
        QIcon,
        QPixmap,
        QImage,
        QPainterPath,
        QLinearGradient,
    )
    from PyQt6.QtCore import (  # type: ignore
        pyqtSignal as Signal,
        pyqtSlot as Slot,
        Qt,
        QMarginsF,
        QDate,
        QLocale,
        QPointF,
    )

    backend = "PyQt6"
    try:
        from PyQt6.QtCharts import (  # type: ignore
            QChart,
            QChartView,
            QPieSeries,
            QPieSlice,
            QLegend,
            QLegendMarker,
            QLineSeries,
            QValueAxis,
            QCategoryAxis,
        )

        charts_available = True
    except Exception:
        charts_available = False

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
    "QPainterPath",
    "QLinearGradient",
    "QGraphicsDropShadowEffect",
    "QMarginsF",
    "QFont",
    "QToolTip",
    "QCursor",
    "QIcon",
    "QPixmap",
    "QImage",
    "QPointF",
    "QDate",
    "QDateEdit",
    "QLocale",
    "QTableWidget",
    "QTableWidgetItem",
    "QHeaderView",
    "QScrollArea",
    "QProgressBar",
    "charts_available",
    "QChart",
    "QChartView",
    "QPieSeries",
    "QLegend",
    "QLegendMarker",
    "QPieSlice",
    "QLineSeries",
    "QValueAxis",
    "QCategoryAxis",
]
