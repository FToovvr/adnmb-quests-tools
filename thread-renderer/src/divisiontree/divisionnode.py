from __future__ import annotations
from typing import List, Optional, Union
from dataclasses import dataclass

from ..configloader import DivisionType, MatchRule, PostRules, Collect, Include

from .node import Node


@dataclass
class DivisionNode(Node):

    intro: str

    type: Optional[DivisionType]

    posts: Optional[List["PostInNode"]]
    post_rules: PostRules

    # 建好后类型不会是 `Collecting`
    children: Optional[Union[List["DivisionTreeNode"], Collect, Include]]

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
    def top_heading_id(self):
        return "top-heading"

    @property
    def file_base_name(self) -> str:
        assert(self.type in (None, DivisionType.FILE))
        return super(DivisionNode, self).file_base_name


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
