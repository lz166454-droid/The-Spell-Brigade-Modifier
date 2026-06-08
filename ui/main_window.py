from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QPushButton, QStackedWidget, QVBoxLayout
from qframelesswindow import FramelessWindow
from ui.i18n import LANGUAGE_LABEL_KEYS, get_language, set_language, tr
from ui.panels import AchievementPanel, CharacterPanel, OverviewPanel, SettingsPanel, TrainerPanel
from ui.signals import signals
from ui.theme import apply_theme_style
from ui.view_models.save_vm import SaveViewModel
from ui.view_models.trainer_vm import TrainerViewModel
from ui.widgets.sidebar import Sidebar
from ui.widgets.toolbar_combo import ToolbarComboBox
from ui.widgets.title_bar import CustomTitleBar

class MainWindow(FramelessWindow):
    _TITLE_BAR_TOP_MARGIN = 40

    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('mainWindow')
        self.resize(980, 700)
        self.setMinimumSize(860, 620)
        self._vm = SaveViewModel(self)
        self._trainer_vm = TrainerViewModel(self)
        self._last_loaded_slot: int | None = None
        self._last_loaded_path: str | None = None
        self._init_ui()
        self._connect_signals()
        apply_theme_style(self)
        get_language()
        self._vm.load()

    def _init_ui(self) -> None:
        self.setTitleBar(CustomTitleBar(self))
        self.titleBar.raise_()
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, self._TITLE_BAR_TOP_MARGIN, 0, 0)
        outer.setSpacing(0)
        toolbar = QFrame(self)
        toolbar.setObjectName('toolbar')
        toolbar_layout = QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(16, 4, 16, 4)
        toolbar_layout.setSpacing(8)
        self._reload_btn = QPushButton(toolbar)
        self._reload_btn.setObjectName('secondaryBtn')
        self._apply_btn = QPushButton(toolbar)
        self._apply_btn.setObjectName('primaryBtn')
        self._apply_btn.setEnabled(False)
        self._trainer_start_btn = QPushButton(toolbar)
        self._trainer_start_btn.setObjectName('trainerStartBtn')
        self._trainer_refresh_btn = QPushButton(toolbar)
        self._trainer_refresh_btn.setObjectName('secondaryBtn')
        self._trainer_refresh_btn.setEnabled(False)
        self._language = ToolbarComboBox(toolbar)
        self._language.setObjectName('toolbarCombo')
        self._language.setFixedHeight(24)
        self._language.setSizeAdjustPolicy(ToolbarComboBox.SizeAdjustPolicy.AdjustToContents)
        self._language.currentIndexChanged.connect(self._on_language_combo_changed)
        toolbar_layout.addStretch(1)
        toolbar_layout.addWidget(self._language)
        toolbar_layout.addWidget(self._reload_btn)
        toolbar_layout.addWidget(self._apply_btn)
        toolbar_layout.addWidget(self._trainer_start_btn)
        toolbar_layout.addWidget(self._trainer_refresh_btn)
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        self._sidebar = Sidebar(self)
        content_wrap = QFrame(self)
        content_wrap.setObjectName('contentArea')
        content_layout = QVBoxLayout(content_wrap)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        self._stack = QStackedWidget(content_wrap)
        self._overview = OverviewPanel(content_wrap)
        self._overview.bind(self._vm)
        self._character = CharacterPanel(content_wrap)
        self._character.bind(self._vm)
        self._achievement = AchievementPanel(content_wrap)
        self._achievement.bind(self._vm)
        self._settings = SettingsPanel(content_wrap)
        self._settings.bind(self._vm)
        self._trainer = TrainerPanel(content_wrap)
        self._trainer.bind(self._trainer_vm)
        self._pages = {
            'overview': self._overview,
            'character': self._character,
            'achievement': self._achievement,
            'trainer': self._trainer,
            'settings': self._settings,
        }
        for panel in self._pages.values():
            self._stack.addWidget(panel)
        content_layout.addWidget(self._stack)
        body.addWidget(self._sidebar)
        body.addWidget(content_wrap, 1)
        self._status = QFrame(self)
        self._status.setObjectName('statusBar')
        self._status.setFixedHeight(28)
        status_layout = QHBoxLayout(self._status)
        status_layout.setContentsMargins(12, 0, 12, 0)
        status_layout.setSpacing(8)
        self._status_left = QLabel(self._status)
        self._status_left.setObjectName('statusBarText')
        self._trainer_status = QLabel(self._status)
        self._trainer_status.setObjectName('trainerStatusText')
        status_layout.addWidget(self._status_left, 1)
        status_layout.addWidget(self._trainer_status, 0)
        outer.addWidget(toolbar)
        outer.addLayout(body, 1)
        outer.addWidget(self._status)
        self.titleBar.raise_()
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self._reload_btn.setText(tr('toolbar.reload'))
        self._apply_btn.setText(tr('toolbar.apply'))
        self._trainer_start_btn.setText(tr('toolbar.start_trainer'))
        self._trainer_refresh_btn.setText(tr('toolbar.refresh_trainer'))
        self._refresh_language_combo()
        self._sidebar.retranslate_ui()
        self._overview.retranslate_ui()
        self._character.retranslate_ui()
        self._achievement.retranslate_ui()
        self._settings.retranslate_ui()
        self._trainer.retranslate_ui()
        if hasattr(self.titleBar, 'retranslate_ui'):
            self.titleBar.retranslate_ui()
        self._set_trainer_attached_ui(self._trainer_vm.attached)
        if self._last_loaded_path is not None and self._last_loaded_slot is not None:
            self._status_left.setText(tr('status.loaded', slot=self._last_loaded_slot, path=self._last_loaded_path))
        else:
            self._status_left.setText(tr('status.ready'))

    def _refresh_language_combo(self) -> None:
        self._language.blockSignals(True)
        current = get_language()
        self._language.clear()
        for code, key in LANGUAGE_LABEL_KEYS:
            self._language.addItem(tr(key), code)
        index = self._language.findData(current)
        if index < 0:
            index = 0
        self._language.setCurrentIndex(index)
        self._language.blockSignals(False)

    def _on_language_combo_changed(self, index: int) -> None:
        lang = self._language.itemData(index)
        if lang and lang != get_language():
            set_language(lang)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.titleBar.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.titleBar.raise_()

    def _connect_signals(self) -> None:
        self._sidebar.page_switched.connect(self._switch_page)
        self._reload_btn.clicked.connect(self._on_reload)
        self._apply_btn.clicked.connect(self._on_apply)
        self._trainer_start_btn.clicked.connect(self._on_trainer_start)
        self._trainer_refresh_btn.clicked.connect(self._on_trainer_refresh)
        self._vm.data_ready.connect(self._refresh_panels)
        self._vm.load_failed.connect(self._on_load_failed)
        self._vm.apply_failed.connect(self._on_apply_failed)
        self._vm.apply_succeeded.connect(self._on_apply_succeeded)
        self._vm.modify_failed.connect(self._on_modify_failed)
        self._trainer_vm.attach_failed.connect(self._on_trainer_failed)
        self._trainer_vm.attach_succeeded.connect(self._on_trainer_started)
        signals.save_changed.connect(self._update_apply_button)
        signals.theme_changed.connect(self._on_theme_changed)
        signals.language_changed.connect(self._on_language_changed)
        signals.status_message.connect(self._set_status)

    def _on_language_changed(self, lang: str) -> None:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app is not None:
            app.setApplicationName(tr('app.name'))
        self.retranslate_ui()

    def _on_theme_changed(self) -> None:
        apply_theme_style(self)
        self._set_trainer_attached_ui(self._trainer_vm.attached)

    def _switch_page(self, page_id: str) -> None:
        panel = self._pages.get(page_id)
        if panel is not None:
            self._stack.setCurrentWidget(panel)
            self._sidebar.select_page(page_id)

    def _refresh_panels(self) -> None:
        self._overview.refresh()
        self._character.refresh()
        self._achievement.refresh()
        self._settings.refresh()
        self._update_apply_button()
        save_dir = self._vm.save_dir
        slot = self._vm.active_slot
        if save_dir is not None:
            self._last_loaded_slot = slot
            self._last_loaded_path = str(save_dir)
            self._set_status(tr('status.loaded', slot=slot, path=save_dir))

    def _update_apply_button(self) -> None:
        self._apply_btn.setEnabled(self._vm.has_changes)

    def _on_reload(self) -> None:
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

    def _on_load_failed(self, message: str) -> None:
        QMessageBox.critical(self, tr('msg.load_failed'), message)
        self._set_status(tr('status.load_failed', message=message))

    def _on_apply_failed(self, message: str) -> None:
        QMessageBox.critical(self, tr('msg.apply_failed'), message)
        self._set_status(tr('status.apply_failed', message=message))

    def _on_modify_failed(self, message: str) -> None:
        QMessageBox.warning(self, tr('msg.modify_failed'), message)

    def _on_trainer_start(self) -> None:
        if self._trainer_vm.attached:
            return
        self._trainer_start_btn.setEnabled(False)
        self._trainer_refresh_btn.setEnabled(False)
        self._trainer_vm.attach()

    def _on_trainer_refresh(self) -> None:
        if not self._trainer_vm.attached:
            return
        self._trainer_refresh_btn.setEnabled(False)
        self._trainer_vm.reattach()

    def _set_trainer_attached_ui(self, attached: bool) -> None:
        self._trainer_start_btn.setEnabled(not attached)
        self._trainer_refresh_btn.setEnabled(attached)
        if attached:
            self._trainer_start_btn.setObjectName('trainerStartBtnActive')
            self._trainer_status.setText(tr('status.trainer_active'))
        else:
            self._trainer_start_btn.setObjectName('trainerStartBtn')
            self._trainer_status.setText(tr('status.trainer_idle'))
        self._trainer_start_btn.style().unpolish(self._trainer_start_btn)
        self._trainer_start_btn.style().polish(self._trainer_start_btn)

    def _on_trainer_started(self) -> None:
        self._set_trainer_attached_ui(True)

    def _on_trainer_failed(self, message: str) -> None:
        self._set_trainer_attached_ui(self._trainer_vm.attached)
        QMessageBox.warning(self, tr('msg.trainer'), message)

    def _on_apply_succeeded(self, message: str) -> None:
        self._refresh_panels()
        self._set_status(message)

    def _set_status(self, message: str) -> None:
        self._status_left.setText(message)
