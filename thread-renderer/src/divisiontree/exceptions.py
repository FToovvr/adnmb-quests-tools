from typing import Any
from dataclasses import dataclass


@dataclass
class UntilMatchRuleIDBelowPreviousException(Exception):
    id: int
    previous_id: int


@dataclass
class UnknownMatchRule(Exception):
    match_rule: Any


@dataclass
class OnlyMatchRuleHasChildrenException(Exception):
    pass
