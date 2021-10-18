import os

from can_msg import CanMsg
import can_msg_fac
from applog import Log
from time import sleep
import common
import traceback
from applog import DEBUG
import threading

TYPE_STANDARD = 0

FLOW_STEPS_FILTER = 0
FLOW_STEPS_SEND_CAN = 1
FLOW_STEPS_WAIT = 2
FLOW_STEPS_BREAK = 3
FLOW_STEPS_SLEEP = 4
FLOW_STEPS_TIMEOUT = 5
FLOW_STEPS_INCLUDE = 6

FLOW_TAG_FILTER="filter"
FLOW_TAG_CAN_TIMEOUT="timeout"
FLOW_TAG_CAN="can"
FLOW_TAG_WAIT="wait"
FLOW_TAG_SLEEP="sleep"
FLOW_TAG_BREAK="break"
FLOW_TAG_DIAG="diag"
FLOW_TAG_INCLUDE="inc"

MAX_CAN_TIMEOUT_MS = (10 * 1000)

TAG="canflow"

log = Log(TAG)

class CanFlow:

    script = None
    canid = 0
    respid = 0
    max_can_timeout = MAX_CAN_TIMEOUT_MS
    cond_can = None
    sending_can_msg = None
    def __init__(self, script = None, cmds = None, canid = 0, respid = 0) -> None:
        self.script = script
        self.canid = canid
        self.respid = respid
        self.cmds = None
        self.max_can_timeout = MAX_CAN_TIMEOUT_MS
        self.sending_can_msg = None
        
    def getName(self):
        return TAG
    
    @staticmethod
    def buildFlow(script = None, cmds = None, canid = 0, respid = 0):
        log.i("build flow")
        return CanFlow(script, cmds, canid, respid)

    def onCanReceive(self, canMsg):
        pass
    
    def wait_cond_can(self, timeout = 0):
        log.i("wait_cond_can %d" % timeout)
        try:
            self.cond_can = threading.Condition()
            with self.cond_can:
                # self.cond_can.acquire()
                waiting = 0.0
                if timeout > 0:
                    waiting = timeout/1000
                else:
                    waiting = self.max_can_timeout
                log.i("wait_cond_can %f" % waiting)
                self.cond_can.wait(waiting)

        finally:
            self.cond_can = None
        
    def release_cond_can(self):
        log.i("release_cond_can")
        if self.cond_can is not None:
            try:
                with self.cond_can:
                    self.cond_can.notify_all()
            except:
                traceback.print_exc()


    def canmsg_callback(self, canresp, err = common.ERR_NONE):
        log.i("canmsg_callback")
        shouldwait = False
        if canresp is not None and canresp.canmsg is not None:
            log.d("Receive response 0x%x for can 0x%x" % (canresp.id, canresp.canmsg.id))
            
            if self.sending_can_msg is not None :
                log.d("sending_can_msg can 0x%x" % (self.sending_can_msg.id))
                if self.sending_can_msg.id == canresp.canmsg.id:
                    log.printBytes("0x%x - 0x%x: " % (canresp.canmsg.id, canresp.id), canresp.data)
                if (canresp.data[1] == 0x7F) and (canresp.data[3] == 0x78):
                    shouldwait = True

        if not shouldwait:
            self.release_cond_can()
            return common.ERR_NONE
        else:
            return common.ERR_PENDING

    def parseStep(self, line):
        step = None
        if (len(line) > 0 and not line.startswith("#")):
            log.d("parseStep: %s" % line)
            lines = line.split(":", 1)
            tag = None
            candis = []
            if lines is not None and len(lines) > 0:
                tag = line[0].strip()
            if (tag is not None and len(tag) > 0):
                if tag == FLOW_TAG_CAN_TIMEOUT:
                    val = lines[1].strip()
                    max_can_timeout = 0
                    if len(val) > 0:
                        max_can_timeout = int(val, 0)
                    if self.max_can_timeout == 0:
                        max_can_timeout = MAX_CAN_TIMEOUT_MS

                    step = [FLOW_STEPS_TIMEOUT, max_can_timeout]
                
                elif tag == FLOW_TAG_FILTER:
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
                            mask = mask | (id & 0xFFFF)
                    else:
                        mask = 0xFFFF
                    step = [FLOW_STEPS_FILTER, mask]

                elif (lines[0] == FLOW_TAG_CAN):
                    ret = can_msg_fac.CanMsgFac.buildMsgFromString(lines[1].strip(), can_msg_fac.CAN_MSG_TYPE_RAW)
                    if ret is not None:
                        ret.setCallback(self.canmsg_callback)
                        step = [FLOW_STEPS_SEND_CAN, ret]
                    else:
                        log.e("invalid step %s" % line)

                elif (lines[0] == FLOW_TAG_DIAG):
                    ret = can_msg_fac.CanMsgFac.buildMsgFromString(lines[1].strip(), can_msg_fac.CAN_MSG_TYPE_DIAG)
                    if ret is not None:
                        ret.setCallback(self.canmsg_callback)
                        step = [FLOW_STEPS_SEND_CAN, ret]
                    else:
                        log.e("invalid step %s" % line)

                elif (lines[0] == FLOW_TAG_WAIT):
                    wait = lines[1].strip()
                    if len(wait) > 0:
                        step = [FLOW_STEPS_WAIT,  int(wait, 0)]
                    else:
                        step = [FLOW_STEPS_WAIT,  0]

                elif (lines[0] == FLOW_TAG_SLEEP):
                    wait = lines[1].strip()
                    time = 0
                    if len(wait) > 0:
                        time = int(wait, 0)
                    if time > 0:
                        step = [FLOW_STEPS_SLEEP,  time]
                    #if 0, do nothing
                elif (lines[0] == FLOW_TAG_BREAK):
                    step = [FLOW_STEPS_BREAK,  None]

                elif (lines[0] == FLOW_TAG_INCLUDE):
                    ipath = lines[1].strip()
                    if ipath is not None and len(ipath) > 0:
                        if not os.path.isabs(ipath):
                            ipath = os.path.abspath(ipath)
                        log.d("Include script '%s'" % (ipath))
                        step = [FLOW_STEPS_INCLUDE, ipath]
                    else:
                        log.e("Parse script '%s' failed, invalid" % ipath)
                
            else:
                log.e("Invalid tag %s" % tag)
        
        return step

    def parseScripts(self, fpath):
        log.i("parseScripts %s" % fpath)
        flows = None
        if (fpath is not None) and (os.path.exists(fpath)):
            try:
                with open(fpath) as fp:
                    flows = []
                    while True:
                        line = fp.readline()
                        if not line:
                            break
                        line = line.strip()
                        step = self.parseStep(line.strip())
                        if step is not None and len(step) > 0:
                            if step[0] == FLOW_STEPS_TIMEOUT:
                                self.max_can_timeout = step[1]
                            elif step[0] == FLOW_STEPS_INCLUDE:
                                log.d("Include script '%s'" % (step[1]))
                                if os.path.exists(step[1]):
                                    iflow = self.parseScripts(step[1])
                                    if iflow is not None and len(iflow) > 0:
                                        flows.extend(iflow)
                                    else:
                                        log.e("Parse script '%s' failed" % step[1])
                                        flows = None
                                        break
                                else:
                                    log.e("Parse script '%s' failed, file not found" % step[1])
                                    flows = None
                                    break
                            else:
                                flows.append(step)
            except:
                traceback.print_exc()
                flows = None
        else:
            flows = None
            log.e("script '%s'  not found" % fpath)
        return flows



    def runScript(self, candev, script):
        log.i("Run flow")
        flows = self.parseScripts(script)
        return self.runFlow(candev, flows)


    def runFlow(self, candev, flows = None):
        log.i("Run flow")
        ret = common.ERR_NONE
        if not candev.isReady():
            log.e("Device not ready to run flow")
            return common.ERR_NOT_READY
        if (flows is None or len(flows) == 0):
            flows = self.parseScripts(self.script)
        
        if flows is not None and len(flows) > 0:
            if DEBUG: 
                log.d("Flow: ")
                step = 0
                for item in flows:
                    if item[0] == FLOW_STEPS_SEND_CAN:
                        log.d("%d: %d, %s" % (step, item[0], item[1].toString()))
                    else:
                        log.d("%d: %d, %d" % (step, item[0], item[1]))
                    step += 1
            step = 0
            prev_step = None
            for item in flows:
                log.d("Run flow step: %d" % step)
                
                if item[0] == FLOW_STEPS_FILTER:
                    log.i("Send mask 0x%x" % item[1])
                    candev.filter(item[1])
                    self.sending_can_msg = None
                elif item[0] == FLOW_STEPS_SEND_CAN:
                    log.i("Send can %s" % item[1].toString())
                    self.sending_can_msg = item[1]
                    item[1].sendTo(candev)

                elif item[0] == FLOW_STEPS_SLEEP:
                    if item[1] > 0:
                        waittime = item[1]/1000
                        log.i("Sleep %f s" % waittime)
                        sleep(waittime)
                    self.sending_can_msg = None
                elif item[0] == FLOW_STEPS_WAIT:
                    wait = item[1]
                    if prev_step is not None and (prev_step[0] == FLOW_STEPS_SEND_CAN):
                        if self.sending_can_msg is not None:
                            self.wait_cond_can(wait)
                    else:
                        # previous step is not can, judge wait as sleep
                        if wait > 0:
                            waittime = item[1]/1000
                            log.i("Sleep %f s" % waittime)
                            sleep(waittime)
                    self.sending_can_msg = None
                elif item[0] == FLOW_STEPS_BREAK:
                    candev.sendBreak()
                    self.sending_can_msg = None
                
                step += 1
                prev_step = item
                
        else:
            log.e("Nothing to do")
        return ret
    

