import common
from applog import Log
from can_flow import CanFlow

TAG="diag"

TYPE_STANDARD = 0

log = Log(TAG)

class CanDiagFlow(CanFlow):


    def getName(self):
        return TAG
    def runPreCond(self, candev):
        log.d("Run pre condition")
        return common.ERR_NONE
    
    def startDiag(self, candev):
        log.d("startDiag")
        return common.ERR_NONE

    def runDiagCmds(self, candev):
        log.d("startDiag")
        return common.ERR_NONE

    def endDiag(self, candev):
        log.d("endDiag")
        return common.ERR_NONE

    def runFlow(self, candev, flows = None):
        log.i("Diag flow, precondition")
        ret = self.runPreCond(candev)
        if (ret is common.ERR_NONE):
            log.i("Diag flow, start")
            ret = self.startDiag(candev)
            if ret == common.ERR_NONE:
                log.i("Diag flow, Run commands")
                ret = self.runDiagCmds(candev)
            else:
                log.e("Start diag failed")
            log.i("Diag flow, end")
            self.endDiag(candev)
        else:
            log.e("Run precondition failed %d" % ret)
        return ret
    

