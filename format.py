from abc import ABC
from typing import List
from segment import Segment


class FileCorruptedError(BaseException):
    pass


class Format(ABC):
    def __init__(self, line_termination: str):
        self.line_termination: str = line_termination

        # initialize the segment list and lines list
        self.segments: List[Segment] = list()
        self.lines: List[str] = list()

        # initialize operation state
        self.parsed: bool = False
        self.composed: bool = False

    def parse(self, file_path: str) -> List[Segment]:
        raise NotImplementedError('Provide the definition of parse method')

    def compose(self, file_path: str = '', segments: List[Segment] = None) -> List[str]:
        raise NotImplementedError('Provide the definition of compose method')

    def verify(self) -> bool:
        for segment in self.segments:
            print(segment)

        return True

    def merge(self, output_file: str, file_paths: List[str]):
        for file_path in file_paths:
            self.parse(file_path)

        self.compose(output_file)
