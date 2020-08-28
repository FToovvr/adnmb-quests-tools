from typing import Optional, Dict, Any, List, Tuple, Optional, Iterable, Callable, OrderedDict
from dataclasses import dataclass

import logging
from pathlib import Path

from .anobbsclient import AnoBBSClient
from .exceptions import NoUserhashException, InvaildUserhashException, GatekeepedException, UnreachableLowerBoundPostIDException, UnexpectedLowerBoundPostIDException


@dataclass
class Page:
    thread_body: OrderedDict[str, Any]
    page_number: int
    replies: List[OrderedDict[str, Any]]


def __fetch_pages_back_to_front(
    client: AnoBBSClient,
    thread_id: int,
    from_upper_bound_page_number: int,
    to_lower_bound_page_number: int,
    lower_bound_post_id: int,
    gatekeeper_page_number: int,
    gatekeeper_post_id: Optional[int]
) -> List[Page]:
    """
    从后向前获取页面

    Parameters
    ----------
    client : AnoBBSClient
        获取页面用的客户端。

    thread_id : int
        目标串的串号。

    from_upper_bound_page_number : int
        页数上界。
        从此处开始获取页面。

    to_lower_bound_page_number : int
        页数下界。
        获取的页面截止到此处，但可能因需要补漏，使获取页面的页数小于此页数。

    lower_bound_post_id : Optional[int]
        串号的下界。
        在到达或越过页数下界后，遇到此串号的回应一般代表已经没有缺漏。
        当然，极端情况下也可能是「卡99」了，这里不做考虑。
        在串号下界为第一页时，此参数应为空。

    gatekeeper_page_number : int
        守门页数，一般是第99页。
        获取超过此页数的页面内容需要登陆。

    gatekeeper_post_id : int
        上一轮中遇到的最大的串号
        如果获取的页面有串号越过（小于）此串号，则表示可能卡99了。
        不过如果该页面已经越过页数下界，且在越过的页面中有回应的串号大于 lower_bound_post_id，则应该没有卡99。
        （但也可能是在这一过程中「卡99」）

    Yields
    ------
    Page
        当前获取到的页面。
        顺序为页数倒叙

    Raises
    ------
    NoUserhashException
        如果需要登陆，但并为登陆。

    GatekeepedException
        如果检测到「卡99」。

    UnreachableLowerBoundPostIDException
        如果提前遇到了下界串号。
    """

    previous_page_min_post_id = None

    for page_number in reversed(range(1, from_upper_bound_page_number + 1)):

        # 检测是否需要登录，如果需要登陆但未登陆，抛异常
        needs_login = page_number > gatekeeper_page_number
        if needs_login and not client.has_logged_in():
            raise NoUserhashException()

        page = client.get_thread(
            thread_id, page=page_number, with_login=needs_login)
        thread_body = OrderedDict(page)
        thread_body.pop("replys")
        if lower_bound_post_id != None:
            lower_bound_index = find_first_index(
                reversed(page["replys"]), lambda post: int(post["id"]) <= lower_bound_post_id)
            if lower_bound_index != None:
                lower_bound_index = len(page["replys"]) - 1 - lower_bound_index
        else:
            lower_bound_index = None
        if lower_bound_index != None:
            # 找到下界串号了，代表抓取结束，没有遗漏

            if page_number > to_lower_bound_page_number:
                # 不应该在下界页面前找到下界串号
                if to_lower_bound_page_number == gatekeeper_page_number:
                    raise GatekeepedException(
                        context="lower_bound_post_id",
                        current_page_number=page_number,
                        gatekeeper_post_id=lower_bound_post_id,
                    )
                raise UnexpectedLowerBoundPostIDException(
                    page_number, to_lower_bound_page_number, lower_bound_post_id)
            if int(page["replys"][lower_bound_index]["id"]) == lower_bound_post_id:
                new_posts = page["replys"][lower_bound_index+1:]
            else:
                new_posts = page["replys"]

            yield Page(
                thread_body=thread_body,
                page_number=to_lower_bound_page_number,
                replies=new_posts,
            )
            return

        if needs_login:
            if int(page["replys"][0]["id"]) <= gatekeeper_post_id:
                # 作为「守门页」后的页面，有串的串号比「之前获取到的「守门页」中最大的串号」要小，代表「卡99」了。
                # 但如果「获取「守门页」最大串号」与「获取当前页」期间，「守门页」或之前连抽了19串或以上，即使「卡99」了也无法发现。
                # 由于间隔越长，连抽19串的可能越大，因此应该在每一轮转存前都获取一次「守门串号」。
                # 由于每一轮从第二页之后都可以用备用方案，之后便不成问题
                raise GatekeepedException(
                    "gatekeeper_post_id", page_number, gatekeeper_post_id)
            if previous_page_min_post_id != None and int(page["replys"][0]["id"]) >= previous_page_min_post_id:
                # 新获取的前一页没有串的串号比旧的后一页要小，要不然就是两页获取期间连抽了19串以上，要不然就是卡99了。
                # 鉴于前者的可能性应该不大，这里便忽略此可能，判定为卡99
                raise GatekeepedException(
                    "previous_page_min_post_id", page_number, previous_page_min_post_id)
        previous_page_min_post_id = int(page["replys"][0]["id"])

        yield Page(
            thread_body=thread_body,
            page_number=page_number,
            replies=page["replys"],
        )

    # 过了第一页

    if lower_bound_post_id == None:
        # return pages
        return

    raise UnreachableLowerBoundPostIDException(lower_bound_post_id)


def find_first_index(iter: Iterable[Any], where: Callable[[Any], bool]) -> Optional[int]:
    try:
        return next(i for i, v in enumerate(iter) if where(v))
    except StopIteration:
        return None


def fetch_page_range_back_to_front(
    client: AnoBBSClient,
    thread_id: int,
    from_upper_bound_page_number: int,
    to_lower_bound_page_number: int,
    lower_bound_post_id: int,
    gatekeeper_page_number: int,
    gatekeeper_post_id: Optional[int]
) -> Tuple[List[Page], Optional[int], bool]:
    """
    Returns
    -------
    [Page]?
        获取到的页面的列表。
        如果为空，代表本轮结果被抛弃。

    int?
        本轮见到的最大的串号。

    bool
        是否应该中断。
        如果为真，则处理完本轮后应该终止程序。
    """

    # 过程是否被中断。
    # 如果为真，页数最小的那页会是 `.previous-page-unchecked`
    aborted = False
    # 是否应该抛弃已经获取到的各页，以防止损害已有数据
    should_abandon = False

    pages: List[Page] = []

    try:
        for page in __fetch_pages_back_to_front(
            client=client,
            thread_id=thread_id,
            from_upper_bound_page_number=from_upper_bound_page_number,
            to_lower_bound_page_number=to_lower_bound_page_number,
            lower_bound_post_id=lower_bound_post_id,
            gatekeeper_page_number=gatekeeper_page_number,
            gatekeeper_post_id=gatekeeper_post_id,
        ):
            msg = f"范围：从第{from_upper_bound_page_number}页至第{to_lower_bound_page_number}页，"
            msg += f"获取处理：第{page.page_number}页"
            if page.page_number < to_lower_bound_page_number:
                msg += f"（将合并至第{to_lower_bound_page_number}页）"
            logging.info(msg)
            if len(pages) == 0 or pages[-1].page_number != to_lower_bound_page_number:
                pages.append(page)
            else:
                pages[-1].replies.extend(page.replies)
            logging.info(f"获取完成：第{page.page_number}页")
    except KeyboardInterrupt:
        logging.warning("收到用户键盘中断，将中断")
        aborted = True
    except NoUserhashException:
        logging.error("未登陆，将中断")
        aborted, should_abandon = True, True
    except GatekeepedException as e:
        logging.error(
            f"出现「卡99」现象，疑似登陆失效，将中断。当前页面页数：{e.current_page_number}，上下文：{e.context}，守门串号：{e.gatekeeper_post_id}")
        aborted, should_abandon = True, True
    except UnreachableLowerBoundPostIDException as e:
        logging.error(f"由于不明原因，无法到达预定的下界串号，将中断。下界串号： {e.lower_bound_post_id}")
        aborted, should_abandon = True, True
    except UnexpectedLowerBoundPostIDException as e:
        logging.error(
            f"在预期之外的大于页数下界的页面遇到了下界串号 {e.lower_bound_post_id}，当前页面页数：{e.current_page_number}，页数下界：{e.expected_lower_bound_page_number}")
        aborted, should_abandon = True, True

    if should_abandon:
        logging.error("将遗弃已获取的页面")
        pages = None

    # 本轮见过的最大的串号。
    # 由于外层每一轮是从前向后的顺序进行处理，
    # 当本轮页数超过守门页时，可以让下一轮有效检测「卡99」
    if pages != None:
        current_round_max_seen_post_id = int(pages[0].replies[-1]["id"])
    else:
        current_round_max_seen_post_id = None

    return (pages, current_round_max_seen_post_id, aborted)
