from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QPushButton, QVBoxLayout, QWidget, QLabel
from ui.i18n import tr
from ui.paths import app_icon_path

class Sidebar(QWidget):
    page_switched = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('sidebar')
        self.setFixedWidth(160)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        self._page_ids = ('save', 'trainer', 'settings')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 16, 12, 16)
        layout.setSpacing(8)
        header = QHBoxLayout()
        header.setSpacing(8)
        icon_label = QLabel(self)
        icon_label.setObjectName('appIcon')
        icon_label.setPixmap(QIcon(app_icon_path()).pixmap(32, 32))
        icon_label.setFixedSize(32, 32)
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        text_col.setContentsMargins(0, 0, 0, 0)
        self._title = QLabel(self)
        self._title.setObjectName('appTitle')
        self._subtitle = QLabel(self)
        self._subtitle.setObjectName('appSubtitle')
        text_col.addWidget(self._title)
        text_col.addWidget(self._subtitle)
        header.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignTop)
        header.addLayout(text_col, 1)
        layout.addLayout(header)
        layout.addSpacing(16)
        self._buttons: dict[str, QPushButton] = {}
        for page_id in self._page_ids:
            btn = QPushButton(self)
            btn.setObjectName('navBtn')
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked=False, pid=page_id: self.page_switched.emit(pid))
            self._group.addButton(btn)
            layout.addWidget(btn)
            self._buttons[page_id] = btn
        layout.addStretch(1)
        self.retranslate_ui()
        self.select_page('save')

    def retranslate_ui(self) -> None:
        self._title.setText(tr('app.name'))
        self._subtitle.setText(tr('app.subtitle'))
        for page_id in self._page_ids:
            self._buttons[page_id].setText(tr(f'nav.{page_id}'))

    def select_page(self, page_id: str) -> None:
        btn = self._buttons.get(page_id)
        if btn is not None:
            btn.setChecked(True)
