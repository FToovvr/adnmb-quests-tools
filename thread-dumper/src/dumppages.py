from typing import Optional, OrderedDict, Any, List, Tuple

from pathlib import Path
import shutil
import json
import os

import anobbsclient

from .fetchpages import fetch_page_range_back_to_front


import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "commons"))
from dumpedpages import PageInfo, get_page_name_and_status  # noqa: E402


def dump_page_range_back_to_front(
    dump_folder_path: Path,
    client: anobbsclient.Client,
    thread_id: int,
    from_upper_bound_page_number: int,
    to_lower_bound_page_number: int,
    gatekeeper_page_number: int,
    gatekeeper_post_id: Optional[int]
) -> Tuple[Optional[int], bool, Optional[int]]:
    """
    Returns
    -------
    int?
        本轮见到的最大的串号。

    bool
        是否应该中断。
        如果为真，则处理完本轮后应该终止程序。

    int?
        当前回应数
    """

    lower_bound_post_id = None
    if to_lower_bound_page_number > 1:
        lower_bound_post_id = get_lower_bound_post_id(
            pages_folder_path=dump_folder_path / "pages",
            page_number=to_lower_bound_page_number,
        )

    (pages, current_round_max_seen_post_id, aborted) = fetch_page_range_back_to_front(
        client=client,
        thread_id=thread_id,
        from_upper_bound_page_number=from_upper_bound_page_number,
        to_lower_bound_page_number=to_lower_bound_page_number,
        lower_bound_post_id=lower_bound_post_id,
        gatekeeper_page_number=gatekeeper_page_number,
        gatekeeper_post_id=gatekeeper_post_id,
    )

    if pages == None:
        return current_round_max_seen_post_id, aborted, None

    pages_folder_path = dump_folder_path / "pages"

    for (i, page) in enumerate(pages):
        (previous_name, _) = get_page_name_and_status(
            pages_folder_path=pages_folder_path,
            page_number=page.page_number,
        )

        current_page_replies = page.replies
        if previous_name != None:
            previous_page_path = pages_folder_path / previous_name
            with open(previous_page_path) as previous_page_file:
                previous_page_replies = list(
                    map(lambda post: anobbsclient.Post(post), json.load(previous_page_file)))
                current_page_replies = merge_posts(
                    previous_page_replies, current_page_replies)

            tmp_path = pages_folder_path / f"_{previous_name}"
            shutil.move(previous_page_path, tmp_path)

        if i == 0 and len(page.replies) != 19:
            current_name = f"{page.page_number}.incomplete.json"
        elif aborted and i == len(pages) - 1:
            current_name = f"{page.page_number}.previous-page-unchecked.json"
        else:
            current_name = f"{page.page_number}.json"

        with open(pages_folder_path / current_name, "w+") as current_file:
            json.dump(list(map(lambda post: post.raw_copy(), current_page_replies)), current_file,
                      indent=2, ensure_ascii=False)

        if previous_name != None:
            os.remove(tmp_path)

    thread_body = pages[-1].thread_body
    reply_count = thread_body.total_reply_count
    with open(dump_folder_path / "thread.json", "w+") as thread_file:
        json.dump(thread_body.raw_copy(keeps_reply_count=False),
                  thread_file, indent=2, ensure_ascii=False)

    return current_round_max_seen_post_id, aborted, reply_count


def get_lower_bound_post_id(pages_folder_path: Path, page_number: int) -> int:
    (name, _) = get_page_name_and_status(
        pages_folder_path=pages_folder_path,
        page_number=page_number,
    )
    if name == None:
        (name, _) = get_page_name_and_status(
            pages_folder_path=pages_folder_path,
            page_number=page_number-1,
        )

    with open(pages_folder_path / name) as file:
        posts = json.load(file)
        return int(posts[-1]["id"])


def merge_posts(a: List[anobbsclient.Post], b: List[anobbsclient.Post]):
    a = {int(post.id): post for post in a}
    b = {int(post.id): post for post in b}
    a.update(b)
    a = [post for (_, post) in a.items()]
    a = sorted(a, key=lambda post: int(post.id))
    return a
