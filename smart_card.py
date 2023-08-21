from enum import IntEnum

from format import Format
from segment import Segment
from format import FileCorruptedError


class CommandStructure(IntEnum):
    CLA = 0,
    INS = 2,
    P1 = 4,
    P2 = 6,
    LE_OR_LC = 8,
    DATA = 10


class SmartCard(Format):
    COMMAND_IDENTIFIER = {
        '01': 'SET_HIGH_ADDRESS_COMMAND',
        '02': 'ERASE_COMMAND',
        '03': 'WRITE_COMMAND',
        '04': 'SET_START_ADDRESS_COMMAND'
    }

    # store max 16 bytes in a single command
    MAX_DATA_LENGTH: int = 32

    def __init__(self, line_termination: str = '\n', file_path: str = None, segments: list[Segment] = None):
        super(SmartCard, self).__init__(line_termination, file_path, segments)

        # command structure
        self.cla: str = '00'
        self.p1: str = ''
        self.p2: str = ''
        self.le_or_lc: str = ''
        self.data: str = ''
        self.data_length: int = 0

        # file information
        self.comment: str = '//'
        self.page_size: int = 128

        # segment structure
        self.segment_address: int = 0
        self.segment_data: str = ''
        self.lower_address: int = 0
        self.data_collected: int = 0
        self.start_address: str = ''

    def _parse(self, command: str):
        """
        Parse the fields of given command
        :param command: command to be parsed
        :return: None
        """
        # fetch 'p1' byte
        self.p1 = command[CommandStructure.P1: CommandStructure.P2]

        # fetch 'p2' byte
        self.p2 = command[CommandStructure.P2: CommandStructure.LE_OR_LC]

        # fetch 'le' or 'lc' byte
        self.le_or_lc = command[CommandStructure.LE_OR_LC: CommandStructure.DATA]
        self.data_length = int(self.le_or_lc, 16)

        # fetch data
        self.data = command[CommandStructure.DATA:]

        # verify length of data
        if self.data != '' and len(self.data) // 2 != int(self.le_or_lc, 16):
            raise FileCorruptedError('Invalid command: 0x{self.le_or_lc} byte of data expected')

    def _parse_set_high_address_command(self, command: str):
        """
        Parse the set high address command
        :param command: command to be parsed
        :return: None
        """
        # parse command
        self._parse(command)

        if self.data_length != 2:
            raise FileCorruptedError('Command length must be 2 bytes')

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

    def _parse_erase_command(self, command: str):
        """
        Parse the erase command
        :param command: command to be parsed
        :return: None
        """
        # parse command
        self._parse(command)

        if self.data_length != 2:
            raise FileCorruptedError('Command length must be 2 bytes')

        # do nothing

    def _parse_write_command(self, command: str):
        """
        Parse the write command
        :param command: command to be parsed
        :return: None
        """
        # parse command
        self._parse(command)

        address: str = self.p1 + self.p2
        _address: int = int(address, 16)

        # append lower 16 bits of 32 bits address from first data record
        if self.segment_data == '':
            self.lower_address = _address

        # check next address
        if _address + self.data_length == self.lower_address:
            # prepend the data to same segment
            self.segment_data = self.data + self.segment_data
            self.lower_address = _address
            self.data_collected += self.data_length

        elif self.lower_address + self.data_collected == _address:
            # append the data to same segment
            self.segment_data += self.data
            self.data_collected += self.data_length

        elif _address + self.data_length < self.lower_address:
            # TODO: holes are to be handled
            raise NotImplementedError('TODO: Yet to be implemented')

        elif self.lower_address + self.data_collected < _address:
            # TODO: holes are to be handled
            raise NotImplementedError('TODO: Yet to be implemented')

        else:
            raise FileCorruptedError('More than one data is stored on same address')

    def _parse_set_start_command(self, command: str):
        """
        Parse the set start command
        :param command: command to be parsed
        :return: None
        """
        # parse command
        self._parse(command)

        if self.data_length != 4:
            raise FileCorruptedError('Command length must be 4 bytes')

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

    def _end_of_file(self):
        """
        Reached the end of file
        :param None
        :return: None
        """
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

    def _compose_set_high_address_command(self, address: str):
        """
        Compose set high address command
        :param address: upper 16 bits of 32 bits address
        :return: None
        """
        # create the command
        _command = f'{self.cla} 01 00 00 02 {address}{self.line_termination}'

        # append the command
        self.lines.append(self.line_termination)
        self.lines.append(f'{self.comment} Set segment high address{self.line_termination}')
        self.lines.append(_command)

    def _compose_erase_command(self, length: str):
        # create the command
        _apdu = f'{self.cla} 02 {self.lower_address:04X} 02 {length}{self.line_termination}'

        # append the command
        self.lines.append(self.line_termination)
        self.lines.append(f'{self.comment} Erase segment{self.line_termination}')
        self.lines.append(_apdu)

    def _compose_write_command(self, data: str):
        _data_length = len(data) // 2

        # create the command
        _apdu = f'{self.cla} 03 {self.lower_address:04X} {_data_length:02X} {data}{self.line_termination}'
        self.lower_address += _data_length

        # append the command
        self.lines.append(_apdu)

    def _compose_set_start_command(self, address: str):
        """
        Compose set start command
        :param address: Start address
        :return: None
        """
        # create the command
        _command = f'{self.cla} 04 00 00 04 {address}{self.line_termination}'

        # append the command
        self.lines.append(self.line_termination)
        self.lines.append(f'{self.comment} Set start address{self.line_termination}')
        self.lines.append(_command)

    def _compose_segment(self, segment: Segment):
        if segment.data == '':
            # add start address command
            self._compose_set_start_command(f'{segment.address:04X}')
        else:
            address: int = int(segment.address, 16)
            self.lower_address = address & 0xFFFF
            address = address >> 16

            # add set high address command
            self._compose_set_high_address_command(f'{address:04X}')

            # add erase command
            self._compose_erase_command(f'{len(segment.data):04X}')

            self.lines.append(self.line_termination)
            self.lines.append(f'{self.comment} Write segment{self.line_termination}')

            # add write command of fixed length, followed by rest data
            i = 0
            _data = segment.data
            while i < len(_data):
                # add write command
                self._compose_write_command(_data[i:i + self.MAX_DATA_LENGTH])
                i += self.MAX_DATA_LENGTH

    def _append_pre_script(self):
        self.lines.append(f'.reset{self.line_termination}')

    def _append_post_script(self):
        self.lines.append(f'.reset{self.line_termination}')
        self.lines.append(f'.end{self.line_termination}')

    def parse(self) -> list[Segment]:
        with open(self.file_path) as hex_file:
            self.lines = hex_file.read().split(self.line_termination)

        # read and parse records
        for line in self.lines:
            try:
                # parse next line if blank line found
                if len(line) == 0:
                    continue

                # try to find comment
                comment_index = line.find(self.comment)
                if comment_index != -1:
                    # comment found in the line, removing it...
                    line = line[:comment_index]

                # remove blank space
                command = line.replace(' ', '')

                # parse next line if blank line found
                if len(command) == 0:
                    continue

                # check 'cla' byte
                cla_byte = command[CommandStructure.CLA:CommandStructure.INS]
                if cla_byte != self.cla:
                    raise FileCorruptedError('Class byte is invalid')

                # fetch record type
                ins_byte = command[CommandStructure.INS:CommandStructure.P1]

                # parse the command
                _parse_command = eval(f'self._parse_{self.COMMAND_IDENTIFIER[ins_byte].lower()}')
                _parse_command(command)
            except IndexError:
                FileCorruptedError('Command contains less bytes')
            except KeyError:
                FileCorruptedError('Command parsing not defined')
            except ValueError:
                FileCorruptedError('Command contains unknown symbol')

        # end of file reached
        self._end_of_file()

        return self.segments

    def compose(self) -> list[str]:
        # append pre-script content
        self._append_pre_script()

        # parse and convert segments
        for segment in self.segments:
            self._compose_segment(segment)

        # append post-script content
        self._append_post_script()

        # write lines if file path is given
        if self.file_path:
            with open(self.file_path, 'w') as file:
                file.writelines(self.lines)

        return self.lines


if __name__ == '__main__':
    smart_card = SmartCard(
        file_path=r'sample_files\sample_smart_card.txt',
    )
    _segments = smart_card.parse()
    print(_segments)

    smart_card = SmartCard(
        file_path=r'sample_files\del_sample_smart_card.txt',
        segments=_segments
    )
    smart_card.compose()
