# Author: anhnh @ 2021

from applog import Log
import common

LOG_TAG = "canmsgfac"

log = Log(LOG_TAG)

CAN_MSG_TYPE_RAW = 0
CAN_MSG_TYPE_DIAG = 1

TYPE_STANDARD = 0

class CanMsgFac:


    @staticmethod
    def buildMsgFromString(msg, type):

        import can_msg
        import can_msg_diag
        canmsg = None
        if msg is not None and len(msg) > 0:
            if type == CAN_MSG_TYPE_RAW:
                canmsg = can_msg.CanMsg()
            else:
                canmsg = can_msg_diag.CanMsgDiag()
            ret = canmsg.parse(msg)
            if ret != common.ERR_NONE:
                canmsg = None
        return canmsg
