from PySide6.QtCore import QObject, QTimer, Signal, Slot
from lab.trainer.session import TrainerSession
from lab.trainer.stats_meta import BASIC_STATS
from ui.trainer_presets import TrainerPreset, TrainerPresetStore

class TrainerViewModel(QObject):
    attach_failed = Signal(str)
    attach_succeeded = Signal()
    stats_updated = Signal(dict, list)
    spells_changed = Signal(list)
    presets_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._session = TrainerSession()
        self._preset_store = TrainerPresetStore()
        self._timer = QTimer(self)
        self._timer.setInterval(800)
        self._timer.timeout.connect(self._on_tick)
        self._last_spell_signature: tuple[tuple[int, tuple[str, ...]], ...] = ()

    @property
    def attached(self) -> bool:
        return self._session.attached

    @property
    def preset_store(self) -> TrainerPresetStore:
        return self._preset_store

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
        self._last_spell_signature = ()
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
            return
        self._apply_default_preset_if_any()

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

    def apply_basic_stats(self, stats: dict[str, float]) -> None:
        if not self._session.attached:
            return
        for item in BASIC_STATS:
            if item.key not in stats:
                continue
            value = float(stats[item.key])
            try:
                ok = self._session.write_stat(item.key, value)
            except Exception as exc:
                self._fail(f'写入属性失败: {item.key}', exc)
                return
            if not ok:
                self._fail(f'写入属性失败: {item.key}')
                return
        try:
            self._emit_snapshot()
        except Exception as exc:
            self._fail('写入后刷新属性失败', exc)

    def apply_preset(self, preset_id: str) -> None:
        preset = self._preset_store.get_preset(preset_id)
        if preset is None:
            return
        self.apply_basic_stats(preset.stats)

    def save_preset(self, name: str, stats: dict[str, float], *, preset_id: str | None = None) -> TrainerPreset:
        preset = self._preset_store.upsert_preset(name, stats, preset_id=preset_id)
        self.presets_changed.emit()
        return preset

    def rename_preset(self, preset_id: str, name: str) -> TrainerPreset:
        preset = self._preset_store.rename_preset(preset_id, name)
        self.presets_changed.emit()
        return preset

    def delete_preset(self, preset_id: str) -> bool:
        deleted = self._preset_store.delete_preset(preset_id)
        if deleted:
            self.presets_changed.emit()
        return deleted

    def set_default_preset(self, preset_id: str | None) -> None:
        self._preset_store.set_default_preset(preset_id)
        self.presets_changed.emit()

    def _apply_default_preset_if_any(self) -> None:
        preset = self._preset_store.get_default_preset()
        if preset is None:
            return
        from lab.trainer.diag import log
        log(f'UI: 自动应用默认预设「{preset.name}」')
        self.apply_basic_stats(preset.stats)

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
        spells = []
        for spell in snapshot.spells:
            stat_fields = [
                {
                    'key': field.key,
                    'label_key': field.label_key,
                    'decimals': field.decimals,
                }
                for field in spell.stat_fields
            ]
            spells.append({
                'id': spell.id,
                'name': spell.name,
                'stats': spell.stats,
                'stat_fields': stat_fields,
            })
        return spells

    def _emit_snapshot(self) -> None:
        snapshot = self._session.read_snapshot()
        spells = self._spell_payload(snapshot)
        spell_signature = tuple((item['id'], tuple(field['key'] for field in item['stat_fields'])) for item in spells)
        if spell_signature != self._last_spell_signature:
            self._last_spell_signature = spell_signature
            self.spells_changed.emit(spells)
        self.stats_updated.emit(snapshot.stats, spells)
