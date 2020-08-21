#!/usr/bin/env python3

from typing import OrderedDict, List, Union, Optional, Dict, Set, NamedTuple
from dataclasses import dataclass, field

from pathlib import Path
import logging
import urllib

from ..configloader import DivisionsConfiguration, DivisionRule, DivisionType
from ..thread import Thread, Post
from .postrender import PostRender

from .topic import Topic, TopicManager
from .toc import generate_toc


@dataclass
class OutputsGenerator:

    post_pool: OrderedDict[int, Post]

    output_folder_path: Path

    intro: Optional[str]

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
        topic_manager: TopicManager = field(default_factory=TopicManager)

    @dataclass
    class InFileState:
        expanded_post_ids: Set[int]  # = field(default_factory=set)
        post_render: PostRender

    @staticmethod
    def generate_outputs(output_folder_path: Path, thread: Thread, configuration: DivisionsConfiguration):
        generator = OutputsGenerator(output_folder_path, thread, configuration)
        generator.generate()

    def __init__(self, output_folder_path: Path, thread: Thread, configuration: DivisionsConfiguration):
        cfg = configuration

        self.post_pool = thread.flattened_post_dict()
        self.output_folder_path = output_folder_path
        self.intro = cfg.intro
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
        topic = self.global_state.topic_manager.new_topic(
            name=self.root_title, is_file_level=True)
        heading_output = topic.generate_heading(in_parent_file=False) + "\n"

        intro_output = ""
        if self.intro != None:
            intro_output = self.intro

        children_output = ""
        with self.global_state.topic_manager.in_next_level():
            for (i, rule) in enumerate(self.root_division_rules):
                if rule.divisionType != DivisionType.FILE:
                    raise f"division type of root division rules must be file. title: {rule.title}"
                children_output += self.__generate(
                    rule=rule,
                    is_last_part=(i == len(self.root_division_rules)-1),
                )

        # toc_output = generate_toc(topic.topics(), self.toc)

        output = heading_output + "\n"
        if intro_output != "":
            output += intro_output + "\n"
        # output += toc_output + "\n"
        output += children_output + "\n"

        output_file_path = self.output_folder_path / "README.md"
        output_file_path.write_text(output)

    def __generate(self,
                   rule: DivisionRule, is_last_part: bool,
                   in_file_state: Optional["OutputsGenerator.InFileState"] = None
                   ) -> Optional[str]:

        topic = self.global_state.topic_manager.new_topic(
            name=rule.title,
            is_file_level=rule.divisionType == DivisionType.FILE,
        )
        logging.debug(
            f"{topic.name}, {topic.nest_level}, {topic.is_file_level}")

        if rule.divisionType == DivisionType.FILE:
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

        if isinstance(rule.match_rule, DivisionRule.MatchUntil) and rule.match_rule.exclude != None:
            self.__remove_excluded_posts_fron_unprocessed_posts(
                excluded_post_ids=rule.match_rule.exclude,
                match_until_id=rule.match_rule.id,
            )

        heading_output = topic.generate_heading(
            in_parent_file=rule.divisionType != DivisionType.FILE,
        ) + "\n"
        intro_output = ""
        if rule.intro != None:
            intro_output = rule.intro

        self_output = ""
        if isinstance(rule.match_rule, DivisionRule.MatchOnly):
            self_output = self.__generate_only(
                only_ids=rule.match_rule.ids,
                post_rules=rule.post_rules,
                in_file_state=in_file_state,
            )
        elif isinstance(rule.match_rule, DivisionRule.MatchUntil):
            self_output = self.__generate_until(
                until=rule.match_rule,
                post_rules=rule.post_rules,
                in_file_state=in_file_state,
            )

        with self.global_state.topic_manager.in_next_level():
            children_output = self.__generate_children(
                rule.children,
                is_last_part=is_last_part,
                in_file_state=in_file_state,
            )

        should_contain_leftover = rule.match_rule == None and is_last_part and nest_level == 1
        if should_contain_leftover:
            leftover_output = self.__generate_leftover(
                post_rules=rule.post_rules,
                in_file_state=in_file_state,
            )

        output = ""
        output += heading_output + "\n"
        if intro_output != "":
            output += intro_output + "\n"
        if self.toc != None and rule.divisionType == DivisionType.FILE:
            toc_output = generate_toc(topics=topic.topics(), toc_cfg=self.toc)
            output += toc_output + "\n"
        if self_output != "":
            output += self_output + "\n"
        output += children_output + "\n"
        if should_contain_leftover:
            output += leftover_output + "\n"

        if rule.divisionType == DivisionType.FILE:
            file_title = topic.title_name()
            output_file_path = self.output_folder_path / (file_title + ".md")
            output_file_path.write_text(output)

            parent_content = topic.generate_heading(
                in_parent_file=True) + "\n\n"
            parent_content += f"⎆ [{file_title}]({file_title}.md)\n"
            return parent_content
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
                            is_last_part: bool,
                            in_file_state: "OutputsGenerator.InFileState"):
        children_output = ""
        for (i, child_rule) in enumerate(rules):
            child_is_last_part = is_last_part and (
                i == len(rules)-1)
            _child_output = self.__generate(
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
                    style=self.defaults.post_style,
                ),
            ) + "\n"

            self.global_state.unprocessed_post_ids.pop(id, None)

        return output

    def __generate_until(self,
                         until: Optional[DivisionRule.MatchUntil],
                         post_rules: Optional[Dict[int, DivisionRule.PostRule]],
                         in_file_state: "OutputsGenerator.InFileState") -> str:
        output = ""
        while len(self.global_state.unprocessed_post_ids.keys()) != 0:
            id = list(self.global_state.unprocessed_post_ids.keys())[0]

            until_text = None
            if until != None:
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
                    style=self.defaults.post_style,
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

    def __generate_leftover(self,
                            post_rules: Optional[Dict[int, DivisionRule.PostRule]],
                            in_file_state: "OutputsGenerator.InFileState") -> str:
        leftover_output = self.__generate_until(
            until=None,
            post_rules=post_rules,
            in_file_state=in_file_state,
        )
        if leftover_output == "":
            return ""

        with self.global_state.topic_manager.in_next_level():
            leftover_topic = self.global_state.topic_manager.new_topic(
                "尚未整理", is_file_level=False)
            output = leftover_topic.generate_heading(
                in_parent_file=True) + "\n\n"
            output += leftover_output + "\n"
            return output
