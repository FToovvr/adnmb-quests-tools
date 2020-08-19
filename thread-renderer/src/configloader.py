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

    defaults: "DivisionsConfiguration.Defaults"
    toc: Union[None, "DivisionsConfiguration.TOCUsingDetails"]

    division_rules: List["DivisionRule"]

    @dataclass(frozen=True)
    class Defaults:
        expand_quote_links: bool

        @staticmethod
        def load_from_object(obj: Optional[Dict[str, Any], None]) -> DivisionsConfiguration.Defaults:
            obj = obj or dict()
            return DivisionsConfiguration.Defaults(
                expand_quote_links=obj.get("expand-quote-links", True),
            )

    @dataclass(frozen=True)
    class TOCUsingDetails:
        use_margin: bool = False
        use_blockquote: bool = False

    @staticmethod
    def load(file: IO, root_folder_path: str) -> DivisionsConfiguration:
        obj = yaml.safe_load(file)

        title = obj["title"]
        po = obj["po"]
        if not isinstance(po, list):
            po = [po]
        defaults = DivisionsConfiguration.Defaults.load_from_object(
            obj.get("defaults", None))

        toc = obj.get("toc", None)
        if toc == False or toc == None:
            toc = None
        else:
            if toc == True or toc == "details" or toc == "details-margin":
                toc = DivisionsConfiguration.TOCUsingDetails(use_margin=True)
            elif toc == "details-blockquote":
                toc = DivisionsConfiguration.TOCUsingDetails(
                    use_blockquote=True)
            else:
                raise f"unknown toc type: {toc}"

        division_rules = obj.get("divisions", list())

        return DivisionsConfiguration(
            root_folder_path=root_folder_path,

            title=title,
            po_cookies=po,
            defaults=defaults,
            toc=toc,
            division_rules=list(map(lambda d: DivisionRule.load_from_object(d),
                                    division_rules))
        )


@dataclass(frozen=True)
class DivisionRule:

    # TODO: normalization for file names
    title: str
    divisionType: "DivisionType"  # = DivisionType.SECTION
    intro: Optional[str] = None
    match_rule: Union[DivisionRule.MatchUntil,
                      DivisionRule.MatchOnly, None] = None
    post_rules: Optional[Dict[int, DivisionRule.PostRule]] = None
    children: Optional[List[DivisionRule]] = None

    @dataclass(frozen=True)
    class MatchUntil:
        id: int
        text_until: Optional[str] = None
        exclude: Optional[List[int]] = None

    @dataclass(frozen=True)
    class MatchOnly:
        ids: [int]

    @dataclass(frozen=True)
    class PostRule:
        expand_quote_links: Optional[Union[bool, List[int]]]

        @staticmethod
        def load_from_object(obj: Optional[Dict[str, Any]]) -> DivisionRule.PostRule:
            obj = obj or dict()

            expand_quote_links = obj.get("expand-quote-links", None)
            if type(expand_quote_links) is int:
                expand_quote_links = [expand_quote_links]

            return DivisionRule.PostRule(
                expand_quote_links=expand_quote_links,
            )

    @staticmethod
    def load_from_object(obj: Dict[Any]) -> DivisionRule:

        title = obj["title"]

        divisionType = obj.get("division-type", "section")
        if divisionType == "section":
            divisionType = DivisionType.SECTION
        elif divisionType == "file":
            divisionType = DivisionType.FILE
        else:
            raise f"unknown division type: {divisionType}"

        intro = obj.get("intro", None)

        match_rule = None
        if "until" in obj:
            if match_rule != None:
                raise "multiple match rules not allowed"
            until = obj["until"]
            if type(until) is int:
                match_rule = DivisionRule.MatchUntil(id=until)
            else:
                exclude = until.get("exclude", None)
                if type(exclude) is int:
                    exclude = [exclude]
                match_rule = DivisionRule.MatchUntil(
                    id=until["id"],
                    text_until=until.get("text-until", None),
                    exclude=exclude,
                )
        if "only" in obj:
            if match_rule != None:
                raise "multiple match rules not allowed"
            only = obj["only"]
            if type(only) is int:
                match_rule = DivisionRule.MatchOnly(ids=[only])
            else:  # List[int]
                match_rule = DivisionRule.MatchOnly(ids=only)

        post_rules = obj.get("post-rules", None)
        if post_rules != None:
            post_rules = dict((id, DivisionRule.PostRule.load_from_object(
                rule_obj)) for (id, rule_obj) in post_rules.items())

        children = obj.get("children", list())

        return DivisionRule(
            title=title,
            divisionType=divisionType,
            intro=intro,
            match_rule=match_rule,
            post_rules=post_rules,
            children=list(map(lambda c: DivisionRule.load_from_object(c),
                              children))
        )


class DivisionType(Enum):
    FILE = auto()
    SECTION = auto()
