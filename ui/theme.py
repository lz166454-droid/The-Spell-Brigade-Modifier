import configparser
from pathlib import Path
from assets.style.style import clear_theme_cache, load_theme_qss
from ui.paths import CONFIG_DIR, CONFIG_FILE
from ui.signals import signals

_current_theme: str | None = None

def _ensure_config() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.is_file():
        config = configparser.ConfigParser()
        config['app'] = {'theme': 'DARK', 'save_dir': ''}
        with CONFIG_FILE.open('w', encoding='utf-8') as fp:
            config.write(fp)

def get_current_theme() -> str:
    global _current_theme
    if _current_theme is not None:
        return _current_theme
    _ensure_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding='utf-8')
    value = config.get('app', 'theme', fallback='DARK').upper()
    _current_theme = value if value in ('DARK', 'LIGHT') else 'DARK'
    return _current_theme

def set_current_theme(theme: str) -> None:
    global _current_theme
    normalized = theme.upper()
    if normalized not in ('DARK', 'LIGHT'):
        normalized = 'DARK'
    _current_theme = normalized
    _ensure_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding='utf-8')
    if 'app' not in config:
        config['app'] = {}
    config['app']['theme'] = normalized
    with CONFIG_FILE.open('w', encoding='utf-8') as fp:
        config.write(fp)

def get_save_dir() -> Path | None:
    _ensure_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding='utf-8')
    value = config.get('app', 'save_dir', fallback='').strip()
    if not value:
        return None
    path = Path(value)
    return path if path.is_dir() else None

def set_save_dir(path: Path | str | None) -> None:
    _ensure_config()
    config = configparser.ConfigParser()
    config.read(CONFIG_FILE, encoding='utf-8')
    if 'app' not in config:
        config['app'] = {}
    if path is None:
        config['app']['save_dir'] = ''
    else:
        config['app']['save_dir'] = str(Path(path))
    with CONFIG_FILE.open('w', encoding='utf-8') as fp:
        config.write(fp)

def toggle_theme() -> str:
    current = get_current_theme()
    new_theme = 'LIGHT' if current == 'DARK' else 'DARK'
    set_current_theme(new_theme)
    clear_theme_cache()
    return new_theme

def apply_theme_style(widget) -> None:
    style = load_theme_qss(get_current_theme())
    if style:
        widget.setStyleSheet(style)

def reload_theme_style() -> str:
    clear_theme_cache()
    return load_theme_qss(get_current_theme())

def apply_theme_and_notify(window) -> None:
    apply_theme_style(window)
    signals.theme_changed.emit()
