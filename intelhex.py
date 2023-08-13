from enum import IntEnum

from format import Format
from format import FileCorruptedError
from segment import Segment


class RecordStructure(IntEnum):
    START_CODE = 0,
    RECORD_LENGTH = 1,
    ADDRESS = 3,
    RECORD_TYPE = 7,
    DATA = 9,
    CHECKSUM = -2


class IntelHex(Format):
    RECORD_IDENTIFIER = {
        '00': 'DATA_RECORD',
        '01': 'END_OF_FILE_RECORD',
        '02': 'EXTENDED_SEGMENT_ADDRESS_RECORD',
        '03': 'START_SEGMENT_ADDRESS_RECORD',
        '04': 'EXTENDED_LINEAR_ADDRESS_RECORD',
        '05': 'START_LINEAR_ADDRESS_RECORD'
    }

    def __init__(self, line_termination: str = '\n', file_path: str = None, segments: list[Segment] = None):
        super(IntelHex, self).__init__(line_termination, file_path, segments)

        # record structure
        self.start_code: str = ':'
        self.record_length: int = 0
        self.address: str = ''
        self.data: str = ''
        self.checksum: str = ''

        # segment structure
        self.segment_address: int = 0
        self.segment_data: str = ''
        self.lower_address: int = 0
        self.data_collected: int = 0
        self.start_address: str = ''

        # file state
        self.end_of_file_reached: bool = False

    @staticmethod
    def _verify_checksum(record: str) -> bool:
        """
        Verify the checksum of a given record.
        Two's complement of the least significant byte (LSB) of the sum of
        all decoded byte values in the record preceding the checksum.
        :param record: record to be verified
        :return: True is checksum verified, False otherwise
        """
        # initialize checksum
        _checksum: int = 0

        # add record bytes
        for i in range(1, len(record), 2):
            _checksum += int(record[i:i + 2], 16)

        # sum of all bytes' checksum = 00 (modulo 256)
        return _checksum & 0xFF == 0

    def _parse(self, record: str):
        """
        Parse the fields of given record
        :param record: record to be parsed
        :return: None
        """
        # fetch number of data bytes
        self.record_length = int(record[RecordStructure.RECORD_LENGTH: RecordStructure.ADDRESS], 16)

        # fetch address
        self.address = record[RecordStructure.ADDRESS: RecordStructure.RECORD_TYPE]

        # fetch data
        self.data = record[RecordStructure.DATA: RecordStructure.CHECKSUM]

        # fetch checksum
        self.checksum = record[RecordStructure.CHECKSUM:]

        # verify length
        if len(self.data) // 2 != self.record_length:
            raise FileCorruptedError('Record contains extra bytes')

        # verify checksum
        if not self._verify_checksum(record):
            raise FileCorruptedError('Checksum mismatch. Record is corrupted')

    def _parse_data_record(self, record: str):
        """
        Parse the data record
        :param record: record to be parsed
        :return: None
        """
        # parse record fields
        self._parse(record)

        record_address: int = int(self.address, 16)

        # append lower 16 bits of 32 bits address from first data record
        if self.segment_data == '':
            self.lower_address = record_address

        # check next address
        if record_address + self.record_length == self.lower_address:
            # prepend the data to same segment
            self.segment_data = self.data + self.segment_data
            self.lower_address = record_address
            self.data_collected += self.record_length

        elif self.lower_address + self.data_collected == record_address:
            # append the data to same segment
            self.segment_data += self.data
            self.data_collected += self.record_length

        elif record_address + self.record_length < self.lower_address:
            # TODO: holes are to be handled
            raise NotImplementedError('TODO: Yet to be implemented')

        elif self.lower_address + self.data_collected < record_address:
            # TODO: holes are to be handled
            raise NotImplementedError('TODO: Yet to be implemented')

        else:
            raise FileCorruptedError('More than one data is stored on same address')

    def _parse_end_of_file_record(self, record: str):
        """
        Parse the end of file record
        :param record: record to be parsed
        :return: None
        """
        # parse record fields
        self._parse(record)

        # store previous parsed data segment
        if self.segment_data != '':
            self.segments.append(
                Segment(
                    address=f'{self.segment_address + self.lower_address:08X}',
                    data=self.segment_data
                )
            )

        # re-initialize the segment data accumulation
        self.segment_address = 0
        self.segment_data = ''

        # mark end of record
        self.end_of_file_reached = True

    def _parse_extended_segment_address_record(self, record: str):
        """
        Parse the extended segment address record
        :param record: record to be parsed
        :return: None
        """
        # parse record fields
        self._parse(record)

        if self.record_length != 2:
            raise FileCorruptedError('Record length must be 2 bytes')

        # store previous parsed data segment
        if self.segment_data != '':
            self.segments.append(
                Segment(
                    address=f'{self.segment_address + self.lower_address:08X}',
                    data=self.segment_data
                )
            )

        # re-initialize the segment data accumulation
        self.segment_address = int(self.data, 16) << 8
        self.segment_data = ''

    def _parse_start_segment_address_record(self, record: str):
        """
        Parse the start segment address record
        :param record: record to be parsed
        :return: None
        """
        # parse record fields
        self._parse(record)

        if self.record_length != 4:
            raise FileCorruptedError('Record length must be 4 bytes')

        if self.start_address != '':
            raise FileCorruptedError('More than one start address found')

        self.start_address = self.data

        # make empty data segment to hold start address
        self.segments.append(
            Segment(
                address=self.start_address,
                data=''
            )
        )

    def _parse_extended_linear_address_record(self, record: str):
        """
        Parse the extended linear address record
        :param record: record to be parsed
        :return: None
        """
        # parse record fields
        self._parse(record)

        if self.record_length != 2:
            raise FileCorruptedError('Record length must be 2 bytes')

        # store previous parsed data segment
        if self.segment_data != '':
            self.segments.append(
                Segment(
                    address=f'{self.segment_address + self.lower_address:08X}',
                    data=self.segment_data
                )
            )

        # re-initialize the segment data accumulation
        self.segment_address = int(self.data, 16) << 16
        self.segment_data = ''

    def _parse_start_linear_address_record(self, record: str):
        """
        Parse the start linear address record
        :param record: record to be parsed
        :return: None
        """
        # parse record fields
        self._parse(record)

        if self.record_length != 4:
            raise FileCorruptedError('Record length must be 4 bytes')

        if self.start_address != '':
            raise FileCorruptedError('More than one start address found')

        self.start_address = self.data

        # make empty data segment to hold start address
        self.segments.append(
            Segment(
                address=self.start_address,
                data=''
            )
        )

    def _add_segment_record(self):
        pass

    def _compose_end_of_file_record(self):
        self.lines.append(f'{self.start_code}00000001FF')

    def parse(self) -> list[Segment]:
        with open(self.file_path) as hex_file:
            self.lines = hex_file.read().split(self.line_termination)

        # read and parse records
        for record in self.lines:
            try:
                # check start code
                start_code = record[RecordStructure.START_CODE:RecordStructure.RECORD_LENGTH]
                if start_code != self.start_code:
                    raise FileCorruptedError('Start of a record not found')

                # fetch record type
                record_type = record[RecordStructure.RECORD_TYPE:RecordStructure.DATA]

                # parse the record
                _parse_record = eval(f'self._parse_{self.RECORD_IDENTIFIER[record_type].lower()}')
                _parse_record(record)

                if self.end_of_file_reached:
                    break
            except IndexError:
                FileCorruptedError('Record contains less bytes')
            except KeyError:
                FileCorruptedError('Record parsing not defined')
            except ValueError:
                FileCorruptedError('Record contains unknown symbol')
        return self.segments

    def compose(self) -> list[str]:
        # parse and convert segments
        for segment in self.segments:
            print(f'Compose Segment {segment}')

        # add end of file record
        self._compose_end_of_file_record()

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
    intel.compose()

    intel = IntelHex(
        file_path=r'sample_files\sample_hex_file_2.hex'
    )
    _segments = intel.parse()
    print(_segments)

    intel = IntelHex(
        file_path=r'sample_files\sample_hex_file_2_del.hex',
        segments=_segments
    )
    intel.compose()

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
