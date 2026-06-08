from lab.trainer import offsets as off
from lab.trainer.diag import log, log_error
from lab.trainer.il2cpp_layout import read_network_variable_float, write_network_variable_float
from lab.trainer.memory import ProcessMemory, TrainerMemoryError
from lab.trainer.offsets import GAME_VERSION, PROCESS_NAMES
from lab.trainer.player_chain import PlayerHandles, format_handles, read_character_stats, resolve_player_handles
from lab.trainer.spell_stats import apply_super_attack, reapply_super_attack
from lab.trainer.static_resolve import TrainerConfig, load_config, resolve_manager_cached, resolve_manager_ptr
from lab.trainer.spell_stats import primary_spell_stat_ptr
from lab.trainer.stat_calc import StatCalcContext, find_stat_by_type, write_stat_panel_value
from lab.trainer.stats_meta import CHARACTER_STATS, STAT_BY_KEY, STAT_BY_TYPE

class TrainerSession:
    def __init__(self) -> None:
        self._mem = ProcessMemory()
        self._config: TrainerConfig | None = None
        self._handles: PlayerHandles | None = None
        self._invincible_mode = False
        self._super_attack = False
        self._saved_damage_resistance = 0.0
        self._saved_spell_damage: list[tuple[int, float]] = []

    @property
    def attached(self) -> bool:
        return self._handles is not None and self._mem.process_handle is not None

    @property
    def handles(self) -> PlayerHandles | None:
        return self._handles

    def attach(self) -> None:
        log('开始附加游戏进程…')
        try:
            self._mem.attach(PROCESS_NAMES)
        except TrainerMemoryError as exc:
            log_error(str(exc))
            raise
        log(f'已附加 PID={self._mem.pid} · GameAssembly={self._mem.game_assembly_base:#x} size={self._mem.game_assembly_size:#x}')
        self._config = load_config(GAME_VERSION)
        if self._mem.game_assembly_size != self._config.game_assembly_size:
            log(f'警告: GameAssembly 大小与配置不符 (当前 {self._mem.game_assembly_size:#x})')
        manager_ptr = resolve_manager_ptr(self._mem, self._config)
        self._config = load_config(GAME_VERSION)
        self._handles = resolve_player_handles(self._mem, manager_ptr)
        if self._handles is None:
            self._mem.detach()
            raise RuntimeError('未能解析本地玩家对象链')
        log(f'对象链: {format_handles(self._handles)}')
        if not self._handles.health_container_ptr:
            self.refresh_handles()
        stats = self.read_all_stats()
        log(f'读取到 {len(stats)} 项角色属性（面板值）')
        for item in CHARACTER_STATS:
            if item.key in stats:
                log(f'  {item.key}: {stats[item.key]}')
        log('附加成功')

    def detach(self) -> None:
        self._invincible_mode = False
        self._super_attack = False
        self._saved_spell_damage.clear()
        self._handles = None
        self._config = None
        self._mem.detach()
        log('已断开附加')

    def refresh_handles(self) -> bool:
        if not self.attached or self._config is None:
            return False
        if self._config.manager_klass_slot_rva is None:
            return False
        try:
            manager_ptr = resolve_manager_cached(self._mem, self._config)
        except RuntimeError:
            return False
        handles = resolve_player_handles(self._mem, manager_ptr)
        if handles is None:
            return False
        self._handles = handles
        self._reapply_cheats()
        return True

    def _reapply_cheats(self) -> None:
        if self._invincible_mode:
            self.set_invincible_mode(True)
        if self._super_attack and self._handles:
            reapply_super_attack(self._mem, self._handles.player_stats_ptr)

    def read_all_stats(self) -> dict[str, float]:
        if not self._handles:
            return {}
        raw = read_character_stats(self._mem, self._handles, CHARACTER_STATS)
        result: dict[str, float] = {}
        for stat_type, value in raw.items():
            item = STAT_BY_TYPE.get(stat_type)
            if not item:
                continue
            result[item.key] = round(value) if item.decimals == 0 else round(value, item.decimals)
        return result

    def read_stat(self, key: str) -> float | None:
        item = STAT_BY_KEY.get(key)
        if not item or not self._handles:
            return None
        from lab.trainer.player_chain import _read_panel_stat
        ctx = StatCalcContext(stats_list_ptr=self._handles.stats_list_ptr)
        return _read_panel_stat(self._mem, self._handles, item, ctx)

    def write_stat(self, key: str, value: float) -> bool:
        item = STAT_BY_KEY.get(key)
        if not item or not self._handles:
            return False
        stat_ptr = find_stat_by_type(self._mem, self._handles.stats_list_ptr, item.stat_type)
        if not stat_ptr and item.panel_source != 'spell_damage':
            return False
        ctx = StatCalcContext(stats_list_ptr=self._handles.stats_list_ptr)
        spell_stat_ptr = 0
        if item.panel_source == 'spell_damage':
            spell_stat_ptr = primary_spell_stat_ptr(self._mem, self._handles.player_stats_ptr, item.stat_type)
            if not spell_stat_ptr and not stat_ptr:
                return False
        ok = write_stat_panel_value(
            self._mem,
            stat_ptr,
            value,
            ctx,
            display_type=item.display_type,
            panel_source=item.panel_source,
            stats_list_ptr=self._handles.stats_list_ptr,
            spell_stat_ptr=spell_stat_ptr,
        )
        if ok and key == 'max_health':
            self._sync_health_max(value)
        return ok

    def _sync_health_max(self, new_max: float) -> None:
        if not self._handles or not self._handles.health_container_ptr or new_max <= 0:
            return
        health_ptr = self._handles.health_container_ptr
        max_nv = self._mem.read_u64(health_ptr + off.HEALTH_SYNCED_MAX)
        cur_nv = self._mem.read_u64(health_ptr + off.HEALTH_SYNCED_CURRENT)
        cur_hp = read_network_variable_float(self._mem, cur_nv)
        new_cur = min(cur_hp, new_max) if cur_hp > new_max else cur_hp
        write_network_variable_float(self._mem, max_nv, new_max)
        write_network_variable_float(self._mem, cur_nv, new_cur)

    def set_invincible_mode(self, enabled: bool) -> bool:
        if not self._handles or not self._handles.health_container_ptr:
            return False
        health_ptr = self._handles.health_container_ptr
        if enabled and not self._invincible_mode:
            self._saved_damage_resistance = self._mem.read_f32(health_ptr + off.HEALTH_DAMAGE_RESISTANCE)
        ok = self._mem.write_u8(health_ptr + off.HEALTH_IS_INVULNERABLE, 1 if enabled else 0)
        if enabled:
            self._mem.write_f32(health_ptr + off.HEALTH_DAMAGE_RESISTANCE, 9999.0)
        else:
            self._mem.write_f32(health_ptr + off.HEALTH_DAMAGE_RESISTANCE, self._saved_damage_resistance)
        self._invincible_mode = enabled
        return ok

    def set_super_attack(self, enabled: bool) -> bool:
        if not self._handles:
            return False
        ok = apply_super_attack(self._mem, self._handles.player_stats_ptr, enabled, self._saved_spell_damage)
        self._super_attack = enabled and ok
        return ok

    @property
    def invincible_mode(self) -> bool:
        return self._invincible_mode

    @property
    def super_attack(self) -> bool:
        return self._super_attack
