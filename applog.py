

DEFAULT_TAG = "canpc"

DEBUG=True

def logD(msg, tag=DEFAULT_TAG):
    if DEBUG:
        print("D (%s) %s" % (tag, msg))

def log(msg, tag=DEFAULT_TAG):
    if DEBUG:
        print("I (%s) %s" % (tag, msg))

def logE(msg, tag=DEFAULT_TAG):
    if DEBUG:
        print("E (%s) %s" % (tag, msg))


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