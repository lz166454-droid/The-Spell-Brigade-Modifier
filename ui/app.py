import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from ui.i18n import get_language, tr
from ui.main_window import MainWindow
from ui.paths import app_icon_path
from ui.theme import apply_theme_style, get_current_theme

def run() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough,
    )
    get_language()
    app = QApplication(sys.argv)
    app.setApplicationName(tr('app.name'))
    app.setWindowIcon(QIcon(app_icon_path()))
    if get_current_theme() == 'DARK':
        app.setStyle('Fusion')
    window = MainWindow()
    window.show()
    return app.exec()

if __name__ == '__main__':
    raise SystemExit(run())
