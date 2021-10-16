
import time


DEFAULT_TAG = "canpc"

DEBUG=True


def current_milli_time():
    return round(time.time() * 1000)

def logD(msg, tag=DEFAULT_TAG):
    if DEBUG:
        print("[%d] D (%s) %s" % (current_milli_time(), tag, msg))

def log(msg, tag=DEFAULT_TAG):
    if DEBUG:
        print("[%d] I (%s) %s" % (current_milli_time(), tag, msg))

def logE(msg, tag=DEFAULT_TAG):
    if DEBUG:
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