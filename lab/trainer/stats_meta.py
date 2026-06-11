from dataclasses import dataclass
from lab.trainer.stat_calc import DISPLAY_MODIFIER_PERCENT, DISPLAY_VALUE, DISPLAY_VALUE_PERCENT

@dataclass(frozen=True)
class CharacterStatDef:
    stat_type: int
    key: str
    decimals: int = 1
    display_type: str = DISPLAY_VALUE
    panel_source: str = 'character'
    panel_positive_modifiers_only: bool = False

BASIC_STATS: tuple[CharacterStatDef, ...] = (
    CharacterStatDef(8, 'max_health', 0),
    CharacterStatDef(16, 'health_regen', 0),
    CharacterStatDef(14, 'armor', 0),
    CharacterStatDef(15, 'dodge', 0),
    CharacterStatDef(7, 'movement_speed', 1, display_type=DISPLAY_MODIFIER_PERCENT),
    CharacterStatDef(12, 'critical_chance', 0),
    CharacterStatDef(13, 'critical_damage', 0, display_type=DISPLAY_VALUE_PERCENT),
    CharacterStatDef(11, 'pickup_radius', 0, display_type=DISPLAY_VALUE_PERCENT),
    CharacterStatDef(10, 'xp_gain', 0, display_type=DISPLAY_VALUE_PERCENT),
    CharacterStatDef(9, 'luck', 0),
    CharacterStatDef(0, 'char_spell_damage', 1, display_type=DISPLAY_VALUE_PERCENT, panel_positive_modifiers_only=True),
    CharacterStatDef(6, 'char_spell_range', 0, display_type=DISPLAY_VALUE_PERCENT),
    CharacterStatDef(2, 'char_spell_fire_rate', 0, display_type=DISPLAY_VALUE_PERCENT),
)
HIDDEN_STATS: tuple[CharacterStatDef, ...] = (
    CharacterStatDef(17, 'rerolls', 0),
    CharacterStatDef(39, 'bans', 0),
    CharacterStatDef(40, 'pins', 0),
    CharacterStatDef(38, 'revive_health_pct'),
    CharacterStatDef(37, 'gold_gain'),
    CharacterStatDef(19, 'revives', 0),
    CharacterStatDef(18, 'revive_speed'),
)
SPELL_STATS: tuple[CharacterStatDef, ...] = (
    CharacterStatDef(0, 'spell_damage', 0, display_type=DISPLAY_VALUE_PERCENT, panel_source='spell'),
    CharacterStatDef(6, 'spell_range', 0, display_type=DISPLAY_VALUE_PERCENT, panel_source='spell'),
    CharacterStatDef(2, 'spell_fire_rate', 0, display_type=DISPLAY_VALUE_PERCENT, panel_source='spell'),
)
CHARACTER_STATS: tuple[CharacterStatDef, ...] = BASIC_STATS + HIDDEN_STATS
STAT_BY_KEY = {item.key: item for item in BASIC_STATS + HIDDEN_STATS}
SPELL_STAT_BY_KEY = {item.key: item for item in SPELL_STATS}
