import subprocess
from pathlib import Path
from PySide6.QtCore import QObject, Signal, Slot
from lab.save_directory import SaveDirectoryEditor, DirectoryLoadResult
from ui.i18n import tr
from ui.signals import signals
from ui.theme import get_save_dir

GAME_PROCESS_NAMES = ('TheSpellBrigade.exe', 'The Spell Brigade.exe')

class SaveViewModel(QObject):
    load_failed = Signal(str)
    data_ready = Signal()
    apply_failed = Signal(str)
    apply_succeeded = Signal(str)
    modify_failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.editor = SaveDirectoryEditor()
        self._load_result: DirectoryLoadResult | None = None

    @property
    def has_changes(self) -> bool:
        return self.editor.has_changes

    @property
    def active_slot(self) -> int:
        return self.editor.active_slot

    @property
    def save_dir(self) -> Path | None:
        return self.editor.save_dir

    def default_save_dir(self) -> Path:
        return self.editor.default_save_dir()

    def configured_save_dir(self) -> Path | None:
        return get_save_dir()

    def load(self, save_dir: Path | None = None) -> None:
        try:
            target = save_dir or get_save_dir() or self.default_save_dir()
            self._load_result = self.editor.load_from_directory(target)
            signals.save_loaded.emit()
            self.data_ready.emit()
        except Exception as exc:
            self.load_failed.emit(str(exc))

    def reload(self) -> None:
        if not self.editor.save_dir:
            self.load()
            return
        try:
            self._load_result = self.editor.reload()
            signals.save_loaded.emit()
            self.data_ready.emit()
        except Exception as exc:
            self.load_failed.emit(str(exc))

    def get_save_data(self):
        return self.editor.get_save_data()

    def get_slot_summaries(self):
        return self.editor.get_slot_summaries()

    def _apply_modify(self, result) -> bool:
        if result.success:
            signals.save_changed.emit()
            return True
        self.modify_failed.emit(result.error or tr('msg.modify_failed_default'))
        return False

    def set_gold(self, gold: int) -> None:
        self._apply_modify(self.editor.update_gold(gold))

    def set_character_level(self, character_id: int, level: int) -> None:
        self._apply_modify(self.editor.update_character_level(character_id, level))

    def set_character_prestige(self, character_id: int, prestige: int) -> None:
        self._apply_modify(self.editor.update_character_prestige(character_id, prestige))

    def unlock_character(self, character_id: int) -> None:
        self._apply_modify(self.editor.unlock_character(character_id))

    def set_achievement(self, achievement_id: int, unlocked: bool) -> None:
        self._apply_modify(self.editor.update_achievement(achievement_id, unlocked))

    def unlock_all_achievements(self) -> None:
        self._apply_modify(self.editor.unlock_all_achievements())

    def max_all_characters(self) -> None:
        self._apply_modify(self.editor.max_all_characters())

    def reset_changes(self) -> None:
        self.editor.reset_changes()
        signals.save_loaded.emit()

    @Slot()
    def apply_changes(self, *, backup: bool = True) -> None:
        try:
            backup_dir = self.editor.apply_to_directory(backup=backup)
            if backup_dir is not None:
                message = tr('msg.apply_success_backup', backup=backup_dir.name)
            else:
                message = tr('msg.apply_success')
            signals.save_applied.emit(message)
            self.apply_succeeded.emit(message)
            self.data_ready.emit()
        except Exception as exc:
            self.apply_failed.emit(str(exc))

    @staticmethod
    def is_game_running() -> bool:
        try:
            result = subprocess.run(
                ['tasklist'],
                capture_output=True,
                text=True,
                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
            )
            output = result.stdout.lower()
            for name in GAME_PROCESS_NAMES:
                if name.lower() in output:
                    return True
        except OSError:
            return False
        return False
