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
from src.trace import Trace, get_processable_page_info_list, needs_update
from src.configloader import DivisionsConfiguration
from src.thread import Thread
from src.divisiontree import TreeBuilder
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

    (page_info_list, stop_reason) = get_processable_page_info_list(
        args.dump_folder_path)
    logging.info(f"将要处理的页数截止到 {page_info_list[-1].number} 页，由于{stop_reason}")
    current_trace = Trace.evaluate(
        div_cfg_path=args.div_cfg_path,
        dump_folder_path=args.dump_folder_path,
        page_info_list=page_info_list,
    )
    if not needs_update(
        current_trace=current_trace,
        output_folder_path=args.output_folder_path,
        ignores_trace=args.ignore_trace
    ):
        logging.info("未检测到发生变化，无需进行生成，退出")
        return

    div_cfg = load_divisions_configuration(args.div_cfg_path)

    thread = Thread.load_from_dump_folder(
        args.dump_folder_path, page_info_list)

    if args.output_folder_path.exists():
        logging.info(f"输出文件夹已存在。根据配置，将覆写该文件夹")
        rmtree(args.output_folder_path, ignore_errors=True)

    args.output_folder_path.mkdir(parents=True)

    post_pool = thread.flattened_post_dict()
    (tree, post_claims) = TreeBuilder.build_tree(
        post_pool=post_pool,
        div_cfg=div_cfg,
    )
    OutputsGenerator.generate_outputs(
        output_folder_path=args.output_folder_path,
        post_pool=post_pool,
        div_cfg=div_cfg,
        div_cfg_folder_path=args.div_cfg_path.parent,
        division_tree=tree,
        post_claims=post_claims,
    )

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


if __name__ == "__main__":
    main(sys.argv)
