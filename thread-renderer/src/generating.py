#!/usr/bin/env python3

from typing import OrderedDict, List, Union, Optional, Dict
from dataclasses import dataclass

from pathlib import Path
import logging

from .configloader import DivisionsConfiguration, DivisionRule, DivisionType
from .thread import Thread, Post


@dataclass
class OutputsGenerator:

    posts: OrderedDict[int, Post]

    output_folder_path: Path

    defaults: DivisionsConfiguration.Defaults

    po_cookies: List[str]
    root_division_rules: [DivisionRule]
    root_title: str

    state: "OutputsGenerator.State"

    @dataclass(frozen=True)
    class OutputFile:
        title: str

    @dataclass
    class State:
        unprocessed_post_ids: OrderedDict[int, None]
        after_text: str = None

    @staticmethod
    def generate_outputs(output_folder_path: Path, thread: Thread, configuration: DivisionsConfiguration):
        generator = OutputsGenerator(output_folder_path, thread, configuration)
        generator.generate()

    def __init__(self, output_folder_path: Path, thread: Thread, configuration: DivisionsConfiguration):
        cfg = configuration

        self.posts = thread.flattened_post_dict()
        self.output_folder_path = output_folder_path
        self.defaults = cfg.defaults
        self.po_cookies = cfg.po_cookies
        self.root_division_rules = cfg.division_rules
        self.root_title = cfg.title

        posts_by_po = filter(lambda post: post.user_id in self.po_cookies,
                             self.posts.values())
        post_ids_by_po = map(lambda post: post.id, posts_by_po)
        self.state = OutputsGenerator.State(
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
                   rule: DivisionRule, is_last_part: bool) -> Union[str, "OutputsGenerator.OutputFile"]:
        if rule.divisionType == DivisionType.FILE:
            nest_level = 1
        else:
            nest_level = parent_nest_level+1

        titles = list(parent_titles)
        titles.append(rule.title)

        if isinstance(rule.match_rule, DivisionRule.MatchUntil) and rule.match_rule.exclude != None:
            self.__remove_excluded_posts_fron_unprocessed_posts(
                excluded_post_ids=rule.match_rule.exclude,
                match_until_id=rule.match_rule.id,
            )

        output = ""

        if rule.divisionType == DivisionType.FILE:
            shown_title = "·".join(titles)
        else:
            shown_title = rule.title

        print(f'{"#" * nest_level} {shown_title}')
        output += f'{"#" * nest_level} {shown_title}\n\n'

        if rule.intro != None:
            output += f"{rule.intro}\n\n"

        children_output = self.__generate_children(
            rule.children,
            is_last_part=is_last_part,
            titles=titles,
            nest_level=nest_level,
        )

        self_output = ""
        is_leftover = rule.match_rule == None and is_last_part and nest_level == 1
        if isinstance(rule.match_rule, DivisionRule.MatchOnly):
            self_output += self.__generate_only(
                only_ids=rule.match_rule.ids,
                post_rules=rule.post_rules,
            )
        elif isinstance(rule.match_rule, DivisionRule.MatchUntil) or is_leftover:
            self_output += self.__generate_until(
                until=rule.match_rule,
                post_rules=rule.post_rules,
                is_leftover=is_leftover
            )

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
            output_file_path = self.output_folder_path / (title + ".md")
            output_file_path.write_text(output)
            return OutputsGenerator.OutputFile(title)
        elif rule.divisionType == DivisionType.SECTION:
            return output
        else:
            raise f"unknown division type: {rule.divisionType}. title: {rule.title}"

    def __remove_excluded_posts_fron_unprocessed_posts(self, excluded_post_ids: List[int], match_until_id: int):
        for excluded_id in excluded_post_ids:
            if excluded_id > match_until_id:
                logging.warning(
                    f'excluded id {excluded_id} greater than upper bound {match_until_id}')
            if excluded_id not in self.state.unprocessed_post_ids:
                logging.warning(
                    f'unnecessary excluded id {excluded_id}')
            else:
                self.state.unprocessed_post_ids.pop(excluded_id)

    def __generate_children(self, rules: [DivisionRule], is_last_part: bool, titles: str, nest_level: int):
        children_output = ""
        for (i, child_rule) in enumerate(rules):
            child_is_last_part = is_last_part and (
                i == len(rules)-1)
            _child_output = self.__generate(
                parent_titles=titles,
                parent_nest_level=nest_level,
                rule=child_rule,
                is_last_part=child_is_last_part,
            )

            if isinstance(_child_output, str):
                children_output += _child_output + "\n"
            elif isinstance(_child_output, OutputsGenerator.OutputFile):
                children_output += f'{"#"*(nest_level+1)} {child_rule.title}\n\n'
                children_output += f"见[{_child_output.title}]({_child_output.title}.md)\n"
            else:
                raise "what? in generate_markdown_outputs"
        return children_output

    def __generate_only(self, only_ids: List[int], post_rules: Optional[Dict[int, DivisionRule.PostRule]]):
        output = ""
        for id in only_ids:
            expand_quote_links = None
            if post_rules != None and id in post_rules:
                expand_quote_links = post_rules[id].expand_quote_links
            expand_quote_links = expand_quote_links or self.defaults.expand_quote_links

            output += self.posts[id].markdown(
                posts=self.posts,
                po_cookies=self.po_cookies,
                expand_quote_links=expand_quote_links,
            ) + "\n"

            self.state.unprocessed_post_ids.pop(id, None)

        return output

    def __generate_until(self,
                         until: DivisionRule.MatchUntil,
                         post_rules: Optional[Dict[int, DivisionRule.PostRule]],
                         is_leftover: bool):
        output = ""
        while len(self.state.unprocessed_post_ids.keys()) != 0:
            id = list(self.state.unprocessed_post_ids.keys())[0]

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

            post = self.posts[id]
            output += post.markdown(
                self.posts,
                po_cookies=self.po_cookies,
                after_text=self.state.after_text,
                until_text=until_text,
                expand_quote_links=expand_quote_links,
            ) + "\n"

            self.state.after_text = until_text
            if until_text != None:
                break
            else:
                self.state.unprocessed_post_ids.pop(id)
        return output
