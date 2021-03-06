#!/usr/bin/env python3

from typing import OrderedDict, List, Set, Union, Optional, Tuple
from dataclasses import dataclass

from ..thread import Post
from ..configloader import DivisionsConfiguration, DivisionRule, PostRule


@dataclass(frozen=True)
class PostRenderer:

    post_pool: OrderedDict[int, Post]
    po_cookies: List[str]

    expanded_post_ids: Set[int]

    @dataclass
    class Options:
        post_rule: PostRule
        style: DivisionsConfiguration.Defaults.PostStyle
        after_text: Optional[str] = None
        until_text: Optional[str] = None

        def clone_and_replace_with(self, **kwargs) -> "PostRenderer.Option":
            d = dict(self.__dict__)
            d.update(kwargs)
            return PostRenderer.Options(**d)

    def render(self, post: Post, options: "PostRenderer.Options") -> str:
        return "\n".join(self.__render_lines(post, options, nest_level=0)) + "\n"

    def __render_lines(self, post: Post, options: "PostRenderer.Options", nest_level: int) -> str:

        lines = []

        self.expanded_post_ids.add(post.id)

        lines.extend(['<blockquote>', ""])

        # 生成头部
        header_line = self.__render_header_line(
            post,
            is_part=options.after_text != None or options.until_text != None,
            is_po=post.user_id in self.po_cookies
        )
        if options.style == DivisionsConfiguration.Defaults.PostStyle.DETAILS_BLOCKQUOTE:
            details_open_tag = "<details"
            if nest_level != 1:
                details_open_tag += " open"
            details_open_tag += ">"
            lines.extend(
                [f'{details_open_tag}<summary>{header_line}</summary><hr/>', ""])
        else:
            lines.extend([header_line, ""])

        # 生成图片部分
        if post.adnmb_img != None and options.post_rule.show_attachment != False:
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
                ['<p style="color: gray; font-size: smaller">（…）</p>', ""])

        lines.append("<p>")

        for line in content.split("<br />\n"):
            if line.strip() == "":
                lines.append("</p><p>")
            else:
                if options.post_rule.expand_quote_links == False:
                    # <span> 标签用于防止文本被被当做markdown解析
                    # 两个空格是markdown换行
                    lines.append(line+"<br />")
                    continue

                lines.extend(self.__render_content_line(
                    line, options, nest_level=nest_level))

        lines.append("</p>")

        if options.until_text != None:
            lines.extend(
                ["", '<p style="color: gray; font-size: smaller">（…）</p>'])

        # 生成附加部分
        if nest_level == 0 and isinstance(options.post_rule.appended, list):
            lines.extend(["", '<hr />',
                          '<p style="font-style: italic">附加：</p>'])

            for appended_post_id in options.post_rule.appended:
                lines.extend(self.__render_lines(
                    self.post_pool[appended_post_id],
                    options=options.clone_and_replace_with(
                        post_rule=PostRule.merge(
                            old=options.post_rule,
                            new=PostRule(appended=False)
                        ),
                        after_text=None, until_text=None,
                    ),
                    nest_level=nest_level+0,
                ))

        if options.style == DivisionsConfiguration.Defaults.PostStyle.DETAILS_BLOCKQUOTE:
            lines.append('</details>')
            lines.append('<hr style="visibility: hidden"/>')

        lines.append('</blockquote>')
        return lines

    def __render_header_line(self, post: Post, is_part: bool, is_po: bool) -> str:
        header_items = [f"No.{post.id}"]
        if is_part:
            header_items.append("（部分）")
        header_items.extend([" ", f"{post.created_at.now}",
                             " ", f'<a href="https://adnmb3.com/t/{post.thread_id}?page={post.page_number}">',
                             f"P{post.page_number}", f'</a>'])

        header_items.extend(
            [" ", f'ID:<span style="font-family: monospace">{post.user_id}</span>'])
        if is_po:
            header_items.extend(
                [" ", f'<span style="color: #2d7091; font-size: smaller; font-weight: bold">(PO主)</span>'])

        return "".join(header_items)

    def __render_content_line(self, line: str, options: "PostRenderer.Options", nest_level: int) -> List[str]:
        lines = []
        unappened_content = ""
        for (content_before, quote_link_id) in PostRenderer.split_line_by_quote_link(line):
            if quote_link_id == None:
                unappened_content += content_before
                continue

            if quote_link_id in self.expanded_post_ids:
                # 之前已经出现过，因此不会展开
                # 为了减少冗余，无论配置如何都不会展开
                # TODO: 点击跳转到包含展开内容的地方
                unappened_content += f'{content_before}<font color="#789922">&gt;&gt;No.{quote_link_id}</font>'
            elif quote_link_id not in self.post_pool:
                # 该引用链接位于串外，无力展开
                # TODO: 是不是可以给个链接？
                unappened_content += f'{content_before}<font color="#789922">&gt;&gt;No.{quote_link_id}（串外）</font>'
            elif options.post_rule.expand_quote_links == False or (
                    isinstance(options.post_rule.expand_quote_links, list) and
                    quote_link_id not in options.post_rule.expand_quote_links):
                # 配置中要求不要展开
                # 也许可以考虑在类型是 details-blockquote 时包含内容，但默认折叠？
                unappened_content += f'{content_before}<font color="#789922">&gt;&gt;No.{quote_link_id}</font>'
            else:
                # 允许展开
                self.expanded_post_ids.add(quote_link_id)

                line = unappened_content + content_before
                unappened_content = ""
                if line.strip() != "":
                    lines.append(line+"<br />")

                lines.extend(self.__render_lines(
                    self.post_pool[quote_link_id],
                    options=options.clone_and_replace_with(
                        after_text=None, until_text=None,
                    ),
                    nest_level=nest_level+1,
                ))
        if unappened_content.strip() != "":
            lines.append(unappened_content+"<br />")

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
                PostRenderer.split_line_by_quote_link(after_font_close)
            )
        return result
