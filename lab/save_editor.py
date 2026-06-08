
import re
from dataclasses import dataclass
from pathlib import Path
from lab.es3_crypto import decrypt_es3, encrypt_es3
from lab.es3_parser import extract_save_data, extract_active_slot
from lab.es3_modifier import modify_gold,modify_challenge_progress,modify_character_rank,add_character_rank,validate_modified_save,ModificationResult

@dataclass
class FileInfo:
    name: str
    path: Path
    size: int

@dataclass
class SaveMetaInfo:
    file_name: str
    active_slot: int
    raw_text: str

class SaveEditor:
    """以 raw_text 为唯一真相源的存档读写层。"""

    def __init__(self) -> None:
        self.raw_text: str | None = None
        self.original_raw_text: str | None = None
        self.file_info: FileInfo | None = None
        self.meta_info: SaveMetaInfo | None = None

    @property
    def has_changes(self) -> bool:
        return self.raw_text != self.original_raw_text

    def load_from_bytes(self, data: bytes, file_name: str = 'unknown') -> None:
        decrypted = decrypt_es3(data)
        raw_text = decrypted.decode('utf-8')
        validation = validate_modified_save(raw_text)
        if not validation.valid:
            pass
        self.raw_text = raw_text
        self.original_raw_text = raw_text
        self.file_info = FileInfo(name=file_name, path=Path(file_name), size=len(data))

    def load_from_path(self, path: str | Path) -> None:
        file_path = Path(path)
        self.load_from_bytes(file_path.read_bytes(), file_path.name)
        self.file_info = FileInfo(name=file_path.name, path=file_path, size=file_path.stat().st_size)

    def load_meta_from_path(self, path: str | Path) -> SaveMetaInfo:
        file_path = Path(path)
        decrypted = decrypt_es3(file_path.read_bytes())
        raw_text = decrypted.decode('utf-8')
        active_slot = extract_active_slot(raw_text)
        if active_slot is None:
            raise ValueError('active_slot not found in save_meta')
        self.meta_info = SaveMetaInfo(file_name=file_path.name, active_slot=active_slot, raw_text=raw_text)
        return self.meta_info

    def clear_meta(self) -> None:
        self.meta_info = None

    def get_save_data(self):
        if not self.raw_text:
            return None
        return extract_save_data(self.raw_text)

    def update_gold(self, gold: int) -> ModificationResult:
        if not self.raw_text:
            return ModificationResult(False, '', 'No save loaded')
        result = modify_gold(self.raw_text, gold)
        if result.success:
            self.raw_text = result.new_raw_text
        return result

    def update_character_level(self, character_id: int, level: int) -> ModificationResult:
        if not self.raw_text:
            return ModificationResult(False, '', 'No save loaded')
        es3_data = extract_save_data(self.raw_text)
        current_rank = es3_data.character_ranks.get(character_id)
        ptnr = current_rank.progress_towards_next_rank if current_rank else 0
        result = modify_character_rank(self.raw_text, character_id, level, ptnr)
        if not result.success and result.error and 'not found' in result.error:
            result = add_character_rank(self.raw_text, character_id, level)
        if result.success:
            self.raw_text = result.new_raw_text
        return result

    def update_character_prestige(self, character_id: int, prestige: int) -> ModificationResult:
        if not self.raw_text:
            return ModificationResult(False, '', 'No save loaded')
        es3_data = extract_save_data(self.raw_text)
        current_rank = es3_data.character_ranks.get(character_id)
        if not current_rank:
            return ModificationResult(False, self.raw_text, f'Character {character_id} not found')
        if current_rank.prestige is None:
            return ModificationResult(False, self.raw_text, f'No Prestige field for character {character_id}')
        result = modify_character_rank(
            self.raw_text,
            character_id,
            current_rank.current_rank,
            current_rank.progress_towards_next_rank,
            prestige,
        )
        if result.success:
            self.raw_text = result.new_raw_text
        return result

    def unlock_character(self, character_id: int) -> ModificationResult:
        if not self.raw_text:
            return ModificationResult(False, '', 'No save loaded')
        es3_data = extract_save_data(self.raw_text)
        if character_id in es3_data.character_ranks:
            return ModificationResult(False, self.raw_text, f'Character {character_id} already unlocked')
        result = add_character_rank(self.raw_text, character_id, 1, 0, 0)
        if result.success:
            self.raw_text = result.new_raw_text
        return result

    def update_achievement(self, achievement_id: int, unlocked: bool) -> ModificationResult:
        if not self.raw_text:
            return ModificationResult(False, '', 'No save loaded')
        es3_data = extract_save_data(self.raw_text)
        current_progress = es3_data.challenges.get(achievement_id)
        current_value = current_progress.value if current_progress else 0
        result = modify_challenge_progress(self.raw_text, achievement_id, current_value, unlocked)
        if result.success:
            self.raw_text = result.new_raw_text
        return result

    def unlock_all_achievements(self) -> ModificationResult:
        if not self.raw_text:
            return ModificationResult(False, '', 'No save loaded')
        es3_data = extract_save_data(self.raw_text)
        last_error = ''
        for achievement_id, progress in es3_data.challenges.items():
            if progress.is_completed:
                continue
            result = self.update_achievement(achievement_id, True)
            if not result.success:
                last_error = result.error or 'unknown error'
                return ModificationResult(False, self.raw_text, last_error)
        return ModificationResult(True, self.raw_text, 'All achievements unlocked')

    def max_all_characters(self, *, max_level: int = 10, prestige: int = 2) -> ModificationResult:
        if not self.raw_text:
            return ModificationResult(False, '', 'No save loaded')
        from lab.game_metadata import get_characters
        for meta in get_characters():
            es3_data = extract_save_data(self.raw_text)
            if meta.id not in es3_data.character_ranks:
                result = self.unlock_character(meta.id)
                if not result.success:
                    return result
            result = self.update_character_level(meta.id, max_level)
            if not result.success:
                return result
            es3_data = extract_save_data(self.raw_text)
            current_rank = es3_data.character_ranks.get(meta.id)
            if current_rank and current_rank.prestige is not None:
                result = self.update_character_prestige(meta.id, prestige)
                if not result.success:
                    return result
        return ModificationResult(True, self.raw_text, 'All characters maxed')

    def reset_changes(self) -> None:
        if self.original_raw_text is not None:
            self.raw_text = self.original_raw_text

    def export_to_bytes(self) -> bytes:
        if not self.raw_text:
            raise ValueError('No save loaded')
        validation = validate_modified_save(self.raw_text)
        if not validation.valid:
            pass
        return encrypt_es3(self.raw_text.encode('utf-8'))

    def export_to_path(self, path: str | Path) -> Path:
        out_path = Path(path)
        out_path.write_bytes(self.export_to_bytes())
        return out_path

    def suggest_export_name(self) -> str:
        if not self.file_info:
            return 'save_edited.es3'
        input_name = self.file_info.name
        if re.match(r'^save_slot_\d+$', input_name, re.IGNORECASE):
            return f'{input_name}_edited'
        base_name = re.sub(r'\.(es3|sav|json)$', '', input_name, flags=re.IGNORECASE)
        return f'{base_name}_edited.es3'
