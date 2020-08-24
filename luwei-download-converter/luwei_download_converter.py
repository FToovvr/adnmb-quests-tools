#!/usr/bin/env python3

from typing import List, OrderedDict

import os
import sys
import logging
import argparse
from pathlib import Path
import shutil
import json

# TODO: --move-assets
# TODO: add .gitattributes if moved assets
# TODO: add .gitignore if specified --git-ignore-assets


def main(args: List[str]):
    logging.debug(f"args: {args}")
    args = parse_args(prog=args[0], args=args[1:])

    if args.dump_folder_path.exists():
        shutil.rmtree(args.dump_folder_path)
    args.dump_folder_path.mkdir(parents=True)
    (args.dump_folder_path / "pages").mkdir(parents=True)

    data_folder_path = args.luwei_downloaded_thread_folder_path / "data"
    max_page_number = get_max_page_number(data_folder_path)

    for page_number in range(1, max_page_number+1):
        data_file_path = data_folder_path / f"{page_number}.data"
        with open(data_file_path) as data_file:
            data_raw = data_file.read()[11:-2]
            thread_page = json.loads(data_raw, object_pairs_hook=OrderedDict)
            last_dumped_post_id = int(thread_page["replys"][-1]["id"])

            if page_number == max_page_number:
                thread_body = OrderedDict(thread_page)
                thread_body.pop("replys")
                thread_body.pop("replyCount")
                with open(args.dump_folder_path / "thread.json", "w+") as thread_file:
                    json.dump(thread_body, thread_file,
                              indent=2, ensure_ascii=False)
                    thread_file.write("\n")

            replies = list(filter(
                lambda post: post["userid"] != "芦苇", thread_page["replys"]))
            with open(args.dump_folder_path / "pages" / f"{page_number}.json", "w+") as page_file:
                json.dump(replies, page_file, indent=2, ensure_ascii=False)
                page_file.write("\n")


def get_max_page_number(data_folder_path: Path) -> int:
    max_page_number = 0
    for data_file_path in data_folder_path.glob("*"):
        name = os.path.splitext(data_file_path.name)[0]
        page_number = int(name)
        max_page_number = max(max_page_number, page_number)
    return max_page_number


def parse_args(prog: str, args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="将芦苇下载的串转换为thread dump",
    )

    parser.add_argument("-i", "--input", '--input-luwei-downloaded-thread-folder',
                        help="输入的芦苇下载串文件夹路径", metavar="<path to luwei downloaded thread folder `tXXXXXXXX`>",
                        type=Path, dest="luwei_downloaded_thread_folder_path", required=True)
    parser.add_argument("-o", "--output", '--output-dump-folder',
                        help="输出的转存文件夹路径，默认为芦苇下载串文件夹同目录下的`dump`文件夹", metavar="<path to dump folder>",
                        type=Path, dest="dump_folder_path")

    args = parser.parse_args(args)
    if args.dump_folder_path == None:
        args.dump_folder_path = args.luwei_downloaded_thread_folder_path.parent / "dump"

    return args


if __name__ == "__main__":
    main(sys.argv)
