import re
from math import log10, floor

MAX_USERNAME_LENGTH = 15

# Only allow alphanumeric characters and underscores
_INVALID_CHARS_PATTERN = re.compile(r'[^a-z0-9_]')

# Note - turns out Auth0 allows many more characters 
# https://auth0.com/docs/authenticate/database-connections/require-username#allowed-characters
# you can use 
# - alphanumeric chcaracters (all convert to lowercase)
# - ^$.!`-#+~_' and @ but no email addresses




def numDigits(number):
    return floor(log10(max(10, number))) + 1

def _total_length(prefix: str, how_many: int) -> int:
    return len(prefix) + numDigits(how_many)


def validate_username(value: str, how_many: int = 1) -> bool:
    if len(value) == 0: # default state - it's fine
        return True
    if _total_length(value, how_many) > MAX_USERNAME_LENGTH:
        return False
    if ' ' in value:
        return False
    if _INVALID_CHARS_PATTERN.search(value):
        return False
    return True


def find_all_matches(string, group=0):
    """
    adapted from https://stackoverflow.com/a/77830224/11594175
    """
    pos = 0
    out = []
    while m := _INVALID_CHARS_PATTERN.search(string, pos):
        pos = m.start() + 1
        # only unique matches. matches are one char wide
        if m[group] not in out:
            out.append(m[group])
    return out

def username_error_message(value: str, how_many: int = 1) -> str:
    """Return a descriptive error message for an invalid username prefix."""
    if len(value) == 0: # default state - it's fine
        return ""
    total = _total_length(value, how_many)
    if total > MAX_USERNAME_LENGTH:
        return f"Final username will be {total} chars (prefix + number suffix). Max is {MAX_USERNAME_LENGTH}."
    match = find_all_matches(value)
    if match:
        return f"Usernames can only contain lower-case letters, numbers, and underscores."
    return ""
