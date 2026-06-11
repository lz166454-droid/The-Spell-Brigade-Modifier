import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from lab.trainer.stats_meta import BASIC_STATS, HIDDEN_STATS
from ui.paths import CONFIG_DIR

PRESETS_FILE = CONFIG_DIR / 'trainer_presets.json'
PRESET_STATS = BASIC_STATS + HIDDEN_STATS
PRESET_STAT_KEYS = frozenset(item.key for item in PRESET_STATS)
MAX_PRESET_NAME_LEN = 32
PRESETS_VERSION = 1

@dataclass(frozen=True)
class TrainerPreset:
    id: str
    name: str
    stats: dict[str, float]
    created_at: str
    updated_at: str

def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def normalize_preset_stats(stats: dict[str, float]) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for item in PRESET_STATS:
        if item.key not in stats:
            continue
        value = float(stats[item.key])
        normalized[item.key] = round(value) if item.decimals == 0 else round(value, item.decimals)
    return normalized

class TrainerPresetStore:
    def __init__(self) -> None:
        self._default_preset_id: str | None = None
        self._presets: list[TrainerPreset] = []
        self.load()

    @property
    def default_preset_id(self) -> str | None:
        return self._default_preset_id

    def load(self) -> None:
        self._default_preset_id = None
        self._presets = []
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        if not PRESETS_FILE.is_file():
            return
        try:
            payload = json.loads(PRESETS_FILE.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(payload, dict):
            return
        default_id = payload.get('default_preset_id')
        if isinstance(default_id, str) and default_id.strip():
            self._default_preset_id = default_id.strip()
        raw_presets = payload.get('presets')
        if not isinstance(raw_presets, list):
            self._validate_default_id()
            return
        for item in raw_presets:
            preset = self._parse_preset(item)
            if preset is not None:
                self._presets.append(preset)
        self._validate_default_id()

    def save(self) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            'version': PRESETS_VERSION,
            'default_preset_id': self._default_preset_id,
            'presets': [
                {
                    'id': preset.id,
                    'name': preset.name,
                    'created_at': preset.created_at,
                    'updated_at': preset.updated_at,
                    'stats': preset.stats,
                }
                for preset in self._presets
            ],
        }
        PRESETS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

    def list_presets(self) -> list[TrainerPreset]:
        return list(self._presets)

    def get_preset(self, preset_id: str) -> TrainerPreset | None:
        for preset in self._presets:
            if preset.id == preset_id:
                return preset
        return None

    def find_by_name(self, name: str) -> TrainerPreset | None:
        normalized = name.strip().casefold()
        for preset in self._presets:
            if preset.name.casefold() == normalized:
                return preset
        return None

    def upsert_preset(self, name: str, stats: dict[str, float], *, preset_id: str | None = None) -> TrainerPreset:
        trimmed = name.strip()
        if not trimmed:
            raise ValueError('empty_name')
        if len(trimmed) > MAX_PRESET_NAME_LEN:
            raise ValueError('name_too_long')
        normalized_stats = normalize_preset_stats(stats)
        now = _utc_now()
        if preset_id is not None:
            for index, preset in enumerate(self._presets):
                if preset.id != preset_id:
                    continue
                updated = TrainerPreset(
                    id=preset.id,
                    name=trimmed,
                    stats=normalized_stats,
                    created_at=preset.created_at,
                    updated_at=now,
                )
                self._presets[index] = updated
                self.save()
                return updated
            raise ValueError('not_found')
        created = TrainerPreset(
            id=str(uuid.uuid4()),
            name=trimmed,
            stats=normalized_stats,
            created_at=now,
            updated_at=now,
        )
        self._presets.append(created)
        self.save()
        return created

    def rename_preset(self, preset_id: str, name: str) -> TrainerPreset:
        trimmed = name.strip()
        if not trimmed:
            raise ValueError('empty_name')
        if len(trimmed) > MAX_PRESET_NAME_LEN:
            raise ValueError('name_too_long')
        for index, preset in enumerate(self._presets):
            if preset.id != preset_id:
                continue
            for other in self._presets:
                if other.id != preset_id and other.name.casefold() == trimmed.casefold():
                    raise ValueError('duplicate_name')
            updated = TrainerPreset(
                id=preset.id,
                name=trimmed,
                stats=preset.stats,
                created_at=preset.created_at,
                updated_at=_utc_now(),
            )
            self._presets[index] = updated
            self.save()
            return updated
        raise ValueError('not_found')

    def delete_preset(self, preset_id: str) -> bool:
        for index, preset in enumerate(self._presets):
            if preset.id != preset_id:
                continue
            del self._presets[index]
            if self._default_preset_id == preset_id:
                self._default_preset_id = None
            self.save()
            return True
        return False

    def set_default_preset(self, preset_id: str | None) -> None:
        if preset_id is None:
            self._default_preset_id = None
            self.save()
            return
        if self.get_preset(preset_id) is None:
            raise ValueError('not_found')
        self._default_preset_id = preset_id
        self.save()

    def get_default_preset(self) -> TrainerPreset | None:
        if not self._default_preset_id:
            return None
        return self.get_preset(self._default_preset_id)

    def _validate_default_id(self) -> None:
        if not self._default_preset_id:
            return
        if self.get_preset(self._default_preset_id) is None:
            self._default_preset_id = None

    @staticmethod
    def _parse_preset(raw: object) -> TrainerPreset | None:
        if not isinstance(raw, dict):
            return None
        preset_id = raw.get('id')
        name = raw.get('name')
        stats = raw.get('stats')
        created_at = raw.get('created_at')
        updated_at = raw.get('updated_at')
        if not isinstance(preset_id, str) or not preset_id.strip():
            return None
        if not isinstance(name, str) or not name.strip():
            return None
        if not isinstance(stats, dict):
            return None
        if not isinstance(created_at, str):
            created_at = _utc_now()
        if not isinstance(updated_at, str):
            updated_at = created_at
        parsed_stats = normalize_preset_stats({key: float(value) for key, value in stats.items() if key in PRESET_STAT_KEYS})
        if not parsed_stats:
            return None
        return TrainerPreset(
            id=preset_id.strip(),
            name=name.strip()[:MAX_PRESET_NAME_LEN],
            stats=parsed_stats,
            created_at=created_at,
            updated_at=updated_at,
        )
