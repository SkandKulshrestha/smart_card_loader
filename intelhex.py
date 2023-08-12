from format import Format
from format import FileCorruptedError
from segment import Segment


class IntelHex(Format):
    RECORD_TYPE = {
        '00': 'DATA',
        '01': 'END_OF_FILE',
        '02': 'EXTENDED_SEGMENT_ADDRESS',
        '03': 'START_SEGMENT_ADDRESS',
        '04': 'EXTENDED_LINEAR_ADDRESS',
        '05': 'START_LINEAR_ADDRESS'
    }

    def __init__(self, line_termination: str = '\n', file_path: str = None, segments: list[Segment] = None):
        super(IntelHex, self).__init__(line_termination, file_path, segments)
        self.start_code: str = ':'
        self.record_length: int = 0
        self.address: str = ''
        self.record_type: str = ''
        self.data: str = ''
        self.checksum: str = ''
        self.segment_address: str = ''
        self.segment_data: str = ''
        self.lower_address: int = 0
        self.end_of_file_reached: bool = False
        self.record = {v: k for k, v in self.RECORD_TYPE.items()}

    def _verify_checksum(self) -> bool:
        # initialize checksum
        _checksum: int = self.record_length

        # add address bytes
        _checksum += int(self.address[:2], 16)
        _checksum += int(self.address[2:], 16)

        # add record type byte
        _checksum += int(self.record_type, 16)

        # add data bytes
        for i in range(0, len(self.data), 2):
            _checksum += int(self.data[i:i + 2], 16)

        # add checksum byte
        _checksum += int(self.checksum, 16)

        # sum of all bytes' checksum = 00 (modulo 256)
        return _checksum & 0xFF == 0

    def _parse_record(self):
        if self.record_type == '00':
            # parse data record

            # handle data record starts without extended address record
            if self.segment_address == '':
                self.segment_address = '0000'

            # append lower 16 bits of 32 bits address from first data record
            if self.segment_data == '':
                self.segment_address += self.address
                self.lower_address = int(self.address, 16)

            # check next address
            if self.lower_address == int(self.address, 16):
                # accumulate the data to same segment
                self.segment_data += self.data
                self.lower_address += self.record_length
            else:
                raise NotImplementedError('TODO: Yet to be implemented')

        elif self.record_type == '01':
            # parse end of file record

            # store previous parsed data segment
            if self.segment_address != '':
                self.segments.append(
                    Segment(
                        address=self.segment_address,
                        data=self.segment_data
                    )
                )

            # re-initialize the segment data accumulation
            self.segment_address = ''
            self.segment_data = ''

            # mark end of record
            self.end_of_file_reached = True

        elif self.record_type == '02':
            # parse extended segment address record
            if self.record_length != 2:
                raise FileCorruptedError('Record length must be 2 bytes')

        elif self.record_type == '03':
            # parse start segment address record
            if self.record_length != 4:
                raise FileCorruptedError('Record length must be 4 bytes')

        elif self.record_type == '04':
            # parse extended linear address record
            if self.record_length != 2:
                raise FileCorruptedError('Record length must be 2 bytes')

            # store previous parsed data segment
            if self.segment_address != '':
                self.segments.append(
                    Segment(
                        address=self.segment_address,
                        data=self.segment_data
                    )
                )

            # re-initialize the segment data accumulation
            self.segment_address = self.data
            self.segment_data = ''

        elif self.record_type == '05':
            # parse start linear address record
            if self.record_length != 4:
                raise FileCorruptedError('Record length must be 4 bytes')

    def _add_segment_record(self):
        pass

    def _add_end_of_file_record(self):
        self.lines.append(f'{self.start_code}00000001FF')

    def parse(self) -> list[Segment]:
        with open(self.file_path) as hex_file:
            hex_data = hex_file.read()

            # read and parse records
            for record in hex_data.split(self.line_termination):
                try:
                    # check start code
                    index = record.find(self.start_code)
                    if index == -1:
                        raise FileCorruptedError('Start of a record not found')
                    index += 1

                    # fetch number of data bytes
                    self.record_length = int(record[index: index + 2], 16)
                    index += 2

                    # fetch address
                    self.address = record[index: index + 4]
                    index += 4

                    # fetch record type
                    self.record_type = record[index: index + 2]
                    index += 2

                    # fetch data
                    self.data = record[index: index + (self.record_length * 2)]
                    index += self.record_length * 2

                    # fetch checksum
                    self.checksum = record[index: index + 2]
                    index += 2

                    # verify checksum
                    if not self._verify_checksum():
                        raise FileCorruptedError('Record is corrupted')

                    # verify length
                    if index != len(record):
                        raise FileCorruptedError('Record contains extra bytes')

                    # verify and parse the fields
                    self._parse_record()

                    if self.end_of_file_reached:
                        break
                except IndexError:
                    FileCorruptedError('Record contains less bytes')
                except ValueError:
                    FileCorruptedError('Record contains unknown symbol')
        return self.segments

    def convert(self) -> list[str]:
        # parse and convert segments
        for segment in self.segments:
            print(segment)

        # add end of file record
        self._add_end_of_file_record()

        # write lines if file path is given
        if self.file_path:
            with open(self.file_path, 'w') as file:
                file.writelines(self.lines)

        return self.lines


if __name__ == '__main__':
    intel = IntelHex(
        file_path=r'sample_files\sample_hex_file.hex'
    )
    _segments = intel.parse()
    print(_segments)

    intel = IntelHex(
        file_path=r'sample_files\sample_hex_file_del.hex',
        segments=_segments
    )
    intel.convert()

    # intel = IntelHex(
    #     file_path=r'sample_files\sample_empty_hex_file.hex'
    # )
    # _segments = intel.parse()
    # print(_segments)
    #
    # intel = IntelHex(
    #     file_path=r'sample_files\sample_empty_hex_file_del.hex',
    #     segments=_segments
    # )
    # intel.convert()
