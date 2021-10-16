

from can_msg import CanMsg
from can_shield import CanShieldDevice
from time import sleep
from applog import Log

import argparse
import sys

log = Log("Main")



def getOpts():


    parser = argparse.ArgumentParser(description="Test can")
    parser.add_argument('--dev', help="CAN device to be used")
    parser.add_argument('--port', help="Port config", default="/dev/cu.usbmodem14201")
    parser.add_argument('--speed', type=int, help="Speed config", default=115200)
    parser.add_argument('--input', help="Text to contains CAN message")
    parser.add_argument('--canmsg', help="Can message to be send")

    return parser.parse_args(sys.argv[1:])


def recv_callback(err, type, resp):
    import can_device
    msg = resp
    if (type is can_device.RECV_TYPE_CAN):
        msg = resp.toString()
    log.d("%s:%s:%s" % (err, type, msg))

if (__name__ == "__main__"):
    options = getOpts()
    if options.dev is None:
        candev = CanShieldDevice()
        
    canmsg = CanMsg(0x604)

    canmsg.maxLen = 8
    canmsg.addData([0x02, 0x19, 0x01])

    candev.start(recv_callback)
    for cnt in range(3):
        log.i ("send %s" % canmsg.toString())
        canmsg.sendTo(candev)
        sleep(1)

    candev.stop()
