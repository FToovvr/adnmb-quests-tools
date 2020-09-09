#!/usr/bin/env python3

from typing import List, Tuple, Dict, Any
from dataclasses import dataclass

import os
import sys
import logging
import logging.config
import argparse
from pathlib import Path
import json

import anobbsclient

from src.fetchpages import fetch_page_range_back_to_front
from src.dumppages import dump_page_range_back_to_front

sys.path.append(str(Path(__file__).parent.parent / "commons"))
from dumpedpages import PageInfo, get_page_info_list, get_page_ranges_for_dumping, get_page_name_and_status  # noqa: E402

HOST = os.environ["ANOBBS_HOST"]
USER_AGENT = os.environ["ANOBBS_CLIENT_ENVIRON"]
APPID = os.environ["ANOBBS_CLIENT_APPID"]
USERHASH = os.environ.get("ANOBBS_USERHASH", None)

client = anobbsclient.Client(
    user_agent=USER_AGENT,
    host=HOST,
    appid=APPID,
    default_request_options={
        "user_cookie": anobbsclient.UserCookie(userhash=USERHASH),
        "login_policy": "when_required",
        "gatekeeper_page_number": 99,
        "uses_luwei_cookie_format": {
            "expires": "Friday,24-Jan-2027 16:24:36 GMT",
        },
    },
)


def main(args: List[str]):
    logging.debug(f"args: {args}")
    args = parse_args(prog=args[0], args=args[1:])

    if args.dump_folder_path.exists():
        # 旧转存文件夹存在，检查串号前后是否一致
        dumped_thread_path = args.dump_folder_path / "thread.json"
        with open(dumped_thread_path) as dumped_thread_file:
            dumped_thread = json.load(dumped_thread_file)
        dumped_thread_id = int(dumped_thread["id"])
        if args.thread_id != dumped_thread_id:
            logging.critical(
                f'指定的串号 {args.thread_id} 与先前转存生成的 `thread.json` 中的串号 {dumped_thread_id} 不一致，将终止')
            exit(1)

    (first_page, _) = client.get_thread_page(
        args.thread_id, page=1, for_analysis=True)
    page_count = (int(first_page.total_reply_count) - 1) // 19 + 1

    if args.dump_folder_path.exists():
        # 旧转存文件夹存在，检查旧文件夹来找出之前尚未完成的页数范围
        page_info_list = get_page_info_list(
            dump_folder_path=args.dump_folder_path)
        page_ranges = get_page_ranges_for_dumping(page_info_list, 99)

    pages_folder_path = args.dump_folder_path / "pages"

    if not args.dump_folder_path.exists():
        args.dump_folder_path.mkdir(parents=True)
        pages_folder_path.mkdir(parents=True)
        page_ranges = [(1, None)]

    logging.info(f"所有将要转存的页面的范围：{page_ranges}")

    needs_extra_round, should_abort = False, False
    max_seen_id = None
    reply_count = None
    for (i, page_range) in enumerate(page_ranges):
        logging.info(f"第{i+1}/{len(page_ranges)}轮，范围：{page_range}")
        (start_page, end_page) = page_range
        if end_page == None:
            if start_page < 99 and page_count > 99:
                needs_extra_round = True
                end_page = 99
            else:
                end_page = page_count
        if end_page > 99:
            if not client.has_cookie():
                logging.warning("守门页后仍有待转存页面，但由于尚未登陆，无法获取。将结束")
                should_abort = True
                break
            if max_seen_id == None:
                (page99, _) = client.get_thread_page(
                    args.thread_id, page=99,
                    for_analysis=True,
                )
                max_seen_id = int(page99.replies[-1].id)
        (max_seen_id, should_abort, reply_count) = dump_page_range_back_to_front(
            dump_folder_path=args.dump_folder_path,
            client=client,
            thread_id=args.thread_id,
            from_upper_bound_page_number=end_page,
            to_lower_bound_page_number=start_page,
            gatekeeper_page_number=99,
            gatekeeper_post_id=max_seen_id,
        )
        if should_abort:
            break
    if (not should_abort) and needs_extra_round:
        if reply_count == None:
            (page99, _) = client.get_thread_page(
                args.thread_id, page=99,
                for_analysis=True,
            )
            reply_count = int(page99.total_reply_count)

        dump_page_range_back_to_front(
            dump_folder_path=args.dump_folder_path,
            client=client,
            thread_id=args.thread_id,
            from_upper_bound_page_number=(reply_count-1)//19+1,
            to_lower_bound_page_number=100,
            gatekeeper_page_number=99,
            gatekeeper_post_id=max_seen_id
        )


def parse_args(prog: str, args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="转存A岛串",
    )

    parser.add_argument("thread_id",
                        help="要转存的串的串号", metavar="<thread id like `12345678`>",
                        type=int)
    parser.add_argument("-o", "--output", '--output-dump-folder',
                        help="输出的转存文件夹路径，默认为脚本执行目录下的`dump`文件夹", metavar="<path to dump folder>",
                        type=Path, dest="dump_folder_path")
    # parser.add_argument("--max-dump-page-count",
    #                     help="本次执行最多转存的页面数量", metavar="<count>",
    #                     type=int, dest="max_dump_page_count", default=None)
    # parser.add_argument("until-page-number",
    #                     help="最多转存到的页数", metavar="<page number>",
    #                     type=int, dest="u
    # ntil_page_number", default=None)
    parser.add_argument("--log-config", "--logging-configuration",
                        help="python logging配置文件的路径", metavar="<path to python logging.conf>",
                        type=Path, dest="log_config")

    args = parser.parse_args(args)

    if args.log_config != None:
        logging.config.fileConfig(
            args.log_config, disable_existing_loggers=False)

    return args


if __name__ == "__main__":
    main(sys.argv)
