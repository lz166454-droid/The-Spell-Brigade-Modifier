"""从 Steam 安装目录提取 Unity 本地化，生成 zh-CN 覆盖表。"""
import argparse
import json
import re
import sys
from pathlib import Path

try:
    import UnityPy
except ImportError:
    print('需要 UnityPy: pip install UnityPy')
    sys.exit(1)

DEFAULT_GAME_DIR = Path(r'E:\STEAM\steamapps\common\The Spell Brigade')
LOCALE_BUNDLE_DIR = 'TheSpellBrigade_Data/StreamingAssets/aa/StandaloneWindows64'
SHARED_BUNDLE = 'localization-assets-shared_assets_all.bundle'
EN_BUNDLE = 'localization-string-tables-english(en)_assets_all.bundle'
ZH_BUNDLE = 'localization-string-tables-chinese(simplified)(zh-cn)_assets_all.bundle'
ROOT = Path(__file__).resolve().parent.parent
META_FILE = ROOT / 'assets' / 'data' / 'game_metadata.json'
OUT_FILE = ROOT / 'assets' / 'data' / 'locale.zh-CN.json'

def load_mono(bundle_path: Path, name_part: str):
    env = UnityPy.load(str(bundle_path))
    for obj in env.objects:
        if obj.type.name != 'MonoBehaviour':
            continue
        data = obj.read()
        if name_part in (data.m_Name or ''):
            return data
    return None

def load_string_tables(bundle_dir: Path) -> tuple[dict[str, str], dict[str, str]]:
    shared = load_mono(bundle_dir / SHARED_BUNDLE, 'Localization_Strings Shared')
    en_table = load_mono(bundle_dir / EN_BUNDLE, 'Localization_Strings_en')
    zh_table = load_mono(bundle_dir / ZH_BUNDLE, 'Localization_Strings_zh-CN')
    if not shared or not en_table or not zh_table:
        raise FileNotFoundError('无法在 bundle 中找到 Localization_Strings 表')
    id_to_key = {entry.m_Id: entry.m_Key for entry in shared.m_Entries}
    en_by_key: dict[str, str] = {}
    zh_by_key: dict[str, str] = {}
    for entry in en_table.m_TableData:
        key = id_to_key.get(entry.m_Id)
        if key:
            en_by_key[key] = entry.m_Localized
    for entry in zh_table.m_TableData:
        key = id_to_key.get(entry.m_Id)
        if key:
            zh_by_key[key] = entry.m_Localized
    return en_by_key, zh_by_key

def strip_rich(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text).strip()

def character_keys(name: str) -> list[str]:
    compact = name.replace(' ', '')
    return [f'Character_{compact}', f'CharacterClass_{compact}']

CURSE_NAME_MAP = {
    'Enemies Drop Less XP': 'EnemiesDropLessXP',
    'Reduce All Healing': 'ReduceAllHealing',
    'No Enchantments': 'NoEnchantments',
    'Take Damage On Level Up': 'TakeDamageOnLevelUp',
    'One Less Spell': 'OneLessSpell',
    'Stronger Enemies': 'StrongerEnemies',
    'One Hit Mode': 'OneHitMode',
    'One Less Store Item': 'OneLessStoreItem',
}

def achievement_keys(name: str, description: str) -> list[str]:
    keys: list[str] = []
    if name.startswith('Title: '):
        keys.append('Title_' + name[7:].replace(' ', ''))
    mode_match = re.fullmatch(r'(\w+) Mode', name)
    if mode_match:
        keys.append(f'Modifier_{mode_match.group(1)}Mode_Name')
    element_match = re.fullmatch(r'(\w+) Element', name)
    if element_match:
        elem = element_match.group(1)
        keys.extend([f'Title_{elem}Element', f'Element_{elem}'])
    skin_match = re.fullmatch(r'(.+?) Skin (\d+)', name)
    if skin_match:
        char = skin_match.group(1).replace(' ', '')
        idx = int(skin_match.group(2)) - 1
        keys.extend([f'Skin_{char}_{idx}', f'Skin_{char}_{skin_match.group(2)}'])
    prestige_match = re.fullmatch(r'(.+?) Prestige', name)
    if prestige_match:
        char = prestige_match.group(1).replace(' ', '')
        keys.append(f'Skin_{char}_Prestige')
    tier_match = re.fullmatch(r'Upgrade Tier (\d+)', name)
    if tier_match:
        keys.append(f'Reward_Name_UpgradeTier_{tier_match.group(1)}')
    if name == 'Double Infusion':
        keys.append('Reward_Name_DoubleInfusion')
    objective_match = re.fullmatch(r'Objective: (\w+)', name)
    if objective_match:
        keys.append(f'Reward_Name_Objective_{objective_match.group(1)}')
    curse_match = re.fullmatch(r'Curse: (.+)', name)
    if curse_match:
        slug = CURSE_NAME_MAP.get(curse_match.group(1))
        if slug:
            keys.append(f'Curse_{slug}_Name_0')
    if '9001' in name or '9001' in description:
        keys.append('Challenge_CastManyFallingStarsAsStarMage_Name')
    if 'Pi Damage' in name or '314' in description:
        keys.append('Challenge_DealPiDamageAsHatty_Name')
    if name == 'Title: Complete All Worlds Nightmare':
        keys.append('Challenge_CompleteAllWorldsNightmare_Name')
    keys.append(name.replace(' ', ''))
    keys.append(name)
    return keys

def pick_zh(keys: list[str], en_by_key: dict[str, str], zh_by_key: dict[str, str], en_name: str) -> tuple[str | None, str | None]:
    for key in keys:
        if key in zh_by_key:
            return key, strip_rich(zh_by_key[key])
    for key, value in en_by_key.items():
        if value == en_name and key in zh_by_key:
            return key, strip_rich(zh_by_key[key])
    plain_name = strip_rich(en_name)
    for key, value in en_by_key.items():
        if plain_name and plain_name.lower() == strip_rich(value).lower() and key in zh_by_key:
            return key, strip_rich(zh_by_key[key])
    if en_name.endswith('_Name') is False:
        for key, value in en_by_key.items():
            if not key.endswith('_Name'):
                continue
            if plain_name.lower() in strip_rich(value).lower() or strip_rich(value).lower() in plain_name.lower():
                if key in zh_by_key and len(strip_rich(value)) <= len(plain_name) + 20:
                    return key, strip_rich(zh_by_key[key])
    return None, None

def extract(game_dir: Path) -> dict:
    bundle_dir = game_dir / LOCALE_BUNDLE_DIR
    if not bundle_dir.is_dir():
        raise FileNotFoundError(f'本地化 bundle 目录不存在: {bundle_dir}')
    en_by_key, zh_by_key = load_string_tables(bundle_dir)
    meta = json.loads(META_FILE.read_text(encoding='utf-8'))
    characters: dict[str, dict] = {}
    achievements: dict[str, dict] = {}
    for ch in meta['characters']:
        cid = str(ch['id'])
        loc_keys = character_keys(ch['name'])
        loc_key, name_zh = pick_zh(loc_keys, en_by_key, zh_by_key, ch['name'])
        class_key = f"CharacterClass_{ch['character_class'].replace(' ', '')}"
        if class_key not in en_by_key:
            class_key = None
            for key in en_by_key:
                if key.startswith('CharacterClass_') and en_by_key[key] == ch['character_class']:
                    class_key = key
                    break
        class_zh = strip_rich(zh_by_key[class_key]) if class_key and class_key in zh_by_key else None
        characters[cid] = {
            'name': name_zh or ch['name'],
            'character_class': class_zh or ch['character_class'],
            'loc_key': loc_key,
            'class_loc_key': class_key,
        }
    for ach in meta['achievements']:
        aid = str(ach['id'])
        loc_keys = achievement_keys(ach['name'], ach.get('description', ''))
        loc_key, name_zh = pick_zh(loc_keys, en_by_key, zh_by_key, ach['name'])
        desc_key = None
        desc_zh = None
        if loc_key and loc_key.endswith('_Name'):
            desc_key = loc_key[:-5]
            if desc_key in zh_by_key:
                desc_zh = strip_rich(zh_by_key[desc_key])
        achievements[aid] = {
            'name': name_zh or ach['name'],
            'description': desc_zh or ach.get('description', ''),
            'loc_key': loc_key,
            'desc_loc_key': desc_key,
        }
    char_matched = sum(1 for v in characters.values() if v.get('loc_key'))
    ach_matched = sum(1 for v in achievements.values() if v.get('loc_key'))
    return {
        'source': str(game_dir),
        'locale': 'zh-CN',
        'stats': {
            'string_keys_en': len(en_by_key),
            'string_keys_zh': len(zh_by_key),
            'characters_matched': char_matched,
            'characters_total': len(characters),
            'achievements_matched': ach_matched,
            'achievements_total': len(achievements),
        },
        'characters': characters,
        'achievements': achievements,
    }

def main() -> int:
    parser = argparse.ArgumentParser(description='从 Steam 游戏目录提取简体中文本地化')
    parser.add_argument('--game-dir', type=Path, default=DEFAULT_GAME_DIR, help='The Spell Brigade 安装目录')
    parser.add_argument('-o', '--output', type=Path, default=OUT_FILE, help='输出 JSON 路径')
    args = parser.parse_args()
    payload = extract(args.game_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    stats = payload['stats']
    print(f"已写入: {args.output}")
    print(f"角色: {stats['characters_matched']}/{stats['characters_total']}")
    print(f"成就: {stats['achievements_matched']}/{stats['achievements_total']}")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
