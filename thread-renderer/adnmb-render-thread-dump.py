#!/usr/bin/env python3

# language features
from __future__ import annotations
from typing import List, Dict, IO, Optional, Union, Any, OrderedDict
from dataclasses import dataclass
# from dataclasses import is_dataclass, asdict  # for debugging
from enum import Enum, auto

# first-patry libraries
import sys
import json
from pathlib import Path
from os.path import splitext
from shutil import rmtree
import argparse
import logging.config
from hashlib import sha1

# third-patry libiraies
import yaml

# this library
from src.configloader import DivisionsConfiguration
from src.thread import Thread
from src.generating import OutputsGenerator


def main(args: List[str]):
    logging.debug(f"args: {args}")
    args = parse_args(prog=args[0], args=args[1:])

    logging.info(f"配置文件路径：{args.div_cfg_path}")
    logging.info(f"输入转存文件夹路径：{args.dump_folder_path}")
    logging.info(f"输出文件夹路径：{args.output_folder_path}")

    if (not args.overwrite_output) and args.output_folder_path.exists():
        logging.critical("配置未允许覆写输出文件夹，呃输出文件夹已存在")
        exit(1)

    current_trace = Trace.evaluate(
        div_cfg_path=args.div_cfg_path,
        dump_folder_path=args.dump_folder_path,
    )
    if not needs_update(
        current_trace=current_trace,
        output_folder_path=args.output_folder_path,
        ignores_trace=args.ignore_trace
    ):
        logging.info("未检测到发生变化，无需进行生成，退出")
        return

    div_cfg = load_divisions_configuration(args.div_cfg_path)

    thread = Thread.load_from_dump_folder(args.dump_folder_path)

    if args.output_folder_path.exists():
        logging.info(f"输出文件夹已存在。根据配置，将覆写该文件夹")
        rmtree(args.output_folder_path, ignore_errors=True)

    args.output_folder_path.mkdir(parents=True)
    OutputsGenerator.generate_outputs(
        output_folder_path=args.output_folder_path,
        thread=thread,
        configuration=div_cfg)

    if not args.no_generate_trace:
        with open(args.output_folder_path / ".trace.json", 'w') as trace_file:
            trace_file.write(json.dumps(current_trace.as_obj(), indent=2))


def parse_args(prog: str, args: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog=prog,
        description="根据切割规则，从A岛串的转存文件渲染为一组markdown文件",
    )
    parser.add_argument("-c", "--div-config", "--divisions-configuration",
                        help="切割规则配置文件的路径", metavar="<path to divisions.yaml>",
                        type=Path, dest="div_cfg_path", required=True)
    parser.add_argument("-i", "--input", '--input-dump-folder',
                        help="输入的转存文件夹路径，默认为配置文件同目录下的`dump`文件夹", metavar="<path to dump folder>",
                        type=Path, dest="dump_folder_path")
    parser.add_argument("-o", "--output",
                        help="输出文件夹路径，默认为配置文件同目录下的`book`文件夹", metavar="<path to output folder>",
                        type=Path, dest="output_folder_path")
    parser.add_argument("--allow-overwrite-output",
                        help="如果输出文件夹存在，删除并重建该文件夹",
                        dest="overwrite_output", action="store_true", default=False)
    parser.add_argument("--log-config", "--logging-configuration",
                        help="python logging配置文件的路径", metavar="<path to python logging.conf>",
                        type=Path, dest="log_config")
    parser.add_argument("--no-generate-trace",
                        help="不记录往后用于检查是否需要更新的状态追踪文件",
                        dest="no_generate_trace", action="store_true", default=False)
    parser.add_argument("--ignore-trace",
                        help="无视状态追踪文件，强制进行生成",
                        dest="ignore_trace", action="store_true", default=False)

    args = parser.parse_args(args)
    default_base_folder_path = args.div_cfg_path.parent
    if args.dump_folder_path == None:
        args.dump_folder_path = default_base_folder_path / "dump"
    if args.output_folder_path == None:
        args.output_folder_path = default_base_folder_path / "book"
    if args.log_config != None:
        logging.config.fileConfig(
            args.log_config, disable_existing_loggers=False)

    return args


def load_divisions_configuration(path: Path) -> DivisionsConfiguration:
    with open(path) as div_cfg_file:
        return DivisionsConfiguration.load(
            div_cfg_file,
            root_folder_path=Path(path).parent.absolute(),
        )


@dataclass
class Trace:
    last_processed_post_id: int
    div_cfg_sha1: str

    @staticmethod
    def load_from_obj(obj: Dict[Any]):
        return Trace(**obj)

    def as_obj(self):
        return self.__dict__

    @staticmethod
    def evaluate(
        div_cfg_path: Path,
        dump_folder_path: Path,
    ) -> Trace:
        with open(dump_folder_path / ".trace.json") as dump_trace_file:
            dump_trace = DumpTrace.load_from_obj(json.load(dump_trace_file))
        with open(div_cfg_path, 'rb') as div_cfg_file:
            h = sha1()
            while True:
                chunk = div_cfg_file.read(h.block_size)
                if not chunk:
                    break
                h.update(chunk)
            div_cfg_sha1 = h.hexdigest()
        return Trace(
            last_processed_post_id=dump_trace.last_dumped_post_id,
            div_cfg_sha1=div_cfg_sha1,
        )


@dataclass
class DumpTrace:
    last_dumped_post_id: int

    @staticmethod
    def load_from_obj(obj: Dict[Any]) -> DumpTrace:
        return DumpTrace(last_dumped_post_id=obj["last_dumped_post_id"])


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


if __name__ == "__main__":
    main(sys.argv)
