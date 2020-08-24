from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Tuple, Optional, List, Union
from enum import Enum, auto

from pathlib import Path
from os.path import splitext
import json
from hashlib import sha1

import logging

import sys
sys.path.append(str(Path(__file__).parent.parent.parent / "commons"))
from dumpedpages import PageInfo, get_processable_page_info_list  # noqa: E402


@dataclass
class Trace:
    last_processed_post_id: int
    div_cfg_sha1: str

    @staticmethod
    def load_from_obj(obj: Dict[Any]):
        return Trace(**obj)

    def as_obj(self):
        return self.__dict__

    # TODO: 新方案
    @staticmethod
    def evaluate(
        div_cfg_path: Path,
        dump_folder_path: Path,
        page_info_list: List[PageInfo]
    ) -> Trace:
        last_page_filename = page_info_list[-1].filename()
        last_page_file_path = dump_folder_path / "pages" / last_page_filename
        with open(last_page_file_path) as last_page_file:
            last_page = json.load(last_page_file)
            last_dumped_post_id = int(last_page[-1]["id"])
        with open(div_cfg_path, 'rb') as div_cfg_file:
            h = sha1()
            while True:
                chunk = div_cfg_file.read(h.block_size)
                if not chunk:
                    break
                h.update(chunk)
            div_cfg_sha1 = h.hexdigest()
        return Trace(
            last_processed_post_id=last_dumped_post_id,
            div_cfg_sha1=div_cfg_sha1,
        )


def needs_update(
    current_trace: Trace,
    output_folder_path: Path,
    ignores_trace: bool
):
    trace_file_path = output_folder_path / ".trace.json"
    if not trace_file_path.exists():
        return True
    elif ignores_trace:
        logging.info(f"根据配置，忽略状态追踪文件")
        return True

    with open(trace_file_path) as trace_file:
        trace = Trace.load_from_obj(json.load(trace_file))

    if trace.last_processed_post_id != current_trace.last_processed_post_id:
        return True

    if trace.div_cfg_sha1 != current_trace.div_cfg_sha1:
        return True

    return False
