from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget
from ui.i18n import tr
from ui.theme import get_save_dir, set_save_dir

class SettingsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(12)
        self._title = QLabel(self)
        self._title.setObjectName('sectionTitle')
        path_label = QLabel(self)
        path_label.setObjectName('fieldLabel')
        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        self._path_edit = QLineEdit(self)
        self._browse_btn = QPushButton(self)
        self._browse_btn.setObjectName('secondaryBtn')
        self._browse_btn.clicked.connect(self._on_browse)
        path_row.addWidget(self._path_edit, 1)
        path_row.addWidget(self._browse_btn)
        self._default_label = QLabel('', self)
        self._default_label.setObjectName('sectionHint')
        self._default_label.setWordWrap(True)
        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self._save_btn = QPushButton(self)
        self._save_btn.setObjectName('primaryBtn')
        self._save_btn.clicked.connect(self._on_save)
        self._reset_btn = QPushButton(self)
        self._reset_btn.setObjectName('secondaryBtn')
        self._reset_btn.clicked.connect(self._on_reset)
        action_row.addWidget(self._save_btn)
        action_row.addWidget(self._reset_btn)
        action_row.addStretch(1)
        self._hint = QLabel(self)
        self._hint.setObjectName('placeholderLabel')
        self._hint.setWordWrap(True)
        layout.addWidget(self._title)
        layout.addWidget(path_label)
        layout.addLayout(path_row)
        layout.addWidget(self._default_label)
        layout.addLayout(action_row)
        layout.addWidget(self._hint)
        layout.addStretch(1)
        self._path_label = path_label
        self._vm = None
        self.retranslate_ui()

    def bind(self, view_model) -> None:
        self._vm = view_model

    def retranslate_ui(self) -> None:
        self._title.setText(tr('settings.title'))
        self._path_label.setText(tr('settings.save_dir'))
        self._browse_btn.setText(tr('settings.browse'))
        self._save_btn.setText(tr('settings.save_reload'))
        self._reset_btn.setText(tr('settings.reset_path'))
        self._hint.setText(tr('settings.hint'))
        self.refresh()

    def refresh(self) -> None:
        if self._vm is None:
            return
        default_dir = self._vm.default_save_dir()
        configured = get_save_dir()
        current = configured or self._vm.save_dir or default_dir
        self._path_edit.setText(str(current))
        self._default_label.setText(tr('settings.default_path', path=default_dir))

    def _on_browse(self) -> None:
        start = self._path_edit.text().strip() or str(Path.home())
        selected = QFileDialog.getExistingDirectory(self, tr('settings.dialog.select_dir'), start)
        if selected:
            self._path_edit.setText(selected)

    def _on_save(self) -> None:
        if self._vm is None:
            return
        path_text = self._path_edit.text().strip()
        if not path_text:
            return
        path = Path(path_text)
        if not path.is_dir():
            from PySide6.QtWidgets import QMessageBox
            QMessageBox.warning(self, tr('settings.dialog.invalid_title'), tr('settings.dialog.invalid_path', path=path))
            return
        set_save_dir(path)
        self._vm.load(path)

    def _on_reset(self) -> None:
        if self._vm is None:
            return
        set_save_dir(None)
        self._vm.load()
