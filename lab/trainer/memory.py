import ctypes
import struct
from ctypes import wintypes

PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_VM_OPERATION = 0x0008
PROCESS_QUERY_INFORMATION = 0x0400
TH32CS_SNAPPROCESS = 0x2
LIST_MODULES_ALL = 0x03
USER_PTR_MIN = 0x10000
USER_PTR_MAX = 0x00007FFFFFFFFFFF

class TrainerMemoryError(Exception):
    pass

class ProcessMemory:
    def __init__(self) -> None:
        self.process_handle: int | None = None
        self.pid: int = 0
        self.game_assembly_base: int = 0
        self.game_assembly_size: int = 0

    def attach(self, process_names: tuple[str, ...]) -> None:
        self.detach()
        pid = _find_pid(process_names)
        if pid is None:
            raise TrainerMemoryError('未找到游戏进程，请先启动 The Spell Brigade')
        access = PROCESS_VM_READ | PROCESS_VM_WRITE | PROCESS_VM_OPERATION | PROCESS_QUERY_INFORMATION
        handle = ctypes.windll.kernel32.OpenProcess(access, False, pid)
        if not handle:
            raise TrainerMemoryError(f'OpenProcess 失败 PID={pid}，请与游戏同权限运行')
        base, size = _module_base(handle, 'GameAssembly.dll')
        if not base:
            raise TrainerMemoryError('未找到 GameAssembly.dll')
        self.process_handle = handle
        self.pid = pid
        self.game_assembly_base = base
        self.game_assembly_size = size

    def detach(self) -> None:
        if self.process_handle:
            ctypes.windll.kernel32.CloseHandle(self.process_handle)
        self.process_handle = None
        self.pid = 0
        self.game_assembly_base = 0
        self.game_assembly_size = 0

    def read(self, address: int, size: int) -> bytes | None:
        if self.process_handle is None:
            return None
        buf = (ctypes.c_char * size)()
        n = ctypes.c_size_t()
        ok = ctypes.windll.kernel32.ReadProcessMemory(
            self.process_handle, ctypes.c_void_p(address), buf, size, ctypes.byref(n),
        )
        if not ok or n.value != size:
            return None
        return buf.raw

    def write(self, address: int, data: bytes) -> bool:
        if self.process_handle is None:
            return False
        buf = (ctypes.c_char * len(data)).from_buffer_copy(data)
        n = ctypes.c_size_t()
        return bool(ctypes.windll.kernel32.WriteProcessMemory(
            self.process_handle, ctypes.c_void_p(address), buf, len(data), ctypes.byref(n),
        ))

    def read_u64(self, address: int) -> int:
        data = self.read(address, 8)
        return struct.unpack('<Q', data)[0] if data else 0

    def read_u32(self, address: int) -> int:
        data = self.read(address, 4)
        return struct.unpack('<I', data)[0] if data else 0

    def read_i32(self, address: int) -> int:
        data = self.read(address, 4)
        return struct.unpack('<i', data)[0] if data else 0

    def read_u8(self, address: int) -> int:
        data = self.read(address, 1)
        return data[0] if data else 0

    def read_f32(self, address: int) -> float:
        data = self.read(address, 4)
        return struct.unpack('<f', data)[0] if data else 0.0

    def write_f32(self, address: int, value: float) -> bool:
        return self.write(address, struct.pack('<f', value))

    def write_u8(self, address: int, value: int) -> bool:
        return self.write(address, bytes([value & 0xFF]))

    def write_u32(self, address: int, value: int) -> bool:
        return self.write(address, struct.pack('<I', value & 0xFFFFFFFF))

    def image_sections(self) -> list[tuple[str, int, int]]:
        if not self.game_assembly_base:
            return []
        dos = self.read(self.game_assembly_base, 0x40)
        if not dos or len(dos) < 0x40:
            return []
        pe_off = struct.unpack_from('<I', dos, 0x3C)[0]
        pe = self.read(self.game_assembly_base + pe_off, 0x200)
        if not pe:
            return []
        num_sections = struct.unpack_from('<H', pe, 6)[0]
        opt_size = struct.unpack_from('<H', pe, 20)[0]
        sec_off = pe_off + 24 + opt_size
        sections: list[tuple[str, int, int]] = []
        for index in range(num_sections):
            sh = self.read(self.game_assembly_base + sec_off + index * 40, 40)
            if not sh:
                continue
            name = sh[:8].split(b'\x00')[0].decode('ascii', 'replace')
            vsize, vaddr = struct.unpack_from('<II', sh, 8)
            sections.append((name, vaddr, vsize))
        return sections

def is_user_ptr(value: int) -> bool:
    return USER_PTR_MIN < value < USER_PTR_MAX

def _find_pid(process_names: tuple[str, ...]) -> int | None:
    kernel32 = ctypes.windll.kernel32
    snap = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == -1:
        return None
    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ('dwSize', wintypes.DWORD), ('cntUsage', wintypes.DWORD),
            ('th32ProcessID', wintypes.DWORD), ('th32DefaultHeapID', ctypes.c_ulonglong),
            ('th32ModuleID', wintypes.DWORD), ('cntThreads', wintypes.DWORD),
            ('th32ParentProcessID', wintypes.DWORD), ('pcPriClassBase', ctypes.c_long),
            ('dwFlags', wintypes.DWORD), ('szExeFile', ctypes.c_char * 260),
        ]
    entry = PROCESSENTRY32()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32)
    names = {name.lower() for name in process_names}
    pid = None
    if kernel32.Process32First(snap, ctypes.byref(entry)):
        while True:
            exe = entry.szExeFile.decode('ascii', 'ignore').lower()
            if exe in names:
                pid = entry.th32ProcessID
                break
            if not kernel32.Process32Next(snap, ctypes.byref(entry)):
                break
    kernel32.CloseHandle(snap)
    return pid

def _module_base(handle: int, module_name: str) -> tuple[int, int]:
    psapi = ctypes.windll.psapi
    arr = (ctypes.c_ulonglong * 1024)()
    needed = wintypes.DWORD()
    if not psapi.EnumProcessModulesEx(handle, ctypes.byref(arr), ctypes.sizeof(arr), ctypes.byref(needed), LIST_MODULES_ALL):
        return 0, 0
    count = needed.value // ctypes.sizeof(ctypes.c_ulonglong)
    buf = ctypes.create_unicode_buffer(260)
    class MODULEINFO(ctypes.Structure):
        _fields_ = [('lpBaseOfDll', ctypes.c_void_p), ('SizeOfImage', wintypes.DWORD), ('EntryPoint', ctypes.c_void_p)]
    for index in range(count):
        mod = arr[index]
        psapi.GetModuleBaseNameW(handle, ctypes.c_void_p(mod), buf, 260)
        if buf.value != module_name:
            continue
        info = MODULEINFO()
        psapi.GetModuleInformation(handle, ctypes.c_void_p(mod), ctypes.byref(info), ctypes.sizeof(info))
        return int(mod), int(info.SizeOfImage)
    return 0, 0
