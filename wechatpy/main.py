""" Bot Main
  run() to run AssBot
"""

import os
import copy
import json
import queue
import random
import time
import threading

from django.conf import settings
from django.core.cache import cache

from .core import WeChatBot
from .listeners import LISTENERS
from .utils import get_suser
from minions.mailer.tasks import email_task


MAX_SEND_FREQUENCY = 10


class AssBot(WeChatBot):
    def email_qr(self, file):
        mail_html = '''<html><body>
        <h1> <span style="color:red">WARNING:</span>
        <code>AssBot 需要扫码登陆!</code></h1>
        <hr>
        <p><img src="cid:qr"></p>
        </body></html>'''
        email_to = list(dict(settings.ADMINS).values())
        subject = '请为 AssBot 扫码！'
        email_from = settings.DEFAULT_FROM_EMAIL
        message_html = mail_html
        email_task.delay(
            email_to=email_to,
            subject=subject,
            email_from=email_from,
            message_html=message_html,
            attachment_path=file,
            extra_attachment_header=('Content-ID', '<qr>'),
        )

    def email_info(self, info):
        mail_html = '''<html><body>
        <h1 style="color:red">WARNING</h1><br>
        <h2><code>INFO: </code>{} <br></h2>
        </body></html>'''.format(info)
        email_to = settings.GEEBOT_ADMIN
        subject = 'AssBot 通知！'
        email_from = settings.DEFAULT_FROM_EMAIL
        message_html = mail_html
        email_task.delay(
            email_to=email_to,
            subject=subject,
            email_from=email_from,
            message_html=message_html,
        )

    def xiaobing(self, msg):
        return msg

    def sender(self, msg):
        user, content = msg['ToUser'], msg['Content']
        suser = get_suser(user)
        sent = self.send_msg(msg['Content'], **user)
        if not all(sent):

            self.log.error('Sent Error, %s, %s' % (suser, msg['Content']))
        else:
            self.log.info('Sent Success %s, %s' % (suser, msg['Content']))

    def mq_forwarder(self, ch, method, properties, body):
        while not self.alive:
            self.log.info('%s listener waiting for consuming' % queue)
            time.sleep(10)

        self.log.info('Received %r' % body)
        msg = json.loads(str(body, 'utf-8'))

        for user in msg['ToUserList']:
            _msg = copy.deepcopy(msg)
            _msg['ToUser'] = user
            suser = get_suser(user)
            delay = cache.ttl(suser)
            if delay:
                self.log.info('Waiting %d, %s %s' % (delay, suser, _msg['Content']))
                time.sleep(delay)
            t = threading.Thread(target=self.sender, args=(_msg, ))
            t.start()
            cache.set(suser, 1, timeout=MAX_SEND_FREQUENCY)

    def receiver(self):
        while not self.store.msgs.empty():
            msg = self.store.msgs.get()
            if msg.get('Content'):
                self.log.info(' Received Msg: %s ' % msg.get('Content'))

    def handle(self):
        self.receiver()


def run():
    assbot = AssBot()
    qr = os.path.join(settings.QR_DIR, 'qr.png')
    assbot.configure(qr=qr, tty=False, email=True)
    for listener in LISTENERS:
        forwarder = threading.Thread(
            target=listener, args=(assbot.mq_forwarder, ))
        forwarder.setDaemon(True)
        forwarder.start()

    try:
        assbot.run()
    except (KeyboardInterrupt, SystemExit):
        if not assbot.store.msgs.empty():
            assbot.log.error('MsgQueue Not Empty: ')
            while not assbot.store.msgs.empty():
                msg = assbot.store.msgs.get()
                assbot.log.error('  Msg: %s' % str(msg))
        assbot.alive = False

