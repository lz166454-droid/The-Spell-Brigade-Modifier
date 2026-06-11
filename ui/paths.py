import sys
from pathlib import Path

APP_NAME = '咒语旅团'
APP_SUBTITLE = '修改器'
APP_VERSION = '0.2.0'

def _project_root() -> Path:
    return Path(__file__).resolve().parent.parent

def _config_root() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).resolve().parent
    return _project_root()

ROOT_DIR = _project_root()
ASSETS_DIR = ROOT_DIR / 'assets'
ICONS_DIR = ASSETS_DIR / 'icons'
LOGO_DIR = ASSETS_DIR / 'logo'
STYLE_DIR = ASSETS_DIR / 'style'
CONFIG_DIR = _config_root() / 'config'
CONFIG_FILE = CONFIG_DIR / 'settings.ini'
APP_ICON_FILE = LOGO_DIR / 'logo.ico'

def icon_path(name: str) -> str:
    return str(ICONS_DIR / name)

def app_icon_path() -> str:
    return str(APP_ICON_FILE)
