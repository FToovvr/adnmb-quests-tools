from __future__ import annotations
from typing import Union, Tuple, List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum, auto
from contextlib import contextmanager

import urllib
import unicodedata

from emoji import UNICODE_EMOJI

from ..configloader import DivisionsConfiguration


# TODO: 不如直接用树结构…
@dataclass(frozen=True)
class Topic:
    manager: "TopicManager"
    index: int

    name: str
    github_markdown_preview_heading_id: str
    nest_level: int
    number: int
    is_file_level: bool = False

    class Scope(Enum):
        GLOBAL = auto()
        # FILE = auto()
        PARENT_FILE = auto()

    def topics(self) -> List[Topic]:
        topics = [self]
        skip = None
        for topic in self.manager.topics[self.index+1:]:
            if skip != None and topic.nest_level > skip:
                continue
            else:
                skip = None
            topics.append(topic)
            if topic.is_file_level:
                skip = topic.nest_level
        return topics

    def generate_link_for_toc(self, in_parent_file: bool) -> str:
        (name, _) = self.__heading_name_and_level(in_parent_file=in_parent_file)
        if self.is_file_level and in_parent_file:
            # return f'⎆ <a href="{self.title_name()}.md">{name}</a>'
            return f'⎆ [{name}]({self.title_name()})'
        else:
            # vscode markdown 预览如果使用 markdown 语法则无法跳转
            return f'<a href="#{self.__heading_id()}">{name}</a>'
            # return f'[{name}](#{self.__heading_id()})'

    def generate_heading(self, in_parent_file: bool = True) -> str:
        (name, level) = self.__heading_name_and_level(
            in_parent_file=in_parent_file,
        )

        heading = f'<h{level} id="{self.__heading_id()}">'
        heading += name
        heading += f'</h{level}>'
        return heading

    def __heading_id(self) -> str:
        id = urllib.parse.quote(self.github_markdown_preview_heading_id)
        if self.number != 1:
            id += f"-{self.number-1}"
        return id

    def __heading_name_and_level(self, in_parent_file: bool) -> Tuple(str, int):
        if self.is_file_level and not in_parent_file:
            path = self.path(scope=Topic.Scope.GLOBAL)
            name = "·".join(path.names())
            return (name, 1)

        nest_level = self.__nest_level_in_parent_file()
        return (self.name, nest_level+1)

    def nest_level_in_current_file(self) -> int:
        if self.is_file_level:
            return 0
        return self.__nest_level_in_parent_file()

    def __nest_level_in_parent_file(self) -> int:
        parent_file_topic = self.__get_parent_file_topic()
        return self.nest_level - parent_file_topic.nest_level

    def __get_parent_file_topic(self) -> Topic:
        path = self.path(scope=Topic.Scope.PARENT_FILE)
        return path[0]

    def title_name(self) -> str:
        if self.nest_level == 0:
            return "README"
        path = self.path(scope=Topic.Scope.GLOBAL)
        return "·".join(path.names()[1:])

    def path(self, scope) -> "TopicPath":
        path = TopicPath()
        current_level = None
        for topic in reversed(self.manager.topics[0:self.index+1]):
            if current_level == None or topic.nest_level < current_level:
                current_level = topic.nest_level
                path.insert(0, topic)
            elif topic.nest_level == current_level:
                continue
            if topic.is_file_level and scope != Topic.Scope.GLOBAL:
                if False:  # scope == Topic.Scope.FILE:
                    break
                elif topic != self:
                    break
        return path

    @staticmethod
    def get_github_markdown_preview_heading_id(name: str) -> str:
        result = ""
        for char in name:
            category = unicodedata.category(char)
            if category.startswith("P") or category.startswith("S"):
                continue
            if char in UNICODE_EMOJI:
                continue
            result += char
        return result


class TopicPath(list):
    def names(self) -> List[str]:
        names = []
        for topic in self:
            if topic == None:
                names.append("（空）")
            names.append(topic.name)
        return names


@dataclass
class TopicManager:
    topics: List[Topic] = field(default_factory=list)
    topic_counts: Dict[str, int] = field(default_factory=dict)
    current_nest_level = 0

    def new_topic(self, name: str, is_file_level: bool) -> Topic:
        github_markdown_preview_heading_id = Topic.get_github_markdown_preview_heading_id(
            name)
        number = self.topic_counts.get(
            github_markdown_preview_heading_id, 0) + 1
        self.topic_counts[github_markdown_preview_heading_id] = number
        topic = Topic(
            manager=self, index=len(self.topics),
            name=name, github_markdown_preview_heading_id=github_markdown_preview_heading_id,
            nest_level=self.current_nest_level,
            number=number, is_file_level=is_file_level,
        )
        self.topics.append(topic)
        return topic

    @contextmanager
    def in_next_level(self):
        self.current_nest_level += 1
        yield
        self.current_nest_level -= 1
