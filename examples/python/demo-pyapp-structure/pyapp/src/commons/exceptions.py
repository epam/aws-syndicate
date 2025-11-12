class ApplicationException(Exception):

    def __init__(self, code, content):
        self.code = code
        self.content = content

    def __str__(self):
        return f'{self.code}:{self.content}'
