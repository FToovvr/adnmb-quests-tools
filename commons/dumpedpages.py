from __future__ import annotations
from typing import Tuple, List, Optional
from dataclasses import dataclass
from enum import Enum, auto

import logging
from pathlib import Path
from os.path import splitext


@dataclass
class PageInfo:

    class Status(Enum):
        COMPLETE = auto()
        INCOMPLETE = auto()
        PREVIOUS_PAGE_UNCHECKED = auto()

        @staticmethod
        def from_sub_ext(sub_ext: str) -> PageInfo.Status:
            if sub_ext == None:
                return PageInfo.Status.COMPLETE
            elif sub_ext == ".incomplete":
                return PageInfo.Status.INCOMPLETE
            elif sub_ext == ".previous-page-unchecked":
                return PageInfo.Status.PREVIOUS_PAGE_UNCHECKED
            else:
                raise f"cannot map file sub-extension `{sub_ext}` to page status"

        def as_sub_ext(self) -> str:
            if self == PageInfo.Status.COMPLETE:
                return ""
            elif self == PageInfo.Status.INCOMPLETE:
                return ".incomplete"
            elif self == PageInfo.Status.PREVIOUS_PAGE_UNCHECKED:
                return ".previous-page-unchecked"

    number: int
    status: "PageInfo.Status"

    def filename(self):
        return f'{self.number}{self.status.as_sub_ext()}.json'


def get_page_info_list(dump_folder_path: Path) -> Tuple[List[PageInfo], str]:
    # 123.previous-page-unchecked.json
    # 456.incomplete.json
    page_infos = {}
    for page_path in (dump_folder_path / "pages").iterdir():
        page_name = splitext(page_path.name)[0]
        page_status = None
        try:
            page_number = int(page_name)
        except ValueError:
            (page_number, page_status) = splitext(page_name)
            page_number = int(page_number)
        if page_number in page_infos:
            logging.critical(f"页面 {page_name} 存在多种状态版本，无法判断，将中断")
            raise KeyError(page_name)
        page_infos[page_number] = page_status
    page_infos = map(lambda kv: PageInfo(
        kv[0], PageInfo.Status.from_sub_ext(kv[1])), page_infos.items())
    page_infos = sorted(page_infos, key=lambda x: x.number)
    return page_infos


def get_processable_page_info_list(dump_folder_path: Path) -> Tuple[List[PageInfo], str]:
    page_infos = get_page_info_list(dump_folder_path=dump_folder_path)

    max_page_number = 0
    stop_reason = None
    for (i, page_info) in enumerate(page_infos):
        if page_info.number != max_page_number+1:
            stop_reason = "之后页数有空缺"
            break
        elif page_info.status == PageInfo.Status.PREVIOUS_PAGE_UNCHECKED:
            stop_reason = "下一页尚未检查本页有无缺漏"
            break
        elif page_info.status == PageInfo.Status.INCOMPLETE:
            max_page_number = page_info.number  # 即 `+= 1`
            if i != len(page_infos) - 1:
                stop_reason = "该页不完整（虽然之后还有页面）"
            break
        else:
            max_page_number = page_info.number
    if max_page_number == page_infos[-1].number:
        stop_reason = "已纳入全部页面"

    return (page_infos[: max_page_number], stop_reason)


def get_page_ranges_for_dumping(
        page_infos: List[PageInfo],
        gakekeeper_page_number: int
) -> List[Tuple[int, int]]:
    ranges = []

    last_page_number = page_infos[0].number
    for page_info in page_infos[1:]:
        if page_info.number != 1 and last_page_number == None:
            # 从第一页开始断页
            ranges.append((1, page_info.number-1))
        elif page_info.status != PageInfo.Status.COMPLETE:
            if page_info.number == 1:
                ranges.append((1, 1))
            else:
                ranges.append((page_info.number-1, page_info.number))
        elif page_info.number - 1 != last_page_number:
            # 断页
            if page_info.status != PageInfo.Status.INCOMPLETE:
                # 断页前的那一页无论是否完整，都算在转存的范围内，
                # 因为更往前的页可能会有串被删除，导致出现位移。
                # 本页完整，不在转存范围内
                ranges.append((last_page_number, page_info.number-1))
            else:
                # 当前页不完整，因此也在转存的范围内
                ranges.append((last_page_number, page_info.number))
        last_page_number = page_info.number

    ranges.append((last_page_number or 1, None))

    merged_ranges = []

    for range in ranges:
        if len(merged_ranges) == 0:
            merged_ranges.append(range)
        elif merged_ranges[-1][1] >= range[0]:
            merged_ranges[-1] = (merged_ranges[-1][0], range[1])
        else:
            merged_ranges.append(range)

    return merged_ranges


def get_page_name_and_status(pages_folder_path: Path, page_number: int) -> Optional[str, PageInfo.Status]:
    for (name, status) in [
        (f"{page_number}.json", PageInfo.Status.COMPLETE),
        (f"{page_number}.incomplete.json", PageInfo.Status.INCOMPLETE),
        (f"{page_number}.previous-page-unchecked.json",
         PageInfo.Status.PREVIOUS_PAGE_UNCHECKED),
    ]:
        if (pages_folder_path / name).exists():
            return (name, status)
    return (None, None)
