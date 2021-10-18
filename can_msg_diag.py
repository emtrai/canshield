from applog import Log
import common
from can_msg import CanMsg
import can_msg_fac


LOG_TAG = "candiag"

log = Log(LOG_TAG)


class CanMsgDiag(CanMsg):
    def __init__(self, id = 0, type = can_msg_fac.TYPE_STANDARD, callback=None):
        super(CanMsgDiag, self).__init__(id = id, type = type, callback = callback)
        self.msgType = can_msg_fac.CAN_MSG_TYPE_DIAG