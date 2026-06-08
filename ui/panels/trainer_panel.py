from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QScrollArea, QVBoxLayout, QWidget,
)
from lab.trainer.stats_meta import CHARACTER_STATS
from ui.i18n import stat_label, tr
from ui.view_models.trainer_vm import TrainerViewModel

class TrainerCommitSpinBox(QDoubleSpinBox):
    value_committed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._baseline = 0.0
        self._committed = False

    def focusInEvent(self, event):
        self._baseline = self.value()
        self._committed = False
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        if not self._committed:
            self.setValue(self._baseline)
        self._committed = False
        super().focusOutEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._committed = True
            value = self.value()
            self.clearFocus()
            self.value_committed.emit(value)
            return
        if event.key() == Qt.Key.Key_Escape:
            self.setValue(self._baseline)
            self.clearFocus()
            return
        super().keyPressEvent(event)

class TrainerPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._vm: TrainerViewModel | None = None
        self._updating = False
        self._stat_spins: dict[str, TrainerCommitSpinBox] = {}
        self._stat_labels: dict[str, QLabel] = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)
        header = QFrame(self)
        header.setObjectName('panelCard')
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(8)
        option_row = QHBoxLayout()
        self._invincible_mode = QCheckBox(header)
        self._invincible_mode.toggled.connect(self._on_invincible_toggled)
        self._super_attack = QCheckBox(header)
        self._super_attack.toggled.connect(self._on_super_attack_toggled)
        option_row.addWidget(self._invincible_mode)
        option_row.addWidget(self._super_attack)
        option_row.addStretch(1)
        header_layout.addLayout(option_row)
        root.addWidget(header)
        stats_card = QFrame(self)
        stats_card.setObjectName('panelCard')
        stats_card_layout = QVBoxLayout(stats_card)
        stats_card_layout.setContentsMargins(16, 12, 16, 12)
        stats_card_layout.setSpacing(8)
        scroll = QScrollArea(stats_card)
        scroll.setObjectName('panelScroll')
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        stats_body = QWidget(scroll)
        stats_body.setObjectName('panelScrollContent')
        stats_body.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        stats_layout = QGridLayout(stats_body)
        stats_layout.setContentsMargins(0, 0, 0, 0)
        stats_layout.setHorizontalSpacing(12)
        stats_layout.setVerticalSpacing(8)
        for row, item in enumerate(CHARACTER_STATS):
            label = QLabel(stats_body)
            label.setObjectName('fieldLabel')
            spin = TrainerCommitSpinBox(stats_body)
            spin.setRange(-99999, 999999)
            spin.setDecimals(item.decimals)
            spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
            spin.setProperty('stat_key', item.key)
            spin.value_committed.connect(self._on_stat_committed)
            stats_layout.addWidget(label, row, 0)
            stats_layout.addWidget(spin, row, 1)
            self._stat_labels[item.key] = label
            self._stat_spins[item.key] = spin
        scroll.setWidget(stats_body)
        stats_card_layout.addWidget(scroll)
        root.addWidget(stats_card, 1)
        self.installEventFilter(self)
        for child in self.findChildren(QWidget):
            if child is not self:
                child.installEventFilter(self)
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self._invincible_mode.setText(tr('trainer.invincible'))
        self._super_attack.setText(tr('trainer.super_attack'))
        for key, label in self._stat_labels.items():
            label.setText(stat_label(key))

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            self._clear_spin_focus_if_clicked_outside(event)
        return super().eventFilter(obj, event)

    def _clear_spin_focus_if_clicked_outside(self, event) -> None:
        focus_spin = self._find_trainer_spin(QApplication.focusWidget())
        if focus_spin is None:
            return
        clicked = QApplication.widgetAt(event.globalPosition().toPoint())
        if clicked is not None and self._widget_in_spin_tree(clicked, focus_spin):
            return
        focus_spin.clearFocus()

    @staticmethod
    def _find_trainer_spin(widget) -> TrainerCommitSpinBox | None:
        while widget is not None:
            if isinstance(widget, TrainerCommitSpinBox):
                return widget
            widget = widget.parentWidget()
        return None

    @staticmethod
    def _widget_in_spin_tree(widget, spin: TrainerCommitSpinBox) -> bool:
        while widget is not None:
            if widget is spin:
                return True
            widget = widget.parentWidget()
        return None

    def bind(self, view_model: TrainerViewModel) -> None:
        self._vm = view_model
        view_model.stats_updated.connect(self._on_stats_updated)

    def _on_stats_updated(self, stats: dict) -> None:
        self._updating = True
        for key, spin in self._stat_spins.items():
            if key in stats and not spin.hasFocus():
                spin.setValue(float(stats[key]))
        self._updating = False

    def _on_stat_committed(self, value: float) -> None:
        if self._updating or self._vm is None:
            return
        spin = self.sender()
        if spin is None:
            return
        key = spin.property('stat_key')
        if key:
            self._vm.apply_stat(str(key), value)

    def _on_invincible_toggled(self, checked: bool) -> None:
        if self._updating or self._vm is None:
            return
        self._vm.set_invincible_mode(checked)

    def _on_super_attack_toggled(self, checked: bool) -> None:
        if self._updating or self._vm is None:
            return
        self._vm.set_super_attack(checked)
