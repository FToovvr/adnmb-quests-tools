from __future__ import annotations
from typing import List, Optional, Union
from dataclasses import dataclass

import urllib

from ..configloader import DivisionType, MatchRule, PostRules, Collecting

from .utils import githubize_heading_name


@dataclass
class DivisionTreeNode:
    parent: Optional["DivisionTreeNode"]

    title: str
    title_number_in_parent_file: int
    intro: str

    type: Optional[DivisionType]

    posts: Optional[List["PostInNode"]]
    post_rules: PostRules

    # 建好后类型不会是 `Collecting`
    children: Optional[Union[List["DivisionTreeNode"], Collecting]]

    # 用于 GitHub Markdown Preview
    @property
    def githubized_title(self) -> str:
        return githubize_heading_name(self.title)

    @property
    def global_nest_level(self) -> int:
        l = 0
        node = self
        while node.parent != None:
            l += 1
            node = node.parent
        return l

    @property
    def nest_level_in_parent_file(self) -> int:
        l = 0
        node = self
        if node.type == DivisionType.FILE:
            l += 1
            node = node.parent

        while node.type == DivisionType.SECTION:
            l += 1
            node = node.parent
        return l

    @property
    def top_heading_name(self) -> str:
        assert(self.type in (None,  DivisionType.FILE))

        return "·".join(self.title_path)

    @property
    def heading_id(self):
        id = urllib.parse.quote(self.githubized_title)
        if self.title_number_in_parent_file != 1:
            id += f"-{self.title_number_in_parent_file-1}"
        return id

    @property
    def top_heading_id(self):
        return "top-heading"

    @property
    def file_base_name(self) -> str:
        assert(self.type in (None, DivisionType.FILE))

        if self.type == None:
            return "README"

        # 去掉主标题
        return "·".join(list(self.title_path)[1:])

    @property
    def path(self) -> [DivisionTreeNode]:
        nodes = []
        node = self
        while True:
            nodes.append(node)
            if node.type == None:
                break
            else:
                node = node.parent
        return reversed(nodes)

    @property
    def title_path(self) -> [str]:
        return map(lambda node: node.title, self.path)


@dataclass(frozen=True)
class PostInNode:
    """
    Attributes
    ----------

    post_id : int
        贴的串号。


    is_weak : bool
        如果为真，且该贴已出现在其他位置，则不会再进行显示。
    """

    post_id: int

    is_weak: bool

    after_text: Optional[str] = None
    until_text: Optional[str] = None
