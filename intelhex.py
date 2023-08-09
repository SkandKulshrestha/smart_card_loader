import os.path

from format import Format
from format import FileCorruptedError


class IntelHex(Format):
    RECORD_TYPE = {
        '00': 'DATA',
        '01': 'END_OF_FILE',
        '02': 'EXTENDED_SEGMENT_ADDRESS',
        '03': 'START_SEGMENT_ADDRESS',
        '04': 'EXTENDED_LINEAR_ADDRESS',
        '05': 'START_LINEAR_ADDRESS'
    }

    def __init__(self, file_path: str):
        super(IntelHex, self).__init__(file_path)
        self.line_termination: str = '\n'
        self.start_code: str = ':'
        self.byte_count: int = 0
        self.address: str = ''
        self.record_type: str = ''
        self.data: str = ''
        self.checksum: str = ''
        self.segments = []

    def verify_checksum(self) -> bool:
        _checksum = self.byte_count
        _checksum += int(self.address[:2], 16)
        _checksum += int(self.address[2:], 16)
        _checksum += int(self.record_type, 16)
        for i in range(0, len(self.data), 2):
            _checksum += int(self.data[i:i + 2], 16)
        _checksum += int(self.checksum, 16)
        return _checksum & 0xFF == 0

    def parse_record(self):
        if self.record_type == '02':
            if self.byte_count != 2:
                raise FileCorruptedError('TODO')
        elif self.record_type == '03':
            if self.byte_count != 4:
                raise FileCorruptedError('TODO')
        elif self.record_type == '04':
            if self.byte_count != 2:
                raise FileCorruptedError('TODO')
        elif self.record_type == '05':
            if self.byte_count != 4:
                raise FileCorruptedError('TODO')

    def parse(self):
        with open(self.file_path) as hex_file:
            hex_data = hex_file.read()
            for record in hex_data.split(self.line_termination):
                try:
                    # check start code
                    index = record.find(self.start_code)
                    if index == -1:
                        raise FileCorruptedError('TODO: write proper message')
                    index += 1

                    # fetch byte count
                    self.byte_count = int(record[index: index + 2], 16)
                    index += 2

                    # fetch address
                    self.address = record[index: index + 4]
                    index += 4

                    # fetch record type
                    self.record_type = record[index: index + 2]
                    index += 2

                    # fetch data
                    self.data = record[index: index + (self.byte_count * 2)]
                    index += self.byte_count * 2

                    # fetch checksum
                    self.checksum = record[index: index + 2]
                    index += 2

                    # verify checksum
                    if not self.verify_checksum():
                        raise FileCorruptedError('TODO')

                    # verify length
                    if index != len(record):
                        raise FileCorruptedError('TODO')

                    print(record)

                    # verify and parse the fields
                    self.parse_record()
                except IndexError:
                    FileCorruptedError('TODO')
                except ValueError:
                    FileCorruptedError('TODO')


if __name__ == '__main__':
    intel = IntelHex(r'sample_files\sample_hex_file.hex')
    intel.parse()

    intel = IntelHex(r'sample_files\sample_empty_hex_file.hex')
    intel.parse()
