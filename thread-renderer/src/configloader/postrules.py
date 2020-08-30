from __future__ import annotations
from typing import Optional, Union, List, Dict, Any
from dataclasses import dataclass


PostRules = Optional[Dict[int, "PostRule"]]


@dataclass(frozen=True)
class PostRule:
    expand_quote_links: Optional[Union[bool, List[int]]] = None
    appended: Optional[List[int]] = None
    show_attachment: Optional[bool] = None

    @staticmethod
    def load_from_object(obj: Optional[Dict[str, Any]]) -> PostRule:
        obj = obj or dict()

        expand_quote_links = obj.get("expand-quote-links", None)
        if type(expand_quote_links) is int:
            expand_quote_links = [expand_quote_links]

        appended = obj.get("appended", None)
        if type(appended) is int:
            appended = [appended]

        return PostRule(
            expand_quote_links=expand_quote_links,
            appended=appended,
            show_attachment=obj.get("show-attachment", True),
        )

    @staticmethod
    def merge(old: PostRule, new: PostRule) -> PostRule:
        rule_dict = None
        if old != None:
            rule_dict = dict(old.__dict__)
        if new != None:
            if rule_dict != None:
                new = [(k, v)
                       for k, v in new.__dict__.items() if v != None]
                rule_dict.update(new)
            else:
                rule_dict = dict(new.__dict__)

        if rule_dict != None:
            return PostRule(**rule_dict)
        return None
