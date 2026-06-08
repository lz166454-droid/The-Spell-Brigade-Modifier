from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox
from assets.style.style import load_tokens
from ui.theme import get_current_theme

class ToolbarComboBox(QComboBox):
    def showPopup(self) -> None:
        count = self.count()
        if count <= 0:
            super().showPopup()
            return
        self.setMaxVisibleItems(count)
        super().showPopup()
        view = self.view()
        if view is None:
            return
        popup = view.window()
        if popup is None or popup is self.window():
            return
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        tokens = load_tokens(get_current_theme())
        bg = tokens['bg_card']
        border = tokens['border_subtle']
        text = tokens['text_primary']
        pressed = tokens['nav_bg_pressed']
        hover = tokens['nav_bg_hover']
        popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        popup.setAutoFillBackground(True)
        popup.setStyleSheet(f'background-color: {bg}; border: 1px solid {border};')
        view.setStyleSheet(
            'QAbstractItemView {'
            f'background-color: {bg}; color: {text}; border: none; outline: none;'
            f'selection-background-color: {pressed}; selection-color: {text};'
            'padding: 2px;'
            '}'
            'QAbstractItemView::item {'
            'min-height: 22px; max-height: 22px; padding: 2px 8px;'
            '}'
            'QAbstractItemView::item:hover {'
            f'background-color: {hover};'
            '}'
            'QAbstractItemView::item:selected {'
            f'background-color: {pressed};'
            '}'
        )
        row_height = max(view.sizeHintForRow(0), 22)
        list_height = row_height * count + 4
        popup_width = max(self.width(), popup.width())
        popup.resize(popup_width, list_height + 2)
        view.setFixedHeight(list_height)
