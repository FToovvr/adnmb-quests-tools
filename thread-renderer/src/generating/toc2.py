from typing import Set

from ..configloader import DivisionType, DivisionsConfiguration
from ..divisiontree import DivisionTreeNode


def render_toc(
    node: DivisionTreeNode,
    toc_cfg: DivisionsConfiguration.TOCUsingDetails,
    nest_level: int = 0
) -> str:
    return "[]()" + __render_toc(
        node=node,
        toc_cfg=toc_cfg,
        nest_level=0,
    ) + "\n"


def __render_toc(
    node: DivisionTreeNode,
    toc_cfg: DivisionsConfiguration.TOCUsingDetails,
    nest_level: int = 0
) -> str:
    is_root = nest_level == 0

    if is_root:
        assert(node.type == DivisionType.FILE)
    else:
        assert(node.type in (DivisionType.FILE, DivisionType.SECTION))

    if is_root:
        heading_name = node.top_heading_name
        heading_id = node.top_heading_id
    else:
        heading_name = node.title
        heading_id = node.heading_id

    if node.type == DivisionType.SECTION or is_root:
        link = f'<a href="#{heading_id}">{heading_name}</a>'
    else:  # node.type == DivisionType.FILE
        link = f'⎆ [{heading_name}]({node.file_base_name}.md)'

    if node.children == None:
        return f'<li>{link}</li>'

    if nest_level + 1 in toc_cfg.collapse_at_levels:
        details_open_tag = "<details>"
    else:
        details_open_tag = "<details open>"

    children_output = ""
    for child_node in node.children:
        children_output += __render_toc(
            node=child_node,
            toc_cfg=toc_cfg,
            nest_level=nest_level+1,
        )

    return f'{details_open_tag}<summary>{link}</summary><blockquote>{children_output}</blockquote></details>'
