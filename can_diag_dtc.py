from can_msg import CanMsg
import common
from applog import Log
from can_flow import CanFlow

TAG="dtc"

TYPE_STANDARD = 0

log = Log(TAG)

class CanDTCFlow(CanFlow):

    def getName(self):
        return TAG
    @staticmethod
    def buildFlow(script = None, cmds = None, canid = 0, respid = 0):
        return CanDTCFlow(script, cmds, canid, respid)

    def runPreCond(self, candev):
        log.i("Run pre condition")
        return common.ERR_NONE

    def runFlow(self, candev):
        ret = self.runPreCond(candev)
        if (ret is common.ERR_NONE):
            canmsg = CanMsg()
            canmsg.id = self.canid

            canmsg.addData([0x02, 0x19, 0x01, 0xFF])
            canmsg.sendTo(candev)
        else:
            log.e("Run precondition failed %d" % ret)
        return ret
    

