

import os
import re
import sys
import copy
import json
import time
import random
import xml.dom.minidom

import requests
import pyqrcode
import traceback

from . import config
from .exception import WeChatBotError
from .storage import Store, Cache

import logging


UNKNOWN = 'UNKNOWN'
SUCCESS = '200'
SCANNED = '201'
BAD_REQUEST = '400'
TIMEOUT = '408'


class AssSession(requests.Session):

    def post(self, url, data=None, json=None, **kwargs):
        retry = config.MAX_RETRY
        while retry:
            try:
                return super(AssSession, self).post(url, data, json, **kwargs)
            except:
                pass
            retry -= 1

    def get(self, url, **kwargs):
        retry = config.MAX_RETRY
        while retry:
            try:
                return super(AssSession, self).post(url, **kwargs)
            except:
                pass
            retry -= 1


class WeChatBot(object):
    """"""

    def __init__(self, auto_reload=True):
        self.configure()
        self.store = Store()
        self.cache = Cache()
        self.session = AssSession()
        self.auto_reload = auto_reload
        self.alive = False
        self.log = logging.getLogger('assbot')

    def _get_default_conf(self):
        ret = {
            'qr': os.path.join(config.BASE_DIR, 'qr.png'),
            'tty': 1,
            'email': None,
        }
        for k, v in ret.items():
            setattr(self, k, v)

    def configure(self, **conf):
        self._get_default_conf()
        for k, v in conf.items():
            setattr(self, k, v)

    def _get_res(self, reg=r'.*', url='', text='', params=None, headers=None,
                 json_res=False):
        res = None
        if text:
            res = re.search(reg, text)
            res = res.groupdict() if res else {}
        elif url:
            headers = headers if headers else config.HEADERS
            r = self.session.get(url, params=params, headers=headers)
            if not r:
                res = {}
                self.log.error('Get Res Error, No Response')
            elif json_res:
                res = r.json()
            else:
                r.encoding = 'utf-8'
                res = re.search(reg, r.text)
                res = res.groupdict() if res else {}
        return res

    def _post_res(self, url='', data=None, content=None, headers=None):
        if url:
            default_headers = copy.copy(config.HEADERS)
            default_headers.update({
                'ContentType': 'application/json; charset=UTF-8',
            })
            headers = headers if headers else default_headers
            r = self.session.post(url, data=data, headers=headers)
            content = r.content.decode('utf-8', 'replace')

        try:
            res = json.loads(content)
        except Exception as e:
            res = {
                'Data': content,
                'BaseResponse': {
                    'Ret': -1004,
                    'ErrMsg': 'Json load err: %s' % e,
                },
            }
        return res

    def init_uuid(self):
        """"""
        url = '{}/jslogin'.format(config.ROOT_URL)
        params = {
            'appid': config.APP_ID,
            'fun': config.FUN,
        }
        reg = r'window.QRLogin.code = (?P<code>\d+); window.QRLogin.uuid = ' \
              r'"(?P<uuid>\S+?)";'
        uuid = self._get_res(reg, url, params=params).get('uuid')
        self.cache.set('uuid', uuid)
        return uuid

    def email_qr(self, file_path):
        """"""

    def email_info(self, info):
        """"""

    def gen_qr_code(self, file_path='', tty=None, scale=8, email=None):
        """"""
        url = '{}/l/{}'.format(config.ROOT_URL, self.cache.uuid)
        qr = pyqrcode.create(url)
        if tty:
            return self.log.debug('Please Scan QR\n' + qr.terminal(quiet_zone=tty))

        file_path = file_path if file_path else self.qr
        qr.png(file=file_path, scale=scale)

        if email and os.path.isfile(file_path):
            self.email_qr(file_path)

        return file_path

    def batch_get_contacts(self, user_list):
        """

        :param user_list:
        :return: {
        'Count': 1,
        'BaseResponse': {'Ret': 0, 'ErrMsg': ''},
        'ContactList': [
            {'Uin': 0,
             'UserName':
             '@@e01dfac872324e045e111fbcbade96799dabc3e38e3c9c17fdaaacc15ff24139'
             ...
             }
        ]
        ...
        }
        """
        url = '{}/webwxbatchgetcontact?type=ex&pass_ticket={}&r={}'.format(
            self.cache.ticket,
            self.cache.pass_ticket,
            int(time.time()),
        )
        data = {
            'BaseRequest': self.cache.base_request,
            'Count': len(user_list),
            'List': [
                {
                    'UserName': user.get('UserName', ''),
                    'EncryChatRoomId': ''
                }
                for user in user_list
            ]
        }
        res = self._post_res(url, data=json.dumps(data))
        return res

    def get_contacts(self):
        """"""
        url = '{}/webwxgetcontact?pass_ticket={}&skey={}&r={}'.format(
            self.cache.ticket,
            self.cache.pass_ticket,
            self.cache.skey,
            int(time.time()),
        )
        res = self._post_res(url, data=json.dumps({}))
        return res

    def contact_type(self, contact):
        """Contact type
            - 0: special account
            - 1: subscription account
            - 2: group
            - 3: friend
        """
        if contact.get('VerifyFlag', '') & 8 != 0:
            return 1
        if contact.get('UserName', '').startswith('@@'):
            return 2
        if contact.get('UserName').startswith('@'):
            return 3
        return 0

    def _get_group_list(self, member_list):
        return list(filter(
            lambda x: self.contact_type(x) == 2,
            member_list
        ))

    def _update_contact(self, user_list):
        for user in user_list:
            user_name = user.get('UserName')
            if not user_name:
                self.log.debug('Wrong User %s' % repr(user))
                continue
            user.update(ContactType=self.contact_type(user))
            self.store.update(user_name, user)

    def add_new_contact(self, user_list):
        """ Add new contact
        For example: groups not in contacts

        :param user_list: [{'UserName': '@....'}]
        """
        res = self.batch_get_contacts(user_list)
        contact_list = res.get('ContactList')
        ret = []
        for contact in contact_list:
            if self.contact_type(contact) == 2:
                member_list = contact.pop('MemberList')
                members = {}
                for member in member_list:
                    members[member.get('UserName')] = member
                contact['Members'] = members
            ret.append(contact)
        self._update_contact(ret)

    def _init_all_contacts(self):
        """"""
        contacts = self.get_contacts()
        member_list = contacts.get('MemberList')
        self._update_contact(member_list)

        group_list = self._get_group_list(member_list)
        if group_list:
            self.add_new_contact(group_list)

    def _set_base_request_info(self, node):
        """"""
        if node.nodeName == 'skey':
            self.cache.set('skey', node.childNodes[0].data)
        elif node.nodeName == 'wxsid':
            self.cache.set('wxsid', node.childNodes[0].data)
        elif node.nodeName == 'wxuin':
            self.cache.set('wxuin', node.childNodes[0].data)
        elif node.nodeName == 'pass_ticket':
            self.cache.set('pass_ticket', node.childNodes[0].data)
        base_request = {
            'Skey': self.cache.skey,
            'Sid': self.cache.wxsid,
            'Uin': self.cache.wxuin,
            'DeviceID': self.cache.pass_ticket,
        }
        self.cache.set('base_request', base_request)
        return base_request

    def _process_login(self, login_res):
        """"""
        reg = r'window.redirect_uri="(?P<redirect_uri>\S+)";'
        redirect_uri = self._get_res(reg, text=login_res).get('redirect_uri')

        r = self.session.get(
            redirect_uri, headers=config.HEADERS, allow_redirects=False
        )
        child_nodes = xml.dom.minidom.parseString(
            r.text
        ).documentElement.childNodes
        for node in child_nodes:
            if not node.childNodes:
                continue
            self._set_base_request_info(node)

        self.cache.set('ticket', redirect_uri[:redirect_uri.rfind('/')])
        self.cache.set('deviceid', 'e' + str(random.random())[2:17])
        for index_url, detail_url in config.BEAT_URL:
            file_url, sync_url = [
                'https://%s/cgi-bin/mmwebwx-bin' % url for url in detail_url
            ]
            if index_url in self.cache.ticket:
                self.cache.set('file_url', file_url)
                self.cache.set('sync_url', sync_url)
                break
        else:
            self.cache.file_url = self.cache.sync_url = self.cache.ticket
        return str(r.status_code)

    def _await_login(self):
        url = '{}/cgi-bin/mmwebwx-bin/login'.format(config.ROOT_URL)
        local_time = int(time.time())
        params = {
            'loginicon': True,
            'uuid': self.cache.uuid,
            'tip': 0,
            'r': local_time / 1579,
            '_': local_time,
        }
        r = self.session.get(url, params=params, headers=config.HEADERS)
        data = self._get_res(r'window.code=(?P<code>\d+)', text=r.text)
        status_code = data.get('code')
        if data and status_code == SUCCESS:
            self._process_login(r.text)
            return SUCCESS
        elif data:
            return status_code
        else:
            return BAD_REQUEST

    def request_ok(self, res):
        if not res:
            return True
        return res.get('BaseResponse', {}).get('Ret', -1) == 0

    def status_notify(self):
        url = '{}/webwxstatusnotify?lang=zh_CN&pass_ticket={}'.format(
            self.cache.ticket, self.cache.pass_ticket
        )
        data = {
            'BaseRequest': self.cache.base_request,
            "Code": 3,
            "FromUserName": self.cache.self.get('UserName'),
            "ToUserName": self.cache.self.get('UserName'),
            "ClientMsgId": int(time.time())
        }
        res = self._post_res(url, data=json.dumps(data))
        return self.request_ok(res)

    @staticmethod
    def _synckey_str(sync_key_dict):
        sync_key_list = [
            '{}_{}'.format(item.get('Key'), item.get('Val'))
            for item in sync_key_dict.get('List')
        ]
        return '|'.join(sync_key_list)

    def _update_sync_key(self, sync_key_dict):
        self.cache.set('sync_key', sync_key_dict)
        self.cache.set('sync_key_str', self._synckey_str(sync_key_dict))

    def _init_web(self):
        url = '{}/webwxinit?r={}'.format(self.cache.ticket, int(time.time()))
        data = {
            'BaseRequest': self.cache.base_request
        }
        res = self._post_res(url, data=json.dumps(data))
        self.cache.set('self', res.get('User'))  # self info
        self._update_sync_key(res.get('SyncKey'))
        return self.request_ok(res)

    def _pre_login(self):
        self.log.info('Init uuid')
        self.init_uuid()
        self.log.info('Gen QR Code')
        self.gen_qr_code(
            file_path=self.qr,
            tty=self.tty,
            email=self.email,
        )
        self.log.info('Waiting for Scan QR')

    def push_login(self):
        # cookies_dict = self.session.cookies.get_dict()
        # TODO:
        return False
        if not self.cache.load('.cookies'):
            return False

        # mmwebwx-bin/webwxpushloginurl?uin=1302760367
        url = '{}/cgi-bin/mmwebwx-bin/webwxpushloginurl?uin={}'.format(
            self.cache.ticket,
            self.cache.wxuin
        )
        res = self._get_res(url=url, json_res=True)
        request_ok = self.request_ok(res) and 'uuid' in res
        if request_ok:
            self.cache.set('uuid', res.get('uuid'))
        return request_ok

    def login(self):
        if self.auto_reload and self.push_login():
            self.email_info(' Push Login, Please Confirm login On Your Phone')
            self.log.info(' Push Login, Please Confirm login On Your Phone')
        else:
            self._pre_login()
        retry = config.MAX_RETRY
        while retry:
            login_status = self._await_login()
            if login_status == SUCCESS:
                self.log.info('Log in Success!')
                break
            elif login_status == SCANNED:
                self.log.debug('Please Confirm Login On Your Phone')
            elif login_status == TIMEOUT:
                time.sleep(20)
                self.log.debug(TIMEOUT + ' Time Out! Retrying %d' % retry)
                self._pre_login()
                retry -= 1
                self.log.debug('Retrying %d' % retry)
                if not retry:
                    self.log.error('Maximum Retries !!')
                    sys.exit()
        return self._init_web()

    def logout(self):
        url = '{}/webwxlogout'.format(self.cache.ticket)
        params = {
            'redirect': 1,
            'type': 1,
            'skey': self.cache.skey
        }
        res = self._get_res(reg='(?P<res>.*)', url=url, params=params)
        self.log.info('Log Out Initiative')
        return res

    def sync_check(self):
        url = '{}/synccheck'.format(self.cache.sync_url)
        params = {
            'r': int(time.time() * 1000),
            'skey': self.cache.skey,
            'sid': self.cache.wxsid,
            'uin': self.cache.wxuin,
            'deviceid': self.cache.deviceid,
            'synckey': self.cache.sync_key_str,
            '_': int(time.time() * 1000),
        }
        reg = r'window.synccheck={retcode:"(?P<retcode>\d+)",' \
              r'selector:"(?P<selector>\d+)"}'
        res = self._get_res(reg, url=url, params=params)
        return res.get('retcode', -1), res.get('selector', -1)

    def sync(self):
        url = '{}/webwxsync?sid={}&skey={}&pass_ticket={}'.format(
            self.cache.ticket, self.cache.wxsid, self.cache.skey,
            self.cache.pass_ticket
        )
        data = {
            'BaseRequest': self.cache.base_request,
            'SyncKey': self.cache.sync_key,
            'rr': ~int(time.time()),
        }
        res = self._post_res(url=url, data=json.dumps(data))
        if not self.request_ok(res):
            return {}

        self._update_sync_key(res.get('SyncCheckKey'))
        return res

    def handle(self):
        """"""

    def handle_msg(self, msg):
        """
        :param msg:
        :return:
        """
        msg_list = msg.get('AddMsgList')
        if not msg_list:
            return {}
        ret = list()
        for msg in msg_list:
            from_user_name = msg['FromUserName']
            if not self.store.get(from_user_name):
                self.add_new_contact([{'UserName': from_user_name}])
            if from_user_name.startswith('@@'):
                # {'Content':
                # '@75c2dc6b639c5a00068791bbbcbad88b7d1797eaa3d5038920db5d802146b30a:<br/>BB'}
                reg = r'(?P<user_name>@\w+)(?:\:\<br\/\>)(?P<content>.*)'
                res = re.search(reg, msg.get('Content', ''))
                res_dict = res.groupdict() if res else {
                    'content': msg.get('Content')}
                msg['FromUserName'], msg['Content'] = res_dict.get(
                    'user_name'), res_dict.get('content')
                from_group = copy.deepcopy(
                    self.store.get(from_user_name)) or {}
                members = from_group.pop('Members', {})
                msg['FromGroup'] = from_group
                msg['FromUser'] = copy.deepcopy(
                    members.get(msg['FromUserName'])) or {}
            else:
                msg['FromUser'] = self.store.get(msg['FromUserName'])
            ret.append(msg)
        return ret

    def receive_msg(self, msg):
        try:
            msgs = self.handle_msg(msg)
        except:
            self.log.error('Handle Msg Error:\n %s' % traceback.format_exc())
        else:
            for msg in msgs:
                self.store.msgs.put(msg)

    def _proc_msg(self):
        retry = config.MAX_RETRY
        while retry:
            sync_time = time.time()
            retcode, selector = self.sync_check()
            self.alive = True
            # self.log.info('alive')
            if retcode == '0':
                res = self.sync()
                if not res or selector == '0':
                    time.sleep(1)
                    continue
                if selector == '2':  # New msg
                    self.receive_msg(res)
            elif retcode in {'1100', '1101'}:
                retry -= 1
                self.log.debug('Log out, Retrying')
                if not retry:
                    self.log.info('Log out')
                    self.alive = False
                    break
            else:
                self.log.debug(
                    'Unknown Code %s, Retrying' % repr([retcode, selector]))
                retry -= 1
                if not retry:
                    self.alive = False
                    self.log.info(
                        'Unkonwn Code %s, Log out' % repr([retcode, selector]))
                    break
            try:
                self.handle()  # Run every time sync
            except:
                self.log.error(traceback.format_exc())

            duration = time.time() - sync_time
            if duration <= 20:
                time.sleep(1)

    def run(self):
        self.login()
        self.status_notify()
        self.log.info('Hello %s' % self.cache.self.get('NickName', ''))
        self.cache.dump('.cookies')
        self._init_all_contacts()
        self._proc_msg()
        self.alive = False

    @staticmethod
    def gen_msgid():
        msg_id = str(int(time.time() * 1e3)) + \
                 str(random.random())[:5].replace('.', '')
        return msg_id

    def _send_msg(self, msg_content, to_user_name):
        url = '{}/webwxsendmsg?pass_ticket={}'.format(
            self.cache.ticket, self.cache.pass_ticket
        )
        msg_id = self.gen_msgid()
        data = {
            'BaseRequest': self.cache.base_request,
            'Msg': {
                "Type": 1,
                "Content": msg_content,
                "FromUserName": self.cache.self['UserName'],
                "ToUserName": to_user_name,
                "LocalID": msg_id,
                "ClientMsgId": msg_id
            }
        }
        data = json.dumps(data, ensure_ascii=False).encode('utf8')
        res = self._post_res(url=url, data=data)
        return self.request_ok(res)

    def send_msg(self, msg_content, **kwargs):
        user_list = self.store.select(**kwargs)
        ret = list()
        for user in user_list:
            ret.append(int(self._send_msg(msg_content, user['UserName'])))
        return ret
