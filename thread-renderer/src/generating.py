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
            posts=posts,
            state=state,
            parent_titles=list(),
            parent_nest_level=0,
            rule=rule,
            is_last_part=(i == len(cfg.divisionRules)-1),
        )


@dataclass
class OutputFile:
    title: str


def generate_markdown_outputs(
        output_folder_path: Path, posts: OrderedDict[int, Post],
        state: "GeneratingState", parent_titles: List[str], parent_nest_level: int,
        rule: DivisionRule, is_last_part: bool) -> Union[str, OutputFile]:
    nest_level = parent_nest_level+1

    print(f'{"#" * nest_level} {rule.title}')

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

    output += f'{"#" * nest_level} {rule.title}\n\n'
    if rule.intro != None:
        output += f"{rule.intro}\n\n"

    children_output = ""
    for (i, child_rule) in enumerate(rule.children):
        child_is_last_part = is_last_part and (i == len(rule.children)-1)
        children_output += generate_markdown_outputs(
            output_folder_path=output_folder_path,
            posts=posts,
            state=state,
            parent_titles=titles,
            parent_nest_level=nest_level,
            rule=child_rule,
            is_last_part=is_last_part,
        ) + "\n"

    self_output = ""
    is_leftover = rule.match_rule == None and is_last_part and nest_level == 1
    print(is_leftover, rule.match_rule, is_last_part, nest_level)
    if isinstance(rule.match_rule, DivisionRule.MatchOnly):
        for id in rule.match_rule.ids:
            self_output += posts[id].markdown(posts=posts) + "\n"
            state.unprocessed_post_ids.pop(id, None)
    elif isinstance(rule.match_rule, DivisionRule.MatchUntil) or is_leftover:
        while len(state.unprocessed_post_ids.keys()) != 0:
            next_id = list(state.unprocessed_post_ids.keys())[0]

            until_text = None
            if not is_leftover:
                if next_id > rule.match_rule.id:
                    break
                elif next_id == rule.match_rule.id:
                    until_text = rule.match_rule.text_until

            post = posts[next_id]
            self_output += post.markdown(
                posts,
                after_text=state.after_text,
                until_text=until_text) + "\n"

            state.after_text = until_text
            if until_text != None:
                break
            else:
                state.unprocessed_post_ids.pop(next_id)

    if is_leftover:
        output += children_output + "\n"
        output += f'{"#" * (nest_level+1)} 尚未整理\n\n'
        output += self_output + "\n"
    else:
        output += self_output + "\n"
        output += children_output + "\n"

    if rule.divisionType == DivisionType.FILE:
        title = "·".join(titles)
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
