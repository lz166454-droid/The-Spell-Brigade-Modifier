from lab.trainer.stat_calc import DISPLAY_LIFETIME_CENTIS, DISPLAY_VALUE, DISPLAY_VALUE_PERCENT

SPELL_LEVEL_KEY = 'level'

_STAT_LABEL_BY_TYPE: dict[int, str] = {
    0: 'spell_damage',
    1: 'spell_range',
    2: 'spell_fire_rate',
    3: 'spell_lifetime',
    4: 'spell_damage_tick_rate',
    5: 'spell_size',
    6: 'spell_size',
    12: 'spell_range',
    13: 'spell_lifetime',
    20: 'spell_projectiles',
}

_STAT_DECIMALS_BY_TYPE: dict[int, int] = {
    0: 0,
    1: 2,
    2: 2,
    3: 2,
    4: 2,
    5: 2,
    6: 2,
    12: 2,
    13: 2,
    20: 0,
}

_LIFETIME_STAT_TYPES = frozenset({3, 13})

def spell_stat_storage_key(stat_type: int) -> str:
    return f't{stat_type}'

def spell_stat_label_key(stat_type: int) -> str:
    return _STAT_LABEL_BY_TYPE.get(stat_type, f'spell_stat_type_{stat_type}')

def spell_stat_decimals(stat_type: int) -> int:
    return _STAT_DECIMALS_BY_TYPE.get(stat_type, 2)

def infer_spell_stat_display_type(stat_type: int, calc_type: int) -> str:
    if stat_type in _LIFETIME_STAT_TYPES:
        return DISPLAY_LIFETIME_CENTIS
    if stat_type == 6 and calc_type != 1:
        return DISPLAY_VALUE
    if stat_type in (0, 1, 2, 4, 5, 12, 20):
        return DISPLAY_VALUE
    if calc_type == 1:
        return DISPLAY_VALUE
    return DISPLAY_VALUE_PERCENT
