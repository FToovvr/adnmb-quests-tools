from ..configloader import DivisionType
from ..divisiontree import DivisionTreeNode


def render_breadcrumb(node: DivisionTreeNode) -> str:
    assert(node.type in (None, DivisionType.FILE))

    items = []
    for node_in_path in list(node.path)[:-1]:
        if node_in_path.type == DivisionType.SECTION:
            # TODO: 考虑 `node_in_path.title_number_in_parent_file`?
            items.append(node_in_path.title)
        else:
            link = f'[{node_in_path.title}]({node_in_path.file_base_name}.md)'
            items.append(link)
    last_item = '<span style="font-weight: bold">'
    last_item += node.title
    last_item += '</span>'
    items.append(last_item)

    output = ' <span style="font-style: bold">・</span> '.join(items)
    return "[]()<nav>当前位于：" + output + "</nav>\n"
