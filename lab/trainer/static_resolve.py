import json
from dataclasses import dataclass
from pathlib import Path
from lab.trainer import offsets as off
from lab.trainer.diag import log
from lab.trainer.il2cpp_layout import klass_name, object_klass, read_list_item, read_list_size, read_typeinfo_klass
from lab.trainer.memory import ProcessMemory, is_user_ptr
ROOT = Path(__file__).resolve().parent.parent.parent
CONFIG_DIR = ROOT / 'assets' / 'trainer'
IDENTITY_CLASS_NAME = 'GameplayPlayerIdentity'
SCAN_SECTIONS = ('.data', '.rdata', '.bss')
MAX_SECTION_SCAN = 0x800000

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

def _write_config(version: str, mutate) -> None:
    path = CONFIG_DIR / f'{version}.json'
    raw = json.loads(path.read_text(encoding='utf-8'))
    mutate(raw)
    path.write_text(json.dumps(raw, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')

def save_klass_slot(version: str, slot_rva: int) -> None:
    def mutate(raw: dict) -> None:
        raw['manager_klass_slot_rva'] = hex(slot_rva)
        raw.pop('manager_static_slot_rva', None)
        raw.pop('manager_init_flag_rva', None)
    _write_config(version, mutate)

def _persist_config_sync(version: str, *, game_assembly_size: int | None = None, identity_typeinfo_rva: int | None = None, clear_manager_slot: bool = False) -> None:
    def mutate(raw: dict) -> None:
        if game_assembly_size is not None:
            raw['game_assembly_size'] = hex(game_assembly_size)
        if identity_typeinfo_rva is not None:
            raw.setdefault('typeinfo_rvas', {})[IDENTITY_CLASS_NAME] = hex(identity_typeinfo_rva)
        if clear_manager_slot:
            raw.pop('manager_klass_slot_rva', None)
            raw.pop('manager_static_slot_rva', None)
    _write_config(version, mutate)

def _find_string_rvas(mem: ProcessMemory, text: str) -> list[int]:
    needle = text.encode('ascii') + b'\x00'
    found: list[int] = []
    chunk_size = 0x100000
    for name, vaddr, vsize in mem.image_sections():
        for start in range(0, vsize, chunk_size):
            data = mem.read(mem.game_assembly_base + vaddr + start, min(chunk_size, vsize - start))
            if not data:
                continue
            offset = 0
            while True:
                index = data.find(needle, offset)
                if index < 0:
                    break
                found.append(vaddr + start + index)
                offset = index + 1
    return found

def _find_klass_in_image_by_name(mem: ProcessMemory, class_name: str) -> int:
    name_addresses = {mem.game_assembly_base + rva for rva in _find_string_rvas(mem, class_name)}
    if not name_addresses:
        return 0
    base = mem.game_assembly_base
    for section_name in SCAN_SECTIONS:
        for name, vaddr, vsize in mem.image_sections():
            if name != section_name:
                continue
            limit = min(vsize, MAX_SECTION_SCAN)
            for offset in range(0, limit - 0x18, 8):
                candidate = base + vaddr + offset
                if mem.read_u64(candidate + 0x10) not in name_addresses:
                    continue
                if klass_name(mem, candidate) == class_name:
                    return candidate
    return 0

def _find_typeinfo_rva_for_klass(mem: ProcessMemory, klass_ptr: int) -> int | None:
    base = mem.game_assembly_base
    for section_name in ('.data', '.bss'):
        for name, vaddr, vsize in mem.image_sections():
            if name != section_name:
                continue
            limit = min(vsize, MAX_SECTION_SCAN)
            for offset in range(0, limit - 8, 8):
                rva = vaddr + offset
                if mem.read_u64(base + rva) == klass_ptr:
                    return rva
    return None

def _discover_identity_typeinfo_rva(mem: ProcessMemory) -> int | None:
    base = mem.game_assembly_base
    for section_name in ('.data', '.bss'):
        for name, vaddr, vsize in mem.image_sections():
            if name != section_name:
                continue
            limit = min(vsize, MAX_SECTION_SCAN)
            for offset in range(0, limit - 8, 8):
                rva = vaddr + offset
                klass_ptr = mem.read_u64(base + rva)
                if not is_user_ptr(klass_ptr):
                    continue
                if klass_name(mem, klass_ptr) == IDENTITY_CLASS_NAME:
                    return rva
    klass_ptr = _find_klass_in_image_by_name(mem, IDENTITY_CLASS_NAME)
    if not klass_ptr:
        return None
    return _find_typeinfo_rva_for_klass(mem, klass_ptr)

def _identity_klass(mem: ProcessMemory, config: TrainerConfig) -> int:
    return read_typeinfo_klass(mem, config.identity_typeinfo_rva)

def _identity_klass_valid(mem: ProcessMemory, config: TrainerConfig) -> bool:
    klass_ptr = _identity_klass(mem, config)
    return bool(klass_ptr) and klass_name(mem, klass_ptr) == IDENTITY_CLASS_NAME

def _ensure_config_synced(mem: ProcessMemory, config: TrainerConfig) -> None:
    clear_manager_slot = False
    new_size = None
    new_typeinfo = None
    if mem.game_assembly_size != config.game_assembly_size:
        log(
            f'GameAssembly 大小变更 {config.game_assembly_size:#x} -> {mem.game_assembly_size:#x}，'
            '重新定位 typeinfo…'
        )
        config.game_assembly_size = mem.game_assembly_size
        new_size = mem.game_assembly_size
        config.manager_klass_slot_rva = None
        clear_manager_slot = True
    if not _identity_klass_valid(mem, config):
        log(f'{IDENTITY_CLASS_NAME} typeinfo 失效，按类名重新扫描…')
        typeinfo_rva = _discover_identity_typeinfo_rva(mem)
        if typeinfo_rva is None:
            return
        log(f'定位 {IDENTITY_CLASS_NAME} typeinfo RVA={typeinfo_rva:#x}')
        config.identity_typeinfo_rva = typeinfo_rva
        new_typeinfo = typeinfo_rva
        config.manager_klass_slot_rva = None
        clear_manager_slot = True
    if new_size is not None or new_typeinfo is not None or clear_manager_slot:
        _persist_config_sync(
            config.game_version,
            game_assembly_size=new_size,
            identity_typeinfo_rva=new_typeinfo,
            clear_manager_slot=clear_manager_slot,
        )

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
        limit = min(vsize, MAX_SECTION_SCAN)
        for offset in range(0, limit - 8, 8):
            klass_slot_rva = vaddr + offset
            manager_ptr = _read_manager_from_klass_slot(mem, klass_slot_rva)
            if _validate_manager(mem, manager_ptr, identity_klass):
                log(f'定位 manager klass 槽 RVA={klass_slot_rva:#x}')
                return klass_slot_rva
    return None

def resolve_manager_ptr(mem: ProcessMemory, config: TrainerConfig) -> int:
    _ensure_config_synced(mem, config)
    if not _identity_klass_valid(mem, config):
        raise RuntimeError(
            f'未能定位 {IDENTITY_CLASS_NAME} typeinfo，'
            '游戏可能已更新，请反馈 GameAssembly 大小与版本号'
        )
    identity_klass = _identity_klass(mem, config)
    if config.manager_klass_slot_rva is not None:
        manager_ptr = _read_manager_from_klass_slot(mem, config.manager_klass_slot_rva)
        if _validate_manager(mem, manager_ptr, identity_klass):
            return manager_ptr
        log('缓存 klass 槽失效，重新扫描…')
        config.manager_klass_slot_rva = None
    slot_rva = _scan_klass_slot(mem, config)
    if slot_rva is None:
        raise RuntimeError(
            '未能定位 GameplayPlayerManager，请确认已进入对局（非主菜单/加载界面）'
        )
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
