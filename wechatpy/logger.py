from __future__ import unicode_literals
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import os
import logging

from django.conf import settings


def getLogger(name):
    log = logging.getLogger(name)
    log.setLevel(logging.DEBUG)

    file = os.path.join(settings.BASE_DIR, 'logs', 'assbot.log')
    fh = logging.FileHandler(file)
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter(
            '[%(levelname)s] %(asctime)s %(name)s:%(lineno)-4s: %(message)s'
    ))

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(logging.Formatter(
        '[%(levelname)s] %(asctime)s %(name)s:%(lineno)-4s: %(message)s'
    ))
    log.addHandler(fh)
    log.addHandler(ch)

    return log
