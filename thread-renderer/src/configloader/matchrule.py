from typing import Union, Optional, List
from dataclasses import dataclass


MatchRule = Union["MatchUntil", "MatchOnly", "Collect", "Include", None]


@dataclass(frozen=True)
class MatchUntil:
    id: int
    text_until: Optional[str] = None
    excluded: Optional[List[int]] = None


@dataclass(frozen=True)
class MatchOnly:
    ids: List[int]


@dataclass(frozen=True)
class Collect:
    parent_title_matches: str


@dataclass(frozen=True)
class Include:
    file_path: str
