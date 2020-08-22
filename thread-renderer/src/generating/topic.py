from __future__ import annotations
from typing import Union, Tuple, List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum, auto
from contextlib import contextmanager

import urllib

from ..configloader import DivisionsConfiguration


# TODO: 不如直接用树结构…
@dataclass(frozen=True)
class Topic:
    manager: "TopicManager"
    index: int

    name: str
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
            return f'⎆ <a href="{self.title_name()}.md">{name}</a>'
        else:
            return f'<a href="#{self.__heading_id()}">{name}</a>'

    def generate_heading(self, in_parent_file: bool = True) -> str:
        (name, level) = self.__heading_name_and_level(
            in_parent_file=in_parent_file,
        )

        heading = f'<h{level} id="{self.__heading_id()}">'
        heading += name
        heading += f'</h{level}>'
        return heading

    def __heading_id(self) -> str:
        id = urllib.parse.quote(self.name)
        if self.number != 1:
            id += f"-{self.number-1}"
        return id

    def __heading_name_and_level(self, in_parent_file: bool) -> Tuple(str, int):
        if self.is_file_level and not in_parent_file:
            path = self.__path(scope=Topic.Scope.GLOBAL)
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
        path = self.__path(scope=Topic.Scope.PARENT_FILE)
        return path[0]

    def title_name(self) -> str:
        path = self.__path(scope=Topic.Scope.GLOBAL)
        return "·".join(path.names()[1:])

    def __path(self, scope) -> "TopicPath":
        path = TopicPath()
        current_level = None
        for topic in reversed(self.manager.topics[0:self.index+1]):
            if current_level == None or topic.nest_level < current_level:
                current_level = topic.nest_level
                path.insert(0, topic)
            if topic.is_file_level and scope != Topic.Scope.GLOBAL:
                if False:  # scope == Topic.Scope.FILE:
                    break
                elif topic != self:
                    break
        return path


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
        number = self.topic_counts.get(name, 0) + 1
        self.topic_counts[name] = number
        topic = Topic(
            manager=self, index=len(self.topics),
            name=name, nest_level=self.current_nest_level,
            number=number, is_file_level=is_file_level,
        )
        self.topics.append(topic)
        return topic

    @contextmanager
    def in_next_level(self):
        self.current_nest_level += 1
        yield
        self.current_nest_level -= 1
