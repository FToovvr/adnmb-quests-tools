from dataclasses import dataclass
from typing import OrderedDict, Optional, List, Dict

import logging
import io
from pathlib import Path

from ..configloader import DivisionsConfiguration, DivisionType, PostRule
from ..thread import Post
from ..divisiontree import DivisionTreeNode, PostInNode
from ..divisiontree.utils import githubize_heading_name

from .postrender import PostRender
from .exceptions import UnexpectedDivisionTypeException
from .breadcrumb import render_breadcrumb
from .toc import render_toc


@dataclass
class OutputBuilder:
    breadcrumb: Optional[str] = None
    heading: Optional[str] = None
    intro: Optional[str] = None
    toc: Optional[str] = None
    self_posts: Optional[str] = None
    children: Optional[str] = None

    def build(self) -> str:

        return "\n".join(filter(lambda x: x != None, [
            self.breadcrumb, self.heading,
            self.intro, self.toc,
            self.self_posts, self.children,
        ]))


@dataclass
class OutputsGenerator:

    output_folder_path: Path

    post_pool: OrderedDict[int, Post]

    div_cfg: DivisionsConfiguration

    division_tree: DivisionTreeNode

    post_claims: Dict[int, DivisionTreeNode]

    @staticmethod
    def generate_outputs(
        output_folder_path: Path,
        post_pool: OrderedDict[int, Post],
        div_cfg: DivisionsConfiguration,
        division_tree: DivisionTreeNode,
        post_claims: Dict[int, DivisionTreeNode]
    ):
        generator = OutputsGenerator(
            output_folder_path=output_folder_path,
            post_pool=post_pool,
            div_cfg=div_cfg,
            division_tree=division_tree,
            post_claims=post_claims,
        )
        generator.__generate_node(
            node=generator.division_tree,
            post_renderer=None,
        )

    def __generate_node(
        self,
        node: DivisionTreeNode,
        post_renderer: Optional[PostRender]
    ) -> Optional[str]:
        logging.debug(
            f'{"#"*(node.global_nest_level+1)} {node.title} [{node.type}]',
        )

        if post_renderer == None or node.type in (None, DivisionType.FILE):
            post_renderer = PostRender(
                post_pool=self.post_pool,
                po_cookies=self.div_cfg.po_cookies,
                expanded_post_ids=set(),
            )

        output = OutputBuilder()

        if node.type in (None, DivisionType.FILE):
            output.breadcrumb = render_breadcrumb(node)

        output.heading = render_heading(
            node,
            is_top_level=(node.type in (None, DivisionType.FILE)),
        )

        output.intro = node.intro

        if node.type == DivisionType.FILE:
            output.toc = render_toc(
                node=node,
                toc_cfg=self.div_cfg.toc,
            )

        if len(node.posts or []) > 0:
            output.self_posts = self.__render_posts(
                post_renderer=post_renderer,
                posts_in_node=node.posts,
                post_rules=node.post_rules,
            )

        if len(node.children or []) > 0:
            output.children = self.__generate_children(
                children=node.children,
                post_renderer=post_renderer,
            )

        output = output.build()
        if node.type == DivisionType.SECTION:
            return output

        if node.type == None:
            output_file_name = "README.md"
        else:  # node.type == DivisionType.FILE
            output_file_name = f"{node.file_base_name}.md"
        with open(self.output_folder_path / output_file_name, "w+") as output_file:
            output_file.write(output)

        if node.type == DivisionType.FILE:
            output_for_parent = render_heading(
                node=node,
                is_top_level=False,
            ) + "\n"
            output_for_parent += f"⎆ [{node.title}]({output_file_name})\n"
            return output_for_parent

    def __render_posts(
        self,
        post_renderer: PostRender,
        posts_in_node: List[PostInNode],
        post_rules: Optional[Dict[int, PostRule]],
    ) -> str:
        output = ""

        default_post_rule = PostRule(
            expand_quote_links=self.div_cfg.defaults.expand_quote_links,
        )

        for post_in_node in posts_in_node:
            post_id = post_in_node.post_id

            if post_in_node.is_weak and post_id in self.post_claims:
                continue

            post = self.post_pool[post_id]

            specific_post_rule = (post_rules or {}).get(post_id, None)
            post_rule = PostRule.merge(default_post_rule, specific_post_rule)

            output += post_renderer.render(
                post=post,
                options=PostRender.Options(
                    post_rule=post_rule,
                    style=self.div_cfg.defaults.post_style,
                    after_text=post_in_node.after_text,
                    until_text=post_in_node.until_text,
                )
            )

        return output

    def __generate_children(
            self,
            children: List[DivisionTreeNode],
            post_renderer: PostRender) -> str:

        outputs = map(lambda child: self.__generate_node(
            node=child,
            post_renderer=post_renderer
        ), children)

        return "\n".join(outputs)


def render_heading(node: DivisionTreeNode, is_top_level: bool):

    if is_top_level:
        nest_level = 0
        heading_name = node.top_heading_name
        heading_id = node.top_heading_id

    else:
        nest_level = node.nest_level_in_parent_file
        heading_name = node.title
        heading_id = node.heading_id

    heading = f'<h{nest_level+1} id="{heading_id}">'
    heading += heading_name
    heading += f'</h{nest_level+1}>'
    return heading + "\n"
