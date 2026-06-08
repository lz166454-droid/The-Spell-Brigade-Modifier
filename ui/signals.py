from PySide6.QtCore import QObject, Signal

class AppSignals(QObject):
    theme_changed = Signal()
    save_loaded = Signal()
    save_changed = Signal()
    save_applied = Signal(str)
    status_message = Signal(str)
    language_changed = Signal(str)

signals = AppSignals()
