from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QTabWidget, QVBoxLayout, QWidget,
)
from lab.trainer.stats_meta import BASIC_STATS, HIDDEN_STATS, SPELL_STATS
from ui.i18n import stat_label, trainer_tab_label, tr
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
        self._basic_spins: dict[str, TrainerCommitSpinBox] = {}
        self._basic_labels: dict[str, QLabel] = {}
        self._hidden_spins: dict[str, TrainerCommitSpinBox] = {}
        self._hidden_labels: dict[str, QLabel] = {}
        self._spell_spins: dict[tuple[int, str], TrainerCommitSpinBox] = {}
        self._spell_labels: dict[tuple[int, str], QLabel] = {}
        self._spell_tab_spell_ids: list[int] = []
        self._spell_names: dict[int, str] = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)
        header = QFrame(self)
        header.setObjectName('panelCard')
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(8)
        option_row = QHBoxLayout()
        option_row.setSpacing(8)
        self._start_btn = QPushButton(header)
        self._start_btn.setObjectName('trainerStartBtn')
        self._refresh_btn = QPushButton(header)
        self._refresh_btn.setObjectName('secondaryBtn')
        self._refresh_btn.setEnabled(False)
        self._start_btn.clicked.connect(self._on_start_clicked)
        self._refresh_btn.clicked.connect(self._on_refresh_clicked)
        divider = QFrame(header)
        divider.setObjectName('trainerHeaderDivider')
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setFrameShadow(QFrame.Shadow.Plain)
        divider.setFixedWidth(1)
        self._invincible_mode = QCheckBox(header)
        self._invincible_mode.toggled.connect(self._on_invincible_toggled)
        self._super_attack = QCheckBox(header)
        self._super_attack.toggled.connect(self._on_super_attack_toggled)
        option_row.addWidget(self._start_btn)
        option_row.addWidget(self._refresh_btn)
        option_row.addWidget(divider)
        option_row.addWidget(self._invincible_mode)
        option_row.addWidget(self._super_attack)
        option_row.addStretch(1)
        header_layout.addLayout(option_row)
        root.addWidget(header)
        self._tabs = QTabWidget(self)
        self._tabs.setObjectName('trainerTabs')
        basic_body, self._basic_spins, self._basic_labels = self._make_stats_grid(BASIC_STATS)
        hidden_body, self._hidden_spins, self._hidden_labels = self._make_stats_grid(HIDDEN_STATS)
        self._tabs.addTab(self._make_tab_page(basic_body), '')
        self._tabs.addTab(self._make_tab_page(hidden_body), '')
        root.addWidget(self._tabs, 1)
        self.installEventFilter(self)
        for child in self.findChildren(QWidget):
            if child is not self:
                child.installEventFilter(self)
        self.retranslate_ui()

    def _make_tab_page(self, body: QWidget) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(20, 16, 20, 16)
        page_layout.setSpacing(12)
        scroll = QScrollArea(page)
        scroll.setObjectName('panelScroll')
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setObjectName('panelScrollViewport')
        scroll.viewport().setAutoFillBackground(False)
        body.setAutoFillBackground(False)
        scroll.setWidget(body)
        page_layout.addWidget(scroll, 1)
        return page

    def _make_stats_grid(
        self,
        stat_defs: tuple,
        *,
        spell_id: int | None = None,
    ) -> tuple[QWidget, dict[str, TrainerCommitSpinBox], dict[str, QLabel]]:
        body = QWidget()
        body.setObjectName('panelScrollContent')
        body.setAutoFillBackground(False)
        layout = QGridLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(8)
        spins: dict[str, TrainerCommitSpinBox] = {}
        labels: dict[str, QLabel] = {}
        for row, item in enumerate(stat_defs):
            label = QLabel(body)
            label.setObjectName('fieldLabel')
            spin = TrainerCommitSpinBox(body)
            spin.setRange(-99999, 999999)
            spin.setDecimals(item.decimals)
            spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
            spin.setProperty('stat_key', item.key)
            spin.setProperty('spell_id', spell_id if spell_id is not None else -1)
            spin.value_committed.connect(self._on_stat_committed)
            layout.addWidget(label, row, 0)
            layout.addWidget(spin, row, 1)
            labels[item.key] = label
            spins[item.key] = spin
        return body, spins, labels

    def _rebuild_spell_tabs(self, spells: list[dict]) -> None:
        preserve_id = None
        current_index = self._tabs.currentIndex()
        if current_index >= 2:
            spell_index = current_index - 2
            if 0 <= spell_index < len(self._spell_tab_spell_ids):
                preserve_id = self._spell_tab_spell_ids[spell_index]
        while self._tabs.count() > 2:
            widget = self._tabs.widget(2)
            self._tabs.removeTab(2)
            if widget is not None:
                widget.deleteLater()
        self._spell_spins.clear()
        self._spell_labels.clear()
        self._spell_tab_spell_ids.clear()
        self._spell_names.clear()
        restore_index = 0
        for index, spell in enumerate(spells):
            spell_id = int(spell['id'])
            name = str(spell.get('name', spell_id))
            self._spell_names[spell_id] = name
            tab_body, spins, labels = self._make_stats_grid(SPELL_STATS, spell_id=spell_id)
            self._tabs.addTab(self._make_tab_page(tab_body), trainer_tab_label('spell', name=f'#{name}'))
            self._spell_tab_spell_ids.append(spell_id)
            for key, spin in spins.items():
                self._spell_spins[(spell_id, key)] = spin
            for key, label in labels.items():
                self._spell_labels[(spell_id, key)] = label
            if preserve_id is not None and spell_id == preserve_id:
                restore_index = 2 + index
        if preserve_id is not None and self._tabs.count() > restore_index:
            self._tabs.setCurrentIndex(restore_index)

    def retranslate_ui(self) -> None:
        self._start_btn.setText(tr('toolbar.start_trainer'))
        self._refresh_btn.setText(tr('toolbar.refresh_trainer'))
        self._invincible_mode.setText(tr('trainer.invincible'))
        self._super_attack.setText(tr('trainer.super_attack'))
        if self._tabs.count() >= 2:
            self._tabs.setTabText(0, trainer_tab_label('basic'))
            self._tabs.setTabText(1, trainer_tab_label('hidden'))
        for key, label in self._basic_labels.items():
            label.setText(stat_label(key))
        for key, label in self._hidden_labels.items():
            label.setText(stat_label(key))
        for index, spell_id in enumerate(self._spell_tab_spell_ids):
            name = self._spell_names.get(spell_id, str(spell_id))
            self._tabs.setTabText(2 + index, trainer_tab_label('spell', name=f'#{name}'))
        for (spell_id, key), label in self._spell_labels.items():
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
        view_model.spells_changed.connect(self._on_spells_changed)
        view_model.attach_succeeded.connect(self._on_attach_state_changed)
        view_model.attach_failed.connect(self._on_attach_state_changed)
        self.set_attached_ui(view_model.attached)

    def set_attached_ui(self, attached: bool) -> None:
        self._start_btn.setEnabled(not attached)
        self._refresh_btn.setEnabled(attached)
        if attached:
            self._start_btn.setObjectName('trainerStartBtnActive')
        else:
            self._start_btn.setObjectName('trainerStartBtn')
        self._start_btn.style().unpolish(self._start_btn)
        self._start_btn.style().polish(self._start_btn)

    def _on_start_clicked(self) -> None:
        if self._vm is None or self._vm.attached:
            return
        self._start_btn.setEnabled(False)
        self._refresh_btn.setEnabled(False)
        self._vm.attach()

    def _on_refresh_clicked(self) -> None:
        if self._vm is None or not self._vm.attached:
            return
        self._refresh_btn.setEnabled(False)
        self._vm.reattach()

    def _on_attach_state_changed(self) -> None:
        if self._vm is None:
            return
        self.set_attached_ui(self._vm.attached)

    def _on_spells_changed(self, spells: list) -> None:
        self._rebuild_spell_tabs(spells)

    def _on_stats_updated(self, stats: dict, spells: list) -> None:
        self._updating = True
        for key, spin in self._basic_spins.items():
            if key in stats and not spin.hasFocus():
                spin.setValue(float(stats[key]))
        for key, spin in self._hidden_spins.items():
            if key in stats and not spin.hasFocus():
                spin.setValue(float(stats[key]))
        for spell in spells:
            spell_id = int(spell['id'])
            spell_stats = spell.get('stats', {})
            for key, value in spell_stats.items():
                spin = self._spell_spins.get((spell_id, key))
                if spin is not None and not spin.hasFocus():
                    spin.setValue(float(value))
        self._updating = False

    def _on_stat_committed(self, value: float) -> None:
        if self._updating or self._vm is None:
            return
        spin = self.sender()
        if spin is None:
            return
        key = spin.property('stat_key')
        if not key:
            return
        spell_id = spin.property('spell_id')
        sid = None if spell_id is None or int(spell_id) < 0 else int(spell_id)
        self._vm.apply_stat(str(key), value, spell_id=sid)

    def _on_invincible_toggled(self, checked: bool) -> None:
        if self._updating or self._vm is None:
            return
        self._vm.set_invincible_mode(checked)

    def _on_super_attack_toggled(self, checked: bool) -> None:
        if self._updating or self._vm is None:
            return
        self._vm.set_super_attack(checked)
