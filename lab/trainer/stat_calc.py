import math
from dataclasses import dataclass
from lab.trainer import offsets as off
from lab.trainer.il2cpp_layout import klass_name, object_klass, read_inline_float_list, read_list_item, read_list_size, restore_list_size_from_items, write_list_size
from lab.trainer.memory import ProcessMemory, is_user_ptr

PERCENT_ADD_EXPONENT = 4.0 / 7.0
STAT_CALC_FLAT = 1
STAT_CALC_PERCENT_ADD = 0
STAT_CALC_PERCENT_ADD_LOG = 2
DISPLAY_VALUE = 'value'
DISPLAY_MODIFIER_PERCENT = 'modifier_percent'
DISPLAY_VALUE_PERCENT = 'value_percent'
DISPLAY_LIFETIME_CENTIS = 'lifetime_centis'
ARMOR_MOVEMENT_SPEED_FACTOR = 0.7
ARMOR_DAMAGE_FACTOR = 0.407
_KLASS_STARTING = 'StartingStatModifier'
_KLASS_HIDDEN = 'HiddenStatModifier'
_KLASS_STATIC = 'StaticStatModifier'
_KLASS_LUCK_ARTIFACT = 'ArtifactStatModifier_IncreaseLuckWhenNotRerolling'
_KLASS_MS_ARMOR_ARTIFACT = 'ArtifactStatModifier_DecreaseMovementSpeedPerArmor'
_KLASS_DMG_ARMOR_ARTIFACT = 'ArtifactStatModifier_IncreaseDamagePerArmor'
_KLASS_CRIT_ON_ATTACK = 'IncreaseCriticalDamageOnAttack'
_STAT_ARMOR = 14

@dataclass(frozen=True)
class StatCalcContext:
    stats_list_ptr: int = 0

def _armor_display_value(mem: ProcessMemory, ctx: StatCalcContext | None) -> float:
    if ctx is None or not is_user_ptr(ctx.stats_list_ptr):
        return 0.0
    armor_ptr = find_stat_by_type(mem, ctx.stats_list_ptr, _STAT_ARMOR)
    if not armor_ptr:
        return 0.0
    return _read_numeric_display_value(mem, armor_ptr, ctx)

def _luck_artifact_value(mem: ProcessMemory, modifier_ptr: int) -> float:
    params_ptr = mem.read_u64(modifier_ptr + 0x10)
    params = read_inline_float_list(mem, params_ptr)
    stores = mem.read_u32(modifier_ptr + 0x18)
    per_store = params[0] if params else 0.0
    cap = params[1] if len(params) > 1 else per_store
    return min(stores * per_store, cap)

def _ms_armor_artifact_value(mem: ProcessMemory, modifier_ptr: int, ctx: StatCalcContext | None) -> float:
    params_ptr = mem.read_u64(modifier_ptr + 0x10)
    params = read_inline_float_list(mem, params_ptr)
    scale = params[0] if params else 1.0
    per_armor = params[1] if len(params) > 1 else 0.0
    armor = _armor_display_value(mem, ctx)
    if scale <= 0.0 or per_armor == 0.0 or armor <= 0.0:
        return 0.0
    return -per_armor * armor * ARMOR_MOVEMENT_SPEED_FACTOR / scale

def _dmg_armor_artifact_value(mem: ProcessMemory, modifier_ptr: int, ctx: StatCalcContext | None) -> float:
    params_ptr = mem.read_u64(modifier_ptr + 0x10)
    params = read_inline_float_list(mem, params_ptr)
    scale = params[0] if params else 1.0
    per_armor = params[1] if len(params) > 1 else 0.0
    armor = _armor_display_value(mem, ctx)
    if scale <= 0.0 or per_armor == 0.0 or armor <= 0.0:
        return 0.0
    return per_armor * armor / scale / ARMOR_DAMAGE_FACTOR

def _crit_on_attack_value(mem: ProcessMemory, modifier_ptr: int) -> float:
    params_ptr = mem.read_u64(modifier_ptr + 0x10)
    params = read_inline_float_list(mem, params_ptr)
    per_attack = params[0] if params else 0.0
    cap = params[1] if len(params) > 1 and params[1] > 0.0 else None
    attacks = mem.read_u32(modifier_ptr + 0x20)
    value = per_attack * attacks
    if cap is not None:
        return min(value, cap)
    return value

def read_modifier_get_value(mem: ProcessMemory, modifier_ptr: int, ctx: StatCalcContext | None = None) -> float:
    if not is_user_ptr(modifier_ptr):
        return 0.0
    name = klass_name(mem, object_klass(mem, modifier_ptr))
    if name in (_KLASS_STARTING, _KLASS_HIDDEN, _KLASS_STATIC):
        return mem.read_f32(modifier_ptr + off.MODIFIER_VALUE)
    if name == _KLASS_LUCK_ARTIFACT:
        return _luck_artifact_value(mem, modifier_ptr)
    if name == _KLASS_MS_ARMOR_ARTIFACT:
        return _ms_armor_artifact_value(mem, modifier_ptr, ctx)
    if name == _KLASS_DMG_ARMOR_ARTIFACT:
        return _dmg_armor_artifact_value(mem, modifier_ptr, ctx)
    if name == _KLASS_CRIT_ON_ATTACK:
        return _crit_on_attack_value(mem, modifier_ptr)
    return 0.0

def read_modifier_value(mem: ProcessMemory, modifier_ptr: int) -> float:
    return read_modifier_get_value(mem, modifier_ptr)

def sum_modifiers(
    mem: ProcessMemory,
    modifiers_ptr: int,
    ctx: StatCalcContext | None = None,
    *,
    non_starting_only: bool = False,
    exclude_hidden: bool = True,
) -> float:
    total = 0.0
    if is_user_ptr(modifiers_ptr):
        restore_list_size_from_items(mem, modifiers_ptr)
    size = read_list_size(mem, modifiers_ptr)
    if size <= 0:
        return total
    for index in range(size):
        modifier_ptr = read_list_item(mem, modifiers_ptr, index)
        if not is_user_ptr(modifier_ptr):
            continue
        name = klass_name(mem, object_klass(mem, modifier_ptr))
        if exclude_hidden and name == _KLASS_HIDDEN:
            continue
        if non_starting_only and name == _KLASS_STARTING:
            continue
        total += read_modifier_get_value(mem, modifier_ptr, ctx)
    return total

def calculate_display_value(base_value: float, modifier_sum: float, calc_type: int) -> float:
    if calc_type == STAT_CALC_FLAT:
        return base_value + modifier_sum
    if calc_type == STAT_CALC_PERCENT_ADD:
        return base_value * (1.0 + modifier_sum / 100.0)
    if calc_type == STAT_CALC_PERCENT_ADD_LOG:
        if base_value <= 0.0:
            return base_value
        scaled = modifier_sum / 100.0
        if scaled <= -1.0:
            return 0.0
        return base_value * math.pow(1.0 + scaled, PERCENT_ADD_EXPONENT)
    return base_value

def _has_non_starting_modifier(mem: ProcessMemory, modifiers_ptr: int) -> bool:
    if not is_user_ptr(modifiers_ptr):
        return False
    restore_list_size_from_items(mem, modifiers_ptr)
    size = read_list_size(mem, modifiers_ptr)
    for index in range(size):
        modifier_ptr = read_list_item(mem, modifiers_ptr, index)
        if not is_user_ptr(modifier_ptr):
            continue
        name = klass_name(mem, object_klass(mem, modifier_ptr))
        if name != _KLASS_STARTING:
            return True
    return False

def _modifier_percent_non_starting_only(mem: ProcessMemory, modifiers_ptr: int) -> bool:
    return _has_non_starting_modifier(mem, modifiers_ptr)

def _read_modifier_percent_panel(mem: ProcessMemory, modifiers_ptr: int, ctx: StatCalcContext | None) -> float:
    non_starting_only = _modifier_percent_non_starting_only(mem, modifiers_ptr)
    return sum_modifiers(mem, modifiers_ptr, ctx, non_starting_only=non_starting_only, exclude_hidden=False)

def _read_numeric_display_value(mem: ProcessMemory, stat_ptr: int, ctx: StatCalcContext | None) -> float:
    base_value = mem.read_f32(stat_ptr + off.STAT_BASE_VALUE)
    calc_type = mem.read_u32(stat_ptr + off.STAT_CALCULATION_TYPE)
    modifiers_ptr = mem.read_u64(stat_ptr + off.STAT_MODIFIERS)
    modifier_sum = sum_modifiers(mem, modifiers_ptr, ctx)
    return calculate_display_value(base_value, modifier_sum, calc_type)

def read_stat_display_value(
    mem: ProcessMemory,
    stat_ptr: int,
    ctx: StatCalcContext | None = None,
    *,
    display_type: str = DISPLAY_VALUE,
) -> float:
    if display_type == DISPLAY_LIFETIME_CENTIS:
        return _read_numeric_display_value(mem, stat_ptr, ctx) / 100.0
    if display_type == DISPLAY_MODIFIER_PERCENT:
        modifiers_ptr = mem.read_u64(stat_ptr + off.STAT_MODIFIERS)
        return _read_modifier_percent_panel(mem, modifiers_ptr, ctx)
    if display_type == DISPLAY_VALUE_PERCENT:
        calc_type = mem.read_u32(stat_ptr + off.STAT_CALCULATION_TYPE)
        modifiers_ptr = mem.read_u64(stat_ptr + off.STAT_MODIFIERS)
        if calc_type == STAT_CALC_FLAT:
            return _read_numeric_display_value(mem, stat_ptr, ctx)
        return sum_modifiers(mem, modifiers_ptr, ctx, exclude_hidden=True)
    return _read_numeric_display_value(mem, stat_ptr, ctx)

def write_stat_base_value(mem: ProcessMemory, stat_ptr: int, value: float) -> bool:
    return mem.write_f32(stat_ptr + off.STAT_BASE_VALUE, value)

def write_stat_display_value(mem: ProcessMemory, stat_ptr: int, display_value: float) -> bool:
    modifiers_ptr = mem.read_u64(stat_ptr + off.STAT_MODIFIERS)
    ok = True
    if is_user_ptr(modifiers_ptr):
        ok = write_list_size(mem, modifiers_ptr, 0)
    ok = mem.write_f32(stat_ptr + off.STAT_BASE_VALUE, display_value) and ok
    return ok

def write_flat_panel_value(mem: ProcessMemory, stat_ptr: int, target: float, ctx: StatCalcContext | None = None) -> bool:
    modifiers_ptr = mem.read_u64(stat_ptr + off.STAT_MODIFIERS)
    if not is_user_ptr(modifiers_ptr):
        return write_stat_base_value(mem, stat_ptr, target)
    fixed_sum, adjustable = _scan_modifiers_for_write(
        mem,
        modifiers_ptr,
        ctx,
        non_starting_only=False,
        exclude_hidden=False,
    )
    for modifier_ptr in adjustable:
        if not mem.write_f32(modifier_ptr + off.MODIFIER_VALUE, 0.0):
            return False
    return write_stat_base_value(mem, stat_ptr, target - fixed_sum)

def _modifier_is_adjustable(name: str) -> bool:
    return name in (_KLASS_STARTING, _KLASS_HIDDEN, _KLASS_STATIC)

def _scan_modifiers_for_write(
    mem: ProcessMemory,
    modifiers_ptr: int,
    ctx: StatCalcContext | None,
    *,
    non_starting_only: bool,
    exclude_hidden: bool,
) -> tuple[float, list[int]]:
    fixed_sum = 0.0
    adjustable: list[int] = []
    if is_user_ptr(modifiers_ptr):
        restore_list_size_from_items(mem, modifiers_ptr)
    size = read_list_size(mem, modifiers_ptr)
    for index in range(size):
        modifier_ptr = read_list_item(mem, modifiers_ptr, index)
        if not is_user_ptr(modifier_ptr):
            continue
        name = klass_name(mem, object_klass(mem, modifier_ptr))
        if non_starting_only and name == _KLASS_STARTING:
            continue
        if exclude_hidden and name == _KLASS_HIDDEN:
            continue
        if _modifier_is_adjustable(name):
            adjustable.append(modifier_ptr)
        else:
            fixed_sum += read_modifier_get_value(mem, modifier_ptr, ctx)
    return fixed_sum, adjustable

def write_modifier_sum_panel_value(
    mem: ProcessMemory,
    stat_ptr: int,
    target: float,
    ctx: StatCalcContext | None = None,
    *,
    non_starting_only: bool = False,
    exclude_hidden: bool = True,
) -> bool:
    modifiers_ptr = mem.read_u64(stat_ptr + off.STAT_MODIFIERS)
    if not is_user_ptr(modifiers_ptr):
        return write_stat_base_value(mem, stat_ptr, target)
    fixed_sum, adjustable = _scan_modifiers_for_write(
        mem,
        modifiers_ptr,
        ctx,
        non_starting_only=non_starting_only,
        exclude_hidden=exclude_hidden,
    )
    if not adjustable:
        return False
    for modifier_ptr in adjustable[:-1]:
        if not mem.write_f32(modifier_ptr + off.MODIFIER_VALUE, 0.0):
            return False
    return mem.write_f32(adjustable[-1] + off.MODIFIER_VALUE, target - fixed_sum)

def write_stat_panel_value(
    mem: ProcessMemory,
    stat_ptr: int,
    target: float,
    ctx: StatCalcContext | None = None,
    *,
    display_type: str = DISPLAY_VALUE,
) -> bool:
    if display_type == DISPLAY_LIFETIME_CENTIS:
        return write_flat_panel_value(mem, stat_ptr, target * 100.0, ctx)
    if display_type == DISPLAY_MODIFIER_PERCENT:
        modifiers_ptr = mem.read_u64(stat_ptr + off.STAT_MODIFIERS)
        non_starting_only = _modifier_percent_non_starting_only(mem, modifiers_ptr)
        return write_modifier_sum_panel_value(mem, stat_ptr, target, ctx, non_starting_only=non_starting_only, exclude_hidden=False)
    if display_type == DISPLAY_VALUE_PERCENT:
        calc_type = mem.read_u32(stat_ptr + off.STAT_CALCULATION_TYPE)
        if calc_type == STAT_CALC_FLAT:
            return write_flat_panel_value(mem, stat_ptr, target, ctx)
        return write_modifier_sum_panel_value(mem, stat_ptr, target, ctx, exclude_hidden=True)
    calc_type = mem.read_u32(stat_ptr + off.STAT_CALCULATION_TYPE)
    if calc_type == STAT_CALC_FLAT:
        return write_flat_panel_value(mem, stat_ptr, target, ctx)
    return write_stat_display_value(mem, stat_ptr, target)

def find_stat_by_type(mem: ProcessMemory, stats_list_ptr: int, stat_type: int) -> int:
    size = read_list_size(mem, stats_list_ptr)
    if size <= 0:
        return 0
    for index in range(size):
        stat_ptr = read_list_item(mem, stats_list_ptr, index)
        if not stat_ptr:
            continue
        if mem.read_u32(stat_ptr + off.STAT_TYPE) == stat_type:
            return stat_ptr
    return 0
