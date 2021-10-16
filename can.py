

from can_msg import CanMsg
from can_shield import CanShieldDevice
from time import sleep
from applog import Log

import argparse
import sys
import os

log = Log("Main")



def getOpts():


    parser = argparse.ArgumentParser(description="Test can")
    parser.add_argument('--dev', help="CAN device to be used")
    parser.add_argument('--port', help="Port config", default="/dev/cu.usbmodem14201")
    parser.add_argument('--speed', type=int, help="Speed config", default=921600)
    parser.add_argument('--input', help="Text to contains CAN message")
    parser.add_argument('--canmsg', help="Can message to be send")

    return parser.parse_args(sys.argv[1:])


def recv_callback(err, type, resp):
    import can_device
    msg = resp
    if (type is can_device.RECV_TYPE_CAN):
        msg = resp.toString()
    log.d("%s:%s:%s" % (err, type, msg))

FLOW_STEPS_MASK = 0
FLOW_STEPS_SEND_CAN = 1
FLOW_STEPS_WAIT = 2
FLOW_STEPS_BREAK = 3
if (__name__ == "__main__"):
    options = getOpts()
    if options.dev is None:
        candev = CanShieldDevice()
    log.i("Port: %s, speed %d" % (options.port, options.speed))
    candev.config(options.port, options.speed)


    if (options.input is not None) and (os.path.exists(options.input)):
        flows = []
        candis = []
        # canmsg_list = []
        with open(options.input) as fp:
            while True:            
                # Get next line from file
                line = fp.readline()
            
                # if line is empty
                # end of file is reached
                if not line:
                    break
                line = line.strip()
                if (not line.startswith("#")):
                    lines = line.split(":", 1)
                    if (len(lines[0]) > 0):
                        if (lines[0] == "ids"):
                            ids = lines[1].split(",")
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

                        elif (lines[0] == "can"):
                            items = lines[1].split(",")
                            if (len(items) > 3):
                                canmsg = CanMsg()
                                canmsg.id = int(items[0].strip(), 0)
                                canmsg.type = int(items[1].strip(), 0)
                                canmsg.maxLen = int(items[2].strip(), 0)
                                datas = items[3].strip().split(" ")
                                if len(datas) > 0:
                                    candata = []
                                    for data in datas:
                                        data = data.strip()
                                        if len(data) > 0:
                                            candata.append(int(data, 0))
                                    if len(candata) > 0:
                                        canmsg.addData(candata)
                                        flows.append([FLOW_STEPS_SEND_CAN, canmsg])
                                        # canmsg_list.append(canmsg)
                                    else:
                                        log.e("%s: no data" % canmsg.id)
                                else:
                                    log.e("%s: no data" % canmsg.id)
                            else:
                                log.e("Invalid data %s" % line)
                        elif (lines[0] == "wait"):
                            wait = lines[1].strip()
                            if len(wait) > 0:
                                flows.append([FLOW_STEPS_WAIT,  int(wait, 0)])
                        elif (lines[0] == "wait"):
                            wait = lines[1].strip()
                            if len(wait) > 0:
                                flows.append([FLOW_STEPS_WAIT,  int(wait, 0)])
                        elif (lines[0] == "break"):
                            flows.append([FLOW_STEPS_BREAK,  None])
                                
        


        if len(flows) > 0:
            candev.start(recv_callback)

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


            candev.stop()
        else:
            log.e("Nothing to do")


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
