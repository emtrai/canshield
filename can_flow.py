import os

from can_msg import CanMsg
from applog import Log
from time import sleep
import common
import traceback
TYPE_STANDARD = 0

FLOW_STEPS_MASK = 0
FLOW_STEPS_SEND_CAN = 1
FLOW_STEPS_WAIT = 2
FLOW_STEPS_BREAK = 3

FLOW_TAG_MASK="mask"
FLOW_TAG_CAN="can"
FLOW_TAG_WAIT="wait"
FLOW_TAG_BREAK="break"

TAG="canflow"

log = Log(TAG)

class CanFlow:

    script = None
    canid = 0
    respid = 0

    def __init__(self, script = None, cmds = None, canid = 0, respid = 0) -> None:
        self.script = None
        self.canid = canid
        self.respid = respid
        self.cmds = None
        
    def getName(self):
        return TAG
    
    @staticmethod
    def buildFlow(script = None, cmds = None, canid = 0, respid = 0):
        return CanFlow(script, cmds, canid, respid)

    def onCanReceive(self, canMsg):
        pass
    
    def runFlow(self, candev):
        log.i("Run flow")
        ret = common.ERR_NONE
        flows = []
        if not candev.isReady():
            return common.ERR_NOT_READY
        if (self.script is not None) and (os.path.exists(self.script)):
            try:
                with open(self.script) as fp:
                    candis = []
                    while True:            
                        line = fp.readline()
                        if not line:
                            break
                        line = line.strip()
                        if (len(line) > 0 and not line.startswith("#")):
                            lines = line.split(":", 1)
                            tag = None
                            if lines is not None and len(lines) > 0:
                                tag = line[0].strip()
                            if (tag is not None and len(tag) > 0):
                                if tag == FLOW_TAG_MASK:
                                    ids = lines[1].strip().split(",")
                                    if (len(ids) > 0):
                                        for id in ids:
                                            id = id.strip()
                                            if len(id) > 0:
                                                candis.append(int(id, 0))
                                    log.i("Id %s" % str(candis))
                                    
                                    mask = 0
                                    if len(candis) > 0:
                                        for id in candis:
                                            mask = mask | id
                                        flows.append([FLOW_STEPS_MASK, mask])

                                elif (lines[0] == FLOW_TAG_CAN):
                                    ret = CanMsg.parse(lines[1].strip())
                                    
                                elif (lines[0] == FLOW_TAG_WAIT):
                                    wait = lines[1].strip()
                                    if len(wait) > 0:
                                        flows.append([FLOW_STEPS_WAIT,  int(wait, 0)])
                                
                                elif (lines[0] == FLOW_TAG_BREAK):
                                    flows.append([FLOW_STEPS_BREAK,  None])
                                
                                else:
                                    log.e("Invalid tag %s", )
                            
                if len(flows) > 0:
                    for item in flows:
                        if item[0] == FLOW_STEPS_MASK:
                            # mask = ~(item[1])
                            mask = (item[1])
                            log.i("Send mask 0x%x" % mask)
                            candev.sendMask(mask)
                            sleep(0.5)
                            candev.sendFilter(item[1])
                        elif item[0] == FLOW_STEPS_SEND_CAN:
                            log.i("Send can %s" % item[1].toString())
                            item[1].sendTo(candev)
                        elif item[0] == FLOW_STEPS_WAIT:
                            waittime = item[1]/1000
                            log.i("Sleep %f s" % waittime)
                            sleep(waittime)
                        elif item[0] == FLOW_STEPS_BREAK:
                            candev.sendBreak()
                else:
                    log.e("Nothing to do")
            except:
                traceback.print_exec()
                ret = common.ERR_EXCEPTION
        return ret;
    

