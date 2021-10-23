# Author: anhnh @ 2021

import common
from serial import Serial
from threading import Thread
from time import sleep
from queue import Queue
import queue

from applog import Log
from can_msg import CanMsg
from can_msg import CanMsgResp
import can_device
import traceback
from can_msg import MAX_LEN

import can_frame
import can_msg
import can_msg_fac

from applog import DEBUG

SEND_TAG="snd"
TAG_SPLIT=":"
VALUE_SPLIT=","

TAG_CAN="can"
TAG_MASK="msk"
TAG_FILTER="flt"

DEFAULT_PORT = '/dev/cu.usbmodem14201'
DEFAULT_SPEED = 115200
DEFAULT_MSG_TIMEOUT_MS = (10 * 1000)
DEFAULT_MSG_MAX_TIMEOUT_MS = (90 * 1000)

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

    canMsgWaitRespList = {}
    canFrameQueue = Queue(100)

    # Thread looping to read data
    def thread_recv_data(self):
        log.i("Start receiving thread")

        while not self.isStop and self.run_recv_thread is not None:
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
                if self.serialDev is not None and self.serialDev.is_open:
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
            id = int(values[0].strip(), 0) # canid
            
            if (id > 0): 
                data = []
                type = int(values[1].strip(), 0)
                maxLen = int(values[2].strip(), 0)
                datastring = values[3].strip()
                if len(datastring) > 0:
                    # data is separated by space
                    datas = datastring.split(" ")
                    if (len(datas) > 0):
                        for i in datas:
                            data.append(int(i.strip(), 0))
                        log.dumpBytes("canframe data ", data)
                        # parse can frame
                        ft = can_frame.FRAME_TYPE_RAW
                        if id in self.canMsgWaitRespList:
                            log.d("Found resp for id 0x%x" % id)
                            canmsgresp = self.canMsgWaitRespList[id]
                            if canmsgresp is not None and canmsgresp.canmsg is not None and canmsgresp.canmsg.msgType == can_msg_fac.CAN_MSG_TYPE_DIAG:
                                ft = can_frame.FRAME_TYPE_EXTEND
                        canframe = can_frame.parse2CanFrame(id = id, type = type, maxLen = maxLen, data = data, ft = ft)
                        if canframe is not None:
                            ret = common.ERR_NONE
                        else:
                            ret = common.ERR_FAILED
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
        log.d("checkToCleanUpCanMsgWait")
        key_del = []
        if len(self.canMsgWaitRespList) > 0:
            for key,resp in self.canMsgWaitRespList.items():
                if (resp is not None and resp.isTimeout()):
                    if resp.canmsg is not None and resp.canmsg.callback is not None:
                        ret = resp.canmsg.callback(resp, common.ERR_TIMEOUT)
                        if ret != common.ERR_PENDING or resp.isMaxTimeout():
                            key_del.append(key)
                        else:
                            resp.timeout = common.current_milli_time() + DEFAULT_MSG_TIMEOUT_MS
                    else:
                        key_del.append(key)
        if len(key_del) > 0:
            for key in key_del:
                del self.canMsgWaitRespList[key]
                log.d("id 0x%x timeout" % key)
        
    def thread_handle_canfram(self, q):
        log.i("thread_handle_canfram")
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
            if self.isStop:
                break
            if canframe is not None:
                log.dumpBytes("handle canframe %s, data" % canframe.toString(), canframe.rawdata)
                if self.rec_can_callback is not None:
                    try:
                        self.rec_can_callback(canframe)
                    except:
                        traceback.print_exc()

                self.checkToCleanUpCanMsgWait()
                if canframe.id in self.canMsgWaitRespList:
                    log.d("Found resp for id 0x%x" % canframe.id)
                    canmsgresp = self.canMsgWaitRespList[canframe.id]
                    ret = common.ERR_NONE
                    if canframe.frametype == can_frame.FRAME_TYPE_RAW:
                        log.d("raw can frame")
                        canmsgresp.setData(canframe.rawdata)
                        if canmsgresp.canmsg is not None and canmsgresp.canmsg.callback is not None:
                            ret = canmsgresp.canmsg.callback(canmsgresp, common.ERR_NONE)
                        if ret != common.ERR_PENDING:
                            del self.canMsgWaitRespList[canframe.id]
                        else:
                            log.i("wait next can response")
                    else:
                        log.d("multiple can frame, type %d" % canframe.exframetype)
                        # receive single frame
                        if canframe.exframetype == can_frame.FRAME_SF:
                            canmsgresp.setData(canframe.data)
                            if canmsgresp.canmsg is not None and canmsgresp.canmsg.callback is not None:
                                ret = canmsgresp.canmsg.callback(canmsgresp, common.ERR_NONE)
                            if ret != common.ERR_PENDING:
                                del self.canMsgWaitRespList[canframe.id]
                            else:
                                log.i("wait next can response")

                        elif canframe.exframetype == can_frame.FRAME_FIRST:
                            canmsgresp.setData(canframe.data)
                            canmsgresp.maxLen = canframe.datalen
                            log.d("maxlen for resp %d" % canmsgresp.maxLen)
                            flowcf = can_frame.CanFrameFlow(canmsgresp.canmsg.id)
                            flowcf.buildFlow(0, 0, 127)
                            self.sendCanFrame(flowcf)
                        elif canframe.exframetype == can_frame.FRAME_CONSECUTIVE:
                            canmsgresp.addData(canframe.data)
                            if canmsgresp.isFull():
                                log.d("received enough data, done")
                                if canmsgresp.canmsg is not None and canmsgresp.canmsg.callback is not None:
                                    ret = canmsgresp.canmsg.callback(canmsgresp, common.ERR_NONE)
                                if ret != common.ERR_PENDING:
                                    del self.canMsgWaitRespList[canframe.id]
                                else:
                                    log.i("wait next can response")
                            else:
                                log.d("not enough data, continue receiving")
                        elif canframe.exframetype == can_frame.FRAME_FLOW:
                            if DEBUG: log.d("can frame flow %s" % canframe.toString())
                            if canframe.flag == can_frame.FLAG_FLOW_CONT:
                                st = canframe.separatetime/1000
                                # due to performance issue of serial, min 0.1s.
                                # TODO: improve perf (i.e. not just send string, but raw buff)
                                if st < 0.1: 
                                    st = 0.1
                                log.i("blocksize %d st %d (%f)" % (canframe.blocksize, canframe.separatetime, st))
                                cnt = canframe.blocksize 
                                if cnt == 0:
                                    cnt = canmsgresp.canmsg.getRemainFrame()
                                
                                while cnt > 0 and not self.isStop:
                                    log.i("Get frame %d" % canmsgresp.canmsg.getCurrentIdx())
                                    cf = canmsgresp.canmsg.getFrame()
                                    if cf is not None:
                                        if DEBUG: log.d("Send consecutive frame %s" % (cf.toString()))
                                        
                                        self.sendCanFrame(cf)
                                        sleep(st)
                                        cnt -= 1
                                    else:
                                        break
                                
                            elif canframe.flag == can_frame.FLAG_FLOW_ABORT:
                                log.d("abort canframe")
                                if canmsgresp.canmsg is not None and canmsgresp.canmsg.callback is not None:
                                    canmsgresp.canmsg.callback(canmsgresp, common.ERR_NONE)
                                del self.canMsgWaitRespList[canframe.id]
                            # TODO:
                            # elif canframe.flag == can_frame.FLAG_FLOW_WAIT:
                else:
                    log.d("can id 0x%x not in waiting list" % canframe.id)


                
                
            else:
                log.d("Invalid can frame")
        log.i("thread_handle_canfram END")
            
    def handleReceiveData(self, msg):
        if msg is not None:
            msg = msg.strip()
            log.d("##########  %s  ##########" % msg)
        else:
            return
        try:
            eles = msg.split(TAG_SPLIT,1)
            type = can_device.RECV_TYPE_ERR
            ret = common.ERR_FAILED
            resp = None
            if (len(eles) > 1):
                tag = eles[0].strip()
                value = eles[1].strip()
                log.d("Tag '%s'" % tag)
                log.d("Value '%s'" % value)

                if tag == TAG_CAN:
                    if value is not None and len(value) > 0:
                        [ret, canframe] = self.parseCanFrame(value.strip())
                        if (ret == common.ERR_NONE):
                            if self.canFrameQueue.full(): # full
                                self.canFrameQueue.get_nowait() # remove oldest frame

                            log.d("Put canframe to queue")
                            self.canFrameQueue.put_nowait(canframe)
                            resp = canframe
                            type = can_device.RECV_TYPE_CAN
                            ret = common.ERR_NONE
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
                    resp = "unknown tag %s" % tag
            else:
                ret = common.ERR_FAILED
                type = can_device.RECV_TYPE_UNKNOWN
                resp = msg
                log.d("Invalid response %s" % msg)


            if self.recv_callback is not None:
                self.recv_callback(ret, type, resp)

        except:
            traceback.print_exc()
            resp = "Exception"
            ret = common.ERR_EXCEPTION
    


    def config(self, port=DEFAULT_PORT, speed=DEFAULT_SPEED):
        log.d("config")
        self.serialPort = port
        self.serialSpeed = speed


    def start(self, recv_callback = None, rec_can_callback = None):
        log.d("start")
        ret = common.ERR_FAILED
        try:
            self.serialDev = Serial(self.serialPort , self.serialSpeed)
            self.recv_callback = recv_callback
            self.rec_can_callback = rec_can_callback

            # thread to read data from serial
            self.run_recv_thread = Thread(target = self.thread_recv_data)

            # thread to handle can frame
            can_thread = Thread(target=self.thread_handle_canfram, args=(self.canFrameQueue,))
            # can_thread.setDaemon(True)

            self.isStop = False
            self.run_recv_thread.start()
            self.filter(0xFFFF) # mask all
            sleep(2) # sleep for a while to wait device init

            # start handling can frame
            can_thread.start()

            ret = common.ERR_NONE
        except:
            traceback.print_exc()
            ret = common.ERR_EXCEPTION
        return ret

    def stop(self):
        log.i("Stop canshield device")
        self.isStop = True
        if (self.serialDev is not None):
            self.serialDev.close()
        if self.canFrameQueue.empty():
            self.canFrameQueue.put_nowait(can_frame.CanFrame()) # dummy canframe
        return common.ERR_NONE

    def dosend(self, msg = None):
        log.i(">>>>> dosend %s" % (msg if msg is not None else ''))
        if self.isReady():
            try:
                if msg is not None and len(msg) > 0:
                    # log.i("dosend %s" % msg)
                    self.serialDev.write(b'\n')
                    self.serialDev.write(msg.encode('utf-8'))
                self.serialDev.write(b'\n') # break waiting in device to check
                ret = common.ERR_NONE
            except:
                traceback.print_exc()
                ret = common.ERR_EXCEPTION
            
        else:
            log.e("Serial port not open")
            ret = common.ERR_NOT_READY
        return ret

    def send(self, canmsg):
        log.i("Send canmsg 0x%x to %s" % (canmsg.id, self.name()))
        canFrames = can_frame.canMsg2Frames(canmsg)
        if canFrames is not None and len(canFrames) > 0:
            canmsg.canFrames = canFrames
            cf = canmsg.getFrame()
            if canmsg.respid > 0:
                canrsp = CanMsgResp(canmsg.respid, canmsg)
                self.canMsgWaitRespList[canmsg.respid] = canrsp
                canrsp.starttime = common.current_milli_time()
                canrsp.timeout =  canrsp.starttime + DEFAULT_MSG_TIMEOUT_MS
                canrsp.maxtimeout =  canrsp.starttime + DEFAULT_MSG_MAX_TIMEOUT_MS
            ret = self.sendCanFrame(cf)
        else:
            ret = common.ERR_NO_DATA
            log.e("Not can frame to send")
        return ret
    
    def sendCanFrame(self, cf):
        if cf is not None:
            # log.i("sendCanFrame 0x%x" % cf.id)
            msg = "%s:0x%x,0x%x,0x%x," % (TAG_CAN, cf.id, cf.type, cf.maxLen)
            log.dumpBytes("sendCanFrame data", cf.rawdata)
            for i in cf.rawdata:
                msg += "0x%02X " % (i & 0xFF)
            return self.dosend(msg)
        else:
            return common.ERR_INVALID

    def filter(self, mask):
        log.i("Filter 0x%x" % mask)
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