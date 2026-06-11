import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from ui.paths import APP_VERSION
MAIN = ROOT / 'main.py'
ASSETS = ROOT / 'assets'
DIST = ROOT / 'dist'
ICON = ROOT / 'assets' / 'logo' / 'logo.ico'
OUTPUT_BASENAME = 'SpellBrigadeModifier'
OUTPUT_NAME = f'{OUTPUT_BASENAME}-v{APP_VERSION}'
# GUI 未引用；仅开发/逆向用
NOFOLLOW_DEV = (
    'lab.trainer_cli',
    'lab.extract_steam_loc',
    'rich',
)
# 实际仅用 QtCore / QtGui / QtWidgets / QtSvg / QtXml
NOFOLLOW_PYSIDE6 = (
    'PySide6.Qt3DAnimation',
    'PySide6.Qt3DCore',
    'PySide6.Qt3DExtras',
    'PySide6.Qt3DInput',
    'PySide6.Qt3DLogic',
    'PySide6.Qt3DRender',
    'PySide6.QtAxContainer',
    'PySide6.QtBluetooth',
    'PySide6.QtCanvasPainter',
    'PySide6.QtCharts',
    'PySide6.QtConcurrent',
    'PySide6.QtDataVisualization',
    'PySide6.QtDBus',
    'PySide6.QtDesigner',
    'PySide6.QtGraphs',
    'PySide6.QtGraphsWidgets',
    'PySide6.QtHelp',
    'PySide6.QtHttpServer',
    'PySide6.QtLocation',
    'PySide6.QtMultimedia',
    'PySide6.QtMultimediaWidgets',
    'PySide6.QtNetwork',
    'PySide6.QtNetworkAuth',
    'PySide6.QtNfc',
    'PySide6.QtOpenGL',
    'PySide6.QtOpenGLWidgets',
    'PySide6.QtPdf',
    'PySide6.QtPdfWidgets',
    'PySide6.QtPositioning',
    'PySide6.QtPrintSupport',
    'PySide6.QtQml',
    'PySide6.QtQuick',
    'PySide6.QtQuick3D',
    'PySide6.QtQuickControls2',
    'PySide6.QtQuickTest',
    'PySide6.QtQuickWidgets',
    'PySide6.QtRemoteObjects',
    'PySide6.QtScxml',
    'PySide6.QtSensors',
    'PySide6.QtSerialBus',
    'PySide6.QtSerialPort',
    'PySide6.QtSpatialAudio',
    'PySide6.QtSql',
    'PySide6.QtStateMachine',
    'PySide6.QtSvgWidgets',
    'PySide6.QtTest',
    'PySide6.QtTextToSpeech',
    'PySide6.QtUiTools',
    'PySide6.QtWebChannel',
    'PySide6.QtWebEngineCore',
    'PySide6.QtWebEngineQuick',
    'PySide6.QtWebEngineWidgets',
    'PySide6.QtWebSockets',
    'PySide6.QtWebView',
)
# 默认 sensible 插件中未用到的目录（保留 platforms / imageformats / iconengines / styles 等）
NOINCLUDE_QT_PLUGINS = (
    'assetimporters',
    'canbus',
    'designer',
    'geometryloaders',
    'geoservices',
    'multimedia',
    'networkinformation',
    'position',
    'qmllint',
    'qmltooling',
    'renderers',
    'renderplugins',
    'sceneparsers',
    'scxmldatamodel',
    'sensors',
    'sqldrivers',
    'texttospeech',
    'tls',
    'vectorimageformats',
    'webview',
)
NOINCLUDE_DATA_FILES = (
    '**/qml/**',
    '**/QtWebEngine*',
)

def _quote(part: str) -> str:
    if ' ' in part:
        return f'"{part}"'
    return part

def _extend_nofollow(cmd: list[str], modules: tuple[str, ...]) -> None:
    for module in modules:
        cmd.append(f'--nofollow-import-to={module}')

def build_nuitka_cmd(*, onefile: bool) -> list[str]:
    cmd = [
        sys.executable,
        '-m',
        'nuitka',
        str(MAIN),
        '--standalone',
        '--enable-plugin=pyside6',
        f'--include-data-dir={ASSETS}=assets',
        f'--output-dir={DIST}',
        f'--output-filename={OUTPUT_NAME}.exe',
        '--windows-console-mode=disable',
        '--assume-yes-for-downloads',
        '--remove-output',
        '--noinclude-qt-translations',
        '--noinclude-setuptools-mode=nofollow',
        '--noinclude-pytest-mode=nofollow',
        '--noinclude-unittest-mode=nofollow',
        '--noinclude-pydoc-mode=nofollow',
        '--nofollow-import-to=*.tests',
        '--nofollow-import-to=pytest',
        '--nofollow-import-to=unittest',
        '--nofollow-import-to=doctest',
        '--nofollow-import-to=pydoc',
    ]
    _extend_nofollow(cmd, NOFOLLOW_DEV)
    _extend_nofollow(cmd, NOFOLLOW_PYSIDE6)
    for plugin in NOINCLUDE_QT_PLUGINS:
        cmd.append(f'--noinclude-qt-plugins={plugin}')
    for pattern in NOINCLUDE_DATA_FILES:
        cmd.append(f'--noinclude-data-files={pattern}')
    if onefile:
        cmd.insert(4, '--onefile')
    if ICON.is_file():
        cmd.insert(-1, f'--windows-icon-from-ico={ICON}')
    return cmd

def main() -> int:
    parser = argparse.ArgumentParser(description='使用 Nuitka 打包咒语旅团修改器')
    parser.add_argument('--folder', action='store_true', help='输出 standalone 目录而非单文件 exe')
    args = parser.parse_args()
    if not MAIN.is_file():
        print(f'Missing entry file: {MAIN}', file=sys.stderr)
        return 1
    if not ASSETS.is_dir():
        print(f'Missing assets directory: {ASSETS}', file=sys.stderr)
        return 1
    if not ICON.is_file():
        print(f'Note: icon not found at {ICON}, exe will have no custom icon')
    DIST.mkdir(parents=True, exist_ok=True)
    cmd = build_nuitka_cmd(onefile=not args.folder)
    print('Running:', ' '.join(_quote(part) for part in cmd))
    completed = subprocess.run(cmd, cwd=ROOT)
    if completed.returncode == 0:
        if args.folder:
            print(f'Done: {DIST / f"{MAIN.stem}.dist" / f"{OUTPUT_NAME}.exe"}')
        else:
            print(f'Done: {DIST / f"{OUTPUT_NAME}.exe"}')
    return completed.returncode

if __name__ == '__main__':
    raise SystemExit(main())
