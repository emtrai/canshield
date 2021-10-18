import common
from applog import Log
from can_flow import CanFlow

TAG="candiag"

TYPE_STANDARD = 0

log = Log(TAG)

class CanDiagFlow(CanFlow):


    def getName(self):
        return TAG
    def runPreCond(self, candev):
        log.i("Run pre condition")
        return common.ERR_ONE
    
    def startDiag(self, candev):
        log.i("startDiag")
        return common.ERR_ONE

    def endDiag(self, candev):
        log.i("endDiag")
        return common.ERR_ONE

    def runFlow(self, candev):
        ret = self.runPreCond(candev)
        if (ret is common.ERR_NONE):
            ret = self.startDiag(candev)
            if ret is common.ERR_NONE:
                ret = super(CanDiagFlow, self).runFlow(candev)
            self.endDiag(candev)
        else:
            log.e("Run precondition failed %d" % ret)
        return ret
    

