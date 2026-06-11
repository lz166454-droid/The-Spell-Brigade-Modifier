import json
from pathlib import Path

_SPELL_TYPES_PATH = Path(__file__).resolve().parents[2] / 'assets' / 'data' / 'spell_types.json'
_types_cache: list[dict] | None = None

def _load_types() -> list[dict]:
    global _types_cache
    if _types_cache is None:
        payload = json.loads(_SPELL_TYPES_PATH.read_text(encoding='utf-8'))
        _types_cache = payload.get('types', [])
    return _types_cache

def spell_display_name(spell_type_id: int, lang: str = 'zh-CN') -> str:
    for item in _load_types():
        if item.get('id') == spell_type_id:
            if lang == 'zh-CN':
                return item.get('name_zh') or item.get('name_en') or str(spell_type_id)
            return item.get('name_en') or str(spell_type_id)
    return str(spell_type_id)
