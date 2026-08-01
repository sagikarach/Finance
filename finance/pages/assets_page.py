from __future__ import annotations

from dataclasses import replace
from typing import List, Optional

from ..qt import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QLabel,
    QToolButton,
    QDialog,
    QPushButton,
    QLineEdit,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QSizePolicy,
    Qt,
)
from ..models.mortgage import AssetKind, Mortgage
from ..models.mortgage_service import MortgageService
from ..models.asset import HousePurchase, build_asset, new_asset_record
from .base_page import BasePage


def _fmt_money(value: float) -> str:
    try:
        return f"{float(value):,.0f}"
    except Exception:
        return str(value)


def _parse_float(text: str) -> Optional[float]:
    s = str(text or "").strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except Exception:
        return None


# מזהה החשבון הקבוע לנכסי רכישה (תואם למסך המשכנתא).
_MORTGAGE_ACCOUNT_NAME = "בנק"


class AssetDialog(QDialog):
    """הוספה/עריכה של נכס: שם + סוג (רכישה/אחר). 'אחר' כולל שווי נוכחי."""

    def __init__(
        self,
        *,
        asset: Optional[Mortgage] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("נכס")
        self.setModal(True)
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass

        self._asset = asset
        self._editing = asset is not None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(10)

        title = QLabel("עריכת נכס" if self._editing else "נכס חדש", self)
        title.setObjectName("HeaderTitle")
        root.addWidget(title)

        self._name = QLineEdit(self)
        self._name.setPlaceholderText("שם הנכס (לדוגמה: דירה ברחוב הרצל)")
        root.addWidget(QLabel("שם", self))
        root.addWidget(self._name)

        self._kind = QComboBox(self)
        self._kind.addItems([k.value for k in AssetKind])
        root.addWidget(QLabel("סוג", self))
        root.addWidget(self._kind)

        self._value_label = QLabel("שווי נוכחי", self)
        self._value = QLineEdit(self)
        self._value.setPlaceholderText("שווי נוכחי (₪)")
        root.addWidget(self._value_label)
        root.addWidget(self._value)

        self._kind.currentTextChanged.connect(self._on_kind_changed)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        save_btn = QPushButton("שמור", self)
        cancel_btn = QPushButton("בטל", self)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        root.addLayout(buttons)
        save_btn.clicked.connect(self._on_save)
        cancel_btn.clicked.connect(self.reject)

        self._load_initial()
        self._on_kind_changed(self._kind.currentText())

    def _on_kind_changed(self, text: str) -> None:
        # שדה השווי רלוונטי ל"אחר" (שווי נוכחי) ול"רכב" (מחיר הקנייה ההתחלתי).
        is_car = str(text) == AssetKind.CAR.value
        is_valued = is_car or str(text) == AssetKind.OTHER.value
        if is_car:
            self._value_label.setText("שווי התחלתי (מחיר קנייה)")
            self._value.setPlaceholderText("מחיר הקנייה (₪)")
        else:
            self._value_label.setText("שווי נוכחי")
            self._value.setPlaceholderText("שווי נוכחי (₪)")
        self._value_label.setVisible(is_valued)
        self._value.setVisible(is_valued)

    def _load_initial(self) -> None:
        a = self._asset
        if a is None:
            return
        self._name.setText(str(a.name or ""))
        try:
            self._kind.setCurrentText(str(getattr(a.kind, "value", a.kind)))
        except Exception:
            pass
        # סוג נעול בעריכה — לא ממירים רכישה <-> אחר.
        self._kind.setEnabled(False)
        if a.current_value:
            self._value.setText(f"{float(a.current_value):.0f}")

    def _on_save(self) -> None:
        name = str(self._name.text() or "").strip()
        if not name:
            QMessageBox.warning(self, "שגיאה", "שם הנכס לא יכול להיות ריק")
            return
        try:
            kind = AssetKind(str(self._kind.currentText()))
        except Exception:
            kind = AssetKind.PURCHASE
        value = _parse_float(self._value.text()) or 0.0

        if self._editing and self._asset is not None:
            self._asset = replace(
                self._asset, name=name, current_value=float(value)
            )
        else:
            self._asset = new_asset_record(
                kind,
                name=name,
                current_value=value,
                account_name=_MORTGAGE_ACCOUNT_NAME,
            )
        self.accept()

    def get_asset(self) -> Optional[Mortgage]:
        return self._asset


class SellDialog(QDialog):
    """מכירת נכס: מחיר מכירה + תאריך."""

    def __init__(
        self,
        *,
        asset: Mortgage,
        suggested_price: float = 0.0,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("מכירת נכס")
        self.setModal(True)
        try:
            self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass

        self._price: Optional[float] = None
        self._date: str = ""

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(10)

        title = QLabel(f"מכירת הנכס: {asset.name}", self)
        title.setObjectName("HeaderTitle")
        root.addWidget(title)

        self._price_edit = QLineEdit(self)
        self._price_edit.setPlaceholderText("מחיר מכירה (₪)")
        if suggested_price:
            self._price_edit.setText(f"{float(suggested_price):.0f}")
        root.addWidget(QLabel("מחיר מכירה", self))
        root.addWidget(self._price_edit)

        self._date_edit = QLineEdit(self)
        self._date_edit.setPlaceholderText("YYYY-MM-DD")
        try:
            from datetime import date

            self._date_edit.setText(date.today().isoformat())
        except Exception:
            pass
        root.addWidget(QLabel("תאריך מכירה", self))
        root.addWidget(self._date_edit)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        save_btn = QPushButton("מכור", self)
        cancel_btn = QPushButton("בטל", self)
        buttons.addWidget(save_btn)
        buttons.addWidget(cancel_btn)
        root.addLayout(buttons)
        save_btn.clicked.connect(self._on_save)
        cancel_btn.clicked.connect(self.reject)

    def _on_save(self) -> None:
        price = _parse_float(self._price_edit.text())
        if price is None or price < 0:
            QMessageBox.warning(self, "שגיאה", "הזן מחיר מכירה תקין")
            return
        self._price = float(price)
        self._date = str(self._date_edit.text() or "").strip()
        self.accept()

    def get_result(self) -> Optional[tuple]:
        if self._price is None:
            return None
        return (self._price, self._date)


class AssetsPage(BasePage):
    def _build_header_left_buttons(self) -> List[QToolButton]:
        buttons: List[QToolButton] = []
        settings_btn = QToolButton(self)
        settings_btn.setObjectName("IconButton")
        try:
            from ..utils.icons import apply_icon

            apply_icon(settings_btn, "gear", size=20, is_dark=self._is_dark_theme())
        except Exception:
            settings_btn.setText("⚙")
        settings_btn.setToolTip("הגדרות")
        if self._navigate is not None:
            settings_btn.clicked.connect(lambda: self._navigate("settings"))
        buttons.append(settings_btn)
        return buttons

    def __init__(self, *args, **kwargs) -> None:
        kwargs.setdefault("page_title", "נכסים")
        kwargs.setdefault("current_route", "assets")
        self._service = MortgageService()
        self._assets: List[Mortgage] = []
        self._table: Optional[QTableWidget] = None
        self._summary_labels: dict = {}
        super().__init__(*args, **kwargs)

    def on_route_activated(self) -> None:
        super().on_route_activated()
        self._reload()

    def _build_content(self, content_col: QVBoxLayout) -> None:
        self._clear_content_layout(content_col)

        root = QWidget(self)
        try:
            root.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        except Exception:
            pass
        content_col.addWidget(root, 1)

        lay = QVBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        # ───────── כרטיסי סיכום ─────────
        self._summary_labels = {}
        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        for key, title_txt, style in (
            ("value", "שווי נכסים", "MonthIncomeCard"),
            ("debt", "יתרת משכנתאות", "MonthExpenseCard"),
            ("net", "שווי נטו", "MonthNetCard"),
            ("count", "נכסים פעילים", "MonthInfoCard"),
        ):
            card = QWidget(root)
            card.setObjectName(style)
            try:
                card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
                card.setAutoFillBackground(True)
            except Exception:
                pass
            cl = QVBoxLayout(card)
            cl.setContentsMargins(16, 16, 16, 16)
            cl.setSpacing(6)
            t = QLabel(title_txt, card)
            t.setObjectName("StatTitle")
            v = QLabel("—", card)
            v.setObjectName("StatValueCard")
            cl.addWidget(t, 0, Qt.AlignmentFlag.AlignHCenter)
            cl.addWidget(v, 0, Qt.AlignmentFlag.AlignHCenter)
            cards_row.addWidget(card, 1)
            self._summary_labels[key] = v
        lay.addLayout(cards_row, 0)

        header_card = QWidget(root)
        header_card.setObjectName("Sidebar")
        try:
            header_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        except Exception:
            pass
        header_row = QHBoxLayout(header_card)
        header_row.setContentsMargins(16, 12, 16, 12)
        header_row.setSpacing(8)
        _hdr_lbl = QLabel("הנכסים שלי", header_card)
        _hdr_lbl.setObjectName("PanelTitle")
        header_row.addWidget(_hdr_lbl, 0)
        header_row.addStretch(1)

        add_btn = QToolButton(header_card)
        add_btn.setObjectName("IconButton")
        add_btn.setText("➕")
        add_btn.setToolTip("הוסף נכס")
        add_btn.clicked.connect(self._on_add)
        header_row.addWidget(add_btn)

        open_btn = QToolButton(header_card)
        open_btn.setObjectName("IconButton")
        open_btn.setText("✎")
        open_btn.setToolTip("פתח / ערוך")
        open_btn.clicked.connect(self._on_open_selected)
        header_row.addWidget(open_btn)

        sell_btn = QToolButton(header_card)
        sell_btn.setObjectName("IconButton")
        sell_btn.setText("💰")
        sell_btn.setToolTip("מכור נכס")
        sell_btn.clicked.connect(self._on_sell)
        header_row.addWidget(sell_btn)

        delete_btn = QToolButton(header_card)
        delete_btn.setObjectName("IconButton")
        delete_btn.setText("🗑")
        delete_btn.setToolTip("מחק נכס")
        delete_btn.clicked.connect(self._on_delete)
        header_row.addWidget(delete_btn)

        lay.addWidget(header_card, 0)

        table_card = QWidget(root)
        table_card.setObjectName("ContentPanel")
        try:
            table_card.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            table_card.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
        except Exception:
            pass
        table_card_l = QVBoxLayout(table_card)
        table_card_l.setContentsMargins(16, 16, 16, 16)
        table_card_l.setSpacing(8)

        self._table = QTableWidget(table_card)
        self._table.setObjectName("ActionHistoryTableWidget")
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["שם", "סוג", "שווי", "מצב"])
        self._table.setRowCount(0)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        try:
            self._table.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
            hh = self._table.horizontalHeader()
            if hh is not None:
                hh.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
                hh.setObjectName("ActionHistoryHeader")
        except Exception:
            pass
        self._table.doubleClicked.connect(self._on_open_selected)
        table_card_l.addWidget(self._table, 1)
        lay.addWidget(table_card, 1)

        self._reload()

    @staticmethod
    def _asset_value(asset: Mortgage) -> float:
        # Each asset reports its own value (house → price, held → current value).
        return float(build_asset(asset).current_value())

    @staticmethod
    def _is_sold(asset: Mortgage) -> bool:
        return not build_asset(asset).is_active

    def _update_summary(self) -> None:
        if not self._summary_labels:
            return
        active = [a for a in self._assets if not self._is_sold(a)]
        total_value = sum(self._asset_value(a) for a in active)
        try:
            outstanding = self._service.total_outstanding()
        except Exception:
            outstanding = 0.0
        net = total_value - outstanding
        values = {
            "value": _fmt_money(total_value),
            "debt": _fmt_money(outstanding),
            "net": _fmt_money(net),
            "count": str(len(active)),
        }
        for key, lbl in self._summary_labels.items():
            try:
                lbl.setText(values.get(key, "—"))
            except Exception:
                pass

    def _reload(self) -> None:
        try:
            self._assets = self._service.list_mortgages()
        except Exception:
            self._assets = []
        self._update_summary()
        if self._table is None:
            return
        self._table.setRowCount(len(self._assets))
        for row, a in enumerate(self._assets):
            kind_txt = str(getattr(a.kind, "value", a.kind))
            sold = self._is_sold(a)
            if sold:
                sale_p = float(getattr(a, "sale_price", 0.0) or 0.0)
                status_txt = (
                    f"נמכר · {_fmt_money(sale_p)}" if sale_p else "נמכר"
                )
            else:
                status_txt = "פעיל"
            name_item = QTableWidgetItem(str(a.name))
            try:
                name_item.setData(Qt.ItemDataRole.UserRole, str(a.id))
            except Exception:
                pass
            items = [
                name_item,
                QTableWidgetItem(kind_txt),
                QTableWidgetItem(_fmt_money(self._asset_value(a))),
                QTableWidgetItem(status_txt),
            ]
            for col, item in enumerate(items):
                if sold:
                    try:
                        from ..qt import QColor

                        item.setForeground(QColor("#94a3b8"))
                    except Exception:
                        pass
                self._table.setItem(row, col, item)

    def _selected_asset(self) -> Optional[Mortgage]:
        if self._table is None:
            return None
        row = self._table.currentRow()
        if row < 0 or row >= len(self._assets):
            return None
        return self._assets[row]

    def _open_asset(self, asset: Mortgage) -> None:
        if isinstance(build_asset(asset), HousePurchase):
            # נווט לעמוד הנכס (סקירת תשלומי הרכישה) עם הנכס הנבחר.
            try:
                if isinstance(self._app_context, dict):
                    self._app_context["selected_mortgage_id"] = str(asset.id)
            except Exception:
                pass
            if self._navigate is not None:
                self._navigate("asset")
        else:
            dlg = AssetDialog(asset=asset, parent=self)
            if dlg.exec() == QDialog.DialogCode.Accepted:
                updated = dlg.get_asset()
                if updated is not None:
                    self._service.upsert_mortgage(updated)
                    self._reload()

    def _on_open_selected(self) -> None:
        a = self._selected_asset()
        if a is None:
            QMessageBox.information(self, "נכס", "בחר נכס")
            return
        self._open_asset(a)

    def _on_add(self) -> None:
        dlg = AssetDialog(parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        asset = dlg.get_asset()
        if asset is None:
            return
        self._service.upsert_mortgage(asset)
        self._reload()
        # נכס רכישה — פתח מיד את מסך הפירוט כדי לבנות את התמהיל.
        if isinstance(build_asset(asset), HousePurchase):
            self._open_asset(asset)

    def _on_delete(self) -> None:
        a = self._selected_asset()
        if a is None:
            QMessageBox.information(self, "מחיקה", "בחר נכס למחיקה")
            return
        res = QMessageBox.question(
            self,
            "מחיקה",
            f'למחוק את "{a.name}"?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if res != QMessageBox.StandardButton.Yes:
            return
        self._service.delete_mortgage(a.id)
        self._reload()

    def _on_sell(self) -> None:
        a = self._selected_asset()
        if a is None:
            QMessageBox.information(self, "מכירה", "בחר נכס למכירה")
            return
        if self._is_sold(a):
            QMessageBox.information(self, "מכירה", f'"{a.name}" כבר נמכר')
            return
        dlg = SellDialog(asset=a, suggested_price=self._asset_value(a), parent=self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        result = dlg.get_result()
        if result is None:
            return
        price, date = result
        # מסומן כנמכר וגם כמאורכב — כך שיוצא אוטומטית מהשווי הנקי, מהסיידבר ומהסכומים.
        updated = replace(
            a, sold=True, archived=True, sale_price=float(price), sale_date=str(date)
        )
        self._service.upsert_mortgage(updated)
        self._reload()
