from PySide6.QtWidgets import QFrame, QHBoxLayout, QMessageBox, QPushButton, QTabWidget, QVBoxLayout, QWidget
from ui.i18n import tr
from ui.panels.achievement_panel import AchievementPanel
from ui.panels.character_panel import CharacterPanel
from ui.panels.overview_panel import OverviewPanel
from ui.signals import signals
from ui.view_models.save_vm import SaveViewModel

class SaveEditPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._vm: SaveViewModel | None = None
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 16, 20, 16)
        root.setSpacing(12)
        header = QFrame(self)
        header.setObjectName('panelCard')
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(8)
        self._reload_btn = QPushButton(header)
        self._reload_btn.setObjectName('secondaryBtn')
        self._apply_btn = QPushButton(header)
        self._apply_btn.setObjectName('primaryBtn')
        self._apply_btn.setEnabled(False)
        self._reload_btn.clicked.connect(self._on_reload)
        self._apply_btn.clicked.connect(self._on_apply)
        header_layout.addWidget(self._reload_btn)
        header_layout.addWidget(self._apply_btn)
        header_layout.addStretch(1)
        root.addWidget(header)
        self._tabs = QTabWidget(self)
        self._tabs.setObjectName('saveEditTabs')
        self._overview = OverviewPanel(self._tabs)
        self._character = CharacterPanel(self._tabs)
        self._achievement = AchievementPanel(self._tabs)
        self._tab_ids = ('overview', 'character', 'achievement')
        self._tab_panels = {
            'overview': self._overview,
            'character': self._character,
            'achievement': self._achievement,
        }
        for tab_id in self._tab_ids:
            self._tabs.addTab(self._tab_panels[tab_id], '')
        root.addWidget(self._tabs, 1)

    def bind(self, view_model: SaveViewModel) -> None:
        self._vm = view_model
        self._overview.bind(view_model)
        self._character.bind(view_model)
        self._achievement.bind(view_model)
        signals.save_changed.connect(self._update_apply_button)
        self._update_apply_button()

    def refresh(self) -> None:
        self._overview.refresh()
        self._character.refresh()
        self._achievement.refresh()
        self._update_apply_button()

    def retranslate_ui(self) -> None:
        self._reload_btn.setText(tr('toolbar.reload'))
        self._apply_btn.setText(tr('toolbar.apply'))
        for index, tab_id in enumerate(self._tab_ids):
            self._tabs.setTabText(index, tr(f'save.tab.{tab_id}'))
        self._overview.retranslate_ui()
        self._character.retranslate_ui()
        self._achievement.retranslate_ui()

    def _update_apply_button(self) -> None:
        if self._vm is not None:
            self._apply_btn.setEnabled(self._vm.has_changes)

    def _on_reload(self) -> None:
        if self._vm is None:
            return
        if self._vm.has_changes:
            answer = QMessageBox.question(
                self,
                tr('dialog.reload.title'),
                tr('dialog.reload.message'),
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._vm.reload()

    def _on_apply(self) -> None:
        if self._vm is None:
            return
        if self._vm.is_game_running():
            answer = QMessageBox.warning(
                self,
                tr('dialog.game_running.title'),
                tr('dialog.game_running.message'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._vm.apply_changes(backup=True)
