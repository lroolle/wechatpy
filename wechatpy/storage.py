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
        with open(file, 'wb') as fp:
            pickle.dump(self.all(), fp)

    def load(self, file):
        try:
            with open(file, 'rb') as fp:
                obj = pickle.load(fp)
            for item in obj:
                self.set(*item)
        except Exception as e:
            return False
        return True


class Store(object):
    """
    * 微信账号:
        - 自己
        - 好友
        - 群聊
        - 公众号
    * 微信消息:
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
        """ Select """
        ret = list()
        limit = kwargs.get('limit', 1)
        for l, (k, v) in zip(itertools.count(), kwargs.items()):
            for user_name, user in self.cache.items():
                if user.get(k) == v:
                    ret.append(user)
                if limit is not None and l == limit:
                    return ret
        return ret
