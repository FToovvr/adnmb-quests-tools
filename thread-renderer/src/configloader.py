#!/usr/bin/env python3

from __future__ import annotations
from typing import List, IO, Optional, Union, Dict, Any
from enum import Enum, auto
from dataclasses import dataclass

from pathlib import Path

import yaml


@dataclass(frozen=True)
class DivisionsConfiguration:

    root_folder_path: Path

    title: str
    po_cookies: List[str]
    divisionRules: List["Division"]

    @staticmethod
    def load(file: IO, root_folder_path: str) -> DivisionsConfiguration:
        obj = yaml.safe_load(file)

        title = obj["title"]
        po = obj["po"]
        if not isinstance(po, list):
            po = [po]
        divisionRules = obj.get("divisions", list())

        return DivisionsConfiguration(
            root_folder_path=root_folder_path,

            title=title,
            po_cookies=po,
            divisionRules=list(map(lambda d: DivisionRule.load_from_object(d),
                                   divisionRules))
        )


@dataclass(frozen=True)
class DivisionRule:

    # TODO: normalization for file names
    title: str
    divisionType: "DivisionType"  # = DivisionType.SECTION
    intro: Optional[str] = None
    match_rule: Union[DivisionRule.MatchUntil,
                      DivisionRule.MatchOnly, None] = None
    children: Optional[List[DivisionRule]] = None

    @dataclass(frozen=True)
    class MatchUntil:
        id: int
        text_until: Optional[str] = None

    @dataclass(frozen=True)
    class MatchOnly:
        ids: [int]

    @staticmethod
    def load_from_object(obj: Dict[Any]) -> DivisionRule:

        title = obj["title"]

        divisionType = obj.get("division-type", "section")
        if divisionType == "section":
            divisionType = DivisionType.SECTION
        elif divisionType == "file":
            divisionType = DivisionType.FILE
        else:
            raise "unknown division type: {}".format(divisionType)

        intro = obj.get("intro", None)

        match_rule = None
        if "until" in obj:
            if match_rule != None:
                raise "multiple match rules not allowed"
            until = obj["until"]
            if isinstance(until, int):
                match_rule = DivisionRule.MatchUntil(id=until)
            else:
                match_rule = DivisionRule.MatchUntil(
                    id=until["id"],
                    text_until=until.get("text-until", None),
                )
        if "only" in obj:
            if match_rule != None:
                raise "multiple match rules not allowed"
            only = obj["only"]
            if isinstance(only, int):
                match_rule = DivisionRule.MatchOnly(ids=[only])
            else:  # List[int]
                match_rule = DivisionRule.MatchOnly(ids=only)

        children = obj.get("children", list())

        return DivisionRule(
            title=title,
            divisionType=divisionType,
            intro=intro,
            match_rule=match_rule,
            children=list(map(lambda c: DivisionRule.load_from_object(c),
                              children))
        )


class DivisionType(Enum):
    FILE = auto()
    SECTION = auto()
