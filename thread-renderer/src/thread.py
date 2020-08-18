#!/usr/bin/env python3

from __future__ import annotations
from typing import Dict, List, OrderedDict, Optional, Any
from dataclasses import dataclass

from pathlib import Path
import json
from os.path import splitext


@dataclass(frozen=True)
class Thread:

    body: "Post"
    pages: Dict[int, List["Post"]]

    @staticmethod
    def load_from_dump_folder(path: Path) -> Thread:
        with open(path / "thread.json") as thread_file:
            thread_object = json.load(thread_file)
            body = Post.load_from_object(thread_object)

        pages = dict()
        for page_path in (path / "pages").iterdir():
            with open(page_path) as page_file:
                page_number = int(splitext(page_path.name)[0])
                page_object = json.load(page_file)
                page = list(map(lambda post_object: Post.load_from_object(post_object),
                                page_object))
                pages[page_number] = page

        return Thread(
            body=body,
            pages=pages,
        )

    def flattened_post_dict(self) -> OrderedDict[int, Post]:
        posts = OrderedDict()

        posts[self.body.id] = self.body
        for page_number in sorted(self.pages.keys()):
            for post in self.pages[page_number]:
                posts[post.id] = post

        return posts


@dataclass(frozen=True)
class Post:
    id: int
    created_at: Post.AdnmbTime
    user_id: str
    name: Optional[str]
    email: Optional[str]
    title: Optional[str]
    content: str
    is_sage: bool
    is_admin: bool
    attachment_name: Optional[str]

    @dataclass(frozen=True)
    class AdnmbTime:
        now: str

    @staticmethod
    def load_from_object(obj: Dict[Any]) -> Post:

        id = int(obj["id"])
        created_at = Post.AdnmbTime(now=obj["now"])
        user_id = obj["userid"]
        name = obj["name"]
        if name == "":
            name = None
        email = obj["email"]
        if email == "":
            email = None
        title = obj["title"]
        if title == "无标题":
            title = None
        content = obj["content"]
        is_sage = int(obj["sage"]) != 0
        is_admin = int(obj["admin"]) != 0
        attachment_name = obj.get("fileName", None)

        return Post(
            id=id, created_at=created_at,
            user_id=user_id, name=name,
            email=email, title=title,
            content=content,
            is_sage=is_sage, is_admin=is_admin,
            attachment_name=attachment_name,
        )

    def markdown(
            self,
            posts: OrderedDict[int, Post],
            after_text: Optional[str] = None,
            until_text: Optional[str] = None) -> str:
        # TODO
        return self.content.split("<br />\n")[0]
