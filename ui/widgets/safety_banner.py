from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel

class SafetyBanner(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('safetyBanner')
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        self._label = QLabel('', self)
        self._label.setObjectName('safetyBannerText')
        self._label.setWordWrap(True)
        layout.addWidget(self._label)
        self.hide()

    def show_warning(self, text: str) -> None:
        self.setObjectName('safetyBanner')
        self._label.setObjectName('safetyBannerText')
        self._label.setText(text)
        self._refresh_style()
        self.show()

    def show_ok(self, text: str) -> None:
        self.setObjectName('safetyBannerOk')
        self._label.setObjectName('safetyBannerOkText')
        self._label.setText(text)
        self._refresh_style()
        self.show()

    def hide_banner(self) -> None:
        self.hide()

    def _refresh_style(self) -> None:
        self.style().unpolish(self)
        self.style().polish(self)
        self._label.style().unpolish(self._label)
        self._label.style().polish(self._label)
