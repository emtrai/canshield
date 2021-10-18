

from can_msg import CanMsg
from can_shield import CanShieldDevice
from time import sleep
from applog import Log

import argparse
import sys
import os
import common
import can_flow
import can_diag_dtc
log = Log("Main")



def getOpts():
    parser = argparse.ArgumentParser(description="Test can")
    parser.add_argument('--dev', help="CAN device to be used")
    parser.add_argument('--port', help="Port config", default="/dev/cu.usbmodem14201")
    parser.add_argument('--speed', type=int, help="Speed config", default=921600)
    parser.add_argument('--script', help="Text to contains CAN message")
    parser.add_argument('--canmsg', help="Can message to be send")
    parser.add_argument('--canid', help="Can message to be send")
    parser.add_argument('--flow', help="Can message to be send")

    return parser.parse_args(sys.argv[1:])


runningflow = None
def recv_callback(err, type, resp):
    import can_device
    msg = resp
    if (type is can_device.RECV_TYPE_CAN):
        msg = resp.toString()
        if runningflow is not None:
            runningflow.onCanReceive(resp)
    log.d("%s:%s:%s" % (err, type, msg))

# FLOW_STEPS_MASK = 0
# FLOW_STEPS_SEND_CAN = 1
# FLOW_STEPS_WAIT = 2
# FLOW_STEPS_BREAK = 3
global canid
global respid
# canid = 0
# respid = 0
flows = {}
flows[can_flow.TAG] = can_flow.CanFlow.buildFlow
flows[can_diag_dtc.TAG] = can_diag_dtc.CanDTCFlow.buildFlow



def setIds(candev = None, params = None):
    global canid
    global respid
    if params is not None and len(params) > 0:
        items = params.split(",")
        nitem = len(items)
        if nitem > 0:
            canid = int(items[0].strip(), 0)
        if nitem > 1:
            respid = int(items[1].strip(), 0)
        log.i("id 0x%x respid 0x%x" % (canid, respid))
    else:
        log.e("Invalid id params")

def paramFlow(params):
    runflow = None
    if (params is not None):
        log.d("Parse Flow %s" % params)
        items = params.split(",",2)
        nitem = len(items)
        name = None
        script = None
        if nitem > 0:
            name = items[0].strip()
        if nitem > 1:
            script = items[1].strip()
        if name is not None and len(name) > 0:
            if name in flows:
                runflow = flows[name](script=script, canid=canid, respid=respid)
    return runflow

def execFlow(candev, flow):
    log.d("execFlow")
    if flow is not None:
        log.i("Run flow %s" % flow.getName())
        runningflow = flow
        ret = flow.runFlow(candev)
        runningflow = None
        log.i("Run flow '%s' Result %d" % (flow.getName(), ret))
    else:
        log.e("invalid flow")
        ret = common.ERR_INVALID
    return ret

def doRunFlow(candev = None, params = None):
    log.d("runFlow %s" % params)
    runFlow = paramFlow(params)
    return execFlow(candev, runFlow)
    

def doRunScript(candev = None, params = None):
    log.d("runScript %s" % params)
    runFlow = can_flow.CanFlow(script = params, canid=canid, respid=respid)
    return execFlow(candev, runFlow)

def doRunCanMsg(candev = None, params = None):
    
    return common.ERR_NONE

def doRunCmds(candev = None, params = None):
    
    return common.ERR_NONE


runflows = []
def doRun(candev = None, params = None):
    ret = common.ERR_NONE
    log.d("doRun")
    if runflows is not None and len(runflows) > 0:
        for flow in runflows:
            ret = execFlow(candev, flow)
            if ret is not common.ERR_NONE:
                log.e("Run flow %s failed %d" % (flow.getName(), ret))
                break
    else:
        log.e("Nothing to run")
        ret = common.ERR_NO_DATA
    return ret

actions = {
        "id":setIds,
        "flow":doRunFlow,
        "script":doRunScript,
        "can":doRunCanMsg,
        "cmd":doRunCmds,
        "run":doRun

    }

if (__name__ == "__main__"):
    import can_flow
    import can_diag_dtc

    options = getOpts()
    if options.dev is None:
        candev = CanShieldDevice()
    log.i("Port: %s, speed %d" % (options.port, options.speed))
    candev.config(options.port, options.speed)

    global canid
    global respid
    canid = 0
    respid = 0
    if (options.canid is not None) and len(options.canid) > 0:
        setIds(params=options.canid)
    
    log.i("Id 0x%x" % canid)

    if options.script is not None and len(options.script) > 0:
        if  (os.path.exists(options.script)):
            runflows.append(can_flow.CanFlow(script = options.script, canid=canid, respid=respid))
    
    if (options.flow is not None) and len(options.flow) > 0:
        runFlow = paramFlow(options.flow)
        if runFlow is not None:
            runflows.append(runFlow)
    
    log.i("Start can device")
    if candev.isReady():
        ret = candev.start(recv_callback)
    else:
        log.e("Can device is not ready, try to connect again")

    if ret == common.ERR_NONE:
        ret = doRun(candev, None)

    while True:

        value = input("Action> ")
        value = value.strip()
        action = None
        params = None
        if len(value) > 0:
            items = value.split(" ", 2)
            nitem = len(items)
            if nitem > 0:
                action = items[0].strip().lower()
            if nitem > 1:
                params = items[1].strip()

        if action is None:
            continue
        if action in actions:
            ret = actions[action](candev, params)
        elif action in ("quit", "exit", "q"):
            break
        else:
            log.e("Invalid action %s" % action)
            log.i("Actions: %s" % str(actions.keys()))

    candev.stop()

    # if (options.input is not None) and (os.path.exists(options.input)):
    #     flows = []
    #     candis = []
    #     # canmsg_list = []
    #     with open(options.input) as fp:
    #         while True:            
    #             # Get next line from file
    #             line = fp.readline()
            
    #             # if line is empty
    #             # end of file is reached
    #             if not line:
    #                 break
    #             line = line.strip()
    #             if (not line.startswith("#")):
    #                 lines = line.split(":", 1)
    #                 if (len(lines[0]) > 0):
    #                     if (lines[0] == "ids"):
    #                         ids = lines[1].split(",")
    #                         if (len(ids) > 0):
    #                             for id in ids:
    #                                 id = id.strip()
    #                                 if len(id) > 0:
    #                                     candis.append(int(id, 0))
    #                         log.i("Id %s" % str(candis))
                            
                            
    #                         mask = 0
    #                         if len(candis) > 0:
    #                             for id in candis:
    #                                 mask = mask | id
    #                             flows.append([FLOW_STEPS_MASK, mask])

    #                     elif (lines[0] == "can"):
    #                         items = lines[1].split(",")
    #                         if (len(items) > 3):
    #                             canmsg = CanMsg()
    #                             canmsg.id = int(items[0].strip(), 0)
    #                             canmsg.type = int(items[1].strip(), 0)
    #                             canmsg.maxLen = int(items[2].strip(), 0)
    #                             datas = items[3].strip().split(" ")
    #                             if len(datas) > 0:
    #                                 candata = []
    #                                 for data in datas:
    #                                     data = data.strip()
    #                                     if len(data) > 0:
    #                                         candata.append(int(data, 0))
    #                                 if len(candata) > 0:
    #                                     canmsg.addData(candata)
    #                                     flows.append([FLOW_STEPS_SEND_CAN, canmsg])
    #                                     # canmsg_list.append(canmsg)
    #                                 else:
    #                                     log.e("%s: no data" % canmsg.id)
    #                             else:
    #                                 log.e("%s: no data" % canmsg.id)
    #                         else:
    #                             log.e("Invalid data %s" % line)
    #                     elif (lines[0] == "wait"):
    #                         wait = lines[1].strip()
    #                         if len(wait) > 0:
    #                             flows.append([FLOW_STEPS_WAIT,  int(wait, 0)])
    #                     elif (lines[0] == "wait"):
    #                         wait = lines[1].strip()
    #                         if len(wait) > 0:
    #                             flows.append([FLOW_STEPS_WAIT,  int(wait, 0)])
    #                     elif (lines[0] == "break"):
    #                         flows.append([FLOW_STEPS_BREAK,  None])
                                
        


    #     if len(flows) > 0:
    #         candev.start(recv_callback)

    #         for item in flows:
    #             if item[0] == FLOW_STEPS_MASK:
    #                 # mask = ~(item[1])
    #                 mask = (item[1])
    #                 log.i("Send mask 0x%x" % mask)
    #                 candev.sendMask(mask)
    #                 sleep(0.5)
    #                 candev.sendFilter(item[1])
    #             elif item[0] == FLOW_STEPS_SEND_CAN:
    #                 log.i("Send can %s" % item[1].toString())
    #                 item[1].sendTo(candev)
    #             elif item[0] == FLOW_STEPS_WAIT:
    #                 waittime = item[1]/1000
    #                 log.i("Sleep %f s" % waittime)
    #                 sleep(waittime)
    #             elif item[0] == FLOW_STEPS_BREAK:
    #                 candev.sendBreak()


    #         candev.stop()
    #     else:
    #         log.e("Nothing to do")


    # canmsg = CanMsg(0x684)

    # canmsg.maxLen = 8
    # canmsg.addData([0x02, 0x19, 0x01])

    # candev.start(recv_callback)

    # sleep(1)
    # for cnt in range(3):
    #     log.i ("send %s" % canmsg.toString())
    #     canmsg.sendTo(candev)
    #     sleep(1)

    # candev.stop()
