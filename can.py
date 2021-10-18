

from genericpath import exists
import traceback
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
    parser.add_argument('--cmd', help="Command to be used")
    parser.add_argument('--canid', help="canid[,respid] : Can id to be used, and response can id if any")
    parser.add_argument('--filter', help="<id>,<id> : List of can id to be set mask/filter")
    parser.add_argument('--flow', help="[name],[script file] : flow <name> to be run with script if any")

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

def rec_can_callback(canframe):
    if canframe is not None:
        log.printBytes(">>> CAN FRAME 0x%x:" % (canframe.id), canframe.rawdata)


global canid
global respid

flows = {}
flows[can_flow.TAG] = can_flow.CanFlow.buildFlow
flows[can_diag_dtc.TAG] = can_diag_dtc.CanDTCFlow.buildFlow
# import can_diag_access
# flows[can_diag_access.TAG] = can_diag_access.CanDiagAcl.buildFlow


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

# parse param flow: <name>,<script path>
def paramFlow(params):
    runflow = None
    if (params is not None):
        log.d("Parse Flow %s" % params)
        items = params.split(",", 1)
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

def execFlow(candev, flow, steps = None):
    log.d("execFlow")
    if flow is not None:
        log.i("Run flow %s" % flow.getName())
        try:
            runningflow = flow
            ret = flow.runFlow(candev, steps)
        except:
            traceback.print_exc()
            ret = common.ERR_EXCEPTION
        finally:
            runningflow = None
        log.i("Run flow '%s' Result %d" % (flow.getName(), ret))
    else:
        log.e("invalid flow")
        ret = common.ERR_INVALID
    return ret

def doRunFlow(candev = None, params = None):
    if params is None or len(params) == 0:
        for key,_ in flows.items():
            print(key)
        # log.i("Flow %s" % str(flows.keys))
        return common.ERR_NONE
    else:
        log.d("runFlow %s" % params)
        runFlow = paramFlow(params)
        return execFlow(candev, runFlow)
    

def doRunScript(candev = None, params = None):
    log.d("runScript %s" % params)
    runFlow = can_flow.CanFlow(script = params, canid=canid, respid=respid)
    return execFlow(candev, runFlow)


def doRunCmds(candev = None, params = None):
    log.i("doRunCmds %s" % params)
    runFlow = can_flow.CanFlow(canid=canid, respid=respid)
    ret = runFlow.parseStep(params)
    if ret is not None and len(ret) > 0 :
        return execFlow(candev, runFlow, [ret])

def doFilter(candev = None, params = None):
    log.i("doFilter %s" % params)
    items = params.split(",")
    candis = []
    for item in items:
        item = item.strip()
        if len(item) > 0:
            candis.append(int(item, 0))
    log.d("Id %s" % str(candis))
    mask = 0
    if len(candis) > 0:
        for id in candis:
            mask = mask | (id & 0xFFFF)
        candev.filter(mask)
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
        "cmd":doRunCmds,
        "run":doRun,
        "filter":doFilter
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
            log.i("Add script from '%s' to list flows" % options.script)
            runflows.append(can_flow.CanFlow(script = options.script, canid=canid, respid=respid))
    
    if (options.canid is not None) and len(options.canid) > 0:
        setIds(params = options.canid )

    if (options.flow is not None) and len(options.flow) > 0:
        runFlow = paramFlow(options.flow)
        if runFlow is not None:
            log.i("Add flow from '%s' to list flows" % options.flow)
            runflows.append(runFlow)
    
    log.i("Start can device")
    ret = 0
    ret = candev.start(recv_callback, rec_can_callback)

    if (options.filter is not None) and len(options.filter) > 0:
        ret = doFilter(candev, options.filter)

    if ret == common.ERR_NONE:
        ret = doRun(candev, None)

    if (options.cmd is not None) and len(options.cmd) > 0:
        log.i("Run command '%s'" % options.cmd)
        ret = doRunCmds(candev, options.cmd)
    
    while True:

        value = input("Action> ")
        value = value.strip()
        action = None
        params = None
        if len(value) > 0:
            items = value.split(" ", 1)
            nitem = len(items)
            if nitem > 0:
                action = items[0].strip().lower()
            if nitem > 1:
                params = items[1].strip()

        if action is None:
            continue
        if action in actions:
            try:
                log.e("Run action '%s'" % action)
                ret = actions[action](candev, params)
            except:
                traceback.print_exc()
        elif action in ("quit", "exit", "q"):
            break
        else:
            log.e("Invalid action %s" % action)
            log.i("Actions: %s" % str(actions.keys()))

    candev.stop()
