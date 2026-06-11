from dataclasses import dataclass
from lab.trainer import offsets as off
from lab.trainer.memory import ProcessMemory, is_user_ptr
from lab.trainer.stat_calc import find_stat_by_type, read_stat_display_value, write_stat_display_value

@dataclass(frozen=True)
class SpellHandle:
    spell_id: int
    spell_attrs_ptr: int
    stats_list_ptr: int
    name: str

_EMPTY_HASH = 0xFFFFFFFF
SUPER_ATTACK_DAMAGE = 9999.0

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

def list_equipped_spells(mem: ProcessMemory, player_stats_ptr: int) -> list[SpellHandle]:
    if not is_user_ptr(player_stats_ptr):
        return []
    dict_ptr = mem.read_u64(player_stats_ptr + off.PLAYER_STATS_SPELL_ATTRS)
    spells: list[SpellHandle] = []
    for spell_id, spell_attrs_ptr in _iter_dict_int_object_entries(mem, dict_ptr):
        stats_list_ptr = mem.read_u64(spell_attrs_ptr + off.SPELL_ATTRIBUTES_STATS)
        if not is_user_ptr(stats_list_ptr):
            continue
        spells.append(SpellHandle(
            spell_id=spell_id,
            spell_attrs_ptr=spell_attrs_ptr,
            stats_list_ptr=stats_list_ptr,
            name=str(spell_id),
        ))
    spells.sort(key=lambda item: item.spell_id)
    return spells

def spells_signature(spells: list[SpellHandle]) -> tuple[int, ...]:
    return tuple(item.spell_id for item in spells)

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
            saved.append((stat_ptr, read_stat_display_value(mem, stat_ptr)))
            write_stat_display_value(mem, stat_ptr, SUPER_ATTACK_DAMAGE)
        return bool(saved)
    ok = True
    for stat_ptr, value in saved:
        ok = write_stat_display_value(mem, stat_ptr, value) and ok
    saved.clear()
    return ok

def reapply_super_attack(mem: ProcessMemory, player_stats_ptr: int) -> None:
    for stat_ptr in _iter_spell_damage_stats(mem, player_stats_ptr):
        write_stat_display_value(mem, stat_ptr, SUPER_ATTACK_DAMAGE)
