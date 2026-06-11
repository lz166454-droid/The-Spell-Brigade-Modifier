import json
from dataclasses import dataclass
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
METADATA_FILE = ROOT_DIR / 'assets' / 'data' / 'game_metadata.json'
LOCALE_ZH_FILE = ROOT_DIR / 'assets' / 'data' / 'locale.zh-CN.json'
DEFAULT_LOCALE = 'zh-CN'
_display_locale: str = DEFAULT_LOCALE

@dataclass(frozen=True)
class CharacterMeta:
    id: int
    name: str
    character_class: str
    max_level: int

@dataclass(frozen=True)
class AchievementMeta:
    id: int
    name: str
    description: str
    category: str

_cache: dict | None = None
_locale_cache: dict | None = None

def set_display_locale(locale: str) -> None:
    global _display_locale, _locale_cache
    _display_locale = locale if locale == 'zh-CN' else 'en'
    _locale_cache = None

def get_display_locale() -> str:
    return _display_locale

def _load_raw() -> dict:
    global _cache
    if _cache is None:
        _cache = json.loads(METADATA_FILE.read_text(encoding='utf-8'))
    return _cache

def _load_locale(locale: str | None = None) -> dict | None:
    global _locale_cache
    active = locale or _display_locale
    if active != 'zh-CN':
        return None
    if _locale_cache is None and LOCALE_ZH_FILE.is_file():
        _locale_cache = json.loads(LOCALE_ZH_FILE.read_text(encoding='utf-8'))
    return _locale_cache

def get_characters() -> list[CharacterMeta]:
    raw = _load_raw()
    return [CharacterMeta(**item) for item in raw.get('characters', [])]

def get_achievements() -> list[AchievementMeta]:
    raw = _load_raw()
    return [AchievementMeta(**item) for item in raw.get('achievements', [])]

def get_categories() -> list[str]:
    raw = _load_raw()
    return list(raw.get('categories', []))

def category_label(category: str, locale: str | None = None) -> str:
    active = locale or _display_locale
    if active == 'zh-CN':
        raw = _load_raw()
        labels = raw.get('category_labels', {})
        if category in labels:
            return labels[category]
    if active == 'en':
        from ui.i18n import tr
        key = f'category.{category}'
        translated = tr(key)
        if translated != key:
            return translated
    return category

def character_display_name(meta: CharacterMeta, locale: str | None = None) -> str:
    loc = _load_locale(locale)
    if loc:
        entry = loc.get('characters', {}).get(str(meta.id))
        if entry and entry.get('name'):
            return entry['name']
    return meta.name

def character_display_class(meta: CharacterMeta, locale: str | None = None) -> str:
    loc = _load_locale(locale)
    if loc:
        entry = loc.get('characters', {}).get(str(meta.id))
        if entry and entry.get('character_class') and entry['character_class'] != meta.character_class:
            return entry['character_class']
    return meta.character_class

def achievement_display_name(meta: AchievementMeta, locale: str | None = None) -> str:
    loc = _load_locale(locale)
    if loc:
        entry = loc.get('achievements', {}).get(str(meta.id))
        if entry and entry.get('name'):
            return entry['name']
    return meta.name

def achievement_display_description(meta: AchievementMeta, locale: str | None = None) -> str:
    loc = _load_locale(locale)
    if loc:
        entry = loc.get('achievements', {}).get(str(meta.id))
        if entry and entry.get('description'):
            return entry['description']
    return meta.description

def character_name(character_id: int, locale: str | None = None) -> str:
    for item in get_characters():
        if item.id == character_id:
            return character_display_name(item, locale)
    return f'#{character_id}'

def achievement_name(achievement_id: int, locale: str | None = None) -> str:
    for item in get_achievements():
        if item.id == achievement_id:
            return achievement_display_name(item, locale)
    return f'#{achievement_id}'

def locale_stats() -> dict | None:
    loc = _load_locale('zh-CN')
    if not loc:
        return None
    return loc.get('stats')
