from dataclasses import dataclass


class InvaildUserhashException(Exception):
    pass


class NoUserhashException(Exception):
    pass


@dataclass
class GatekeepedException(Exception):
    context: str
    current_page_number: int
    gatekeeper_post_id: int


@dataclass
class UnreachableLowerBoundPostIDException(Exception):
    lower_bound_post_id: int


@dataclass
class UnexpectedLowerBoundPostIDException(Exception):
    current_page_number: int
    expected_lower_bound_page_number: int
    lower_bound_post_id: int
