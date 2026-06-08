import json
from dataclasses import dataclass
from pathlib import Path
from lab.trainer import offsets as off
from lab.trainer.diag import log
from lab.trainer.il2cpp_layout import object_klass, read_list_item, read_list_size, read_typeinfo_klass
from lab.trainer.memory import ProcessMemory, is_user_ptr
ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = ROOT / 'assets' / 'trainer'

@dataclass
class TrainerConfig:
    game_version: str
    game_assembly_size: int
    identity_typeinfo_rva: int
    manager_klass_slot_rva: int | None

def load_config(version: str) -> TrainerConfig:
    path = CONFIG_DIR / f'{version}.json'
    if not path.is_file():
        raise FileNotFoundError(f'缺少 Trainer 配置: {path}')
    raw = json.loads(path.read_text(encoding='utf-8'))
    slot = raw.get('manager_klass_slot_rva')
    if slot is None:
        slot = raw.get('manager_static_slot_rva')
    return TrainerConfig(
        game_version=raw['game_version'],
        game_assembly_size=int(raw['game_assembly_size'], 16),
        identity_typeinfo_rva=int(raw['typeinfo_rvas']['GameplayPlayerIdentity'], 16),
        manager_klass_slot_rva=int(slot, 16) if slot else None,
    )

def save_klass_slot(version: str, slot_rva: int) -> None:
    path = CONFIG_DIR / f'{version}.json'
    raw = json.loads(path.read_text(encoding='utf-8'))
    raw['manager_klass_slot_rva'] = hex(slot_rva)
    raw.pop('manager_static_slot_rva', None)
    raw.pop('manager_init_flag_rva', None)
    path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

def _identity_klass(mem: ProcessMemory, config: TrainerConfig) -> int:
    return read_typeinfo_klass(mem, config.identity_typeinfo_rva)

def _validate_manager(mem: ProcessMemory, manager_ptr: int, identity_klass: int) -> bool:
    if not is_user_ptr(manager_ptr):
        return False
    identities_ptr = mem.read_u64(manager_ptr + off.MANAGER_IDENTITIES)
    size = read_list_size(mem, identities_ptr)
    if size < 1 or size > 8:
        return False
    matched = 0
    for index in range(size):
        identity_ptr = read_list_item(mem, identities_ptr, index)
        if not is_user_ptr(identity_ptr):
            return False
        if object_klass(mem, identity_ptr) != identity_klass:
            return False
        stats_ptr = mem.read_u64(identity_ptr + off.IDENTITY_STATS)
        if not is_user_ptr(stats_ptr):
            return False
        stats_list = mem.read_u64(stats_ptr + off.PLAYER_STATS_CHARACTER_STATS)
        stat_count = read_list_size(mem, stats_list)
        if stat_count < 8 or stat_count > 50:
            return False
        matched += 1
    return matched == size

def _read_manager_from_klass_slot(mem: ProcessMemory, klass_slot_rva: int) -> int:
    klass_ptr = mem.read_u64(mem.game_assembly_base + klass_slot_rva)
    if not is_user_ptr(klass_ptr):
        return 0
    static_fields = mem.read_u64(klass_ptr + off.IL2CPP_CLASS_STATIC_FIELDS)
    if not is_user_ptr(static_fields):
        return 0
    return mem.read_u64(static_fields)

def _scan_klass_slot(mem: ProcessMemory, config: TrainerConfig) -> int | None:
    identity_klass = _identity_klass(mem, config)
    if not identity_klass:
        return None
    for name, vaddr, vsize in mem.image_sections():
        if name not in ('.data', '.bss'):
            continue
        limit = min(vsize, 0x400000)
        for offset in range(0, limit - 8, 8):
            klass_slot_rva = vaddr + offset
            manager_ptr = _read_manager_from_klass_slot(mem, klass_slot_rva)
            if _validate_manager(mem, manager_ptr, identity_klass):
                log(f'定位 manager klass 槽 RVA={klass_slot_rva:#x}')
                return klass_slot_rva
    return None

def resolve_manager_ptr(mem: ProcessMemory, config: TrainerConfig) -> int:
    identity_klass = _identity_klass(mem, config)
    if config.manager_klass_slot_rva is not None:
        manager_ptr = _read_manager_from_klass_slot(mem, config.manager_klass_slot_rva)
        if _validate_manager(mem, manager_ptr, identity_klass):
            return manager_ptr
        log('缓存 klass 槽失效，重新扫描…')
    slot_rva = _scan_klass_slot(mem, config)
    if slot_rva is None:
        raise RuntimeError('未能定位 GameplayPlayerManager，请确认正在对局中')
    save_klass_slot(config.game_version, slot_rva)
    config.manager_klass_slot_rva = slot_rva
    return _read_manager_from_klass_slot(mem, slot_rva)

def resolve_manager_cached(mem: ProcessMemory, config: TrainerConfig) -> int:
    if config.manager_klass_slot_rva is None:
        raise RuntimeError('manager klass 槽未初始化')
    identity_klass = _identity_klass(mem, config)
    manager_ptr = _read_manager_from_klass_slot(mem, config.manager_klass_slot_rva)
    if not _validate_manager(mem, manager_ptr, identity_klass):
        raise RuntimeError('manager 已失效')
    return manager_ptr
