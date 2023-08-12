class Segment:
    def __init__(self, address: str, data: str):
        self.address = address
        self.data = data

    def __repr__(self):
        return f'Data at {self.address}: {self.data}'
