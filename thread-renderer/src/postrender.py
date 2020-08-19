#!/usr/bin/env python3

from typing import OrderedDict, List, Set, Union, Optional, Tuple
from dataclasses import dataclass

from .thread import Post


@dataclass(frozen=True)
class PostRender:

    post_pool: OrderedDict[int, Post]
    po_cookies: List[str]

    expanded_post_ids: Set[int]

    @dataclass
    class Options:
        expand_quote_links: Union[bool, List[int]]
        after_text: Optional[str] = None
        until_text: Optional[str] = None

        def clone_and_replace_with(self, **kwargs) -> "PostRender.Option":
            d = dict(self.__dict__)
            d.update(kwargs)
            return PostRender.Options(**d)

    def render(self, post, options: "PostRender.Options") -> str:
        return "\n".join(self.__render_lines(post, options)) + "\n"

    def __render_lines(self, post, options: "PostRender.Options") -> str:

        lines = []

        self.expanded_post_ids.add(post.id)

        # 生成头部
        lines.extend([self.__render_header_line(
            post,
            is_part=options.after_text != None or options.until_text != None,
            is_po=post.user_id in self.po_cookies
        ), ""])

        # 生成图片部分
        if post.attachment_name != None:
            image = f'<img width="40%" src="https://nmbimg.fastmirror.org/image/{post.adnmb_img}{post.adnmb_ext}">'
            lines.extend([image, ""])

        # 生成正文部分
        content = post.content.replace('\r\n', '\n')
        if options.after_text != None:
            p = content.partition(options.after_text)
            # 必定切割成功，因为 until_text 已经找了一次
            content = p[2]
        if options.until_text != None:
            p = content.partition(options.until_text)
            if p[1] == "":
                raise f"bad until_text {options.until_text}. post id: {post.id}"
            content = p[0] + p[1]

        if options.after_text != None:
            lines.extend(
                ['<span style="color: gray; font-size: smaller">（…）</span>  ', ""])

        for line in content.split("<br />\n"):
            if line.strip() == "":
                lines.append("")
            else:
                if options.expand_quote_links == False:
                    # <span> 标签用于防止文本被被当做markdown解析
                    # 两个空格是markdown换行
                    lines.append(f"<span>{line}</span>  ")
                    continue

                lines.extend(self.__render_content_line(line, options))

        if options.until_text != None:
            lines.extend(
                ["", '<span style="color: gray; font-size: smaller">（…）</span>  '])

        return list(map(lambda line: f"> {line}", lines))

    def __render_header_line(self, post: Post, is_part: bool, is_po: bool) -> str:
        header_items = [f"No.{post.id}"]
        if is_part:
            header_items.append("（部分）")
        header_items.extend([" ", f"{post.created_at.now}",
                             " ", f"[P{post.page_number}]",
                             f"(https://adnmb2.com/t/{post.thread_id}?page={post.page_number})"])
        if not is_po:
            header_items.extend([" ", f"ID:{post.user_id}"])
        return "".join(header_items)

    def __render_content_line(self, line: str, options: "PostRender.Options") -> List[str]:
        lines = []
        unappened_content = ""
        for (content_before, quote_link_id) in PostRender.split_line_by_quote_link(line):
            if quote_link_id == None:
                unappened_content += content_before
                continue

            should_expand = options.expand_quote_links == True or (
                quote_link_id in options.expand_quote_links)
            should_expand = should_expand and quote_link_id not in self.expanded_post_ids

            if not should_expand:
                unappened_content += f'{content_before}<font color="#789922">&gt;&gt;No.{quote_link_id}</font>'
            else:
                self.expanded_post_ids.add(quote_link_id)

                line = unappened_content + content_before
                unappened_content = ""
                if line.strip() != "":
                    lines.append(f"<span>{line}</span>  ")

                if quote_link_id != None:
                    if quote_link_id not in self.post_pool:
                        lines.append(f"> {quote_link_id} 【串外引用】")
                    else:
                        lines.extend(self.__render_lines(
                            self.post_pool[quote_link_id],
                            options=options.clone_and_replace_with(
                                after_text=None, until_text=None,
                            ),
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
                PostRender.split_line_by_quote_link(after_font_close)
            )
        return result
