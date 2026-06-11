
import re
from dataclasses import dataclass, field

@dataclass
class ChallengeProgress:
    value: int
    is_completed: bool

@dataclass
class CharacterRank:
    current_rank: int
    progress_towards_next_rank: float
    prestige: int | None = None

@dataclass
class ES3SaveData:
    version_number: str
    play_time_in_minutes: int
    gold: int
    character_ranks: dict[int, CharacterRank] = field(default_factory=dict)
    selected_character: int = 0
    selected_skins: dict[int, int] = field(default_factory=dict)
    challenges: dict[int, ChallengeProgress] = field(default_factory=dict)
    number_of_attempted_runs: int = 0

def extract_save_data(raw_text: str) -> ES3SaveData:
    return ES3SaveData(
        version_number=_extract_version_number(raw_text),
        play_time_in_minutes=_extract_play_time(raw_text),
        gold=_extract_gold(raw_text),
        character_ranks=_extract_character_ranks(raw_text),
        selected_character=_extract_selected_character(raw_text),
        selected_skins=_extract_selected_skins(raw_text),
        challenges=_extract_challenges(raw_text),
        number_of_attempted_runs=_extract_attempted_runs(raw_text),
    )

def _extract_version_number(raw_text: str) -> str:
    match = re.search(r'"VersionNumber"\s*:\s*"([^"]+)"', raw_text)
    return match.group(1) if match else 'unknown'

def _extract_play_time(raw_text: str) -> int:
    match = re.search(r'"PlayTimeInMinutes"\s*:\s*(\d+)', raw_text)
    return int(match.group(1)) if match else 0

def _extract_gold(raw_text: str) -> int:
    match = re.search(r'"Gold"\s*:\s*(\d+)', raw_text)
    return int(match.group(1)) if match else 0

def _extract_selected_character(raw_text: str) -> int:
    match = re.search(r'"SelectedCharacter"\s*:\s*(\d+)', raw_text)
    return int(match.group(1)) if match else 0

def _extract_attempted_runs(raw_text: str) -> int:
    match = re.search(r'"NumberOfAttemptedRuns"\s*:\s*(\d+)', raw_text)
    return int(match.group(1)) if match else 0

def _extract_character_ranks(raw_text: str) -> dict[int, CharacterRank]:
    ranks: dict[int, CharacterRank] = {}
    section_match = re.search(r'"RankProgressPerCharacter"\s*:\s*\{([\s\S]*?)\n\t\t\t\}', raw_text)
    if not section_match:
        return ranks
    entry_pattern = re.compile(
        r'(\d+):\{\s*"CurrentRank"\s*:\s*(\d+)\s*,\s*"ProgressTowardsNextRank"\s*:\s*(-?\d+(?:\.\d+)?)(?:\s*,\s*"Prestige"\s*:\s*(\d+))?'
    )
    for match in entry_pattern.finditer(section_match.group(1)):
        character_id = int(match.group(1))
        prestige = int(match.group(4)) if match.group(4) is not None else None
        ranks[character_id] = CharacterRank(
            current_rank=int(match.group(2)),
            progress_towards_next_rank=float(match.group(3)),
            prestige=prestige,
        )
    return ranks

def _extract_selected_skins(raw_text: str) -> dict[int, int]:
    skins: dict[int, int] = {}
    section_match = re.search(r'"SelectedSkinPerCharacter"\s*:\s*\{([^}]*)\}', raw_text)
    if not section_match:
        return skins
    for match in re.finditer(r'(\d+)\s*:\s*(\d+)', section_match.group(1)):
        skins[int(match.group(1))] = int(match.group(2))
    return skins

def _extract_challenges(raw_text: str) -> dict[int, ChallengeProgress]:
    challenges: dict[int, ChallengeProgress] = {}
    old_section = _extract_challenge_section(raw_text, 'ProgressForChallenges')
    new_section = _extract_challenge_section(raw_text, 'New_ProgressForChallenges')
    challenges.update(old_section)
    challenges.update(new_section)
    return challenges

def _extract_challenge_section(raw_text: str, section_name: str) -> dict[int, ChallengeProgress]:
    result: dict[int, ChallengeProgress] = {}
    if section_name == 'ProgressForChallenges':
        section_regex = r'(?:^|[,{])\s*"ProgressForChallenges"\s*:\s*\{([\s\S]*?)\n\t\t\t\}'
    else:
        section_regex = r'"New_ProgressForChallenges"\s*:\s*\{([\s\S]*?)\n\t\t\t\}'
    section_match = re.search(section_regex, raw_text)
    if not section_match:
        return result
    entry_pattern = re.compile(
        r'(\d+):\{\s*"Value"\s*:\s*(-?\d+)\s*,\s*"IsCompleted"\s*:\s*(true|false)'
    )
    for match in entry_pattern.finditer(section_match.group(1)):
        result[int(match.group(1))] = ChallengeProgress(
            value=int(match.group(2)),
            is_completed=match.group(3) == 'true',
        )
    return result

def extract_active_slot(raw_text: str) -> int | None:
    match = re.search(r'"active_slot"\s*:\s*\{[^}]*"value"\s*:\s*(-?\d+)', raw_text)
    return int(match.group(1)) if match else None

def get_completed_challenge_ids(raw_text: str) -> list[int]:
    challenges = _extract_challenges(raw_text)
    completed = [cid for cid, prog in challenges.items() if prog.is_completed]
    return sorted(completed)
