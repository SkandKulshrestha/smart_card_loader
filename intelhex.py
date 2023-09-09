from enum import IntEnum
from typing import List

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


# TODO: handling of extended/linear record based on intel hex

class IntelHex(Format):
    RECORD_IDENTIFIER = {
        '00': 'DATA_RECORD',
        '01': 'END_OF_FILE_RECORD',
        '02': 'EXTENDED_SEGMENT_ADDRESS_RECORD',
        '03': 'START_SEGMENT_ADDRESS_RECORD',
        '04': 'EXTENDED_LINEAR_ADDRESS_RECORD',
        '05': 'START_LINEAR_ADDRESS_RECORD'
    }

    # store max 16 bytes in a single record
    MAX_DATA_LENGTH: int = 16 * 2  # 2 characters for each byte

    def __init__(self, line_termination: str = '\n'):
        super(IntelHex, self).__init__(line_termination)

        # record identifier
        self.record_identifier = {v: k for k, v in self.RECORD_IDENTIFIER.items()}

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
        self.end_of_file_line_number: int = 0

    def _update_segment_info(self, segment_address: int = 0, segment_data: str = '',
                             lower_address: int = 0, data_collected: int = 0):
        self.segment_address = segment_address
        self.segment_data = segment_data
        self.lower_address = lower_address
        self.data_collected = data_collected

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

        # reset the segment data info
        self._update_segment_info()

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

        # update the segment data info
        self._update_segment_info(segment_address=int(self.data, 16) << 8)

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
            if self.start_address == self.data:
                return

            raise FileCorruptedError('More than one start address found')

        self.start_address = (int(self.data[:4], 16) << 4) + int(self.data[4:], 16)

        # make empty data segment to hold start address
        self.segments.append(
            Segment(
                address=f'{self.start_address:08X}',
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

        # update the segment data info
        self._update_segment_info(segment_address=int(self.data, 16) << 16)

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
            if self.start_address == self.data:
                return

            raise FileCorruptedError('More than one start address found')

        self.start_address = self.data

        # make empty data segment to hold start address
        self.segments.append(
            Segment(
                address=self.start_address,
                data=''
            )
        )

    @staticmethod
    def _calculate_checksum(record: str) -> str:
        # initialize checksum
        _checksum: int = 0

        # calculate checksum of record bytes
        for i in range(0, len(record), 2):
            _checksum += int(record[i:i + 2], 16)

        _checksum = _checksum & 0xFF

        # calculate two's complement (modulo 256)
        _checksum = ((_checksum ^ 0xFF) + 1) & 0xFF

        return f'{_checksum:02X}'

    def _compose_data_record(self, data: str):
        _data_length = len(data) // 2

        # create the record except checksum
        _record_bytes = f'{_data_length:02X}{self.lower_address:04X}{self.record_identifier["DATA_RECORD"]}{data}'
        self.lower_address += _data_length

        # calculate the checksum
        _checksum_byte = self._calculate_checksum(_record_bytes)

        # append the record
        self.lines.append(f'{self.start_code}{_record_bytes}{_checksum_byte}{self.line_termination}')

    def _compose_end_of_file_record(self):
        # create the record except checksum
        _record_bytes = f'000000{self.record_identifier["END_OF_FILE_RECORD"]}'

        # calculate the checksum
        _checksum_byte = self._calculate_checksum(_record_bytes)

        # append the record
        self.lines.append(f'{self.start_code}{_record_bytes}{_checksum_byte}')

    def _compose_extended_segment_address_record(self, address: str):
        # create the record except checksum
        _record_bytes = f'020000{self.record_identifier["EXTENDED_SEGMENT_ADDRESS_RECORD"]}{address}'

        # calculate the checksum
        _checksum_byte = self._calculate_checksum(_record_bytes)

        # append the record
        self.lines.append(f'{self.start_code}{_record_bytes}{_checksum_byte}{self.line_termination}')

    def _compose_start_segment_address_record(self, address: str):
        # create the record except checksum
        _record_bytes = f'040000{self.record_identifier["START_SEGMENT_ADDRESS_RECORD"]}{address}'

        # calculate the checksum
        _checksum_byte = self._calculate_checksum(_record_bytes)

        # append the record
        self.lines.append(f'{self.start_code}{_record_bytes}{_checksum_byte}{self.line_termination}')

    def _compose_extended_linear_address_record(self, address: str):
        # create the record except checksum
        _record_bytes = f'020000{self.record_identifier["EXTENDED_LINEAR_ADDRESS_RECORD"]}{address}'

        # calculate the checksum
        _checksum_byte = self._calculate_checksum(_record_bytes)

        # append the record
        self.lines.append(f'{self.start_code}{_record_bytes}{_checksum_byte}{self.line_termination}')

    def _compose_start_linear_address_record(self, address: str):
        # create the record except checksum
        _record_bytes = f'040000{self.record_identifier["START_LINEAR_ADDRESS_RECORD"]}{address}'

        # calculate the checksum
        _checksum_byte = self._calculate_checksum(_record_bytes)

        # append the record
        self.lines.append(f'{self.start_code}{_record_bytes}{_checksum_byte}{self.line_termination}')

    def _compose_segment(self, segment: Segment):
        if segment.data == '':
            # add start linear address record
            self._compose_start_linear_address_record(segment.address)
        else:
            address: int = int(segment.address, 16)
            self.lower_address = address & 0xFFFF
            address = address >> 16

            # add extended linear address record
            self._compose_extended_linear_address_record(f'{address:04X}')

            # add data records of fixed length, followed by rest data
            i = 0
            _data = segment.data
            while i < len(_data):
                # add data record
                self._compose_data_record(_data[i:i + self.MAX_DATA_LENGTH])
                i += self.MAX_DATA_LENGTH

    def parse(self, file_path: str) -> List[Segment]:
        if not self.parsed:
            # parse the file
            with open(file_path) as hex_file:
                lines = hex_file.read().split(self.line_termination)

            # read and parse records
            for record in lines:
                if record:
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
                    except IndexError:
                        FileCorruptedError('Record contains less bytes')
                    except KeyError:
                        FileCorruptedError('Record parsing not defined')
                    except ValueError:
                        FileCorruptedError('Record contains unknown symbol')

                # save the line
                self.lines.append(f'{record}{self.line_termination}')

                # verify end of record reached
                if self.end_of_file_reached:
                    break

            # hex file must contain end of file record
            if not self.end_of_file_reached:
                FileCorruptedError('File does not contain end of file record')

            # mark file as parsed
            self.parsed = True

        return self.segments

    def compose(self, file_path: str = '', segments: List[Segment] = None) -> List[str]:
        if not self.composed:
            if self.parsed and segments is not None:
                # remove end of file record, i.e., only last line
                self.lines = self.lines[:-1]
                self.segments.extend(segments)

            # compose the file content
            if segments is not None:
                try:
                    # parse and convert segments
                    for segment in segments:
                        self._compose_segment(segment)

                    # add end of file record
                    self._compose_end_of_file_record()
                except KeyError:
                    FileCorruptedError('Record identifier does not exist')

            # mark file as composed
            self.composed = True

        # write lines if file path is given
        if file_path:
            with open(file_path, 'w') as file:
                file.writelines(self.lines)

        return self.lines


if __name__ == '__main__':
    intel = IntelHex()
    _segments = intel.parse(file_path=r'sample_files\sample_hex_file.hex')
    print(_segments)

    intel = IntelHex()
    intel.compose(
        file_path=r'sample_files\del_sample_hex_file.hex',
        segments=_segments
    )

    intel = IntelHex()
    _segments = intel.parse(file_path=r'sample_files\sample_hex_file_2.hex')
    print(_segments)
    intel.compose(file_path=r'sample_files\del_sample_hex_file_2.hex')

    intel = IntelHex()
    _segments = intel.parse(file_path=r'sample_files\sample_empty_hex_file.hex')
    print(_segments)
    intel.compose(file_path=r'sample_files\del_sample_empty_hex_file.hex')
