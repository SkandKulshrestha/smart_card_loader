from segment import Segment


class FileCorruptedError(BaseException):
    pass


class Format:
    def __init__(self, line_termination: str, file_path: str, segments: list[Segment] = None):
        self.line_termination: str = line_termination
        self.file_path: str = file_path
        if segments is None:
            self.segments: list = list()
        else:
            self.segments: list = segments
        self.lines: list = list()

    def parse(self):
        raise NotImplementedError('Provide the definition of parse method')

    def compose(self) -> list[str]:
        raise NotImplementedError('Provide the definition of compose method')
