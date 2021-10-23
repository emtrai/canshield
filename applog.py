# Author: anhnh @ 2021

DEFAULT_TAG = "canpc"

DEBUG=True
DEBUG=False

from common import current_milli_time

def logD(msg, tag=DEFAULT_TAG):
    if DEBUG:
        print("[%d] D (%s) %s" % (current_milli_time(), tag, msg))

def log(msg, tag=DEFAULT_TAG):
    print("[%d] I (%s) %s" % (current_milli_time(), tag, msg))

def logE(msg, tag=DEFAULT_TAG):
    print("[%d] E (%s) %s" % (current_milli_time(), tag, msg))


class Log:
    tag = DEFAULT_TAG
    def __init__(self, tag=DEFAULT_TAG):
        self.tag = tag

    def d(self, msg):
        logD(msg, self.tag)

    def i(self, msg):
        log(msg, self.tag)

    def e(self, msg):
        logE(msg, self.tag)

    def dumpBytes(self, msg, data):
        if DEBUG:
            self.printBytes(msg, data)

    def printBytes(self, msg, data):
        if (data is not None and len(data) > 0):
            msg += "(%d) 0x" % len(data)
            for i in data:
                msg += "%02x" % i
        else:
            msg += "no data"
        self.i(msg)