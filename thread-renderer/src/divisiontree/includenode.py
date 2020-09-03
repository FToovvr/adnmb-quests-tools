from dataclasses import dataclass

from ..configloader import DivisionType

from .node import Node


@dataclass
class IncludeNode(Node):
    file_path: str

    @property
    def nest_level_in_parent_file(self) -> int:
        l = 1
        node = self.parent

        while node.type == DivisionType.SECTION:
            l += 1
            node = node.parent
        return l
