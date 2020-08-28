#!/usr/bin/env python3

from __future__ import annotations
from typing import Dict, List, OrderedDict, Optional, Any, Tuple, Union, Set
from dataclasses import dataclass

from pathlib import Path
import json
from os.path import splitext
import logging

from .trace import PageInfo


@dataclass(frozen=True)
class Thread:

    body: "Post"
    pages: List[List["Post"]]

    @staticmethod
    def load_from_dump_folder(path: Path, page_info_list: List[PageInfo]) -> Thread:
        thread_id = None
        with open(path / "thread.json") as thread_file:
            thread_object = json.load(thread_file)
            thread_id = thread_object["id"]
            body = Post.load_from_object(
                thread_object,
                thread_id=thread_id,
                page_number=1,
            )

        pages = []
        for page_info in page_info_list:
            with open(path / "pages" / page_info.filename()) as page_file:
                page_object = json.load(page_file)
                page = list(map(
                    lambda post_object:
                    Post.load_from_object(
                        post_object,
                        thread_id=thread_id,
                        page_number=page_info.number,
                    ),
                    page_object,
                ))
                pages.append(page)

        return Thread(
            body=body,
            pages=pages,
        )

    def flattened_post_dict(self) -> OrderedDict[int, Post]:
        posts = OrderedDict()

        posts[self.body.id] = self.body
        for page in self.pages:
            for post in page:
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
    adnmb_img: Optional[str]
    adnmb_ext: Optional[str]

    thread_id: int
    page_number: int

    @dataclass(frozen=True)
    class AdnmbTime:
        now: str

    @staticmethod
    def load_from_object(
            obj: Dict[Any],
            thread_id: int, page_number: int) -> Post:

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
        adnmb_img = obj["img"]
        if adnmb_img == "":
            adnmb_img = None
        adnmb_ext = obj["ext"]
        if adnmb_ext == "":
            adnmb_ext = None

        return Post(
            id=id, created_at=created_at,
            user_id=user_id, name=name,
            email=email, title=title,
            content=content,
            is_sage=is_sage, is_admin=is_admin,
            adnmb_img=adnmb_img, adnmb_ext=adnmb_ext,

            thread_id=thread_id,
            page_number=page_number,
        )
