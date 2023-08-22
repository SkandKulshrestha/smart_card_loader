from abc import ABC
from typing import List
from segment import Segment


class FileCorruptedError(BaseException):
    pass


class Format(ABC):
    def __init__(self, line_termination: str, file_path: str, segments: List[Segment] = None):
        self.line_termination: str = line_termination
        self.file_path: str = file_path
        if segments is None:
            self.segments: List[Segment] = list()
        else:
            self.segments: List[Segment] = segments
        self.lines: List[str] = list()

    def parse(self) -> List[Segment]:
        raise NotImplementedError('Provide the definition of parse method')

    def compose(self) -> List[str]:
        raise NotImplementedError('Provide the definition of compose method')

    def verify(self) -> bool:
        raise NotImplementedError('Provide the definition of verify method')

    def merge(self, file_path: str, segments: List[Segment] = None):
        raise NotImplementedError('Provide the definition of merge method')
