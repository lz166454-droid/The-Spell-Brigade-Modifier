import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from lab.save.es3_crypto import decrypt_es3, encrypt_es3
from lab.save.es3_parser import extract_save_data, extract_active_slot
from lab.save.save_editor import SaveEditor

SLOT_COUNT = 10
DEFAULT_SAVE_DIR = Path.home() / 'AppData/LocalLow/BoltBlasterGames/TheSpellBrigade'

@dataclass
class SlotSummary:
    index: int
    path: Path
    gold: int
    play_time: int
    size: int
    exists: bool

@dataclass
class DirectoryLoadResult:
    save_dir: Path
    active_slot: int
    slot_summaries: list[SlotSummary]

class SaveDirectoryEditor:
    """管理游戏存档目录：读取 active slot，修改后写回全部槽位。"""

    def __init__(self) -> None:
        self.save_dir: Path | None = None
        self.active_slot: int = 0
        self.editor = SaveEditor()
        self._slot_summaries: list[SlotSummary] = []

    @property
    def has_changes(self) -> bool:
        return self.editor.has_changes

    def default_save_dir(self) -> Path:
        return DEFAULT_SAVE_DIR

    def load_from_directory(self, save_dir: str | Path | None = None) -> DirectoryLoadResult:
        directory = Path(save_dir) if save_dir else self.default_save_dir()
        if not directory.is_dir():
            raise FileNotFoundError(f'存档目录不存在: {directory}')
        meta_path = directory / 'save_meta'
        if not meta_path.is_file():
            raise FileNotFoundError(f'缺少 save_meta: {meta_path}')
        meta_raw = decrypt_es3(meta_path.read_bytes()).decode('utf-8')
        active_slot = extract_active_slot(meta_raw)
        if active_slot is None:
            raise ValueError('save_meta 中未找到 active_slot')
        slot_path = directory / f'save_slot_{active_slot}'
        if not slot_path.is_file():
            raise FileNotFoundError(f'活动槽位文件不存在: {slot_path}')
        self.save_dir = directory
        self.active_slot = active_slot
        self.editor.load_from_path(slot_path)
        self._slot_summaries = self._scan_slots(directory)
        return DirectoryLoadResult(directory, active_slot, list(self._slot_summaries))

    def reload(self) -> DirectoryLoadResult:
        if not self.save_dir:
            raise RuntimeError('尚未加载存档目录')
        return self.load_from_directory(self.save_dir)

    def get_save_data(self):
        return self.editor.get_save_data()

    def get_slot_summaries(self) -> list[SlotSummary]:
        return list(self._slot_summaries)

    def update_gold(self, gold: int):
        return self.editor.update_gold(gold)

    def update_character_level(self, character_id: int, level: int):
        return self.editor.update_character_level(character_id, level)

    def update_character_prestige(self, character_id: int, prestige: int):
        return self.editor.update_character_prestige(character_id, prestige)

    def unlock_character(self, character_id: int):
        return self.editor.unlock_character(character_id)

    def update_achievement(self, achievement_id: int, unlocked: bool):
        return self.editor.update_achievement(achievement_id, unlocked)

    def unlock_all_achievements(self):
        return self.editor.unlock_all_achievements()

    def max_all_characters(self, *, max_level: int = 10, prestige: int = 2):
        return self.editor.max_all_characters(max_level=max_level, prestige=prestige)

    def reset_changes(self) -> None:
        self.editor.reset_changes()

    def apply_to_directory(self, *, backup: bool = True) -> Path | None:
        if not self.save_dir:
            raise RuntimeError('尚未加载存档目录')
        if not self.editor.raw_text:
            raise RuntimeError('无存档数据')
        backup_dir: Path | None = None
        if backup:
            backup_dir = self._create_backup(self.save_dir)
        payload = self.editor.export_to_bytes()
        for index in range(SLOT_COUNT):
            slot_path = self.save_dir / f'save_slot_{index}'
            slot_path.write_bytes(payload)
        self.editor.original_raw_text = self.editor.raw_text
        self._slot_summaries = self._scan_slots(self.save_dir)
        return backup_dir

    def _scan_slots(self, directory: Path) -> list[SlotSummary]:
        summaries: list[SlotSummary] = []
        for index in range(SLOT_COUNT):
            slot_path = directory / f'save_slot_{index}'
            if not slot_path.is_file():
                summaries.append(SlotSummary(index, slot_path, 0, 0, 0, False))
                continue
            raw = decrypt_es3(slot_path.read_bytes()).decode('utf-8')
            data = extract_save_data(raw)
            summaries.append(SlotSummary(
                index, slot_path, data.gold, data.play_time_in_minutes, slot_path.stat().st_size, True,
            ))
        return summaries

    def _create_backup(self, directory: Path) -> Path:
        stamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_root = directory / 'backups' / stamp
        backup_root.mkdir(parents=True, exist_ok=True)
        for name in ['save_meta'] + [f'save_slot_{i}' for i in range(SLOT_COUNT)]:
            src = directory / name
            if src.is_file():
                shutil.copy2(src, backup_root / name)
        return backup_root
