from typing import Union, Optional, List
from dataclasses import dataclass


MatchRule = Union["MatchUntil", "MatchOnly", "Collecting", None]


@dataclass(frozen=True)
class MatchUntil:
    id: int
    text_until: Optional[str] = None
    excluded: Optional[List[int]] = None


@dataclass(frozen=True)
class MatchOnly:
    ids: List[int]


@dataclass(frozen=True)
class Collecting:
    parent_title_matches: str
