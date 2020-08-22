from .topic import Topic


def generate_navigation(topic: Topic) -> str:
    assert(topic.is_file_level)

    items = []
    path = topic.path(scope=Topic.Scope.GLOBAL)
    for topic_in_path in path[:-1]:
        if topic_in_path.is_file_level:
            link = f'<a href="{topic_in_path.title_name()}.md">'
            link += topic_in_path.name
            link += '</a>'
            items.append(link)
        else:
            items.append(topic_in_path.name)
    last_item = '<span style="font-weight: bold">'
    last_item += topic.name
    last_item += '</span>'
    items.append(last_item)

    output = ' <span style="font-style: bold">・</span> '.join(items)
    return "<nav>当前位于：" + output + "</nav>\n"
