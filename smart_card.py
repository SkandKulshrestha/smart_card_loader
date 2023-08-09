from segment import Segment


class SmartCard:
    def __init__(self):
        self.CLA = '00'
        self.lines = []
        self.comment = '//'
        self.termination = '\n'

    def set_address(self, high_address: str):
        _apdu = f'{self.CLA} 01 00 00 02 {high_address.zfill(4)}{self.termination}'
        self.lines.append(self.termination)
        self.lines.append(f'{self.comment} Set segment high address{self.termination}')
        self.lines.append(_apdu)

    def erase(self, low_address: str, length: str):
        _apdu = f'{self.CLA} 02 00 00 04 {low_address.zfill(4)} {length.zfill(4)}{self.termination}'
        self.lines.append(self.termination)
        self.lines.append(f'{self.comment} Erase segment{self.termination}')
        self.lines.append(_apdu)

    def write(self, low_address: str, data: str, length: str):
        i = 0
        data_length = int(length, 16)
        self.lines.append(self.termination)
        self.lines.append(f'{self.comment} Write segment{self.termination}')

        # writing 128 byte
        while data_length > 128:
            _data = data[i:i + 256]
            _apdu = f'{self.CLA} 03 00 00 84 {low_address.zfill(4)} {_data}{self.termination}'
            self.lines.append(_apdu)
            data_length -= 128
            i += 256

        _data = data[i:]
        _apdu = f'{self.CLA} 03 00 00 {data_length + 4:02X} {low_address.zfill(4)} {_data}{self.termination}'
        self.lines.append(_apdu)

    def convert(self, segments: list[Segment], file_path: str):
        for segment in segments:
            self.set_address(segment.address[:4])
            self.erase(segment.address[4:], hex(len(segment.data) // 2)[2:])
            self.write(segment.address[4:], segment.data, hex(len(segment.data) // 2)[2:])
        print(self.lines)
        with open(file_path, 'w') as file:
            file.writelines(self.lines)


if __name__ == '__main__':
    smart_card = SmartCard()
    smart_card.convert([
        Segment(address='00000000', data='0102'),
        Segment(address='10000000', data='030405')
    ], file_path='loader.txt')
