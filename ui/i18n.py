import configparser
import json
from pathlib import Path
from ui.paths import ASSETS_DIR, CONFIG_DIR, CONFIG_FILE

SUPPORTED_LANGUAGES = ('zh-CN', 'en')
DEFAULT_LANGUAGE = 'zh-CN'
LANGUAGE_LABEL_KEYS: tuple[tuple[str, str], ...] = (
    ('zh-CN', 'settings.language_zh'),
    ('en', 'settings.language_en'),
)
_I18N_DIR = ASSETS_DIR / 'i18n'
_current_language: str | None = None
_strings_cache: dict[str, dict[str, str]] = {}

def _ensure_config() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.is_file():
        config = configparser.ConfigParser()
        config['app'] = {'theme': 'DARK', 'save_dir': '', 'language': DEFAULT_LANGUAGE}
        with CONFIG_FILE.open('w', encoding='utf-8') as fp:
            config.write(fp)

def _load_strings(lang: str) -> dict[str, str]:
    if lang not in _strings_cache:
        path = _I18N_DIR / f'{lang}.json'
        _strings_cache[lang] = json.loads(path.read_text(encoding='utf-8'))
    return _strings_cache[lang]

def _sync_game_locale(lang: str) -> None:
    from lab.save.game_metadata import set_display_locale
    set_display_locale(lang)

def get_language() -> str:
    global _current_language
    if _current_language is not None:
        return _current_language
    _ensure_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding='utf-8')
    value = config.get('app', 'language', fallback=DEFAULT_LANGUAGE)
    _current_language = value if value in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    _sync_game_locale(_current_language)
    return _current_language

def toggle_language() -> str:
    current = get_language()
    next_lang = 'en' if current == 'zh-CN' else 'zh-CN'
    set_language(next_lang)
    return next_lang

def set_language(lang: str, *, emit: bool = True) -> None:
    global _current_language
    normalized = lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    if normalized == _current_language:
        return
    _current_language = normalized
    _ensure_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding='utf-8')
    if 'app' not in config:
        config['app'] = {}
    config['app']['language'] = normalized
    with CONFIG_FILE.open('w', encoding='utf-8') as fp:
        config.write(fp)
    _sync_game_locale(normalized)
    if emit:
        from ui.signals import signals
        signals.language_changed.emit(normalized)

def tr(key: str, **kwargs) -> str:
    lang = get_language()
    text = _load_strings(lang).get(key)
    if text is None and lang != DEFAULT_LANGUAGE:
        text = _load_strings(DEFAULT_LANGUAGE).get(key)
    if text is None:
        return key
    if not kwargs:
        return text
    merged = {
        'app_name': tr('app.name'),
        'app_subtitle': tr('app.subtitle'),
        **kwargs,
    }
    try:
        return text.format(**merged)
    except KeyError:
        return text

def stat_label(stat_key: str) -> str:
    return tr(f'trainer.stat.{stat_key}')

def trainer_tab_label(tab: str, **kwargs) -> str:
    return tr(f'trainer.tab.{tab}', **kwargs)
