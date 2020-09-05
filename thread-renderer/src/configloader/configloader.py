#!/usr/bin/env python3

from __future__ import annotations
from typing import List, IO, Optional, Union, Dict, Any
from enum import Enum, auto
from dataclasses import dataclass, field

from pathlib import Path

import yaml

from .matchrule import MatchRule, MatchUntil, MatchOnly, Collect, Include
from .postrules import PostRules, PostRule
from .utils import flatten_list


@dataclass(frozen=True)
class DivisionsConfiguration:

    root_folder_path: Path

    title: str
    po_cookies: List[str]

    intro: Optional[str]

    defaults: "DivisionsConfiguration.Defaults"
    toc: Union[None, "DivisionsConfiguration.TOCUsingDetails"]

    division_rules: List["DivisionRule"]

    @dataclass(frozen=True)
    class Defaults:
        expand_quote_links: bool
        post_style: "PostStyle"

        class PostStyle(Enum):
            BLOCKQUOTE = auto()
            DETAILS_BLOCKQUOTE = auto()

        @staticmethod
        def load_from_object(obj: Optional[Dict[str, Any], None]) -> DivisionsConfiguration.Defaults:
            obj = obj or dict()

            post_style = obj.get("post-style", None)
            if post_style == None or post_style == "blockquote":
                post_style = DivisionsConfiguration.Defaults.PostStyle.BLOCKQUOTE
            elif post_style == "details-blockquote":
                post_style = DivisionsConfiguration.Defaults.PostStyle.DETAILS_BLOCKQUOTE
            else:
                raise f"unknown post-style value: {post_style}"

            return DivisionsConfiguration.Defaults(
                expand_quote_links=obj.get("expand-quote-links", True),
                post_style=post_style,
            )

    @dataclass(frozen=True)
    class TOCUsingDetails:
        use_margin: bool = False
        use_blockquote: bool = False
        collapse_at_levels: List[int] = field(default_factory=list)

    @staticmethod
    def load(file: IO, root_folder_path: str) -> DivisionsConfiguration:
        obj = yaml.safe_load(file)

        title = obj["title"]
        po = obj["po"]
        if not isinstance(po, list):
            po = [po]
        intro = obj.get("intro", None)
        defaults = DivisionsConfiguration.Defaults.load_from_object(
            obj.get("defaults", None))

        toc = obj.get("toc", "details-margin")
        if toc == False or toc == None:
            toc = None
        else:
            toc_collapse_at_levels = [3]
            if isinstance(toc, str):
                toc_style = toc
            elif toc == True:
                toc_style = "details-blockquote"
            else:
                toc_style = toc.get("style", "details-blockquote")
                toc_collapse = toc.get("collapse", {})
                toc_collapse_at_levels = toc_collapse.get(
                    "at-levels", None) or []
                if type(toc_collapse_at_levels) is int:
                    toc_collapse_at_levels = [toc_collapse_at_levels]

            use_blockquote, use_margin = False, False
            if toc_style in ["details", "details-blockquote"]:
                use_blockquote = True
            elif toc_style == "details-margin":
                use_margin = True
            else:
                raise f"unknown toc type: {toc}"

            toc = DivisionsConfiguration.TOCUsingDetails(
                use_blockquote=use_blockquote,
                use_margin=use_margin,
                collapse_at_levels=toc_collapse_at_levels,
            )

        division_rules = obj.get("divisions", list())

        return DivisionsConfiguration(
            root_folder_path=root_folder_path,

            title=title,
            po_cookies=po,
            intro=intro,
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
    match_rule: MatchRule = None
    post_rules: PostRules = None
    children: Optional[List[DivisionRule]] = None

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
                match_rule = MatchUntil(id=until)
            else:
                excluded = until.get("excluded", None)
                if type(excluded) is int:
                    excluded = [excluded]
                elif isinstance(excluded, list):
                    # 支持将嵌套扁平化
                    # 用于 workaround vscode 的 yaml 插件在格式化过长的数组时，会让每个元素占用一行
                    excluded = flatten_list(excluded)
                match_rule = MatchUntil(
                    id=until["id"],
                    text_until=until.get("text-until", None),
                    excluded=excluded,
                )
        if "only" in obj:
            if match_rule != None:
                raise "multiple match rules not allowed"
            only = obj["only"]
            if type(only) is int:
                match_rule = MatchOnly(ids=[only])
            else:  # List[int]
                match_rule = MatchOnly(ids=only)
        if "collect" in obj:
            if match_rule != None:
                raise "multiple match rules not allowed"
            collect = obj["collect"]
            match_rule = Collect(
                parent_title_matches=collect["parent-title-matches"],
            )
        if "include" in obj:
            if match_rule != None:
                raise "multiple match rules not allowed"
            include = obj["include"]
            match_rule = Include(
                file_path=include["file"],
            )

        post_rules = obj.get("post-rules", None)
        if post_rules != None:
            post_rules = dict((id, PostRule.load_from_object(
                rule_obj)) for (id, rule_obj) in post_rules.items())

        children = obj.get("children", list())

        return DivisionRule(
            title=title,
            divisionType=divisionType,
            intro=intro,
            match_rule=match_rule,
            post_rules=post_rules,
            children=list(map(lambda c: DivisionRule.load_from_object(c),
                              children or []))
        )


class DivisionType(Enum):
    FILE = auto()
    SECTION = auto()
