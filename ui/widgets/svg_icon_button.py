from PySide6.QtCore import QSize, QRectF, QFile, Qt
from PySide6.QtGui import QPainter
from PySide6.QtXml import QDomDocument
from ui.icons import svg_paint
try:
    from qframelesswindow.titlebar.title_bar_buttons import SvgTitleBarButton
except ImportError:
    SvgTitleBarButton = None

class SvgIconButton(SvgTitleBarButton):
    def __init__(self, icon_path, parent=None, icon_size=None):
        if SvgTitleBarButton is None:
            raise ImportError('请安装 PySidesix-Frameless-Window')
        super().__init__(icon_path, parent)
        self._icon_size = icon_size or QSize(25, 25)
        self._original_svg = None

    def setIcon(self, iconPath):
        f = QFile(iconPath)
        if f.open(QFile.OpenModeFlag.ReadOnly):
            content = f.readAll()
            self._svgDom.setContent(content)
            self._original_svg = QDomDocument()
            self._original_svg.setContent(content)
            f.close()

    def setIconSize(self, size):
        self._icon_size = size
        self.update()

    def iconSize(self):
        return self._icon_size

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        color, bgColor = self._getColors()
        painter.setBrush(bgColor)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRect(self.rect())
        if not self._svgDom.isNull():
            if self._original_svg is not None:
                source = self._original_svg.toByteArray()
            else:
                source = self._svgDom.toByteArray()
            icon_rect = QRectF(
                (self.width() - self._icon_size.width()) / 2,
                (self.height() - self._icon_size.height()) / 2,
                self._icon_size.width(),
                self._icon_size.height(),
            )
            svg_paint.render(
                painter,
                icon_rect,
                source,
                color.name(),
                original_dom=self._original_svg,
            )
