from __future__ import annotations
from typing import Dict, Any, Optional
from dataclasses import dataclass

from pathlib import Path
import json
import os


@dataclass(frozen=True)
class Trace:
    thread_id: int
    known_reply_count: int
    last_dumped_post_id: int

    @staticmethod
    def __load_from_obj(obj: Dict[Any]) -> Trace:
        return Trace(
            known_reply_count=obj.get("known_reply_count", 0),
            last_dumped_post_id=obj.get("last_dumped_post_id", 0),
        )

    @staticmethod
    def load(trace_file_path: Path) -> Optional[Trace]:
        if trace_file_path.exists():
            with open(trace_file_path) as trace_file:
                obj = json.load(trace_file)
            thread_file_path = trace_file_path.parent / "thread.json"
            obj.update(("thread_id", Trace.__get_thread_id(thread_file_path)))
            return Trace.__load_from_obj(obj)
        else:
            return None

    @staticmethod
    def load_by_examining_dump_folder(dump_folder_path: Path):
        pages_folder_path = dump_folder_path / "pages"
        page_file_paths = (pages_folder_path).glob("*")
        page_count = max(filter(lambda path: int(
            os.path.splitext(path.name)[0]), page_file_paths))

        last_page_path = pages_folder_path / f"{page_count}.json"
        with open(last_page_path) as last_page_file:
            last_page = json.load(last_page_file)

        return Trace(
            thread_id=Trace.__get_thread_id(dump_folder_path / "thread.json"),
            known_reply_count=int(last_page["replyCount"]),
            last_dumped_post_id=int(last_page["replys"][-1]["id"]),
        )

    @staticmethod
    def __get_thread_id(thread_file_path: Path) -> int:
        with open(thread_file_path) as thread_file:
            thread = json.load(thread_file)
        return int(thread["id"])


def needs_update(old_trace: Trace, current_thread: Dict[Any]) -> bool:
    return int(current_thread["replyCount"]) > old_trace.known_reply_count
