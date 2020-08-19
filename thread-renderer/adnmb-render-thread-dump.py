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

# third-patry libiraies
import yaml

# this library
from src.configloader import DivisionsConfiguration
from src.thread import Thread
from src.generating import OutputsGenerator


def main(args: List[str]):
    if len(args) != 2:
        exit_with_message(f"usage: {args[0]} <divisions.yaml>",
                          status_code=1)

    div_cfg_path = args[1]
    try:
        with open(div_cfg_path) as div_cfg_file:
            try:
                div_cfg = DivisionsConfiguration.load(
                    div_cfg_file,
                    root_folder_path=Path(div_cfg_path).parent.absolute(),
                )
            except Exception as e:
                exit_with_message(f"failed to load {div_cfg_path}: {e}",
                                  status_code=3)
    except Exception as e:
        exit_with_message(f"unable to open {div_cfg_path}: {e}",
                          status_code=2)

    thread = Thread.load_from_dump_folder(div_cfg.root_folder_path / "dump")

    output_folder_path = div_cfg.root_folder_path / "book"
    rmtree(output_folder_path, ignore_errors=True)
    output_folder_path.mkdir(parents=True)
    OutputsGenerator.generate_outputs(
        output_folder_path=output_folder_path,
        thread=thread,
        configuration=div_cfg)


def exit_with_message(message: str, status_code: int):
    print(message, file=sys.stderr)
    sys.exit(status_code)


if __name__ == "__main__":
    main(sys.argv)
