#!/usr/bin/env python3

from __future__ import annotations
from typing import Dict, List, OrderedDict, Optional, Any, Tuple, Union, Set
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
        thread_id = None
        with open(path / "thread.json") as thread_file:
            thread_object = json.load(thread_file)
            thread_id = thread_object["id"]
            body = Post.load_from_object(
                thread_object,
                thread_id=thread_id,
                page_number=1,
            )

        pages = dict()
        for page_path in (path / "pages").iterdir():
            with open(page_path) as page_file:
                page_number = int(splitext(page_path.name)[0])
                page_object = json.load(page_file)
                page = list(map(
                    lambda post_object:
                    Post.load_from_object(
                        post_object,
                        thread_id=thread_id,
                        page_number=page_number,
                    ),
                    page_object,
                ))
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
        attachment_name = obj.get("fileName", None)
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
            attachment_name=attachment_name,
            adnmb_img=adnmb_img, adnmb_ext=adnmb_ext,

            thread_id=thread_id,
            page_number=page_number,
        )

    def markdown(
            self,
            posts: OrderedDict[int, Post], po_cookies: List[str],
            expand_quote_links: Union[bool, List[int]],
            expanded_post_ids: Set[int],
            after_text: Optional[str] = None,
            until_text: Optional[str] = None) -> str:
        return "\n".join(self.markdown_lines(
            posts=posts, po_cookies=po_cookies,
            after_text=after_text, until_text=until_text,
            expand_quote_links=expand_quote_links,
            expanded_post_ids=expanded_post_ids,
        )) + "\n"

    def markdown_lines(
            self,
            posts: OrderedDict[int, Post], po_cookies: List[str],
            expand_quote_links: Union[bool, List[int]],
            expanded_post_ids: Set[int],
            after_text: Optional[str] = None,
            until_text: Optional[str] = None) -> str:

        lines = []

        expanded_post_ids.add(self.id)

        # 生成头部
        header_items = [f"No.{self.id}"]
        if after_text != None or until_text != None:
            header_items.append("（部分）")
        header_items.extend([" ", f"{self.created_at.now}",
                             " ", f"[P{self.page_number}]",
                             f"(https://adnmb2.com/t/{self.thread_id}?page={self.page_number})"])
        if self.user_id not in po_cookies:
            header_items.extend([" ", f"ID:{self.user_id}"])
        header = "".join(header_items)
        lines.extend([header, ""])

        # 生成图片部分
        if self.attachment_name != None:
            image = f'<img width="40%" src="https://nmbimg.fastmirror.org/image/{self.adnmb_img}{self.adnmb_ext}">'
            lines.extend([image, ""])

        # 生成正文部分
        content = self.content.replace('\r\n', '\n')
        if after_text != None:
            p = content.partition(after_text)
            # 必定能找到，因为 until_text 已经找了一次
            content = p[2]
        if until_text != None:
            p = content.partition(until_text)
            if p[1] == "":
                raise f"bad until_text {until_text}. post id: {self.id}"
            content = p[0] + p[1]

        if after_text != None:
            lines.extend(
                ['<span style="color: gray; font-size: smaller">（…）</span>  ', ""])
        for line in content.split("<br />\n"):
            if line.strip() == "":
                lines.append("")
            else:
                if expand_quote_links == False:
                    # <span> 标签用于防止文本被被当做markdown解析
                    # 两个空格是markdown换行
                    lines.append(f"<span>{line}</span>  ")
                    continue

                lines.extend(Post.__generate_content(
                    posts=posts, po_cookies=po_cookies,
                    line=line, expand_quote_links=expand_quote_links,
                    expanded_post_ids=expanded_post_ids,
                ))

        if until_text != None:
            lines.extend(
                ["", '<span style="color: gray; font-size: smaller">（…）</span>  '])

        return list(map(lambda line: f"> {line}", lines))

    @staticmethod
    def __generate_content(
            posts: OrderedDict[int, Post], po_cookies: List[str],
            line: str, expand_quote_links: Union[bool, List[int]],
            expanded_post_ids: Set[int]) -> List[str]:
        lines = []
        unappened_content = ""
        for (content_before, quote_link_id) in Post.split_line_by_quote_link(line):
            if quote_link_id == None:
                unappened_content += content_before
                continue

            should_expand = expand_quote_links == True or (
                quote_link_id in expand_quote_links)
            should_expand = should_expand and quote_link_id not in expanded_post_ids

            if not should_expand:
                unappened_content += f'{content_before}<font color="#789922">&gt;&gt;No.{quote_link_id}</font>'
            else:
                expanded_post_ids.add(quote_link_id)

                line = unappened_content + content_before
                unappened_content = ""
                if line.strip() != "":
                    lines.append(f"<span>{line}</span>  ")

                if quote_link_id != None:
                    if quote_link_id not in posts:
                        lines.append(f"> {quote_link_id} 【串外引用】")
                    else:
                        lines.extend(
                            posts[quote_link_id].markdown_lines(
                                posts, po_cookies=po_cookies,
                                expand_quote_links=expand_quote_links,
                                expanded_post_ids=expanded_post_ids,
                            ))
        if unappened_content.strip() != "":
            lines.append(f"<span>{unappened_content}</span>  ")
        lines.append("")

        return lines

    @staticmethod
    def split_line_by_quote_link(line: str) -> List[Tuple[str, Optional[int]]]:
        (before_font_open, font_open, after_font_open) = line.partition(
            '<font color="#789922">&gt;&gt;No.')
        if font_open == "":
            return [(line, None)]
        (font_inner, font_close, after_font_close) = after_font_open.partition('</font>')
        if font_close == "":
            raise "what? in split_line_by_quote_link"
        result = [(before_font_open, int(font_inner))]
        if after_font_close != "":
            result.extend(
                Post.split_line_by_quote_link(after_font_close)
            )
        return result
