from typing import NamedTuple, Optional, List, Dict
from dataclasses import dataclass, field

import urllib


class Topic(NamedTuple):
    name: str
    nest_level: int
    number: int
    external_name: Optional[str] = None

    def generate_link_for_toc(self):
        if self.external_name != None:
            return f'⎆ <a href="{self.external_name}.md">{self.name}</a>'
        else:
            return f'<a href="#{self.get_heading_id()}">{self.name}</a>'

    def generate_heading(self):
        heading = f'<h{self.nest_level} id="{self.get_heading_id()}">'
        heading += self.name
        heading += f'</h{self.nest_level}>'
        return heading

    def get_heading_id(self):
        id = urllib.parse.quote(self.name)
        if self.number != 1:
            id += f"-{self.number-1}"
        return id


@dataclass
class TopicManager:
    topics: List[Topic] = field(default_factory=list)
    topic_counts: Dict[str, int] = field(default_factory=dict)

    def new_topic(self,
                  name: str, nest_level: int,
                  external_name: Optional[str] = None
                  ) -> Topic:
        number = self.topic_counts.get(name, 0) + 1
        self.topic_counts[name] = number
        topic = Topic(
            name, nest_level=nest_level,
            number=number, external_name=external_name,
        )
        self.topics.append(topic)
        return topic
