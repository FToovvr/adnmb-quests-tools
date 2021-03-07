from typing import Optional, Dict, Any, List, Tuple, Optional, Iterable, Callable, OrderedDict
from dataclasses import dataclass

import logging
from pathlib import Path

import anobbsclient
from anobbsclient.walk import create_walker, ReversalThreadWalkTarget


@dataclass
class Page:
    thread_body: anobbsclient.ThreadBody
    page_number: int
    replies: List[anobbsclient.Post]


def fetch_page_range_back_to_front(
    client: anobbsclient.Client,
    thread_id: int,
    from_upper_bound_page_number: int,
    to_lower_bound_page_number: int,
    lower_bound_post_id: int,
    gatekeeper_post_id: Optional[int]
) -> Tuple[List[Page], Optional[int], bool]:
    """
    Returns
    -------
    Optional[List[Page]]
        获取到的页面的列表。
        如果为空，代表本轮结果被抛弃。

    Optional[int]
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
        for (n, page, _) in create_walker(
            target=ReversalThreadWalkTarget(
                thread_id=thread_id,
                start_page_number=from_upper_bound_page_number,
                gatekeeper_post_id=gatekeeper_post_id,
                stop_before_post_id=lower_bound_post_id,
                expected_stop_page_number=to_lower_bound_page_number,
            ),
            client=client,
        ):
            msg = f"范围：从第{from_upper_bound_page_number}页至第{to_lower_bound_page_number}页，"
            msg += f"获取处理：第{n}页"
            if n < to_lower_bound_page_number:
                msg += f"（将合并至第{to_lower_bound_page_number}页）"
            logging.info(msg)
            if len(pages) == 0 or pages[-1].page_number != to_lower_bound_page_number:
                pages.append(Page(
                    thread_body=page.body,
                    page_number=n,
                    replies=page.replies,
                ))
            else:
                pages[-1].replies.extend(page.replies)
            logging.info(f"获取完成：第{n}页")
    except KeyboardInterrupt:
        logging.warning("收到用户键盘中断，将中断")
        aborted = True
    except anobbsclient.RequiresLoginException:
        logging.error("未登陆，将中断")
        aborted, should_abandon = True, True
    except anobbsclient.GatekeptException as e:
        logging.error(
            f"出现「卡99」现象，疑似登陆失效，将中断。当前页面页数：{e.current_page_number}，上下文：{e.context}，守门串号：{e.gatekeeper_post_id}")
        aborted, should_abandon = True, True
    except anobbsclient.UnreachableLowerBoundPostIDException as e:
        logging.error(f"由于不明原因，无法到达预定的下界串号，将中断。下界串号： {e.lower_bound_post_id}")
        aborted, should_abandon = True, True
    except anobbsclient.UnexpectedLowerBoundPostIDException as e:
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
        if len(pages[0].replies) != 0:
            current_round_max_seen_post_id = int(pages[0].replies[-1].id)
        elif len(pages) > 1:
            current_round_max_seen_post_id = int(pages[1].replies[-1].id)
        else:
            current_round_max_seen_post_id = None
    else:
        current_round_max_seen_post_id = None

    return (pages, current_round_max_seen_post_id, aborted)
