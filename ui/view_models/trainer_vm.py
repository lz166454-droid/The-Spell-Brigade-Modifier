from PySide6.QtCore import QObject, QTimer, Signal, Slot
from lab.trainer.session import TrainerSession

class TrainerViewModel(QObject):
    attach_failed = Signal(str)
    attach_succeeded = Signal()
    stats_updated = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._session = TrainerSession()
        self._timer = QTimer(self)
        self._timer.setInterval(800)
        self._timer.timeout.connect(self._on_tick)

    @property
    def attached(self) -> bool:
        return self._session.attached

    @Slot()
    def attach(self) -> None:
        from lab.trainer.diag import log
        log('UI: 用户点击启动修改')
        self._connect_session()

    @Slot()
    def reattach(self) -> None:
        from lab.trainer.diag import log
        log('UI: 用户点击刷新附加')
        self._timer.stop()
        if self._session.attached:
            self._session.detach()
        self._connect_session()

    def _connect_session(self) -> None:
        try:
            self._session.attach()
        except Exception as exc:
            self.attach_failed.emit(str(exc))
            return
        self._timer.start()
        self.attach_succeeded.emit()
        self._emit_snapshot()
        QTimer.singleShot(300, self._deferred_attach_refresh)

    def _deferred_attach_refresh(self) -> None:
        if not self._session.attached:
            return
        self._session.refresh_handles()
        self._emit_snapshot()

    @Slot(str, float)
    def apply_stat(self, key: str, value: float) -> None:
        if not self._session.attached:
            return
        if not self._session.write_stat(key, value):
            self.attach_failed.emit(f'写入属性失败: {key}')
            return
        self._emit_snapshot()

    @Slot(bool)
    def set_invincible_mode(self, enabled: bool) -> None:
        if not self._session.attached:
            return
        if not self._session.set_invincible_mode(enabled):
            self.attach_failed.emit('无法设置无敌模式（生命容器未就绪）')

    @Slot(bool)
    def set_super_attack(self, enabled: bool) -> None:
        if not self._session.attached:
            return
        if not self._session.set_super_attack(enabled):
            self.attach_failed.emit('无法设置超级攻击（未找到已装备咒语）')

    def _on_tick(self) -> None:
        if not self._session.attached:
            self._timer.stop()
            return
        if not self._session.refresh_handles():
            return
        self._emit_snapshot()

    def _emit_snapshot(self) -> None:
        stats = self._session.read_all_stats()
        self.stats_updated.emit(stats)
