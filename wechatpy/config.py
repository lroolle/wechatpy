import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_QR = 'qr.png'
DEFAULT_QR_PATH = os.path.join(BASE_DIR, DEFAULT_QR)
MAX_RETRY = 3

USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) ' \
             'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 ' \
             'Safari/537.36'
HEADERS = {'User-Agent': USER_AGENT}

APP_ID = 'wx782c26e4c19acffb'
FUN = 'new'

ROOT_URL = 'https://login.weixin.qq.com'

BEAT_URL = (
    ('wx2.qq.com', ('file.wx2.qq.com', 'webpush.wx2.qq.com')),
    ('wx8.qq.com', ('file.wx8.qq.com', 'webpush.wx8.qq.com')),
    ('qq.com', ('file.wx.qq.com', 'webpush.wx.qq.com')),
    ('web2.wechat.com', ('file.web2.wechat.com', 'webpush.web2.wechat.com')),
    ('wechat.com', ('file.web.wechat.com', 'webpush.web.wechat.com'))
)
