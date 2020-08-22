from typing import List, Union

from ..configloader import DivisionsConfiguration

from .topic import Topic


def generate_toc(
        topics: List[Topic],
        toc_cfg: Union[None, DivisionsConfiguration.TOCUsingDetails],
        uses_relative_levels: bool = True
) -> str:
    if isinstance(toc_cfg, DivisionsConfiguration.TOCUsingDetails):
        return generate_toc_using_details(
            topics, toc_cfg=toc_cfg,
            uses_relative_levels=uses_relative_levels,
        )
    raise f"unimplemented toc configuration: {toc_cfg}"


def generate_toc_using_details(
        topics: List[Topic],
        toc_cfg: DivisionsConfiguration.TOCUsingDetails,
        uses_relative_levels: bool = True
) -> str:

    toc = ""

    root_level = None
    if not uses_relative_levels:
        root_level = 1

    for (i, topic) in enumerate(topics):
        if root_level == None:
            root_level = topic.nest_level
        current_level = topic.nest_level - root_level
        next_level = 0
        if i+1 < len(topics):
            next_level = topics[i+1].nest_level - root_level

        DETAILS_STYLE = "margin: 8px 0px 8px 16px; padding: 1px"
        if next_level > current_level:
            first = True
            while next_level > current_level:
                if first:
                    summary = topic.generate_link_for_toc(
                        in_parent_file=i != 0,
                    )
                    first = False
                else:
                    summary = '<span style="color: red; font-style: italic">缺失</span>'

                details = f'<details'
                if current_level+1 not in toc_cfg.collapse_at_levels:
                    details += ' open'
                if toc_cfg.use_margin:
                    details += f' style="{DETAILS_STYLE}; background-color: #80808020"'
                details += f'><summary>{summary}</summary>'
                toc += details
                if toc_cfg.use_blockquote:
                    toc += "<blockquote>"
                current_level += 1
        else:
            li = f'<li'
            if toc_cfg.use_margin:
                li += f' style="{DETAILS_STYLE}"'
            li += f'>{topic.generate_link_for_toc(in_parent_file=(i!=0))}</li>'
            toc += li
            while next_level < current_level:
                current_level -= 1
                if toc_cfg.use_blockquote:
                    toc += '</blockquote>'
                toc += '</details>'

    return toc + "\n"
