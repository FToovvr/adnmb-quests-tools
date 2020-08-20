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

# third-patry libiraies
import yaml

# this library
from src.configloader import DivisionsConfiguration
from src.thread import Thread
from src.generating import OutputsGenerator


def main(args: List[str]):
    args = parse_args(prog=args[0], args=args[1:])

    try:
        with open(args.div_cfg_path) as div_cfg_file:
            try:
                div_cfg = DivisionsConfiguration.load(
                    div_cfg_file,
                    root_folder_path=Path(args.div_cfg_path).parent.absolute(),
                )
            except Exception as e:
                exit_with_message(f"failed to load {args.div_cfg_path}: {e}",
                                  status_code=3)
    except Exception as e:
        exit_with_message(f"unable to open {args.div_cfg_path}: {e}",
                          status_code=2)

    thread = Thread.load_from_dump_folder(args.dump_folder_path)

    args.output_folder_path.mkdir(parents=True)
    OutputsGenerator.generate_outputs(
        output_folder_path=args.output_folder_path,
        thread=thread,
        configuration=div_cfg)


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

    args = parser.parse_args(args)
    default_base_folder_path = args.div_cfg_path.parent
    if args.dump_folder_path == None:
        args.dump_folder_path = default_base_folder_path / "dump"
    if args.output_folder_path == None:
        args.output_folder_path = default_base_folder_path / "book"
    if args.output_folder_path.exists():
        if args.overwrite_output:
            rmtree(args.output_folder_path, ignore_errors=True)
        else:
            raise f"output folder exists: {args.output_folder_path}"
    if args.log_config != None:
        logging.config.fileConfig(
            args.log_config, disable_existing_loggers=False)

    return args


def exit_with_message(message: str, status_code: int):
    print(message, file=sys.stderr)
    sys.exit(status_code)


if __name__ == "__main__":
    main(sys.argv)
