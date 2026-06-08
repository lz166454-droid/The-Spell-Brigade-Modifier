from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QSpinBox, QVBoxLayout, QWidget
from ui.i18n import tr
from ui.widgets.safety_banner import SafetyBanner
from ui.widgets.slot_grid import SlotGrid

class OverviewPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating = False
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)
        self._banner = SafetyBanner(self)
        root.addWidget(self._banner)
        resource_card = QFrame(self)
        resource_card.setObjectName('panelCard')
        resource_layout = QVBoxLayout(resource_card)
        resource_layout.setContentsMargins(16, 16, 16, 16)
        resource_layout.setSpacing(12)
        self._title = QLabel(resource_card)
        self._title.setObjectName('sectionTitle')
        resource_layout.addWidget(self._title)
        gold_row = QHBoxLayout()
        gold_row.setSpacing(12)
        self._gold_label = QLabel(resource_card)
        self._gold_label.setObjectName('fieldLabel')
        self._gold_spin = QSpinBox(resource_card)
        self._gold_spin.setRange(0, 999_999_999)
        self._gold_spin.setGroupSeparatorShown(True)
        self._gold_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self._gold_spin.valueChanged.connect(self._on_gold_changed)
        gold_row.addWidget(self._gold_label)
        gold_row.addWidget(self._gold_spin, 1)
        resource_layout.addLayout(gold_row)
        preset_row = QHBoxLayout()
        preset_row.setSpacing(8)
        for value, label in ((50_000, '50k'), (100_000, '100k'), (999_999, '999k')):
            btn = QPushButton(label, resource_card)
            btn.setObjectName('goldPresetBtn')
            btn.clicked.connect(lambda checked=False, v=value: self._gold_spin.setValue(v))
            preset_row.addWidget(btn)
        preset_row.addStretch(1)
        resource_layout.addLayout(preset_row)
        stats_row = QHBoxLayout()
        stats_row.setSpacing(24)
        self._play_time_label = QLabel(resource_card)
        self._play_time_label.setObjectName('statValue')
        self._version_label = QLabel(resource_card)
        self._version_label.setObjectName('statValue')
        self._achievement_label = QLabel(resource_card)
        self._achievement_label.setObjectName('statValue')
        stats_row.addWidget(self._play_time_label)
        stats_row.addWidget(self._version_label)
        stats_row.addWidget(self._achievement_label)
        stats_row.addStretch(1)
        resource_layout.addLayout(stats_row)
        root.addWidget(resource_card)
        slot_card = QFrame(self)
        slot_card.setObjectName('slotPanel')
        slot_card.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        slot_layout = QVBoxLayout(slot_card)
        slot_layout.setContentsMargins(16, 12, 16, 12)
        slot_layout.setSpacing(6)
        self._slot_title = QLabel(slot_card)
        self._slot_title.setObjectName('sectionTitle')
        self._slot_hint = QLabel(slot_card)
        self._slot_hint.setObjectName('sectionHint')
        slot_layout.addWidget(self._slot_title)
        slot_layout.addWidget(self._slot_hint)
        self._slot_grid = SlotGrid(slot_card)
        slot_layout.addWidget(self._slot_grid, 0, Qt.AlignmentFlag.AlignTop)
        root.addWidget(slot_card)
        root.addStretch(1)
        self._vm = None
        self.retranslate_ui()

    def bind(self, view_model) -> None:
        self._vm = view_model

    def retranslate_ui(self) -> None:
        self._title.setText(tr('overview.title'))
        self._gold_label.setText(tr('overview.gold'))
        self._slot_title.setText(tr('overview.slot_title'))
        self._slot_hint.setText(tr('overview.slot_hint'))
        self._slot_grid.retranslate_ui()
        self.refresh()

    def refresh(self) -> None:
        if self._vm is None:
            return
        data = self._vm.get_save_data()
        if data is None:
            self._play_time_label.setText(tr('overview.play_time_empty'))
            self._version_label.setText(tr('overview.version_empty'))
            self._achievement_label.setText(tr('overview.achievement_empty'))
            return
        self._updating = True
        self._gold_spin.setValue(data.gold)
        self._updating = False
        completed = sum(1 for item in data.challenges.values() if item.is_completed)
        total = len(data.challenges)
        self._play_time_label.setText(tr('overview.play_time', minutes=data.play_time_in_minutes))
        self._version_label.setText(tr('overview.version', version=data.version_number))
        self._achievement_label.setText(tr('overview.achievement', completed=completed, total=total))
        self._slot_grid.update_slots(self._vm.get_slot_summaries(), self._vm.active_slot)
        self._refresh_banner()

    def _refresh_banner(self) -> None:
        if self._vm is None:
            return
        if self._vm.is_game_running():
            self._banner.show_warning(tr('banner.game_running'))
            return
        self._banner.show_ok(tr('banner.game_safe'))

    def _on_gold_changed(self, value: int) -> None:
        if self._updating or self._vm is None:
            return
        self._vm.set_gold(value)
