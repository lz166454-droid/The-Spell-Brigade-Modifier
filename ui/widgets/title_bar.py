from qframelesswindow import StandardTitleBar
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QIcon
from ui.i18n import get_language, toggle_language, tr
from ui.paths import APP_VERSION, app_icon_path, icon_path
from ui.theme import apply_theme_and_notify, get_current_theme, toggle_theme
from ui.signals import signals
from ui.widgets.svg_icon_button import SvgIconButton

class LanguageButton(SvgIconButton):
    def __init__(self, parent=None):
        super().__init__(_language_icon_path(get_language()), parent)
        self.setObjectName('titleBarLanguageBtn')
        self.clicked.connect(self._toggle_language)
        signals.language_changed.connect(self._sync_icon)

    def _sync_icon(self, _lang: str = '') -> None:
        self.setIcon(_language_icon_path(get_language()))
        self.update()

    def _toggle_language(self) -> None:
        next_lang = toggle_language()
        if next_lang == 'zh-CN':
            signals.status_message.emit(tr('status.language_zh'))
        else:
            signals.status_message.emit(tr('status.language_en'))

def _language_icon_path(lang: str) -> str:
    if lang == 'zh-CN':
        return icon_path('language-cn.svg')
    return icon_path('language-en.svg')

class ThemeButton(SvgIconButton):
    def __init__(self, parent=None):
        super().__init__(icon_path('theme.svg'), parent)
        self.setObjectName('titleBarThemeBtn')
        self.clicked.connect(self._toggle_theme)

    def _toggle_theme(self):
        old_theme = get_current_theme()
        toggle_theme()
        self.setIcon(icon_path('theme.svg'))
        window = self.window()
        if window is not None:
            apply_theme_and_notify(window)
        if old_theme == 'DARK':
            signals.status_message.emit(tr('status.theme_light'))
        else:
            signals.status_message.emit(tr('status.theme_dark'))

class CustomTitleBar(StandardTitleBar):
    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName('customTitleBar')
        self._parent = parent
        app_icon = app_icon_path()
        if self._parent:
            self._parent.setWindowIcon(QIcon(app_icon))
        if hasattr(self, 'iconLabel'):
            self.iconLabel.setPixmap(QIcon(app_icon).pixmap(20, 20))
        if hasattr(self, 'titleLabel'):
            self.titleLabel.setObjectName('titleLabel')
            self.titleLabel.setStyleSheet('')
        if hasattr(self, 'minBtn'):
            self.minBtn.setObjectName('minBtn')
        if hasattr(self, 'maxBtn'):
            self.maxBtn.setObjectName('maxBtn')
        if hasattr(self, 'closeBtn'):
            self.closeBtn.setObjectName('closeBtn')
        self._add_title_bar_buttons()
        self.retranslate_ui()

    def retranslate_ui(self) -> None:
        if hasattr(self, 'setTitle') and self._parent:
            self.setTitle(tr('app.window_title', version=APP_VERSION))

    def _add_title_bar_buttons(self):
        if not hasattr(self, 'hBoxLayout') or not hasattr(self, 'minBtn'):
            return
        min_btn_index = self.hBoxLayout.indexOf(self.minBtn)
        if min_btn_index < 0:
            return
        language_button = LanguageButton(parent=self)
        language_button.setIconSize(QSize(25, 25))
        self.hBoxLayout.insertWidget(min_btn_index, language_button, 0, Qt.AlignmentFlag.AlignRight)
        min_btn_index = self.hBoxLayout.indexOf(self.minBtn)
        theme_button = ThemeButton(parent=self)
        theme_button.setIconSize(QSize(25, 25))
        self.hBoxLayout.insertWidget(min_btn_index, theme_button, 0, Qt.AlignmentFlag.AlignRight)
