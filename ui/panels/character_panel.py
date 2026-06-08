from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea, QSpinBox, QVBoxLayout, QWidget
from lab.game_metadata import character_display_class, character_display_name, get_characters
from ui.i18n import tr

class CharacterPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._updating = False
        self._rows: dict[int, dict] = {}
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)
        header = QHBoxLayout()
        self._title = QLabel(self)
        self._title.setObjectName('sectionTitle')
        self._summary = QLabel('', self)
        self._summary.setObjectName('statValue')
        self._max_all_btn = QPushButton(self)
        self._max_all_btn.setObjectName('secondaryBtn')
        self._max_all_btn.clicked.connect(self._on_max_all)
        header.addWidget(self._title)
        header.addStretch(1)
        header.addWidget(self._summary)
        header.addWidget(self._max_all_btn)
        root.addLayout(header)
        scroll = QScrollArea(self)
        scroll.setObjectName('panelScroll')
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.viewport().setObjectName('panelScrollViewport')
        scroll.viewport().setAutoFillBackground(False)
        self._list_host = QWidget(scroll)
        self._list_host.setObjectName('panelScrollContent')
        self._list_host.setAutoFillBackground(False)
        self._list_layout = QVBoxLayout(self._list_host)
        self._list_layout.setContentsMargins(0, 0, 0, 0)
        self._list_layout.setSpacing(8)
        scroll.setWidget(self._list_host)
        root.addWidget(scroll, 1)
        self._vm = None
        self._build_rows()
        self.retranslate_ui()

    def _build_rows(self) -> None:
        for meta in get_characters():
            card = QFrame(self._list_host)
            card.setObjectName('panelCard')
            row = QHBoxLayout(card)
            row.setContentsMargins(12, 8, 12, 8)
            row.setSpacing(12)
            name_label = QLabel(character_display_name(meta), card)
            name_label.setObjectName('fieldLabel')
            class_label = QLabel(character_display_class(meta), card)
            class_label.setObjectName('statValue')
            level_label = QLabel(card)
            level_label.setObjectName('fieldLabel')
            level_spin = QSpinBox(card)
            level_spin.setRange(1, meta.max_level)
            level_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
            level_spin.valueChanged.connect(lambda value, cid=meta.id: self._on_level_changed(cid, value))
            prestige_label = QLabel(card)
            prestige_label.setObjectName('fieldLabel')
            prestige_spin = QSpinBox(card)
            prestige_spin.setRange(0, 10)
            prestige_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
            prestige_spin.valueChanged.connect(lambda value, cid=meta.id: self._on_prestige_changed(cid, value))
            unlock_btn = QPushButton(card)
            unlock_btn.setObjectName('goldPresetBtn')
            unlock_btn.clicked.connect(lambda checked=False, cid=meta.id: self._on_unlock(cid))
            row.addWidget(name_label)
            row.addWidget(class_label, 1)
            row.addWidget(level_label)
            row.addWidget(level_spin)
            row.addWidget(prestige_label)
            row.addWidget(prestige_spin)
            row.addWidget(unlock_btn)
            self._list_layout.addWidget(card)
            self._rows[meta.id] = {
                'meta': meta,
                'name_label': name_label,
                'class_label': class_label,
                'level_label': level_label,
                'prestige_label': prestige_label,
                'level_spin': level_spin,
                'prestige_spin': prestige_spin,
                'unlock_btn': unlock_btn,
            }

    def bind(self, view_model) -> None:
        self._vm = view_model

    def retranslate_ui(self) -> None:
        self._title.setText(tr('character.title'))
        self._max_all_btn.setText(tr('character.max_all'))
        for widgets in self._rows.values():
            meta = widgets['meta']
            widgets['name_label'].setText(character_display_name(meta))
            widgets['class_label'].setText(character_display_class(meta))
            widgets['level_label'].setText(tr('character.level'))
            widgets['prestige_label'].setText(tr('character.prestige'))
        self.refresh()

    def refresh(self) -> None:
        if self._vm is None:
            return
        data = self._vm.get_save_data()
        if data is None:
            return
        self._updating = True
        unlocked = 0
        for character_id, widgets in self._rows.items():
            rank = data.character_ranks.get(character_id)
            level_spin = widgets['level_spin']
            prestige_spin = widgets['prestige_spin']
            unlock_btn = widgets['unlock_btn']
            if rank is None:
                level_spin.setEnabled(False)
                prestige_spin.setEnabled(False)
                unlock_btn.setEnabled(True)
                unlock_btn.setText(tr('character.unlock'))
            else:
                unlocked += 1
                level_spin.setEnabled(True)
                unlock_btn.setEnabled(False)
                unlock_btn.setText(tr('character.unlocked'))
                level_spin.setValue(rank.current_rank)
                has_prestige = rank.prestige is not None
                prestige_spin.setEnabled(has_prestige)
                if has_prestige:
                    prestige_spin.setValue(rank.prestige)
                else:
                    prestige_spin.setValue(0)
        self._updating = False
        total = len(self._rows)
        self._summary.setText(tr('character.summary', unlocked=unlocked, total=total))

    def _on_level_changed(self, character_id: int, value: int) -> None:
        if self._updating or self._vm is None:
            return
        self._vm.set_character_level(character_id, value)

    def _on_prestige_changed(self, character_id: int, value: int) -> None:
        if self._updating or self._vm is None:
            return
        self._vm.set_character_prestige(character_id, value)

    def _on_unlock(self, character_id: int) -> None:
        if self._vm is None:
            return
        self._vm.unlock_character(character_id)
        self.refresh()

    def _on_max_all(self) -> None:
        if self._vm is None:
            return
        self._vm.max_all_characters()
        self.refresh()
