import common


RECV_TYPE_UNKNOWN = 0
RECV_TYPE_CAN = 1
RECV_TYPE_ERR = 2

class CanDevice:



    def start(self, recv_callback):
        return common.ERR_NOT_SUPPORT

    def sendMask(self, mask):
        return common.ERR_NOT_SUPPORT

    def sendFilter(self, filter):
        return common.ERR_NOT_SUPPORT

    def send(self, canmsg):
        return common.ERR_NOT_SUPPORT

    def stop(self):
        return common.ERR_NOT_SUPPORT
    def sendBreak(self):
        return common.ERR_NOT_SUPPORT

