from typing import List, Union

from ..configloader import DivisionsConfiguration

from .topic import Topic


def generate_toc(
        topics: List[Topic],
        toc_cfg: Union[None, DivisionsConfiguration.TOCUsingDetails]
) -> str:
    if isinstance(toc_cfg, DivisionsConfiguration.TOCUsingDetails):
        return generate_toc_using_details(topics, toc_cfg=toc_cfg)
    raise f"unimplemented toc configuration: {toc_cfg}"


def generate_toc_using_details(
        topics: List[Topic],
        toc_cfg: DivisionsConfiguration.TOCUsingDetails
) -> str:

    toc = ""

    for (i, topic) in enumerate(topics):
        current_level = topic.nest_level
        next_level = 1
        if i+1 < len(topics):
            next_level = topics[i+1].nest_level

        DETAILS_STYLE = "margin: 8px 0px 8px 16px; padding: 1px"
        if next_level > current_level:
            first = True
            while next_level > current_level:
                if first:
                    summary = topic.generate_link_for_toc()
                    first = False
                else:
                    summary = '<span style="color: red; font-style: italic">缺失</span>'

                if toc_cfg.use_blockquote:
                    toc += "> " * (current_level - 1)
                details = f'<details'
                if current_level <= 2:  # TODO: 允许自定义深度
                    details += ' open'
                if toc_cfg.use_margin:
                    details += f' style="{DETAILS_STYLE}; background-color: #80808020"'
                details += f'><summary>{summary}</summary>'
                toc += details
                if toc_cfg.use_blockquote:
                    toc += "\n"
                    toc += "> " * (current_level - 1)
                    toc += "\n"
                current_level += 1
        else:
            if toc_cfg.use_blockquote:
                toc += "> " * (current_level - 1)
            li = f'<li'
            if toc_cfg.use_margin:
                li += f' style="{DETAILS_STYLE}"'
            li += f'>{topic.generate_link_for_toc()}</li>'
            toc += li
            if toc_cfg.use_blockquote:
                toc += "\n"
                toc += "> " * (current_level - 1)
                toc += "\n"
            while next_level < current_level:
                current_level -= 1
                if toc_cfg.use_blockquote:
                    toc += "> " * (current_level - 1)
                toc += '</details>'
                if toc_cfg.use_blockquote:
                    toc += "\n"
                    toc += "> " * (current_level - 1)
                    toc += "\n"

    return toc + "\n"
