import unicodedata

from emoji import UNICODE_EMOJI


def githubize_heading_name(name: str) -> str:
    result = ""
    for char in name:
        category = unicodedata.category(char)
        if category.startswith("P") or category.startswith("S"):
            continue
        if char in UNICODE_EMOJI:
            continue
        result += char
    return result
