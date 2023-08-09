class FileCorruptedError(BaseException):
    pass


class Format:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def parse(self):
        raise NotImplementedError('Provide the definition of parse method')
