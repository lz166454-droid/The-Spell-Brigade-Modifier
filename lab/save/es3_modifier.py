
import re
from dataclasses import dataclass

@dataclass
class ModificationResult:
    success: bool
    new_raw_text: str
    error: str | None = None

@dataclass
class ValidationResult:
    valid: bool
    errors: list[str]

def modify_gold(raw_text: str, new_value: int) -> ModificationResult:
    pattern = re.compile(r'("Gold"\s*:\s*)(\d+)')
    if not pattern.search(raw_text):
        return ModificationResult(False, raw_text, 'Gold field not found')
    return ModificationResult(True, pattern.sub(rf'\g<1>{new_value}', raw_text, count=1))

def modify_challenge_progress(
    raw_text: str,
    challenge_id: int,
    new_value: int,
    is_completed: bool,
) -> ModificationResult:
    pattern = re.compile(
        rf'((?:^|[{{,]){challenge_id}:\{{[^}}]*"Value"\s*:\s*)(-?\d+)([^}}]*"IsCompleted"\s*:\s*)(true|false)',
        re.MULTILINE,
    )
    if not pattern.search(raw_text):
        return ModificationResult(False, raw_text, f'Challenge {challenge_id} not found')
    completed_str = 'true' if is_completed else 'false'
    new_raw_text = pattern.sub(rf'\g<1>{new_value}\g<3>{completed_str}', raw_text)
    return ModificationResult(True, new_raw_text)

def modify_character_rank(
    raw_text: str,
    character_id: int,
    current_rank: int,
    progress_towards_next_rank: float = 0,
    prestige: int | None = None,
) -> ModificationResult:
    pattern = re.compile(
        rf'((?:^|[{{,]){character_id}:\{{[^}}]*"CurrentRank"\s*:\s*)(\d+)([^}}]*"ProgressTowardsNextRank"\s*:\s*)(-?\d+(?:\.\d+)?)',
        re.DOTALL,
    )
    if not pattern.search(raw_text):
        return ModificationResult(False, raw_text, f'Character {character_id} not found')
    new_raw_text = pattern.sub(
        rf'\g<1>{current_rank}\g<3>{progress_towards_next_rank}',
        raw_text,
        count=1,
    )
    if prestige is not None:
        prestige_pattern = re.compile(
            rf'((?:^|[{{,]){character_id}:\{{[^}}]*"Prestige"\s*:\s*)(\d+)',
            re.DOTALL,
        )
        if prestige_pattern.search(new_raw_text):
            new_raw_text = prestige_pattern.sub(rf'\g<1>{prestige}', new_raw_text, count=1)
    return ModificationResult(True, new_raw_text)

def add_character_rank(
    raw_text: str,
    character_id: int,
    current_rank: int,
    progress_towards_next_rank: float = 0,
    prestige: int = 0,
) -> ModificationResult:
    exists_pattern = re.compile(rf'(?:^|[{{,]){character_id}:\{{[^}}]*"CurrentRank"', re.DOTALL)
    if exists_pattern.search(raw_text):
        return ModificationResult(False, raw_text, f'Character {character_id} already exists')
    if not re.search(r'"RankProgressPerCharacter"\s*:\s*\{', raw_text):
        return ModificationResult(False, raw_text, 'RankProgressPerCharacter section not found')
    section_content_match = re.search(
        r'"RankProgressPerCharacter"\s*:\s*\{([\s\S]*?)\n\t\t\t\}',
        raw_text,
    )
    has_prestige = bool(
        section_content_match and re.search(r'"Prestige"\s*:\s*\d+', section_content_match.group(1))
    )
    if has_prestige:
        end_pattern = re.compile(
            r'("RankProgressPerCharacter"\s*:\s*\{[\s\S]*?"Prestige"\s*:\s*\d+\s*\})(\s*\})'
        )
        new_entry = (
            f',{character_id}:{{\n\t\t\t\t"CurrentRank" : {current_rank},\n'
            f'\t\t\t\t"ProgressTowardsNextRank" : {progress_towards_next_rank},\n'
            f'\t\t\t\t"Prestige" : {prestige}\n\t\t\t}}'
        )
    else:
        end_pattern = re.compile(
            r'("RankProgressPerCharacter"\s*:\s*\{[\s\S]*?"ProgressTowardsNextRank"\s*:\s*-?\d+(?:\.\d+)?\s*\})(\s*\})'
        )
        new_entry = (
            f',{character_id}:{{\n\t\t\t\t"CurrentRank" : {current_rank},\n'
            f'\t\t\t\t"ProgressTowardsNextRank" : {progress_towards_next_rank}\n\t\t\t}}'
        )
    if not end_pattern.search(raw_text):
        return ModificationResult(False, raw_text, 'Could not find RankProgressPerCharacter section end')
    new_raw_text = end_pattern.sub(rf'\g<1>{new_entry}\g<2>', raw_text, count=1)
    return ModificationResult(True, new_raw_text)

def validate_modified_save(raw_text: str) -> ValidationResult:
    errors: list[str] = []
    if not re.search(r'"Gold"\s*:\s*\d+', raw_text):
        errors.append('Gold field missing or malformed')
    if not re.search(r'"ProgressForChallenges"\s*:\s*\{', raw_text):
        errors.append('ProgressForChallenges section missing')
    if not re.search(r'"RankProgressPerCharacter"\s*:\s*\{', raw_text):
        errors.append('RankProgressPerCharacter section missing')
    open_braces = raw_text.count('{')
    close_braces = raw_text.count('}')
    if open_braces != close_braces:
        errors.append(f'Bracket mismatch: {open_braces} open, {close_braces} close')
    open_brackets = raw_text.count('[')
    close_brackets = raw_text.count(']')
    if open_brackets != close_brackets:
        errors.append(f'Square bracket mismatch: {open_brackets} open, {close_brackets} close')
    return ValidationResult(len(errors) == 0, errors)
