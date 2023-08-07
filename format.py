class Format:
    RECORD_TYPE = {
        '00': 'DATA',
        '01': 'END_OF_FILE',
        '02': 'EXTENDED_SEGMENT_ADDRESS',
        '03': 'START_SEGMENT_ADDRESS',
        '04': 'EXTENDED_LINEAR_ADDRESS',
        '05': 'START_LINEAR_ADDRESS'
    }

    def __init__(self, file_path: str):
        self.file_path = file_path

    def parse(self):
        with open(self.file_path) as hex_file:
            pass
