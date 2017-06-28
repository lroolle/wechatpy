

def get_msgdict(msg, users):
    ret = {
        'Content': msg,
        'ToUserList': [{'NickName': user} for user in users]
    }
    return ret


def get_suser(user):
    """ str user"""
    suser = ''.join(['@{}:{}'.format(*item) for item in user.items()])
    return suser