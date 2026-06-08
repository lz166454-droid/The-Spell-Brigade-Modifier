from dataclasses import dataclass
from lab.trainer.stat_calc import DISPLAY_MODIFIER_PERCENT, DISPLAY_VALUE, DISPLAY_VALUE_PERCENT

@dataclass(frozen=True)
class CharacterStatDef:
    stat_type: int
    key: str
    decimals: int = 1
    display_type: str = DISPLAY_VALUE
    panel_source: str = 'character'

CHARACTER_STATS: tuple[CharacterStatDef, ...] = (
    CharacterStatDef(8, 'max_health', 0),
    CharacterStatDef(16, 'health_regen', 0),
    CharacterStatDef(14, 'armor', 0),
    CharacterStatDef(15, 'dodge', 0),
    CharacterStatDef(7, 'movement_speed', 0, display_type=DISPLAY_MODIFIER_PERCENT),
    CharacterStatDef(0, 'spell_damage', 0, display_type=DISPLAY_VALUE_PERCENT, panel_source='spell_damage'),
    CharacterStatDef(6, 'spell_range', 0, display_type=DISPLAY_VALUE_PERCENT),
    CharacterStatDef(2, 'spell_fire_rate', 0, display_type=DISPLAY_VALUE_PERCENT),
    CharacterStatDef(12, 'critical_chance', 0),
    CharacterStatDef(13, 'critical_damage', 0, display_type=DISPLAY_VALUE_PERCENT),
    CharacterStatDef(11, 'pickup_radius', 0, display_type=DISPLAY_VALUE_PERCENT),
    CharacterStatDef(10, 'xp_gain', 0, display_type=DISPLAY_VALUE_PERCENT),
    CharacterStatDef(9, 'luck', 0),
    CharacterStatDef(17, 'rerolls', 0),
    CharacterStatDef(18, 'revive_speed'),
    CharacterStatDef(19, 'revives', 0),
    CharacterStatDef(37, 'gold_gain'),
    CharacterStatDef(38, 'revive_health_pct'),
    CharacterStatDef(39, 'bans', 0),
    CharacterStatDef(40, 'pins', 0),
)

STAT_BY_KEY = {item.key: item for item in CHARACTER_STATS}
STAT_BY_TYPE = {item.stat_type: item for item in CHARACTER_STATS}
