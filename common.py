

import time


ERR_NONE = 0
ERR_FAILED = -1
ERR_NOT_SUPPORT = -2
ERR_INVALID = -3
ERR_NO_DATA = -4
ERR_NOT_READY = -5
ERR_TIMEOUT = -6
ERR_EXCEPTION = -7
ERR_PENDING = -8

DEFAULT_TAG = "canpc"

DEBUG=True


def current_milli_time():
    return round(time.time() * 1000)