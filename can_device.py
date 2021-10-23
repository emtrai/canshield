# Author: anhnh @ 2021

import common


RECV_TYPE_UNKNOWN = 0
RECV_TYPE_CAN = 1
RECV_TYPE_ERR = 2

class CanDevice:

    def name(self):
        return "unknown"

    def isReady(self):
        return False

    def start(self, recv_callback = None, rec_can_callback = None):
        return common.ERR_NOT_SUPPORT

    def sendMask(self, mask):
        return common.ERR_NOT_SUPPORT

    def sendFilter(self, filter):
        return common.ERR_NOT_SUPPORT

    def filter(self, filter):
        return common.ERR_NOT_SUPPORT

    def send(self, canmsg):
        return common.ERR_NOT_SUPPORT

    def stop(self):
        return common.ERR_NOT_SUPPORT
    def sendBreak(self):
        return common.ERR_NOT_SUPPORT

