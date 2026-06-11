from PySide6.QtCore import QEvent, Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QScrollArea, QSizePolicy, QTabWidget, QVBoxLayout,
    QWidget,
)
from lab.trainer.stats_meta import BASIC_STATS, HIDDEN_STATS
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
        self._tab_preview_active = False
        self._basic_spins: dict[str, TrainerCommitSpinBox] = {}
        self._basic_labels: dict[str, QLabel] = {}
        self._hidden_spins: dict[str, TrainerCommitSpinBox] = {}
        self._hidden_labels: dict[str, QLabel] = {}
        self._spell_spins: dict[tuple[int, str], TrainerCommitSpinBox] = {}
        self._spell_labels: dict[tuple[int, str], QLabel] = {}
        self._spell_tab_spell_ids: list[int] = []
        self._spell_tab_names: dict[int, str] = {}
        self._spell_label_keys: dict[tuple[int, str], str] = {}
        self._basic_section_title: QLabel | None = None
        self._hidden_section_title: QLabel | None = None
        self._preset_section_title: QLabel | None = None
        self._preset_list: QListWidget | None = None
        self._preset_empty_hint: QLabel | None = None
        self._preset_apply_btn: QPushButton | None = None
        self._preset_preview_btn: QPushButton | None = None
        self._preset_save_btn: QPushButton | None = None
        self._preset_default_btn: QPushButton | None = None
        self._preset_rename_btn: QPushButton | None = None
        self._preset_delete_btn: QPushButton | None = None
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
        basic_body, self._basic_spins, self._basic_labels, self._hidden_spins, self._hidden_labels = self._make_combined_basic_body()
        self._tabs.addTab(self._make_tab_page(basic_body), '')
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
        scroll.setWidget(self._wrap_left_aligned(body))
        page_layout.addWidget(scroll, 1)
        return page

    @staticmethod
    def _wrap_left_aligned(body: QWidget) -> QWidget:
        body.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        wrap = QWidget()
        wrap.setAutoFillBackground(False)
        wrap_layout = QHBoxLayout(wrap)
        wrap_layout.setContentsMargins(0, 0, 0, 0)
        wrap_layout.setSpacing(0)
        wrap_layout.addWidget(body, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        wrap_layout.addStretch(1)
        return wrap

    @staticmethod
    def _make_column_divider(parent: QWidget) -> QFrame:
        divider = QFrame(parent)
        divider.setObjectName('trainerColumnDivider')
        divider.setFrameShape(QFrame.Shape.VLine)
        divider.setFrameShadow(QFrame.Shadow.Plain)
        divider.setFixedWidth(1)
        return divider

    def _make_combined_basic_body(
        self,
    ) -> tuple[QWidget, dict[str, TrainerCommitSpinBox], dict[str, QLabel], dict[str, TrainerCommitSpinBox], dict[str, QLabel]]:
        body = QWidget()
        body.setObjectName('panelScrollContent')
        body.setAutoFillBackground(False)
        body.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        row = QHBoxLayout(body)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        left_col, basic_spins, basic_labels, self._basic_section_title = self._make_stats_column(BASIC_STATS, 'basic')
        right_col, hidden_spins, hidden_labels, self._hidden_section_title = self._make_stats_column(HIDDEN_STATS, 'hidden')
        preset_col = self._make_preset_column(body)
        divider_left = self._make_column_divider(body)
        divider_right = self._make_column_divider(body)
        row.addWidget(left_col, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        row.addWidget(divider_left, 0)
        row.addWidget(right_col, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        row.addWidget(divider_right, 0)
        row.addWidget(preset_col, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        row.addStretch(1)
        return body, basic_spins, basic_labels, hidden_spins, hidden_labels

    def _make_preset_column(self, parent: QWidget) -> QWidget:
        column = QWidget(parent)
        column.setAutoFillBackground(False)
        column.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        column.setFixedWidth(220)
        column_layout = QVBoxLayout(column)
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.setSpacing(8)
        self._preset_section_title = QLabel(column)
        self._preset_section_title.setObjectName('sectionTitle')
        column_layout.addWidget(self._preset_section_title)
        self._preset_list = QListWidget(column)
        self._preset_list.setObjectName('trainerPresetList')
        self._preset_list.setMinimumHeight(180)
        self._preset_list.itemSelectionChanged.connect(self._update_preset_actions)
        self._preset_list.itemDoubleClicked.connect(self._on_preset_preview_clicked)
        column_layout.addWidget(self._preset_list, 1)
        self._preset_empty_hint = QLabel(column)
        self._preset_empty_hint.setObjectName('placeholderLabel')
        self._preset_empty_hint.setWordWrap(True)
        column_layout.addWidget(self._preset_empty_hint)
        action_row_top = QHBoxLayout()
        action_row_top.setSpacing(8)
        self._preset_preview_btn = QPushButton(column)
        self._preset_preview_btn.setObjectName('secondaryBtn')
        self._preset_apply_btn = QPushButton(column)
        self._preset_apply_btn.setObjectName('trainerPresetApplyBtn')
        self._preset_save_btn = QPushButton(column)
        self._preset_save_btn.setObjectName('secondaryBtn')
        self._preset_preview_btn.clicked.connect(self._on_preset_preview_clicked)
        self._preset_apply_btn.clicked.connect(self._on_preset_apply_clicked)
        self._preset_save_btn.clicked.connect(self._on_preset_save_clicked)
        action_row_top.addWidget(self._preset_preview_btn)
        action_row_top.addWidget(self._preset_apply_btn)
        column_layout.addLayout(action_row_top)
        action_row_save = QHBoxLayout()
        action_row_save.setSpacing(8)
        action_row_save.addWidget(self._preset_save_btn)
        column_layout.addLayout(action_row_save)
        action_row_bottom = QHBoxLayout()
        action_row_bottom.setSpacing(8)
        self._preset_default_btn = QPushButton(column)
        self._preset_default_btn.setObjectName('secondaryBtn')
        action_row_bottom.addWidget(self._preset_default_btn)
        column_layout.addLayout(action_row_bottom)
        action_row_manage = QHBoxLayout()
        action_row_manage.setSpacing(8)
        self._preset_rename_btn = QPushButton(column)
        self._preset_rename_btn.setObjectName('secondaryBtn')
        self._preset_delete_btn = QPushButton(column)
        self._preset_delete_btn.setObjectName('secondaryBtn')
        self._preset_default_btn.clicked.connect(self._on_preset_default_clicked)
        self._preset_rename_btn.clicked.connect(self._on_preset_rename_clicked)
        self._preset_delete_btn.clicked.connect(self._on_preset_delete_clicked)
        action_row_manage.addWidget(self._preset_rename_btn)
        action_row_manage.addWidget(self._preset_delete_btn)
        column_layout.addLayout(action_row_manage)
        return column

    def _make_stats_column(
        self,
        stat_defs: tuple,
        section_key: str,
    ) -> tuple[QWidget, dict[str, TrainerCommitSpinBox], dict[str, QLabel], QLabel]:
        column = QWidget()
        column.setAutoFillBackground(False)
        column.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        column_layout = QVBoxLayout(column)
        column_layout.setContentsMargins(0, 0, 0, 0)
        column_layout.setSpacing(8)
        section_title = QLabel(column)
        section_title.setObjectName('sectionTitle')
        section_title.setText(trainer_tab_label(section_key))
        column_layout.addWidget(section_title)
        grid_body, spins, labels = self._make_stats_grid(stat_defs)
        column_layout.addWidget(grid_body)
        column_layout.addStretch(1)
        return column, spins, labels, section_title

    def _make_stats_grid(
        self,
        stat_defs: tuple,
        *,
        spell_id: int | None = None,
    ) -> tuple[QWidget, dict[str, TrainerCommitSpinBox], dict[str, QLabel]]:
        body = QWidget()
        body.setObjectName('panelScrollContent')
        body.setAutoFillBackground(False)
        body.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        layout = QGridLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(4)
        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 1)
        spins: dict[str, TrainerCommitSpinBox] = {}
        labels: dict[str, QLabel] = {}
        for row, item in enumerate(stat_defs):
            label = QLabel(body)
            label.setObjectName('fieldLabel')
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            label.setText(stat_label(item.key))
            spin = TrainerCommitSpinBox(body)
            spin.setObjectName('trainerStatSpin')
            spin.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            spin.setFixedWidth(112)
            spin.setRange(-99999, 999999)
            spin.setDecimals(item.decimals)
            spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
            spin.setProperty('stat_key', item.key)
            spin.setProperty('spell_id', spell_id if spell_id is not None else -1)
            spin.value_committed.connect(self._on_stat_committed)
            layout.addWidget(label, row, 0)
            layout.addWidget(spin, row, 1, Qt.AlignmentFlag.AlignLeft)
            labels[item.key] = label
            spins[item.key] = spin
        layout.setRowStretch(len(stat_defs), 1)
        return body, spins, labels

    def _rebuild_spell_tabs(self, spells: list[dict]) -> None:
        preserve_id = None
        current_index = self._tabs.currentIndex()
        if current_index >= 1:
            spell_index = current_index - 1
            if 0 <= spell_index < len(self._spell_tab_spell_ids):
                preserve_id = self._spell_tab_spell_ids[spell_index]
        while self._tabs.count() > 1:
            widget = self._tabs.widget(1)
            self._tabs.removeTab(1)
            if widget is not None:
                widget.deleteLater()
        self._spell_spins.clear()
        self._spell_labels.clear()
        self._spell_tab_spell_ids.clear()
        self._spell_tab_names.clear()
        self._spell_label_keys.clear()
        restore_index = 0
        for index, spell in enumerate(spells):
            spell_id = int(spell['id'])
            display_name = str(spell.get('name', spell_id))
            self._spell_tab_names[spell_id] = display_name
            stat_fields = spell.get('stat_fields', [])
            tab_body, spins, labels = self._make_dynamic_stats_grid(stat_fields, spell_id=spell_id)
            self._tabs.addTab(self._make_tab_page(tab_body), trainer_tab_label('spell', name=display_name))
            self._spell_tab_spell_ids.append(spell_id)
            for key, spin in spins.items():
                self._spell_spins[(spell_id, key)] = spin
            for key, label in labels.items():
                self._spell_labels[(spell_id, key)] = label
            for field in stat_fields:
                field_key = field['key']
                self._spell_label_keys[(spell_id, field_key)] = field['label_key']
            if preserve_id is not None and spell_id == preserve_id:
                restore_index = 1 + index
        if preserve_id is not None and self._tabs.count() > restore_index:
            self._tabs.setCurrentIndex(restore_index)

    def _make_dynamic_stats_grid(
        self,
        stat_fields: list[dict],
        *,
        spell_id: int,
    ) -> tuple[QWidget, dict[str, TrainerCommitSpinBox], dict[str, QLabel]]:
        body = QWidget()
        body.setObjectName('panelScrollContent')
        body.setAutoFillBackground(False)
        body.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Expanding)
        layout = QGridLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(4)
        layout.setColumnStretch(0, 0)
        layout.setColumnStretch(1, 0)
        layout.setColumnStretch(2, 1)
        spins: dict[str, TrainerCommitSpinBox] = {}
        labels: dict[str, QLabel] = {}
        for row, field in enumerate(stat_fields):
            key = field['key']
            label_key = field['label_key']
            decimals = int(field.get('decimals', 2))
            label = QLabel(body)
            label.setObjectName('fieldLabel')
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            label.setText(stat_label(label_key))
            spin = TrainerCommitSpinBox(body)
            spin.setObjectName('trainerStatSpin')
            spin.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            spin.setFixedWidth(112)
            spin.setRange(-99999, 999999)
            spin.setDecimals(decimals)
            spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)
            spin.setProperty('stat_key', key)
            spin.setProperty('spell_id', spell_id)
            spin.value_committed.connect(self._on_stat_committed)
            layout.addWidget(label, row, 0)
            layout.addWidget(spin, row, 1, Qt.AlignmentFlag.AlignLeft)
            labels[key] = label
            spins[key] = spin
        layout.setRowStretch(len(stat_fields), 1)
        return body, spins, labels

    def retranslate_ui(self) -> None:
        self._start_btn.setText(tr('toolbar.start_trainer'))
        self._refresh_btn.setText(tr('toolbar.refresh_trainer'))
        self._invincible_mode.setText(tr('trainer.invincible'))
        self._super_attack.setText(tr('trainer.super_attack'))
        if self._tabs.count() >= 1:
            self._tabs.setTabText(0, trainer_tab_label('basic'))
        if self._basic_section_title is not None:
            self._basic_section_title.setText(trainer_tab_label('basic'))
        if self._hidden_section_title is not None:
            self._hidden_section_title.setText(trainer_tab_label('hidden'))
        for key, label in self._basic_labels.items():
            label.setText(stat_label(key))
        for key, label in self._hidden_labels.items():
            label.setText(stat_label(key))
        for index, spell_id in enumerate(self._spell_tab_spell_ids):
            display_name = self._spell_tab_names.get(spell_id, str(spell_id))
            self._tabs.setTabText(1 + index, trainer_tab_label('spell', name=display_name))
        for (spell_id, key), label in self._spell_labels.items():
            label_key = self._spell_label_keys.get((spell_id, key), key)
            label.setText(stat_label(label_key))
        if self._preset_section_title is not None:
            self._preset_section_title.setText(tr('trainer.tab.presets'))
        if self._preset_empty_hint is not None:
            self._preset_empty_hint.setText(tr('trainer.preset.empty_hint'))
        if self._preset_preview_btn is not None:
            self._preset_preview_btn.setText(tr('trainer.preset.preview'))
        if self._preset_apply_btn is not None:
            self._preset_apply_btn.setText(tr('trainer.preset.apply'))
        if self._preset_save_btn is not None:
            self._preset_save_btn.setText(tr('trainer.preset.save_as'))
        if self._preset_rename_btn is not None:
            self._preset_rename_btn.setText(tr('trainer.preset.rename'))
        if self._preset_delete_btn is not None:
            self._preset_delete_btn.setText(tr('trainer.preset.delete'))
        self._refresh_preset_list()

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
        return False

    def bind(self, view_model: TrainerViewModel) -> None:
        self._vm = view_model
        view_model.stats_updated.connect(self._on_stats_updated)
        view_model.spells_changed.connect(self._on_spells_changed)
        view_model.attach_succeeded.connect(self._on_attach_state_changed)
        view_model.attach_failed.connect(self._on_attach_state_changed)
        view_model.presets_changed.connect(self._refresh_preset_list)
        self.set_attached_ui(view_model.attached)
        self._refresh_preset_list()

    def set_attached_ui(self, attached: bool) -> None:
        self._start_btn.setEnabled(not attached)
        self._refresh_btn.setEnabled(attached)
        if attached:
            self._start_btn.setObjectName('trainerStartBtnActive')
        else:
            self._start_btn.setObjectName('trainerStartBtn')
        self._start_btn.style().unpolish(self._start_btn)
        self._start_btn.style().polish(self._start_btn)
        self._update_preset_actions()

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
        if self._vm.attached:
            self._tab_preview_active = False
        self.set_attached_ui(self._vm.attached)

    def _on_spells_changed(self, spells: list) -> None:
        self._rebuild_spell_tabs(spells)

    def _on_stats_updated(self, stats: dict, spells: list) -> None:
        self._updating = True
        if not self._tab_preview_active:
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
        if str(key) in self._basic_spins or str(key) in self._hidden_spins:
            self._tab_preview_active = False
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

    def _selected_preset_id(self) -> str | None:
        if self._preset_list is None:
            return None
        item = self._preset_list.currentItem()
        if item is None:
            return None
        preset_id = item.data(Qt.ItemDataRole.UserRole)
        return str(preset_id) if preset_id else None

    def _capture_tab_stats(self) -> dict[str, float]:
        stats: dict[str, float] = {}
        for key, spin in self._basic_spins.items():
            stats[key] = float(spin.value())
        for key, spin in self._hidden_spins.items():
            stats[key] = float(spin.value())
        return stats

    def _refresh_preset_list(self) -> None:
        if self._vm is None or self._preset_list is None:
            return
        selected_id = self._selected_preset_id()
        default_id = self._vm.preset_store.default_preset_id
        self._preset_list.blockSignals(True)
        self._preset_list.clear()
        presets = self._vm.preset_store.list_presets()
        restore_row = -1
        for index, preset in enumerate(presets):
            label = tr('trainer.preset.default_mark', name=preset.name) if preset.id == default_id else preset.name
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, preset.id)
            self._preset_list.addItem(item)
            if preset.id == selected_id:
                restore_row = index
        if restore_row >= 0:
            self._preset_list.setCurrentRow(restore_row)
        self._preset_list.blockSignals(False)
        if self._preset_empty_hint is not None:
            self._preset_empty_hint.setVisible(not presets)
        self._update_preset_actions()

    def _update_preset_actions(self) -> None:
        selected_id = self._selected_preset_id()
        attached = self._vm is not None and self._vm.attached
        if self._preset_preview_btn is not None:
            self._preset_preview_btn.setEnabled(selected_id is not None)
        if self._preset_apply_btn is not None:
            self._preset_apply_btn.setEnabled(selected_id is not None and attached)
        if self._preset_save_btn is not None:
            self._preset_save_btn.setEnabled(True)
        if self._preset_rename_btn is not None:
            self._preset_rename_btn.setEnabled(selected_id is not None)
        if self._preset_delete_btn is not None:
            self._preset_delete_btn.setEnabled(selected_id is not None)
        if self._preset_default_btn is not None:
            is_default = selected_id is not None and self._vm is not None and selected_id == self._vm.preset_store.default_preset_id
            self._preset_default_btn.setEnabled(selected_id is not None)
            self._preset_default_btn.setText(tr('trainer.preset.clear_default') if is_default else tr('trainer.preset.set_default'))

    def _clear_tab_spin_focus(self) -> None:
        for spin in list(self._basic_spins.values()) + list(self._hidden_spins.values()):
            if spin.hasFocus():
                spin.clearFocus()

    def _show_preset_preview(self, stats: dict[str, float]) -> None:
        self._clear_tab_spin_focus()
        self._updating = True
        self._tab_preview_active = True
        for key, spin in self._basic_spins.items():
            if key in stats:
                spin.setValue(float(stats[key]))
        for key, spin in self._hidden_spins.items():
            if key in stats:
                spin.setValue(float(stats[key]))
        self._updating = False

    def _on_preset_preview_clicked(self, *_args) -> None:
        if self._vm is None:
            return
        preset_id = self._selected_preset_id()
        if preset_id is None:
            return
        preset = self._vm.preset_store.get_preset(preset_id)
        if preset is None:
            return
        self._show_preset_preview(preset.stats)

    def _on_preset_apply_clicked(self, *_args) -> None:
        if self._vm is None or not self._vm.attached:
            return
        preset_id = self._selected_preset_id()
        if preset_id is None:
            return
        self._tab_preview_active = False
        self._vm.apply_preset(preset_id)
        self._flash_preset_apply_btn()

    def _flash_preset_apply_btn(self) -> None:
        btn = self._preset_apply_btn
        if btn is None:
            return
        btn.setObjectName('trainerPresetApplyBtnFlash')
        btn.style().unpolish(btn)
        btn.style().polish(btn)
        QTimer.singleShot(380, self._restore_preset_apply_btn_style)

    def _restore_preset_apply_btn_style(self) -> None:
        btn = self._preset_apply_btn
        if btn is None:
            return
        btn.setObjectName('trainerPresetApplyBtn')
        btn.style().unpolish(btn)
        btn.style().polish(btn)

    def _on_preset_save_clicked(self) -> None:
        if self._vm is None:
            return
        stats = self._capture_tab_stats()
        name, ok = QInputDialog.getText(self, tr('trainer.preset.save_dialog_title'), tr('trainer.preset.save_dialog_label'))
        if not ok:
            return
        trimmed = name.strip()
        if not trimmed:
            QMessageBox.warning(self, tr('trainer.preset.dialog_title'), tr('trainer.preset.error.empty_name'))
            return
        existing = self._vm.preset_store.find_by_name(trimmed)
        if existing is not None:
            answer = QMessageBox.question(
                self,
                tr('trainer.preset.dialog_title'),
                tr('trainer.preset.confirm_overwrite', name=trimmed),
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
            try:
                self._vm.save_preset(trimmed, stats, preset_id=existing.id)
            except ValueError:
                QMessageBox.warning(self, tr('trainer.preset.dialog_title'), tr('trainer.preset.error.name_too_long'))
                return
            self._refresh_preset_list()
            return
        try:
            preset = self._vm.save_preset(trimmed, stats)
        except ValueError as exc:
            message = tr('trainer.preset.error.name_too_long') if str(exc) == 'name_too_long' else tr('trainer.preset.error.empty_name')
            QMessageBox.warning(self, tr('trainer.preset.dialog_title'), message)
            return
        if self._preset_list is not None:
            for row in range(self._preset_list.count()):
                item = self._preset_list.item(row)
                if item is not None and item.data(Qt.ItemDataRole.UserRole) == preset.id:
                    self._preset_list.setCurrentRow(row)
                    break

    def _on_preset_default_clicked(self) -> None:
        if self._vm is None:
            return
        preset_id = self._selected_preset_id()
        if preset_id is None:
            return
        if preset_id == self._vm.preset_store.default_preset_id:
            self._vm.set_default_preset(None)
        else:
            self._vm.set_default_preset(preset_id)

    def _on_preset_rename_clicked(self) -> None:
        if self._vm is None:
            return
        preset_id = self._selected_preset_id()
        if preset_id is None:
            return
        preset = self._vm.preset_store.get_preset(preset_id)
        if preset is None:
            return
        name, ok = QInputDialog.getText(
            self,
            tr('trainer.preset.rename_dialog_title'),
            tr('trainer.preset.save_dialog_label'),
            text=preset.name,
        )
        if not ok:
            return
        trimmed = name.strip()
        if not trimmed:
            QMessageBox.warning(self, tr('trainer.preset.dialog_title'), tr('trainer.preset.error.empty_name'))
            return
        try:
            self._vm.rename_preset(preset_id, trimmed)
        except ValueError as exc:
            if str(exc) == 'duplicate_name':
                QMessageBox.warning(self, tr('trainer.preset.dialog_title'), tr('trainer.preset.error.duplicate_name'))
            elif str(exc) == 'name_too_long':
                QMessageBox.warning(self, tr('trainer.preset.dialog_title'), tr('trainer.preset.error.name_too_long'))
            else:
                QMessageBox.warning(self, tr('trainer.preset.dialog_title'), tr('trainer.preset.error.empty_name'))
            return

    def _on_preset_delete_clicked(self) -> None:
        if self._vm is None:
            return
        preset_id = self._selected_preset_id()
        if preset_id is None:
            return
        preset = self._vm.preset_store.get_preset(preset_id)
        if preset is None:
            return
        is_default = preset_id == self._vm.preset_store.default_preset_id
        message = tr('trainer.preset.confirm_delete_default', name=preset.name) if is_default else tr('trainer.preset.confirm_delete', name=preset.name)
        answer = QMessageBox.question(self, tr('trainer.preset.dialog_title'), message)
        if answer != QMessageBox.StandardButton.Yes:
            return
        self._vm.delete_preset(preset_id)
