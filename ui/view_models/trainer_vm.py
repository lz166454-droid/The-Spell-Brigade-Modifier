from PySide6.QtCore import QObject, QTimer, Signal, Slot
from lab.trainer.session import TrainerSession

class TrainerViewModel(QObject):
    attach_failed = Signal(str)
    attach_succeeded = Signal()
    stats_updated = Signal(dict, list)
    spells_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._session = TrainerSession()
        self._timer = QTimer(self)
        self._timer.setInterval(800)
        self._timer.timeout.connect(self._on_tick)
        self._last_spell_ids: tuple[int, ...] = ()

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

    def _fail(self, message: str, exc: BaseException | None = None) -> None:
        from lab.trainer.diag import log_error, log_exception
        if exc is not None:
            log_exception(message, exc)
            detail = f'{message}: {exc}'
        else:
            log_error(message)
            detail = message
        self.attach_failed.emit(detail)

    def _connect_session(self) -> None:
        self._last_spell_ids = ()
        try:
            self._session.attach()
        except Exception as exc:
            self._fail('附加失败', exc)
            return
        self._timer.start()
        self.attach_succeeded.emit()
        try:
            self._emit_snapshot()
        except Exception as exc:
            self._timer.stop()
            if self._session.attached:
                self._session.detach()
            self._fail('读取属性失败', exc)
            return
        QTimer.singleShot(300, self._deferred_attach_refresh)

    def _deferred_attach_refresh(self) -> None:
        if not self._session.attached:
            return
        self._session.refresh_handles()
        try:
            self._emit_snapshot()
        except Exception as exc:
            self._fail('延迟刷新属性失败', exc)

    def apply_stat(self, key: str, value: float, spell_id: int | None = None) -> None:
        if not self._session.attached:
            return
        try:
            ok = self._session.write_stat(key, value, spell_id=spell_id)
        except Exception as exc:
            target = f'{key}#{spell_id}' if spell_id is not None else key
            self._fail(f'写入属性失败: {target}', exc)
            return
        if not ok:
            target = f'{key}#{spell_id}' if spell_id is not None else key
            self._fail(f'写入属性失败: {target}')
            return
        try:
            self._emit_snapshot()
        except Exception as exc:
            self._fail('写入后刷新属性失败', exc)

    @Slot(bool)
    def set_invincible_mode(self, enabled: bool) -> None:
        if not self._session.attached:
            return
        if not self._session.set_invincible_mode(enabled):
            self._fail('无法设置无敌模式（生命容器未就绪）')

    @Slot(bool)
    def set_super_attack(self, enabled: bool) -> None:
        if not self._session.attached:
            return
        if not self._session.set_super_attack(enabled):
            self._fail('无法设置超级攻击（未找到已装备咒语）')

    def _on_tick(self) -> None:
        if not self._session.attached:
            self._timer.stop()
            return
        if not self._session.refresh_handles():
            return
        try:
            self._emit_snapshot()
        except Exception as exc:
            self._fail('定时刷新属性失败', exc)

    def _spell_payload(self, snapshot) -> list[dict]:
        return [
            {
                'id': spell.id,
                'spell_type': spell.spell_type_id,
                'name': spell.name,
                'stats': spell.stats,
            }
            for spell in snapshot.spells
        ]

    def _emit_snapshot(self) -> None:
        snapshot = self._session.read_snapshot()
        spells = self._spell_payload(snapshot)
        spell_ids = tuple(item['id'] for item in spells)
        if spell_ids != self._last_spell_ids:
            self._last_spell_ids = spell_ids
            self.spells_changed.emit(spells)
        self.stats_updated.emit(snapshot.stats, spells)
