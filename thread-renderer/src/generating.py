#!/usr/bin/env python3

from typing import OrderedDict, List, Union, Optional, Dict, Set, NamedTuple
from dataclasses import dataclass, field

from pathlib import Path
import logging
import urllib

from .configloader import DivisionsConfiguration, DivisionRule, DivisionType
from .thread import Thread, Post
from .postrender import PostRender


@dataclass
class OutputsGenerator:

    post_pool: OrderedDict[int, Post]

    output_folder_path: Path

    defaults: DivisionsConfiguration.Defaults

    toc: Union[None, DivisionsConfiguration.TOCUsingDetails]

    po_cookies: List[str]
    root_division_rules: [DivisionRule]
    root_title: str

    state: "OutputsGenerator.GlobalState"

    @dataclass
    class GlobalState:
        unprocessed_post_ids: OrderedDict[int, None]
        after_text: str = None

    @dataclass
    class InFileState:
        expanded_post_ids: Set[int]  # = field(default_factory=set)
        post_render: PostRender

        titles: List["OutputsGenerator.InFileState.Title"] = field(
            default_factory=list)  # (title, nest_level, number)
        title_counts: Dict[str, int] = field(default_factory=dict)

        class Title(NamedTuple):
            title: str
            nest_level: int
            number: int

    @staticmethod
    def generate_outputs(output_folder_path: Path, thread: Thread, configuration: DivisionsConfiguration):
        generator = OutputsGenerator(output_folder_path, thread, configuration)
        generator.generate()

    def __init__(self, output_folder_path: Path, thread: Thread, configuration: DivisionsConfiguration):
        cfg = configuration

        self.post_pool = thread.flattened_post_dict()
        self.output_folder_path = output_folder_path
        self.defaults = cfg.defaults
        self.toc = cfg.toc
        self.po_cookies = cfg.po_cookies
        self.root_division_rules = cfg.division_rules
        self.root_title = cfg.title

        posts_by_po = filter(lambda post: post.user_id in self.po_cookies,
                             self.post_pool.values())
        post_ids_by_po = map(lambda post: post.id, posts_by_po)
        self.global_state = OutputsGenerator.GlobalState(
            unprocessed_post_ids=OrderedDict(
                map(lambda id: (id, None), post_ids_by_po))
        )

    def generate(self):
        for (i, rule) in enumerate(self.root_division_rules):
            if rule.divisionType != DivisionType.FILE:
                raise f"division type of root division rules must be file. title: {rule.title}"
            self.__generate(
                parent_titles=[self.root_title],
                parent_nest_level=0,
                rule=rule,
                is_last_part=(i == len(self.root_division_rules)-1),
            )

    def __generate(self,
                   parent_titles: List[str], parent_nest_level: int,
                   rule: DivisionRule, is_last_part: bool,
                   in_file_state: Optional["OutputsGenerator.InFileState"] = None
                   ) -> Optional[str]:
        if rule.divisionType == DivisionType.FILE:
            nest_level_in_parent = parent_nest_level+1
            parent_in_file_state = in_file_state

            nest_level = 1
            expanded_post_ids = set()
            in_file_state = OutputsGenerator.InFileState(
                expanded_post_ids=expanded_post_ids,
                post_render=PostRender(
                    post_pool=self.post_pool,
                    po_cookies=self.po_cookies,
                    expanded_post_ids=expanded_post_ids,
                ),
            )
        elif in_file_state == None:
            raise "what? in __generate"
        else:
            nest_level = parent_nest_level+1

        if isinstance(rule.match_rule, DivisionRule.MatchUntil) and rule.match_rule.exclude != None:
            self.__remove_excluded_posts_fron_unprocessed_posts(
                excluded_post_ids=rule.match_rule.exclude,
                match_until_id=rule.match_rule.id,
            )

        output = ""

        titles = list(parent_titles)
        titles.append(rule.title)
        if rule.divisionType == DivisionType.FILE:
            shown_title = "·".join(titles)
        else:
            shown_title = rule.title
        title_number = in_file_state.title_counts.get(shown_title, 0) + 1
        in_file_state.title_counts[shown_title] = title_number
        in_file_state.titles.append(
            OutputsGenerator.InFileState.Title(shown_title, nest_level, title_number))
        if rule.divisionType == DivisionType.FILE and parent_in_file_state != None:
            title_number_in_parent = parent_in_file_state.title_counts.get(
                rule.title, 0) + 1
            parent_in_file_state.title_counts[rule.title] = title_number_in_parent
            parent_in_file_state.titles.append(
                OutputsGenerator.InFileState.Title(rule.title, nest_level_in_parent, title_number_in_parent))

        print(f'{"#" * nest_level} {shown_title}')
        if rule.divisionType != DivisionType.FILE:
            # FILE 输出标题延后
            output += OutputsGenerator.__generate_heading(
                shown_title, nest_level, title_number) + "\n"
            # FILE 输出 intro 延后
            if rule.intro != None:
                output += f"{rule.intro}\n\n"

        children_output = self.__generate_children(
            rule.children,
            is_last_part=is_last_part,
            titles=titles,
            nest_level=nest_level,
            in_file_state=in_file_state,
        )

        self_output = ""
        is_leftover = rule.match_rule == None and is_last_part and nest_level == 1
        if isinstance(rule.match_rule, DivisionRule.MatchOnly):
            self_output += self.__generate_only(
                only_ids=rule.match_rule.ids,
                post_rules=rule.post_rules,
                in_file_state=in_file_state,
            )
        elif isinstance(rule.match_rule, DivisionRule.MatchUntil) or is_leftover:
            self_output += self.__generate_until(
                until=rule.match_rule,
                post_rules=rule.post_rules,
                is_leftover=is_leftover,
                in_file_state=in_file_state,
            )

        if is_leftover:
            output += children_output + "\n"
            if self_output != "":
                output += OutputsGenerator.__generate_heading(
                    "尚未整理", nest_level+1, title_number) + "\n"
                output += self_output + "\n"
        else:
            output += self_output + "\n"
            output += children_output + "\n"

        if rule.divisionType == DivisionType.FILE:
            _output = output
            output = OutputsGenerator.__generate_heading(
                shown_title, 1, title_number) + "\n"
            if rule.intro != None:
                output += f"{rule.intro}\n\n"
            if self.toc != None:
                toc = OutputsGenerator.__generate_toc(
                    in_file_state.titles, toc_cfg=self.toc)
                output += toc + "\n"
            output += _output + "\n"
            title = "·".join(titles[1:])
            output_file_path = self.output_folder_path / (title + ".md")
            output_file_path.write_text(output)

            if parent_in_file_state != None:
                parent_content = OutputsGenerator.__generate_heading(
                    rule.title, nest_level_in_parent+1, title_number_in_parent) + "\n"
                parent_content += f"见[{title}]({title}.md)\n"
                return parent_content
            return None
        elif rule.divisionType == DivisionType.SECTION:
            return output
        else:
            raise f"unknown division type: {rule.divisionType}. title: {rule.title}"

    def __remove_excluded_posts_fron_unprocessed_posts(self, excluded_post_ids: List[int], match_until_id: int):
        for excluded_id in excluded_post_ids:
            if excluded_id > match_until_id:
                logging.warning(
                    f'excluded id {excluded_id} greater than upper bound {match_until_id}')
            if excluded_id not in self.global_state.unprocessed_post_ids:
                logging.warning(
                    f'unnecessary excluded id {excluded_id}')
            else:
                self.global_state.unprocessed_post_ids.pop(excluded_id)

    def __generate_children(self,
                            rules: [DivisionRule],
                            is_last_part: bool, titles: str, nest_level: int,
                            in_file_state: "OutputsGenerator.InFileState"):
        children_output = ""
        for (i, child_rule) in enumerate(rules):
            child_is_last_part = is_last_part and (
                i == len(rules)-1)
            _child_output = self.__generate(
                parent_titles=titles,
                parent_nest_level=nest_level,
                rule=child_rule,
                is_last_part=child_is_last_part,
                in_file_state=in_file_state,
            )

            if isinstance(_child_output, str):
                children_output += _child_output + "\n"
            else:
                raise "what? in generate_markdown_outputs"
        return children_output

    def __generate_only(self,
                        only_ids: List[int],
                        post_rules: Optional[Dict[int, DivisionRule.PostRule]],
                        in_file_state: "OutputsGenerator.InFileState"):
        output = ""
        for id in only_ids:
            expand_quote_links = None
            if post_rules != None and id in post_rules:
                expand_quote_links = post_rules[id].expand_quote_links
            expand_quote_links = expand_quote_links or self.defaults.expand_quote_links

            output += in_file_state.post_render.render(
                self.post_pool[id],
                options=PostRender.Options(
                    expand_quote_links=expand_quote_links,
                ),
            ) + "\n"

            self.global_state.unprocessed_post_ids.pop(id, None)

        return output

    def __generate_until(self,
                         until: DivisionRule.MatchUntil,
                         post_rules: Optional[Dict[int, DivisionRule.PostRule]],
                         is_leftover: bool, in_file_state: "OutputsGenerator.InFileState"):
        output = ""
        while len(self.global_state.unprocessed_post_ids.keys()) != 0:
            id = list(self.global_state.unprocessed_post_ids.keys())[0]

            until_text = None
            if not is_leftover:
                if id > until.id:
                    break
                elif id == until.id:
                    until_text = until.text_until

            expand_quote_links = None
            if post_rules != None and id in post_rules:
                expand_quote_links = post_rules[id].expand_quote_links
            expand_quote_links = expand_quote_links or self.defaults.expand_quote_links

            post = self.post_pool[id]
            output += in_file_state.post_render.render(
                post,
                options=PostRender.Options(
                    expand_quote_links=expand_quote_links,
                    after_text=self.global_state.after_text,
                    until_text=until_text,
                ),
            ) + "\n"

            self.global_state.after_text = until_text
            if until_text != None:
                break
            else:
                self.global_state.unprocessed_post_ids.pop(id)
        return output

    @staticmethod
    def __generate_heading(title: str, level: int, number: int):
        return f'<h{level} id="{OutputsGenerator.__get_heading_id(title, number)}">{title}</h{level}>\n'

    @staticmethod
    def __get_heading_id(title: str, number: int):
        id = urllib.parse.quote(title)
        if number != 1:
            id += f"-{number-1}"
        return id

    @staticmethod
    def __generate_toc(
        titles: "OutputsGenerator.InFileState.Title",
            toc_cfg: Union[None, DivisionsConfiguration.TOCUsingDetails]) -> str:
        if isinstance(toc_cfg, DivisionsConfiguration.TOCUsingDetails):
            return OutputsGenerator.__generate_toc_using_details(
                titles, toc_cfg=toc_cfg)
        raise f"unimplemented toc configuration: {toc_cfg}"

    @staticmethod
    def __generate_toc_using_details(
            titles: "OutputsGenerator.InFileState.Title",
            toc_cfg: DivisionsConfiguration.TOCUsingDetails) -> str:

        toc = ""

        for (i, title_tuple) in enumerate(titles):
            current_level = title_tuple.nest_level
            next_level = 1
            if i+1 < len(titles):
                next_level = titles[i+1].nest_level

            title = title_tuple.title
            title_href = "#" + \
                OutputsGenerator.__get_heading_id(title, title_tuple.number)
            DETAILS_STYLE = "margin: 8px 0px 8px 16px; padding: 1px"
            if next_level > current_level:
                first = True
                while next_level > current_level:
                    if first:
                        summary = title
                        first = False
                    else:
                        summary = '<span style="color: red; font-style: italic">缺失</span>'
                        title_href = '#'

                    if toc_cfg.use_blockquote:
                        toc += "> " * (current_level - 1)
                    details = f'<details'
                    if current_level <= 2:  # TODO: 允许自定义深度
                        details += ' open'
                    if toc_cfg.use_margin:
                        details += f' style="{DETAILS_STYLE}; background-color: #80808020"'
                    details += f'><summary><a href="{title_href}">{summary}</a></summary>'
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
                li += f'><a href="{title_href}">{title}</a></li>'
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
