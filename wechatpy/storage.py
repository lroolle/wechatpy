""""""


import pickle
import itertools
from queue import Queue


class Cache(dict):
    """"""
    def __getattr__(self, item):
        return self.get(item)

    def __setattr__(self, key, value):
        self[key] = value

    def set(self, key, value):
        self[key] = value

    def all(self):
        return list(self.items())

    def dump(self, file):
        """"""
        pickle.dump(self.all(), file)

    def load(self, file):
        obj = pickle.load(file)
        for k, v in obj:
            self.set(k, v)


class Store(object):
    """
    * 微信账号:
        - 自己
        - 好友
        - 群聊
        - 公众号

    * 微信消息:
        -
        -
        -

    """

    def __init__(self, backend=None):
        self.cache = backend() if backend else Cache()
        self.msgs = Queue()

    def update(self, k, v):
        self.cache.set(k, v)

    def get(self, key):
        return self.cache.get(key)

    def select(self, **kwargs):
        """"""

    def has_user(self, user_name):
        return self.cache.haskey()

    def get_friend(self, user_name='', nick_name=''):
        pass

    def get_group(self, user_name, nick_name):
        pass

    def get_subscription_account(self, user_name, nick_name):
        pass

