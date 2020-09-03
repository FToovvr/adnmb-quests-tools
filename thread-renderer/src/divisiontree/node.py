from __future__ import annotations
from typing import Optional
from dataclasses import dataclass

import urllib

from .utils import githubize_heading_name


@dataclass
class Node:
    parent: Optional["Node"]

    title: str
    title_number_in_parent_file: int

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
    def heading_id(self):
        id = urllib.parse.quote(self.githubized_title)
        if self.title_number_in_parent_file != 1:
            id += f"-{self.title_number_in_parent_file-1}"
        return id

    @property
    def file_base_name(self) -> str:
        if self.parent == None:
            return "README"

        # 去掉主标题
        return "·".join(list(self.title_path)[1:])

    @property
    def path(self) -> [Node]:
        nodes = []
        node = self
        while True:
            nodes.append(node)
            if node.parent == None:
                break
            else:
                node = node.parent
        return reversed(nodes)

    @property
    def title_path(self) -> [str]:
        return map(lambda node: node.title, self.path)
