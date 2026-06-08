import json
import re
from pathlib import Path

_STYLE_ROOT = Path(__file__).resolve().parent
_TOKEN_PATTERN = re.compile(r'\{\{(\w+)\}\}')
_MANIFEST = [
    'base/reset.qss',
    'widgets/button.qss',
    'widgets/input.qss',
    'widgets/nav.qss',
    'widgets/panel.qss',
    'widgets/scrollbar.qss',
    'widgets/list.qss',
]
_theme_cache: dict[str, str] = {}

def _normalize_theme(theme: str) -> str:
    value = str(theme or 'DARK').strip().upper()
    return value if value in ('DARK', 'LIGHT') else 'DARK'

def _theme_key(theme: str) -> str:
    return 'dark' if _normalize_theme(theme) == 'DARK' else 'light'

def _read_text(relative_path: str) -> str:
    path = _STYLE_ROOT / relative_path
    if not path.is_file():
        raise FileNotFoundError(f'QSS 片段不存在: {path}')
    return path.read_text(encoding='utf-8-sig')

def _load_tokens(theme: str) -> dict[str, str]:
    path = _STYLE_ROOT / 'tokens' / f'{_theme_key(theme)}.json'
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        return {}
    return {str(key): str(value) for key, value in data.items()}

def load_tokens(theme: str | None = None) -> dict[str, str]:
    from ui.theme import get_current_theme
    resolved = _normalize_theme(theme if theme else get_current_theme())
    return _load_tokens(resolved)

def inject_tokens(content: str, theme: str) -> str:
    tokens = _load_tokens(theme)
    if not tokens:
        return content
    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return tokens.get(key, match.group(0))
    return _TOKEN_PATTERN.sub(replace, content)

def load_theme_qss(theme: str, *, use_cache: bool = True) -> str:
    normalized = _normalize_theme(theme)
    if use_cache and normalized in _theme_cache:
        return _theme_cache[normalized]
    parts: list[str] = []
    for relative in _MANIFEST:
        chunk = inject_tokens(_read_text(relative), normalized)
        parts.append(chunk)
    content = '\n'.join(parts)
    if use_cache:
        _theme_cache[normalized] = content
    return content

def clear_theme_cache() -> None:
    _theme_cache.clear()
