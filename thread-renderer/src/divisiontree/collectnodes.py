from typing import List, Optional

from ..configloader import Collecting

from .divisiontree import DivisionTreeNode


def collect_nodes(
    node: DivisionTreeNode,
    rule: Collecting,
    collecting_nodes: List[DivisionTreeNode]
) -> Optional[List[DivisionTreeNode]]:

    if node.children == None or node in collecting_nodes:
        return None

    collected_nodes = []

    for child in node.children:
        if child.title == rule.parent_title_matches:
            collected_nodes.extend(child.children)
        else:
            child_collect_nodes = collect_nodes(
                node=child,
                rule=rule,
                collecting_nodes=collecting_nodes,
            )
            if child_collect_nodes != None:
                collected_nodes.extend(child_collect_nodes)

    if len(collected_nodes) > 0:
        return collected_nodes
    return None
