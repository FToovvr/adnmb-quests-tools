#!/usr/bin/env python3

from typing import OrderedDict, List, Union
from dataclasses import dataclass

from pathlib import Path
import logging

from .configloader import DivisionsConfiguration, DivisionRule, DivisionType
from .thread import Thread, Post


def generate_outputs(
        output_folder_path: Path,
        thread: Thread,
        configuration: DivisionsConfiguration):
    cfg = configuration

    posts: OrderedDict[Post] = thread.flattened_post_dict()

    posts_by_po = filter(lambda post: post.user_id in cfg.po_cookies,
                         posts.values())
    post_ids_by_po = map(lambda post: post.id, posts_by_po)

    state = GeneratingState(
        unprocessed_post_ids=OrderedDict(
            map(lambda id: (id, None), post_ids_by_po))
    )

    for (i, rule) in enumerate(cfg.divisionRules):
        if rule.divisionType != DivisionType.FILE:
            raise f"division type of root division rules must be file. title: {rule.title}"
        generate_markdown_outputs(
            output_folder_path=output_folder_path,
            defaults=cfg.defaults,
            po_cookies=configuration.po_cookies,
            posts=posts,
            state=state,
            parent_titles=[cfg.title],
            parent_nest_level=0,
            rule=rule,
            is_last_part=(i == len(cfg.divisionRules)-1),
        )


@dataclass(frozen=True)
class OutputFile:
    title: str


def generate_markdown_outputs(
        output_folder_path: Path, defaults: DivisionsConfiguration.Defaults,
        po_cookies: List[str], posts: OrderedDict[int, Post],
        state: "GeneratingState", parent_titles: List[str], parent_nest_level: int,
        rule: DivisionRule, is_last_part: bool) -> Union[str, OutputFile]:
    if rule.divisionType == DivisionType.FILE:
        nest_level = 1
    else:
        nest_level = parent_nest_level+1

    titles = list(parent_titles)
    titles.append(rule.title)

    if isinstance(rule.match_rule, DivisionRule.MatchUntil) and rule.match_rule.exclude != None:
        for excluded_id in rule.match_rule.exclude:
            if excluded_id > rule.match_rule.id:
                logging.warning(
                    f'excluded id {excluded_id} greater than upper bound {rule.match_rule.id}. rule-path: {".".join(titles)}')
            if excluded_id not in state.unprocessed_post_ids:
                logging.warning(
                    f'unnecessary excluded id {excluded_id}. rule-path: {".".join(titles)}')
            else:
                state.unprocessed_post_ids.pop(excluded_id)

    output = ""

    if rule.divisionType == DivisionType.FILE:
        shown_title = "·".join(titles)
    else:
        shown_title = rule.title

    print(f'{"#" * nest_level} {shown_title}')
    output += f'{"#" * nest_level} {shown_title}\n\n'

    if rule.intro != None:
        output += f"{rule.intro}\n\n"

    children_output = ""
    for (i, child_rule) in enumerate(rule.children):
        child_is_last_part = is_last_part and (i == len(rule.children)-1)
        _children_output = generate_markdown_outputs(
            output_folder_path=output_folder_path,
            defaults=defaults,

            po_cookies=po_cookies,
            posts=posts,
            state=state,
            parent_titles=titles,
            parent_nest_level=nest_level,
            rule=child_rule,
            is_last_part=child_is_last_part,
        )

        if isinstance(_children_output, str):
            children_output += _children_output + "\n"
        elif isinstance(_children_output, OutputFile):
            child_titles = list(titles)
            child_titles.append(child_rule.title)
            child_title = "·".join(child_titles)
            children_output += f'{"#"*(nest_level+1)} {child_rule.title}\n\n'
            children_output += f"见[{child_title}]({child_title}.md)\n"
        else:
            raise "what? in generate_markdown_outputs"

    self_output = ""
    is_leftover = rule.match_rule == None and is_last_part and nest_level == 1
    if isinstance(rule.match_rule, DivisionRule.MatchOnly):
        for id in rule.match_rule.ids:
            expand_quote_links = None
            if rule.post_rules != None:
                if id in rule.post_rules:
                    expand_quote_links = rule.post_rules[id].expand_quote_links
            expand_quote_links = expand_quote_links or defaults.expand_quote_links

            self_output += posts[id].markdown(
                posts=posts,
                po_cookies=po_cookies,
                expand_quote_links=expand_quote_links,
            ) + "\n"

            state.unprocessed_post_ids.pop(id, None)
    elif isinstance(rule.match_rule, DivisionRule.MatchUntil) or is_leftover:
        while len(state.unprocessed_post_ids.keys()) != 0:
            id = list(state.unprocessed_post_ids.keys())[0]

            until_text = None
            if not is_leftover:
                if id > rule.match_rule.id:
                    break
                elif id == rule.match_rule.id:
                    until_text = rule.match_rule.text_until

            expand_quote_links = None
            if rule.post_rules != None:
                if id in rule.post_rules:
                    expand_quote_links = rule.post_rules[id].expand_quote_links
            expand_quote_links = expand_quote_links or defaults.expand_quote_links

            post = posts[id]
            self_output += post.markdown(
                posts,
                po_cookies=po_cookies,
                after_text=state.after_text,
                until_text=until_text,
                expand_quote_links=expand_quote_links,
            ) + "\n"

            state.after_text = until_text
            if until_text != None:
                break
            else:
                state.unprocessed_post_ids.pop(id)

    if is_leftover:
        output += children_output + "\n"
        if self_output != "":
            output += f'{"#" * (nest_level+1)} 尚未整理\n\n'
            output += self_output + "\n"
    else:
        output += self_output + "\n"
        output += children_output + "\n"

    if rule.divisionType == DivisionType.FILE:
        title = "·".join(titles[1:])
        output_file_path = output_folder_path / (title + ".md")
        output_file_path.write_text(output)
        return OutputFile(title)
    elif rule.divisionType == DivisionType.SECTION:
        return output
    else:
        raise f"unknown division type: {rule.divisionType}. title: {rule.title}"


@dataclass
class GeneratingState:
    unprocessed_post_ids: OrderedDict[int, None]
    after_text: str = None
