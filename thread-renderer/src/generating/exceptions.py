from typing import Optional
from dataclasses import dataclass

from ..configloader import DivisionType


@dataclass
class UnexpectedDivisionTypeException(Exception):
    got: Optional[DivisionType]
    expected: Optional[DivisionType]
