from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QMessageBox, QStackedWidget, QVBoxLayout
from qframelesswindow import FramelessWindow
from ui.i18n import get_language, tr
from ui.panels import SaveEditPanel, SettingsPanel, TrainerPanel
from ui.signals import signals
from ui.theme import apply_theme_style
from ui.view_models.save_vm import SaveViewModel
from ui.view_models.trainer_vm import TrainerViewModel
from ui.widgets.sidebar import Sidebar
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
        self._save_edit = SaveEditPanel(content_wrap)
        self._save_edit.bind(self._vm)
        self._settings = SettingsPanel(content_wrap)
        self._settings.bind(self._vm)
        self._trainer = TrainerPanel(content_wrap)
        self._trainer.bind(self._trainer_vm)
        self._pages = {
            'save': self._save_edit,
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
        outer.addLayout(body, 1)
        outer.addWidget(self._status)
        self.titleBar.raise_()
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        self._sidebar.retranslate_ui()
        self._save_edit.retranslate_ui()
        self._settings.retranslate_ui()
        self._trainer.retranslate_ui()
        if hasattr(self.titleBar, 'retranslate_ui'):
            self.titleBar.retranslate_ui()
        self._set_trainer_attached_ui(self._trainer_vm.attached)
        if self._last_loaded_path is not None and self._last_loaded_slot is not None:
            self._status_left.setText(tr('status.loaded', slot=self._last_loaded_slot, path=self._last_loaded_path))
        else:
            self._status_left.setText(tr('status.ready'))

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.titleBar.raise_()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.titleBar.raise_()

    def _connect_signals(self) -> None:
        self._sidebar.page_switched.connect(self._switch_page)
        self._vm.data_ready.connect(self._refresh_panels)
        self._vm.load_failed.connect(self._on_load_failed)
        self._vm.apply_failed.connect(self._on_apply_failed)
        self._vm.apply_succeeded.connect(self._on_apply_succeeded)
        self._vm.modify_failed.connect(self._on_modify_failed)
        self._trainer_vm.attach_failed.connect(self._on_trainer_failed)
        self._trainer_vm.attach_succeeded.connect(self._on_trainer_started)
        self._trainer_vm.detached.connect(self._on_trainer_detached)
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
        self._save_edit.refresh()
        self._settings.refresh()
        save_dir = self._vm.save_dir
        slot = self._vm.active_slot
        if save_dir is not None:
            self._last_loaded_slot = slot
            self._last_loaded_path = str(save_dir)
            self._set_status(tr('status.loaded', slot=slot, path=save_dir))

    def _on_load_failed(self, message: str) -> None:
        QMessageBox.critical(self, tr('msg.load_failed'), message)
        self._set_status(tr('status.load_failed', message=message))

    def _on_apply_failed(self, message: str) -> None:
        QMessageBox.critical(self, tr('msg.apply_failed'), message)
        self._set_status(tr('status.apply_failed', message=message))

    def _on_modify_failed(self, message: str) -> None:
        QMessageBox.warning(self, tr('msg.modify_failed'), message)

    def _set_trainer_attached_ui(self, attached: bool) -> None:
        self._trainer.set_attached_ui(attached)
        if attached:
            self._trainer_status.setText(tr('status.trainer_active'))
        else:
            self._trainer_status.setText(tr('status.trainer_idle'))

    def _on_trainer_started(self) -> None:
        self._set_trainer_attached_ui(True)

    def _on_trainer_detached(self) -> None:
        self._set_trainer_attached_ui(False)

    def _on_trainer_failed(self, message: str) -> None:
        self._set_trainer_attached_ui(self._trainer_vm.attached)
        QMessageBox.warning(self, tr('msg.trainer'), message)

    def _on_apply_succeeded(self, message: str) -> None:
        self._refresh_panels()
        self._set_status(message)

    def _set_status(self, message: str) -> None:
        self._status_left.setText(message)
