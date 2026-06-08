import re
from PySide6.QtCore import QByteArray, QRectF
from PySide6.QtGui import QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtXml import QDomDocument

_FILL_TAGS = ('path', 'circle', 'rect', 'polygon')
_STROKE_TAGS = ('path', 'line', 'polyline', 'circle', 'rect', 'polygon')
_SKIP_FILL = frozenset(('none', 'transparent'))

def tinted_svg_bytes(svg_source: bytes | QByteArray, color: str) -> QByteArray:
    dom = QDomDocument()
    if not dom.setContent(svg_source):
        if isinstance(svg_source, QByteArray):
            return svg_source
        return QByteArray(svg_source)
    _apply_color_to_dom(dom, color)
    return dom.toByteArray()

def colored_svg_dom(
    svg_source: bytes,
    color: str,
    *,
    original_dom: QDomDocument | None = None,
) -> QDomDocument:
    dom = QDomDocument()
    if original_dom is not None and not original_dom.isNull():
        dom.setContent(original_dom.toByteArray())
    else:
        dom.setContent(svg_source)
    _apply_color_to_dom(dom, color)
    return dom

def render(
    painter: QPainter,
    rect: QRectF,
    svg_source: bytes,
    color: str,
    *,
    rotation_deg: float = 0,
    original_dom: QDomDocument | None = None,
) -> None:
    dom = colored_svg_dom(svg_source, color, original_dom=original_dom)
    renderer = QSvgRenderer(dom.toByteArray())
    painter.save()
    if rotation_deg:
        center_x = rect.x() + rect.width() / 2
        center_y = rect.y() + rect.height() / 2
        painter.translate(center_x, center_y)
        painter.rotate(rotation_deg)
        painter.translate(-center_x, -center_y)
    renderer.render(painter, rect)
    painter.restore()

def _apply_color_to_dom(dom: QDomDocument, color: str) -> None:
    for tag in _FILL_TAGS:
        nodes = dom.elementsByTagName(tag)
        for i in range(nodes.length()):
            element = nodes.at(i).toElement()
            if element.hasAttribute('fill'):
                fill_val = element.attribute('fill').strip().lower()
                if fill_val not in _SKIP_FILL:
                    element.setAttribute('fill', color)
            if element.hasAttribute('style'):
                style = element.attribute('style')
                style = re.sub(r'fill:\s*[^;]+(;|)', f'fill:{color};', style)
                element.setAttribute('style', style)
    for tag in _STROKE_TAGS:
        nodes = dom.elementsByTagName(tag)
        for i in range(nodes.length()):
            element = nodes.at(i).toElement()
            if element.hasAttribute('stroke'):
                element.setAttribute('stroke', color)
