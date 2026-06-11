from dataclasses import dataclass
from lab.trainer import offsets as off
from lab.trainer.il2cpp_layout import read_list_item, read_list_size
from lab.trainer.memory import ProcessMemory, is_user_ptr
from lab.trainer.spell_names import spell_display_name
from lab.trainer.spell_stat_meta import (
    infer_spell_stat_display_type,
    spell_stat_decimals,
    spell_stat_label_key,
    spell_stat_storage_key,
    SPELL_LEVEL_KEY,
)
from lab.trainer.stat_calc import (
    find_stat_by_type,
    read_stat_display_value,
    write_flat_panel_value,
    write_modifier_sum_panel_value,
    write_stat_panel_value,
    StatCalcContext,
    DISPLAY_VALUE,
    STAT_CALC_FLAT,
    STAT_CALC_PERCENT_ADD,
    STAT_CALC_PERCENT_ADD_LOG,
    PERCENT_ADD_EXPONENT,
    calculate_display_value,
    sum_modifiers,
)

@dataclass(frozen=True)
class SpellStatField:
    key: str
    stat_type: int | None
    label_key: str
    decimals: int

@dataclass(frozen=True)
class SpellHandle:
    spell_id: int
    level: int
    spell_attrs_ptr: int
    stats_list_ptr: int
    name: str
    stat_fields: tuple[SpellStatField, ...]

_EMPTY_HASH = 0xFFFFFFFF
SUPER_ATTACK_DAMAGE = 9999.0
_CHAR_STAT_SPELL_DAMAGE = 0
_CHAR_STAT_SPELL_FIRE_RATE = 2
_CHAR_STAT_SPELL_RANGE = 6
_SPELL_DAMAGE_TYPE = 0
_SPELL_FIRE_RATE_TYPE = 2
_SPELL_SIZE_TYPES = frozenset({5, 6})

def _char_bonus_stat_type(spell_stat_type: int) -> int | None:
    if spell_stat_type == _SPELL_DAMAGE_TYPE:
        return _CHAR_STAT_SPELL_DAMAGE
    if spell_stat_type == _SPELL_FIRE_RATE_TYPE:
        return _CHAR_STAT_SPELL_FIRE_RATE
    if spell_stat_type in _SPELL_SIZE_TYPES:
        return _CHAR_STAT_SPELL_RANGE
    return None

def _read_char_spell_mod_sum(
    mem: ProcessMemory,
    ctx: StatCalcContext,
    char_stat_type: int,
    *,
    exclude_panel_dynamic: bool = False,
) -> float:
    if not is_user_ptr(ctx.stats_list_ptr):
        return 0.0
    stat_ptr = find_stat_by_type(mem, ctx.stats_list_ptr, char_stat_type)
    if not stat_ptr:
        return 0.0
    modifiers_ptr = mem.read_u64(stat_ptr + off.STAT_MODIFIERS)
    return sum_modifiers(
        mem,
        modifiers_ptr,
        ctx,
        exclude_hidden=False,
        exclude_panel_dynamic=exclude_panel_dynamic,
    )

def _combined_mod_sum_for_panel(base: float, panel_target: float, calc_type: int) -> float:
    if calc_type == STAT_CALC_FLAT:
        return panel_target - base
    if calc_type == STAT_CALC_PERCENT_ADD:
        if base == 0.0:
            return 0.0
        return (panel_target / base - 1.0) * 100.0
    if calc_type == STAT_CALC_PERCENT_ADD_LOG:
        if base <= 0.0:
            return 0.0
        ratio = panel_target / base
        if ratio <= 0.0:
            return -100.0
        return (pow(ratio, 1.0 / PERCENT_ADD_EXPONENT) - 1.0) * 100.0
    return panel_target - base

def _read_spell_stat_panel_value(
    mem: ProcessMemory,
    stat_ptr: int,
    stat_type: int,
    ctx: StatCalcContext,
) -> float:
    calc_type = mem.read_u32(stat_ptr + off.STAT_CALCULATION_TYPE)
    char_stat_type = _char_bonus_stat_type(stat_type)
    if char_stat_type is not None:
        base_value = mem.read_f32(stat_ptr + off.STAT_BASE_VALUE)
        modifiers_ptr = mem.read_u64(stat_ptr + off.STAT_MODIFIERS)
        spell_mod = sum_modifiers(mem, modifiers_ptr, ctx, exclude_hidden=False)
        char_mod = _read_char_spell_mod_sum(mem, ctx, char_stat_type)
        return calculate_display_value(base_value, spell_mod + char_mod, calc_type)
    display_type = infer_spell_stat_display_type(stat_type, calc_type)
    return read_stat_display_value(mem, stat_ptr, ctx, display_type=display_type)

def _write_spell_stat_panel_value(
    mem: ProcessMemory,
    stat_ptr: int,
    stat_type: int,
    panel_value: float,
    ctx: StatCalcContext,
) -> bool:
    calc_type = mem.read_u32(stat_ptr + off.STAT_CALCULATION_TYPE)
    char_stat_type = _char_bonus_stat_type(stat_type)
    if char_stat_type is not None:
        base_value = mem.read_f32(stat_ptr + off.STAT_BASE_VALUE)
        char_mod = _read_char_spell_mod_sum(mem, ctx, char_stat_type)
        combined_mod = _combined_mod_sum_for_panel(base_value, panel_value, calc_type)
        spell_mod_target = combined_mod - char_mod
        if calc_type == STAT_CALC_FLAT:
            return write_flat_panel_value(mem, stat_ptr, base_value + spell_mod_target, ctx)
        return write_modifier_sum_panel_value(mem, stat_ptr, spell_mod_target, ctx, exclude_hidden=False)
    display_type = infer_spell_stat_display_type(stat_type, calc_type)
    return write_stat_panel_value(mem, stat_ptr, panel_value, ctx, display_type=display_type)

def _iter_dict_int_object_entries(mem: ProcessMemory, dict_ptr: int):
    if not is_user_ptr(dict_ptr):
        return
    entries_ptr = mem.read_u64(dict_ptr + off.DICT_ENTRIES)
    if not is_user_ptr(entries_ptr):
        return
    max_len = mem.read_u32(entries_ptr + off.IL2CPP_ARRAY_MAX_LENGTH)
    for index in range(max_len):
        entry_addr = entries_ptr + off.IL2CPP_ARRAY_DATA + index * off.DICT_ENTRY_INT_OBJECT_SIZE
        if mem.read_u32(entry_addr) == _EMPTY_HASH:
            continue
        spell_id = mem.read_i32(entry_addr + 8)
        value_ptr = mem.read_u64(entry_addr + 16)
        if is_user_ptr(value_ptr):
            yield spell_id, value_ptr

def _build_stat_fields(mem: ProcessMemory, stats_list_ptr: int) -> tuple[SpellStatField, ...]:
    fields: list[SpellStatField] = []
    fields.append(SpellStatField(
        key=SPELL_LEVEL_KEY,
        stat_type=None,
        label_key='spell_level',
        decimals=0,
    ))
    size = read_list_size(mem, stats_list_ptr)
    stat_types: list[int] = []
    for index in range(size):
        stat_ptr = read_list_item(mem, stats_list_ptr, index)
        if not stat_ptr:
            continue
        stat_type = mem.read_u32(stat_ptr + off.STAT_TYPE)
        stat_types.append(stat_type)
    for stat_type in sorted(set(stat_types)):
        fields.append(SpellStatField(
            key=spell_stat_storage_key(stat_type),
            stat_type=stat_type,
            label_key=spell_stat_label_key(stat_type),
            decimals=spell_stat_decimals(stat_type),
        ))
    return tuple(fields)

def list_equipped_spells(mem: ProcessMemory, player_stats_ptr: int) -> list[SpellHandle]:
    if not is_user_ptr(player_stats_ptr):
        return []
    dict_ptr = mem.read_u64(player_stats_ptr + off.PLAYER_STATS_SPELL_ATTRS)
    spells: list[SpellHandle] = []
    for spell_id, spell_attrs_ptr in _iter_dict_int_object_entries(mem, dict_ptr):
        stats_list_ptr = mem.read_u64(spell_attrs_ptr + off.SPELL_ATTRIBUTES_STATS)
        if not is_user_ptr(stats_list_ptr):
            continue
        level = mem.read_i32(spell_attrs_ptr + off.SPELL_ATTRIBUTES_LEVEL)
        stat_fields = _build_stat_fields(mem, stats_list_ptr)
        spells.append(SpellHandle(
            spell_id=spell_id,
            level=level,
            spell_attrs_ptr=spell_attrs_ptr,
            stats_list_ptr=stats_list_ptr,
            name=spell_display_name(spell_id),
            stat_fields=stat_fields,
        ))
    spells.sort(key=lambda item: item.spell_id)
    return spells

def spells_signature(spells: list[SpellHandle]) -> tuple[tuple[int, tuple[str, ...]], ...]:
    return tuple((item.spell_id, tuple(field.key for field in item.stat_fields)) for item in spells)

def read_spell_stats(
    mem: ProcessMemory,
    handle: SpellHandle,
    ctx: StatCalcContext,
) -> dict[str, float]:
    values: dict[str, float] = {SPELL_LEVEL_KEY: float(handle.level)}
    for field in handle.stat_fields:
        if field.stat_type is None:
            continue
        stat_ptr = find_stat_by_type(mem, handle.stats_list_ptr, field.stat_type)
        if not stat_ptr:
            continue
        value = _read_spell_stat_panel_value(mem, stat_ptr, field.stat_type, ctx)
        values[field.key] = value
    return values

def write_spell_stat(
    mem: ProcessMemory,
    handle: SpellHandle,
    key: str,
    value: float,
    ctx: StatCalcContext,
) -> bool:
    if key == SPELL_LEVEL_KEY:
        return mem.write_u32(handle.spell_attrs_ptr + off.SPELL_ATTRIBUTES_LEVEL, int(value))
    for field in handle.stat_fields:
        if field.key != key or field.stat_type is None:
            continue
        stat_ptr = find_stat_by_type(mem, handle.stats_list_ptr, field.stat_type)
        if not stat_ptr:
            return False
        return _write_spell_stat_panel_value(mem, stat_ptr, field.stat_type, value, ctx)
    return False

def spell_stat_ptr(mem: ProcessMemory, player_stats_ptr: int, spell_id: int, stat_type: int) -> int:
    if not is_user_ptr(player_stats_ptr):
        return 0
    dict_ptr = mem.read_u64(player_stats_ptr + off.PLAYER_STATS_SPELL_ATTRS)
    for entry_id, spell_attrs_ptr in _iter_dict_int_object_entries(mem, dict_ptr):
        if entry_id != spell_id:
            continue
        stats_list_ptr = mem.read_u64(spell_attrs_ptr + off.SPELL_ATTRIBUTES_STATS)
        return find_stat_by_type(mem, stats_list_ptr, stat_type)
    return 0

def _iter_spell_damage_stats(mem: ProcessMemory, player_stats_ptr: int):
    for handle in list_equipped_spells(mem, player_stats_ptr):
        stat_ptr = find_stat_by_type(mem, handle.stats_list_ptr, off.STAT_TYPE_DAMAGE)
        if stat_ptr:
            yield stat_ptr

def apply_super_attack(mem: ProcessMemory, player_stats_ptr: int, enabled: bool, saved: list[tuple[int, float]]) -> bool:
    if not is_user_ptr(player_stats_ptr):
        return False
    if enabled:
        saved.clear()
        for stat_ptr in _iter_spell_damage_stats(mem, player_stats_ptr):
            saved.append((stat_ptr, read_stat_display_value(mem, stat_ptr, display_type=DISPLAY_VALUE)))
            write_stat_panel_value(mem, stat_ptr, SUPER_ATTACK_DAMAGE, display_type=DISPLAY_VALUE)
        return bool(saved)
    ok = True
    for stat_ptr, value in saved:
        ok = write_stat_panel_value(mem, stat_ptr, value, display_type=DISPLAY_VALUE) and ok
    saved.clear()
    return ok

def reapply_super_attack(mem: ProcessMemory, player_stats_ptr: int) -> None:
    for stat_ptr in _iter_spell_damage_stats(mem, player_stats_ptr):
        write_stat_panel_value(mem, stat_ptr, SUPER_ATTACK_DAMAGE, display_type=DISPLAY_VALUE)
