import common
from serial import Serial
from threading import Thread
from time import sleep


from applog import Log
from can_msg import CanMsg
import can_device
import traceback

SEND_TAG="snd"
TAG_SPLIT=":"
VALUE_SPLIT=","

TAG_CAN="can"

DEFAULT_PORT = '/dev/cu.usbmodem14201'
DEFAULT_SPEED = 115200

LOG_TAG="canshield"

log = Log(LOG_TAG)
class CanShieldDevice:

    recv_callback = None
    isStop = True

    serialDev = None
    serialPort = DEFAULT_PORT
    serialSpeed = DEFAULT_SPEED
    run_thread = None


    def threaded_function(self):
        log.i("Start receiving thread")

        while not self.isStop:
            if self.serialDev is not None and self.serialDev.is_open:
                msg = self.serialDev.readline()
                
                if (msg is not None) and len(msg) > 0:
                    self.handleReceiveData(str(msg, 'utf-8'))
            else:
                break;
        
        log.i("Receiving thread is stopped")

    def handleReceiveData(self, msg):
        log.i("rec %s" % msg)
        try:
            eles = msg.split(TAG_SPLIT,1)
            type = can_device.RECV_TYPE_ERR
            ret = common.ERR_FAIED
            resp = None

            if (len(eles) > 1):
                tag = eles[0]
                value = eles[1]
                log.d("Tag %s" % tag)
                log.d("Value %s" % value)

                if tag is TAG_CAN:
                    values = value.split(VALUE_SPLIT)
                    if len(values) > 3:
                        can = CanMsg()
                        can.id = int(values[0], 0)
                        can.type = int(values[1], 0)
                        can.maxLen = int(values[2], 0)
                        if len(value[3] > 0):
                            datas = value[3].split(" ")
                            if (len(datas) > 0):
                                for i in datas:
                                    can.data.append(int(i, 0))
                                resp = can
                                type = can_device.RECV_TYPE_CAN
                                ret = common.ERR_NONE
                            else:
                                resp = "Invalid can data"
                                ret = common.ERR_INVALID
                        else:
                            resp = "No can data"
                            ret = common.ERR_INVALID
                    else:
                        resp = "No data"
                        ret = common.ERR_INVALID
                else:
                    ret = common.ERR_NONE
                    type = can_device.RECV_TYPE_UNKNOWN
                    resp = msg
            else:
                ret = common.ERR_FAIED
                type = can_device.RECV_TYPE_UNKNOWN
                resp = msg
                log.e("Invalid response %s" % msg)
        except:
            traceback.print_exc()
            resp = "Exception"
            ret = common.ERR_EXCEPTION
    
        if self.recv_callback is not None:
            self.recv_callback(ret, type, resp)


    def config(self, port=DEFAULT_PORT, speed=DEFAULT_SPEED):
        log.d("config")
        self.serialPort = port
        self.serialSpeed = speed


    def start(self, recv_callback):
        log.d("start")
        self.serialDev = Serial(self.serialPort , self.serialSpeed)
        self.recv_callback = recv_callback
        run_thread = Thread(target = self.threaded_function)

        self.isStop = False
        run_thread.start()

        return common.ERR_NONE;

    def stop(self):
        self.isStop = True
        self.serialDev.close()
        return common.ERR_NONE;

    def send(self, canmsg):
        msg = "0x%x,0x%x,0x%x," % (canmsg.id, canmsg.type,canmsg.maxLen)
        
        for i in canmsg.data:
            msg += "0x%X " % i
        msg += "\n"
        log.i("send %s" % msg)
        self.serialDev.write(msg.encode('utf-8'))
