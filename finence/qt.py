from __future__ import annotations

from typing import Any, Optional
import importlib
import sys

if getattr(sys, "frozen", False):
    try:
        import PySide6.QtCore  # noqa: F401
        import PySide6.QtGui  # noqa: F401
        import PySide6.QtWidgets  # noqa: F401

        try:
            import PySide6.QtCharts  # noqa: F401
        except Exception:
            pass
    except Exception:
        pass


def _import_module(name: str) -> Optional[Any]:
    try:
        return importlib.import_module(name)
    except Exception:
        return None


_widgets = _import_module("PySide6.QtWidgets") or _import_module("PyQt6.QtWidgets")
_gui = _import_module("PySide6.QtGui") or _import_module("PyQt6.QtGui")
_core = _import_module("PySide6.QtCore") or _import_module("PyQt6.QtCore")
_charts = _import_module("PySide6.QtCharts") or _import_module("PyQt6.QtCharts")

backend = "unknown"
if _widgets is not None:
    try:
        backend = (
            "PySide6"
            if str(getattr(_widgets, "__name__", "")).startswith("PySide6")
            else "PyQt6"
        )
    except Exception:
        backend = "unknown"


def _get(mod: Optional[Any], name: str) -> Any:
    if mod is None:
        return None
    return getattr(mod, name, None)


QApplication: Any = _get(_widgets, "QApplication")
QMainWindow = _get(_widgets, "QMainWindow")
QWidget = _get(_widgets, "QWidget")
QStackedWidget = _get(_widgets, "QStackedWidget")
QFrame = _get(_widgets, "QFrame")
QSizePolicy = _get(_widgets, "QSizePolicy")
QHBoxLayout = _get(_widgets, "QHBoxLayout")
QVBoxLayout = _get(_widgets, "QVBoxLayout")
QLabel = _get(_widgets, "QLabel")
QStyledItemDelegate = _get(_widgets, "QStyledItemDelegate")
QToolButton = _get(_widgets, "QToolButton")
QPushButton = _get(_widgets, "QPushButton")
QLineEdit = _get(_widgets, "QLineEdit")
QCheckBox = _get(_widgets, "QCheckBox")
QDialog = _get(_widgets, "QDialog")
QListWidget = _get(_widgets, "QListWidget")
QListWidgetItem = _get(_widgets, "QListWidgetItem")
QComboBox = _get(_widgets, "QComboBox")
QSpinBox = _get(_widgets, "QSpinBox")
QMenu = _get(_widgets, "QMenu")
QWidgetAction = _get(_widgets, "QWidgetAction")
QMenuBar = _get(_widgets, "QMenuBar")
QGraphicsDropShadowEffect = _get(_widgets, "QGraphicsDropShadowEffect")
QToolTip = _get(_widgets, "QToolTip")
QDateEdit = _get(_widgets, "QDateEdit")
QTableWidget = _get(_widgets, "QTableWidget")
QTableWidgetItem = _get(_widgets, "QTableWidgetItem")
QHeaderView = _get(_widgets, "QHeaderView")
QScrollArea = _get(_widgets, "QScrollArea")
QProgressBar = _get(_widgets, "QProgressBar")
QMessageBox = _get(_widgets, "QMessageBox")
QFileDialog: Any = _get(_widgets, "QFileDialog")

QAction: Any = _get(_gui, "QAction")
QPainter = _get(_gui, "QPainter")
QColor = _get(_gui, "QColor")
QPen = _get(_gui, "QPen")
QFont = _get(_gui, "QFont")
QCursor = _get(_gui, "QCursor")
QIcon = _get(_gui, "QIcon")
QPixmap = _get(_gui, "QPixmap")
QImage = _get(_gui, "QImage")
QPainterPath = _get(_gui, "QPainterPath")
QLinearGradient = _get(_gui, "QLinearGradient")
QPalette: Any = _get(_gui, "QPalette")

Signal = _get(_core, "Signal") or _get(_core, "pyqtSignal")
Slot = _get(_core, "Slot") or _get(_core, "pyqtSlot")
Qt: Any = _get(_core, "Qt")
QEvent = _get(_core, "QEvent")
QTimer = _get(_core, "QTimer")
QMarginsF = _get(_core, "QMarginsF")
QDate = _get(_core, "QDate")
QLocale = _get(_core, "QLocale")
QPointF = _get(_core, "QPointF")
QSize: Any = _get(_core, "QSize")

charts_available = bool(_charts is not None)
QChart = _get(_charts, "QChart")
QChartView = _get(_charts, "QChartView")
QPieSeries = _get(_charts, "QPieSeries")
QPieSlice = _get(_charts, "QPieSlice")
QLegend = _get(_charts, "QLegend")
QLegendMarker = _get(_charts, "QLegendMarker")
QLineSeries = _get(_charts, "QLineSeries")
QValueAxis = _get(_charts, "QValueAxis")
QCategoryAxis = _get(_charts, "QCategoryAxis")

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
    "QStyledItemDelegate",
    "QToolButton",
    "QPushButton",
    "QLineEdit",
    "QCheckBox",
    "QDialog",
    "QListWidget",
    "QListWidgetItem",
    "QComboBox",
    "QSpinBox",
    "QMenu",
    "QWidgetAction",
    "QMenuBar",
    "QAction",
    "Signal",
    "Slot",
    "Qt",
    "QEvent",
    "QPainter",
    "QColor",
    "QPen",
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
    "QPalette",
    "QPointF",
    "QDate",
    "QDateEdit",
    "QLocale",
    "QTimer",
    "QSize",
    "QTableWidget",
    "QTableWidgetItem",
    "QHeaderView",
    "QScrollArea",
    "QProgressBar",
    "QMessageBox",
    "QFileDialog",
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
