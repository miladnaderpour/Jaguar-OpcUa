class OpcUaPreRecordedMessage:
    Mid: int
    Title: str = ''
    FileName = ''

    def __init__(self, mid: int, title: str, filename: str):
        self.Mid = mid
        self.Title = title
        self.FileName = filename
