from dataclasses import dataclass
from lab.trainer import offsets as off
from lab.trainer.il2cpp_layout import read_list_item, read_list_size, read_network_variable_float
from lab.trainer.memory import ProcessMemory, is_user_ptr
from lab.trainer.spell_stats import spell_stat_ptr
from lab.trainer.stat_calc import StatCalcContext, find_stat_by_type, read_stat_display_value, sum_positive_modifiers
from lab.trainer import offsets as off

@dataclass
class PlayerHandles:
    manager_ptr: int
    identity_ptr: int
    player_stats_ptr: int
    stats_list_ptr: int
    gameplay_player_ptr: int
    health_container_ptr: int

def _pick_local_identity(mem: ProcessMemory, manager_ptr: int) -> int:
    identities_ptr = mem.read_u64(manager_ptr + off.MANAGER_IDENTITIES)
    size = read_list_size(mem, identities_ptr)
    if size <= 0:
        return 0
    local_ptr = 0
    owner_ptr = 0
    fallback_ptr = 0
    best_stats = 0
    for index in range(size):
        identity_ptr = read_list_item(mem, identities_ptr, index)
        if not is_user_ptr(identity_ptr):
            continue
        if mem.read_u8(identity_ptr + off.NB_IS_LOCAL_PLAYER):
            local_ptr = identity_ptr
        if mem.read_u8(identity_ptr + off.NB_IS_OWNER):
            owner_ptr = identity_ptr
        stats_ptr = mem.read_u64(identity_ptr + off.IDENTITY_STATS)
        stat_count = read_list_size(mem, mem.read_u64(stats_ptr + off.PLAYER_STATS_CHARACTER_STATS))
        if stat_count > best_stats:
            best_stats = stat_count
            fallback_ptr = identity_ptr
    if local_ptr:
        return local_ptr
    if owner_ptr:
        return owner_ptr
    if size == 1:
        return read_list_item(mem, identities_ptr, 0)
    return fallback_ptr

def _pick_local_from_player_list(mem: ProcessMemory, list_ptr: int) -> int:
    size = read_list_size(mem, list_ptr)
    if size <= 0:
        return 0
    local_player = 0
    fallback = 0
    for index in range(size):
        candidate = read_list_item(mem, list_ptr, index)
        if not is_user_ptr(candidate):
            continue
        if mem.read_u8(candidate + off.NB_IS_LOCAL_PLAYER) or mem.read_u8(candidate + off.NB_IS_OWNER):
            local_player = candidate
        if not fallback:
            fallback = candidate
    if local_player:
        return local_player
    return fallback

def _resolve_gameplay_player(mem: ProcessMemory, manager_ptr: int, identity_ptr: int) -> int:
    for field in (off.MANAGER_ALIVE_PLAYERS, off.MANAGER_TARGETABLE_PLAYERS):
        list_ptr = mem.read_u64(manager_ptr + field)
        player = _pick_local_from_player_list(mem, list_ptr)
        if player:
            return player
    network_obj = mem.read_u64(identity_ptr + off.IDENTITY_CURRENT_PLAYER)
    if not is_user_ptr(network_obj):
        return 0
    children_ptr = mem.read_u64(network_obj + off.NETWORK_OBJECT_CHILD_BEHAVIOURS)
    size = read_list_size(mem, children_ptr)
    for index in range(size):
        candidate = read_list_item(mem, children_ptr, index)
        if not is_user_ptr(candidate):
            continue
        health_ptr = mem.read_u64(candidate + off.PLAYER_HEALTH_CONTAINER)
        if is_user_ptr(health_ptr):
            return candidate
    return 0

def _looks_like_health_container(mem: ProcessMemory, candidate_ptr: int) -> bool:
    max_nv = mem.read_u64(candidate_ptr + off.HEALTH_SYNCED_MAX)
    if not is_user_ptr(max_nv):
        return False
    return read_network_variable_float(mem, max_nv) > 0.0

def _resolve_health_container(mem: ProcessMemory, identity_ptr: int, gameplay_player_ptr: int) -> int:
    if is_user_ptr(gameplay_player_ptr):
        health_ptr = mem.read_u64(gameplay_player_ptr + off.PLAYER_HEALTH_CONTAINER)
        if is_user_ptr(health_ptr):
            return health_ptr
    network_obj = mem.read_u64(identity_ptr + off.IDENTITY_CURRENT_PLAYER)
    if not is_user_ptr(network_obj):
        return 0
    children_ptr = mem.read_u64(network_obj + off.NETWORK_OBJECT_CHILD_BEHAVIOURS)
    size = read_list_size(mem, children_ptr)
    for index in range(size):
        candidate = read_list_item(mem, children_ptr, index)
        if is_user_ptr(candidate) and _looks_like_health_container(mem, candidate):
            return candidate
    return 0

def resolve_player_handles(mem: ProcessMemory, manager_ptr: int) -> PlayerHandles | None:
    if not is_user_ptr(manager_ptr):
        return None
    identity_ptr = _pick_local_identity(mem, manager_ptr)
    if not is_user_ptr(identity_ptr):
        return None
    player_stats_ptr = mem.read_u64(identity_ptr + off.IDENTITY_STATS)
    if not is_user_ptr(player_stats_ptr):
        return None
    stats_list_ptr = mem.read_u64(player_stats_ptr + off.PLAYER_STATS_CHARACTER_STATS)
    if not is_user_ptr(stats_list_ptr):
        return None
    gameplay_player_ptr = _resolve_gameplay_player(mem, manager_ptr, identity_ptr)
    health_container_ptr = _resolve_health_container(mem, identity_ptr, gameplay_player_ptr)
    return PlayerHandles(
        manager_ptr=manager_ptr,
        identity_ptr=identity_ptr,
        player_stats_ptr=player_stats_ptr,
        stats_list_ptr=stats_list_ptr,
        gameplay_player_ptr=gameplay_player_ptr,
        health_container_ptr=health_container_ptr,
    )

def format_handles(handles: PlayerHandles) -> str:
    return (
        f'manager={handles.manager_ptr:#x} identity={handles.identity_ptr:#x} '
        f'stats={handles.stats_list_ptr:#x} player={handles.gameplay_player_ptr:#x} '
        f'health={handles.health_container_ptr:#x}'
    )

def read_panel_stat(
    mem: ProcessMemory,
    handles: PlayerHandles,
    item,
    ctx: StatCalcContext,
    *,
    spell_id: int | None = None,
) -> float | None:
    if item.panel_source == 'spell':
        if spell_id is None:
            return None
        stat_ptr = spell_stat_ptr(mem, handles.player_stats_ptr, spell_id, item.stat_type)
        if not stat_ptr:
            return None
        return read_stat_display_value(mem, stat_ptr, ctx, display_type=item.display_type)
    stat_ptr = find_stat_by_type(mem, handles.stats_list_ptr, item.stat_type)
    if not stat_ptr:
        return None
    if item.panel_positive_modifiers_only:
        modifiers_ptr = mem.read_u64(stat_ptr + off.STAT_MODIFIERS)
        return sum_positive_modifiers(mem, modifiers_ptr, ctx)
    return read_stat_display_value(mem, stat_ptr, ctx, display_type=item.display_type)

def read_character_stats(mem: ProcessMemory, handles: PlayerHandles, stat_defs: tuple) -> dict[str, float]:
    values: dict[str, float] = {}
    ctx = StatCalcContext(stats_list_ptr=handles.stats_list_ptr)
    for item in stat_defs:
        value = read_panel_stat(mem, handles, item, ctx)
        if value is not None:
            values[item.key] = value
    return values
