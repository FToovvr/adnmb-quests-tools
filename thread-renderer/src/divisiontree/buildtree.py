from dataclasses import dataclass
from typing import OrderedDict, List, Dict, Optional, Tuple

from ..configloader import DivisionsConfiguration, DivisionRule, DivisionType, MatchUntil, MatchOnly
from ..thread import Thread, Post

from .divisiontree import DivisionTreeNode, PostInNode
from .exceptions import UnknownMatchRule, OnlyMatchRuleHasChildrenException
from .utils import githubize_heading_name


@dataclass
class TreeBuilder:
    post_pool: OrderedDict[int, Post]
    post_ids: List[int]
    post_i: int
    post_claims: Dict[int, DivisionTreeNode]

    div_cfg: DivisionsConfiguration

    remain_post: Optional[Tuple[int, str]] = None

    has_been_built = False

    def __init__(self, post_pool: OrderedDict[int, Post], div_cfg: DivisionsConfiguration):
        self.post_pool = post_pool
        self.post_ids = list(self.post_pool.keys())
        self.post_i = 0
        self.post_claims = {}

        self.div_cfg = div_cfg

    @staticmethod
    def build_tree(post_pool: OrderedDict[int, Post], div_cfg: DivisionsConfiguration) -> "DivisionTreeNode":
        builder = TreeBuilder(
            post_pool=post_pool,
            div_cfg=div_cfg,
        )
        return (builder.__build_root(), builder.post_claims)

    def __build_root(self) -> DivisionTreeNode:
        assert(not self.has_been_built)
        self.has_been_built = True

        root = DivisionTreeNode(
            parent=None,
            title=self.div_cfg.title,
            title_number_in_parent_file=1,
            intro=self.div_cfg.intro,
            type=None,
            posts=[],
            post_rules=None,
            children=None,
        )
        root.children = list(map(lambda rule: self.__build_node(
            rule=rule,
            parent_node=root,
            heading_name_counts={
                githubize_heading_name(root.top_heading_name): 1,
            },
        ), self.div_cfg.division_rules))

        return root

    def __build_node(
        self,
        rule: DivisionRule,
        parent_node: DivisionTreeNode,
        heading_name_counts: Dict[str, int],
    ) -> DivisionTreeNode:
        node = DivisionTreeNode(
            parent=parent_node,
            title=rule.title,
            title_number_in_parent_file=None,
            intro=rule.intro,
            type=rule.divisionType,
            posts=None,
            post_rules=rule.post_rules,
            children=None,
        )

        current_heading_name_counts = heading_name_counts.get(
            node.githubized_title, 0)+1
        node.title_number_in_parent_file = current_heading_name_counts
        heading_name_counts[node.githubized_title] = current_heading_name_counts
        if node.type == DivisionType.FILE:
            heading_name_counts = {
                githubize_heading_name(node.top_heading_name): 1,
            }

        if rule.children != None and len(rule.children) > 0:
            if isinstance(rule.match_rule, MatchOnly):
                raise OnlyMatchRuleHasChildrenException
            node.children = list(
                map(lambda rule: self.__build_node(
                    rule=rule,
                    parent_node=node,
                    heading_name_counts=heading_name_counts,
                ), rule.children))

        if isinstance(rule.match_rule, MatchUntil):
            posts = self.__collect_match_until_posts(rule.match_rule)
            children_has_match_until = len(
                list(filter(lambda c: isinstance(c.match_rule, MatchUntil), rule.children))) > 0
            if children_has_match_until:
                node.children.append(
                    self.__build_leftover_node(
                        posts=posts,
                        parent_node=node,
                        heading_name_counts=heading_name_counts,
                    )
                )
            else:
                node.posts = posts
        elif isinstance(rule.match_rule, MatchOnly):
            posts = self.__collcet_match_only_posts(rule.match_rule)
            for post in posts:
                if post.post_id in self.post_claims:
                    self.post_claims[post.post_id].append(node)
                else:
                    self.post_claims[post.post_id] = [node]
            node.posts = posts
        elif rule.match_rule == None:
            pass
        else:
            raise UnknownMatchRule(rule.match_rule)

        for post_rule in (rule.post_rules or {}).values():
            for appended in (post_rule.appended or []):
                if appended in self.post_claims:
                    self.post_claims[appended].append(node)
                else:
                    self.post_claims[appended] = [node]

        if rule == self.div_cfg.division_rules[-1]:
            leftover_post_ids = self.post_ids[self.post_i:]
            if len(leftover_post_ids) > 0:
                node.children.append(
                    self.__build_leftover_node(
                        posts=list(map(lambda post_id: PostInNode(
                            post_id=post_id,
                            is_weak=True,
                        ), leftover_post_ids)),
                        parent_node=node,
                        heading_name_counts=heading_name_counts,
                    )
                )
            self.post_i = len(self.post_ids)

        return node

    def __build_leftover_node(
        self,
        posts: List[PostInNode],
        parent_node: DivisionTreeNode,
        heading_name_counts: Dict[str, int],
    ) -> DivisionTreeNode:
        posts = list(filter(
            lambda post_in_node: self.post_pool[post_in_node.post_id].user_id in self.div_cfg.po_cookies, posts))

        if self.remain_post != None:
            posts[0] = PostInNode(
                post_id=self.remain_post[0],
                is_weak=True,
                after_text=self.remain_post[1],
            )
            self.remain_post = None

        node = DivisionTreeNode(
            parent=parent_node,
            title="尚未整理",
            title_number_in_parent_file=None,
            intro=None,
            type=DivisionType.SECTION,
            posts=posts,
            post_rules=None,
            children=None,
        )

        current_heading_name_counts = heading_name_counts.get(
            node.githubized_title, 0)+1
        node.title_number_in_parent_file = current_heading_name_counts
        heading_name_counts[node.githubized_title] = current_heading_name_counts

        return node

    # TODO: 如果 id 比之前的要小，抛出 `UntilMatchRuleIDBelowPreviousException`
    def __collect_match_until_posts(self, match_until: MatchUntil) -> List[PostInNode]:
        posts: PostInNode = []

        while self.post_i < len(self.post_ids):
            post_id = self.post_ids[self.post_i]
            if post_id > match_until.id:
                break

            after_text = None
            if self.remain_post != None:
                if self.remain_post[0] == post_id:
                    after_text = self.remain_post[1]
                else:
                    posts.append(PostInNode(
                        post_id=post_id,
                        is_weak=True,
                        after_text=self.remain_post[1],
                    ))
                self.remain_post = None

            post = self.post_pool[post_id]

            is_not_excluded = post_id not in (match_until.excluded or [])
            is_po = post.user_id in self.div_cfg.po_cookies
            if is_not_excluded and is_po:
                if post_id == match_until.id:
                    until_text = match_until.text_until
                else:
                    until_text = None
                posts.append(PostInNode(
                    post_id=post_id,
                    is_weak=True,
                    after_text=after_text,
                    until_text=until_text,
                ))

            if match_until.text_until != None and post_id == match_until.id:
                self.remain_post = (post_id, match_until.text_until)
                break
            self.post_i += 1

        return posts

    def __collcet_match_only_posts(self, match_only: MatchOnly) -> List[PostInNode]:
        return list(map(lambda id: PostInNode(post_id=id, is_weak=False), match_only.ids))
