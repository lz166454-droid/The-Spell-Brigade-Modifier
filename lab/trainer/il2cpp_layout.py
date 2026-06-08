from lab.trainer import offsets as off
from lab.trainer.memory import ProcessMemory, is_user_ptr

def read_list_size(mem: ProcessMemory, list_ptr: int) -> int:
    if not is_user_ptr(list_ptr):
        return -1
    return mem.read_u32(list_ptr + off.LIST_SIZE)

def write_list_size(mem: ProcessMemory, list_ptr: int, size: int) -> bool:
    if not is_user_ptr(list_ptr):
        return False
    return mem.write_u32(list_ptr + off.LIST_SIZE, max(0, size))

def restore_list_size_from_items(mem: ProcessMemory, list_ptr: int) -> int:
    if not is_user_ptr(list_ptr):
        return 0
    size = read_list_size(mem, list_ptr)
    if size > 0:
        return size
    array_ptr = mem.read_u64(list_ptr + off.LIST_ITEMS)
    if not is_user_ptr(array_ptr):
        return 0
    capacity = mem.read_u32(array_ptr + off.IL2CPP_ARRAY_MAX_LENGTH)
    restored = 0
    for index in range(capacity):
        item_ptr = mem.read_u64(array_ptr + off.IL2CPP_ARRAY_DATA + index * 8)
        if is_user_ptr(item_ptr):
            restored = index + 1
    if restored > 0:
        write_list_size(mem, list_ptr, restored)
    return restored

def read_list_item(mem: ProcessMemory, list_ptr: int, index: int) -> int:
    if not is_user_ptr(list_ptr):
        return 0
    array_ptr = mem.read_u64(list_ptr + off.LIST_ITEMS)
    if not is_user_ptr(array_ptr):
        return 0
    return mem.read_u64(array_ptr + off.IL2CPP_ARRAY_DATA + index * 8)

def read_typeinfo_klass(mem: ProcessMemory, typeinfo_rva: int) -> int:
    if not mem.game_assembly_base:
        return 0
    return mem.read_u64(mem.game_assembly_base + typeinfo_rva)

def object_klass(mem: ProcessMemory, obj_ptr: int) -> int:
    if not is_user_ptr(obj_ptr):
        return 0
    return mem.read_u64(obj_ptr + off.IL2CPP_OBJECT_KLASS)

def klass_name(mem: ProcessMemory, klass_ptr: int) -> str:
    if not is_user_ptr(klass_ptr):
        return ''
    name_ptr = mem.read_u64(klass_ptr + 0x10)
    if not is_user_ptr(name_ptr):
        return ''
    raw = mem.read(name_ptr, 96)
    if not raw:
        return ''
    return raw.split(b'\x00')[0].decode('ascii', 'replace')

def read_inline_float_list(mem: ProcessMemory, list_ptr: int) -> list[float]:
    if not is_user_ptr(list_ptr):
        return []
    items_ptr = mem.read_u64(list_ptr + off.LIST_ITEMS)
    if not is_user_ptr(items_ptr):
        return []
    count = mem.read_u32(items_ptr + off.IL2CPP_ARRAY_MAX_LENGTH)
    return [mem.read_f32(items_ptr + off.IL2CPP_ARRAY_DATA + index * 4) for index in range(count)]

def read_network_variable_float(mem: ProcessMemory, nv_ptr: int) -> float:
    if not is_user_ptr(nv_ptr):
        return 0.0
    value = mem.read_f32(nv_ptr + off.NV_FLOAT_INTERNAL_VALUE)
    if value != 0.0:
        return value
    last_value = mem.read_f32(nv_ptr + off.NV_FLOAT_LAST_INTERNAL_VALUE)
    if last_value > 0.0:
        return last_value
    return 0.0

def read_nullable_float(mem: ProcessMemory, base_ptr: int) -> float | None:
    if not is_user_ptr(base_ptr):
        return None
    if not mem.read_u8(base_ptr):
        return None
    return mem.read_f32(base_ptr + 4)

def write_network_variable_float(mem: ProcessMemory, nv_ptr: int, value: float) -> bool:
    if not is_user_ptr(nv_ptr):
        return False
    return mem.write_f32(nv_ptr + off.NV_FLOAT_INTERNAL_VALUE, value)
