# Author: anhnh @ 2021

from can_msg import CanMsg
import common
from applog import Log
from can_flow import CanFlow
import can_msg_fac
from can_diag_flow import CanDiagFlow
TAG="dtc"

TYPE_STANDARD = 0

log = Log(TAG)

class CanDTCFlow(CanDiagFlow):

    def getName(self):
        return TAG
    
    @staticmethod
    def buildFlow(script = None, cmds = None, canid = 0, respid = 0, params = None):
        log.i("build flow")
        return CanDTCFlow(script, cmds, canid, respid)


    def canmsg_callback(self, canresp, err = common.ERR_NONE):
        log.i("can_acl_callback")
        if canresp is not None and canresp.canmsg is not None:
            log.d("Receive response %d for can %d" % (canresp.id, canresp.canmsg.id))
            if canresp.canmsg.id == self.respid:
                log.dumpBytes("data ", canresp.data)

        self.release_cond_can()
        return common.ERR_NONE

    def runDiagCmds(self, candev, params = None):
        log.i("runDiagCmds ")
        if self.canid != 0 and self.respid != 0:
            can_diag_diag = can_msg_fac.CanMsgFac.buildMsgFromString("0x%x, 0x%x, 0, 8, 0x19 0x01 0xFF" % (self.canid, self.respid), can_msg_fac.CAN_MSG_TYPE_DIAG)
            if can_diag_diag is not None:
                can_diag_diag.setCallback(self.canmsg_callback)
                can_diag_diag.sendTo(candev)
                self.wait_cond_can()
                ret = common.ERR_NONE
            else:
                log.e("Failed to build can acl")
                ret = common.ERR_FAILED
        else:
            ret = common.ERR_INVALID
            log.e("No can id or resp id to run")
        
        return ret
    

