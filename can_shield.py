import common
from serial import Serial
from threading import Thread
from time import sleep
from Queue import Queue

from applog import Log
from can_msg import CanMsg
from can_msg import CanMsgResp
import can_device
import traceback
from can_msg import MAX_LEN

import can_frame


SEND_TAG="snd"
TAG_SPLIT=":"
VALUE_SPLIT=","

TAG_CAN="can"
TAG_MASK="msk"
TAG_FILTER="flt"

DEFAULT_PORT = '/dev/cu.usbmodem14201'
DEFAULT_SPEED = 115200
DEFAULT_MSG_TIMEOUT_MS = 100

TAG="canshield"

log = Log(TAG)
class CanShieldDevice:

    recv_callback = None
    rec_can_callback = None
    isStop = True

    serialDev = None
    serialPort = DEFAULT_PORT
    serialSpeed = DEFAULT_SPEED
    run_recv_thread = None
    can_thread = None

    canMsgSent = {}
    canMsgWaitRespList = {}
    canFrameQueue = Queue(100)

    # Thread looping to read data
    def thread_recv_data(self):
        log.i("Start receiving thread")

        while not self.isStop and not self.run_recv_thread:
            # read one by one
            if self.serialDev is not None and self.serialDev.is_open:
                msg = self.serialDev.readline()
                
                # received message
                # msg must be text
                if (msg is not None) and len(msg) > 0:
                    try:
                        self.handleReceiveData(str(msg, 'utf-8'))
                    except:
                        log.e("Failed to parse receive data")
                
                # just want to device not to be hung
                self.serialDev.write(b'\n')

            else:
                log.e("Device is not ready, out")
                break
        
        self.run_recv_thread = None
        log.i("Receiving thread is stopped")

    # parse data to can frame
    def parseCanFrame(self, value):
        log.d("parseCanFrame: %s" % value)
        # id,type,len,data --> 4 elements
        values = value.split(VALUE_SPLIT)
        canframe = None
        if len(values) > 3: # must be 4 elements
            id = int(values[0].stript(), 0) # canid
            
            if (id > 0): 
                data = None
                type = int(values[1].stript(), 0)
                maxLen = int(values[2].stript(), 0)
                datastring = value[3].stript()
                if len(datastring) > 0:
                    # data is separated by space
                    datas = datastring.split(" ")
                    if (len(datas) > 0):
                        for i in datas:
                            data.append(int(i.strip(), 0))
                        # parse can frame
                        canframe = can_frame.parse2CanFrame(id = id, type = type, maxLen = maxLen, data = data)
                        if canframe is not None:
                            ret = common.ERR_NONE
                        else:
                            ret = common.ERR_FAIED
                            log.e("ParseCanFrame failed")
                    else:
                        log.e("parseCanFrame: Invalid can data")
                        ret = common.ERR_INVALID
                else:
                    log.e("parseCanFrame: No can data")
                    ret = common.ERR_INVALID
            else:
                log.e("parseCanFrame: invalid response id")
                ret = common.ERR_INVALID
        else:
            log.e("parseCanFrame: No data")
            ret = common.ERR_INVALID

        return [ret, canframe]

    def checkToCleanUpCanMsgWait(self):
        if len(self.canMsgWaitRespList) > 0:
            for key,resp in self.canMsgWaitRespList.items():
                if (resp is not None and resp.isTimeout()):
                    del self.canMsgWaitRespList[key]
        
    def handleReceiveCanFrame(self, q):
        while not self.isStop:
            try:
                canframe = q.get(timeout = 1000)
            except queue.Empty:
                # timeout, continue
                # https://docs.python.org/3/library/queue.html
                continue
            except:
                traceback.print_exc()
                # TODO: Should out?
            
            if canframe is not None:
                if canframe.id in self.canMsgWaitRespList:
                    canmsgresp = self.canMsgWaitRespList[canframe.id]
                    # receive single frame
                    if canframe.frametype == can_frame.FRAME_SF:
                        canmsgresp.setData(canframe.data)
                        del self.canMsgWaitRespList[canframe.id]
                        if canmsgresp.canmsg is not None and canmsgresp.canmsg.callback is not None:
                            canmsgresp.canmsg.callback(canmsgresp)

                    elif canframe.frametype == can_frame.FRAME_FIRST:
                        canmsgresp.setData(canframe.data)
                        canmsgresp.maxLen = canframe.datalen
                        flowcf = can_frame.CanFrameFlow(id)
                        flowcf.buildFlow(0, 0, 0)
                        self.sendCanFrame(flowcf)
                    elif canframe.frametype == can_frame.FRAME_CONSECUTIVE:
                        canmsgresp.addData(canframe.data)
                        
                    elif canframe.frametype == can_frame.FRAME_FLOW:
                        if canframe.flag == can_frame.FLAG_FLOW_CONT:
                            cnt = canframe.blocksize 
                            if cnt == 0:
                                cnt = canmsgresp.canmsg.getRemainFrame()
                            
                            cf = canmsgresp.canmsg.getFrame()
                            while cf is not None and cnt > 0:
                                self.sendCanFrame(cf)
                                sleep(canframe.separatetime/1000)
                                cf = canmsgresp.canmsg.getFrame()
                                cnt -= 1
                        elif canframe.flag == can_frame.FLAG_FLOW_ABORT:
                            del self.canMsgWaitRespList[canframe.id]
                            if canmsgresp.canmsg is not None and canmsgresp.canmsg.callback is not None:
                                canmsgresp.canmsg.callback(canmsgresp)
                        # TODO:
                        # elif canframe.flag == can_frame.FLAG_FLOW_WAIT:


                if self.rec_can_callback is not None:
                    self.rec_can_callback(canframe)
                
                self.checkToCleanUpCanMsgWait()

    def handleReceiveData(self, msg):
        if msg is not None:
            msg = msg.strip()
            log.d("<<< %s >>>" % msg)
        else:
            # no data, skip
            return
        # print("<<<")
        # print(msg)
        # print(">>>")
        try:
            eles = msg.split(TAG_SPLIT,1)
            type = can_device.RECV_TYPE_ERR
            ret = common.ERR_FAIED
            resp = None
            done = True
            if (len(eles) > 1):
                tag = eles[0]
                value = eles[1]
                log.d("Tag %s" % tag)
                log.d("Value %s" % value)

                if tag is TAG_CAN:
                    if value is not None and len(value) > 0:
                        [ret, canframe] = self.parseCanFrame(value.strip())
                        if (ret == common.ERR_NONE):
                            if self.canFrameQueue.full():
                                self.canFrameQueue.get_nowait() # remove oldest frame

                            self.canFrameQueue.put_nowait(canframe)
                        else:
                            resp = "Parse can frame failed"
                            type = can_device.RECV_TYPE_ERR
                    else:
                        ret = common.ERR_INVALID
                        resp = "Invalid received data"
                        type = can_device.RECV_TYPE_ERR

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


    def start(self, recv_callback = None, rec_can_callback = None):
        log.d("start")
        ret = common.ERR_FAIED
        try:
            self.serialDev = Serial(self.serialPort , self.serialSpeed)
            self.recv_callback = recv_callback
            self.rec_can_callback = rec_can_callback
            self.run_recv_thread = Thread(target = self.thread_recv_data)

           
            can_thread = Thread(target=self.handleReceiveCanFrame, args=(self.canFrameQueue))
            can_thread.setDaemon(True)

            self.isStop = False
            self.run_recv_thread.start()
            self.filter(0xFFFF) # mask all
            sleep(3) # sleep for a while to wait device init

            # start handling can frame
            can_thread.start()

            ret = common.ERR_NONE
        except:
            traceback.print_exc()
            ret = common.ERR_EXCEPTION
        return ret;

    def stop(self):
        self.isStop = True
        if (self.serialDev is not None):
            self.serialDev.close()
        return common.ERR_NONE

    def dosend(self, msg = None):
        if self.serialDev is not None and self.serialDev.is_open:
            if msg is not None and len(msg) > 0:
                log.i("dosend %s" % msg)
                self.serialDev.write(b'\n')
                self.serialDev.write(msg.encode('utf-8'))
            self.serialDev.write(b'\n')
            ret = common.ERR_NONE
        else:
            log.e("Serial port not open")
            ret = common.ERR_NOT_READY
        return ret

    def send(self, canmsg):
        log.i("Send canmsg 0x%x to %s" % (canmsg.id, self.name()))
        canFrames = can_frame.canMsg2Frames(canmsg)
        canmsg.canFrames = canFrames
        if len(self.data) <= MAX_LEN:
            log.i("Send Single Frame")
            msg = "%s:0x%x,0x%x,0x%x," % (TAG_CAN, canmsg.id, canmsg.type, MAX_LEN)
            for i in canmsg.data:
                msg += "0x%X " % i
            if canmsg.respid > 0:
                self.canMsgSent[canmsg.id] = canmsg
                self.canMsgWaitRespList[canmsg.respid] = CanMsgResp(canmsg.respid, canmsg)
                canmsg.starttime = common.current_milli_time()
                canmsg.timeout = DEFAULT_MSG_TIMEOUT_MS
            return self.dosend(msg)
    
    def sendCanFrame(self, canframe):
        log.i("sendCanFrame")
        msg = "%s:0x%x,0x%x,0x%x," % (TAG_CAN, canframe.id, canframe.type, canframe.maxLen)
        for i in canframe.rawdata:
            msg += "0x%02X " % i
        return self.dosend(msg)

    def filter(self, mask):
        self.sendMask(mask)
        sleep(0.5)
        self.sendFilter(mask)

    def filterIds(self, candis):
        mask = 0
        for id in candis:
            mask = mask | id
        self.filter(mask)

    def sendMask(self, mask):
        msg = "%s:0x%x" % (TAG_MASK, mask)
        return self.dosend(msg)

    def sendFilter(self, filter):
        msg = "%s:0x%x" % (TAG_FILTER, filter)
        return self.dosend(msg)
    
    def sendBreak(self):
        log.i("send break")
        return self.dosend()


    def isReady(self):
        return (self.serialDev is not None and self.serialDev.is_open)

    def name(self):
        return TAG