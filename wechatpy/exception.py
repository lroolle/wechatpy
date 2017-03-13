

class WeChatBotError(BaseException):

    def __init__(self, message='WeChatBot Error'):
        self.message = message