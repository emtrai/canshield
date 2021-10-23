# Author: anhnh @ 2021

from applog import DEBUG, Log
import common

TAG = "canframe"

log = Log(TAG)


TYPE_STANDARD = 0

MAX_LEN = 8

FRAME_SF = 0
FRAME_FIRST = 1
FRAME_CONSECUTIVE = 2
FRAME_FLOW = 3

FRAME_TYPE_RAW = 0
FRAME_TYPE_EXTEND = 1


class CanFrame:
    id = 0
    type = TYPE_STANDARD
    maxLen = 0
    frametype = FRAME_TYPE_RAW
    rawdata = None
    def __init__(self, id = 0, type = TYPE_STANDARD, maxLen = MAX_LEN):
        self.id = id
        self.frametype = FRAME_TYPE_RAW
        self.rawdata = None
        self.type = type
        self.maxLen = maxLen

    def build(self, data):
        self.rawdata = [0] * self.maxLen
        sz = len(data)
        idx = 0
        while idx < self.maxLen and idx < sz:
            self.rawdata[idx] = data[idx] & 0xFF
            idx += 1

        return idx

    def parse(self, rawdata):
        log.d("CanFrame: Parse")
        self.build(rawdata)
        return common.ERR_NONE

    def toString(self):
        msg = "id 0x%x type %d maxLen %d frametype %d" % (self.id, self.type, self.maxLen, self.frametype)
        return msg

class CanFrameSF(CanFrame):
    data = None
    exframetype = 0
    def __init__(self, id = 0, type = TYPE_STANDARD, maxLen = MAX_LEN):
        super(CanFrameSF, self).__init__(id, type, maxLen)
        self.data = None
        self.exframetype = FRAME_SF
        self.frametype = FRAME_TYPE_EXTEND
    
    def parse(self, rawdata):
        log.d("CanFrameSF: Parse")
        if (rawdata is not None):
            log.dumpBytes("rawdata: ", rawdata)

            self.rawdata = rawdata

            datalen = (self.rawdata[0] & 0x0F)            
            log.d("data len %d" % datalen)

            sz = len(self.rawdata) - 1
            datalen = datalen if datalen < sz else sz

            log.d("data len %d" % datalen)

            if datalen > 0:
                self.data = self.rawdata[1:datalen+1]

            log.dumpBytes("data: ", self.data)

            return common.ERR_NONE
        else:
            log.e("CanFrame: Parse failed")
            return common.ERR_INVALID

    # return >=0 on success, < 0 for error
    def build(self, data):
        log.d("CanFrame build")
        log.dumpBytes("data ", data)
        self.rawdata = [0] * self.maxLen
        sz = len(data)
        self.rawdata[0] = (sz & 0x0F)
        cnt = 1
        idx = 0
        while cnt < self.maxLen and idx < sz:
            self.rawdata[cnt] = data[idx] & 0xFF
            cnt += 1
            idx += 1
        log.d("idx %d" % idx)
        return idx

    def toString(self):
        msg = "%s exframetype %d" % (super(CanFrameSF, self).toString(),  self.exframetype)
        return msg


class CanFrameFirst(CanFrameSF):
    datalen = 0
    def __init__(self, id = 0, type = TYPE_STANDARD, maxLen = MAX_LEN):
        super(CanFrameFirst, self).__init__(id, type, maxLen)
        self.exframetype = FRAME_FIRST
        self.datalen = 0

    def parse(self, rawdata):
        
        log.dumpBytes("CanFrameFirst parse raw", rawdata)

        self.rawdata = rawdata
        sz = (self.rawdata[1] & 0xFFFF)
        sz = sz | ((self.rawdata[0] & 0x0F) << 8)
        self.datalen = sz
        sz = len(self.rawdata) - 2
        sz = self.datalen if self.datalen < sz else sz
        if sz > 0:
            self.data = self.rawdata[2:sz+2]

        log.d("datalen %d" % self.datalen)
        log.dumpBytes("data ", self.data)
        return common.ERR_NONE

    def build(self, data):
        self.rawdata = [0] * self.maxLen
        sz = len(data)
        self.rawdata[0] = ((0x1 << 4) |  (((sz & 0xFF00) >> 8) & 0x0F))
        self.rawdata[1] = (sz & 0xFF)
        
        cnt = 2
        idx = 0
        while cnt < self.maxLen and idx < sz:
            self.rawdata[cnt] = data[idx] & 0xFF
            cnt += 1
            idx += 1

        return idx

FLAG_FLOW_CONT = 0
FLAG_FLOW_WAIT = 1
FLAG_FLOW_ABORT = 2
class CanFrameFlow(CanFrameSF):
    flag = 0
    blocksize = 0
    separatetime = 0
    def __init__(self, id = 0, type = TYPE_STANDARD, maxLen = MAX_LEN):
        
        super(CanFrameFlow, self).__init__(id, type, maxLen)
        self.exframetype = FRAME_FLOW
        self.flag = 0
        self.separatetime = 0
        self.blocksize = 0

    def buildFlow(self, flag = 0, blocksize = 0, separatetime = 0):
        log.d("build Flow %d %d %d" %(flag, blocksize, separatetime))
        ret = common.ERR_NONE
        self.rawdata = [0] * self.maxLen
        self.rawdata[0] = ((0x03 << 4) & 0xF0) | (flag & 0x0F)
        self.rawdata[1] = 0xFF & blocksize
        self.rawdata[2] = 0xFF & separatetime

        log.dumpBytes("flow data: ", self.rawdata)

        self.flag = flag
        self.separatetime = separatetime
        self.blocksize = blocksize
        return ret


    def parse(self, rawdata):
        log.dumpBytes("CanFrameFlow parse raw", rawdata)
        self.flag = rawdata[0] & 0x0F
        self.blocksize = rawdata[1]
        self.separatetime = rawdata[2]
        log.d("Flow %d %d %d" %(self.flag, self.blocksize, self.separatetime))
        self.rawdata = rawdata
        return common.ERR_NONE

    def toString(self):
        msg = super(CanFrameFlow, self).toString()
        return "%s flag %d bz %d st %d" % (msg, self.flag, self.blocksize, self.separatetime)


class CanFrameConsecutive(CanFrameFirst):
    idx = 0
    def __init__(self, id = 0, idx = 0, type = 0, maxLen = MAX_LEN):
        super(CanFrameConsecutive, self).__init__(id, type, maxLen)
        self.exframetype = FRAME_CONSECUTIVE
        self.idx = idx

    def build(self, data):
        self.rawdata = [0] * self.maxLen
        sz = len(data)
        self.rawdata[0] = ((0x2 << 4) |  (self.idx & 0x0F))
        cnt = 1
        idx = 0
        while cnt < self.maxLen and idx < sz:
            self.rawdata[cnt] = data[idx] & 0xFF
            cnt += 1
            idx += 1

        return idx

    def parse(self, rawdata):
        
        log.dumpBytes("CanFrameConsecutive parse raw", rawdata)

        self.rawdata = rawdata

        self.idx = (self.rawdata[0] & 0x0F)
        sz = len(self.rawdata) - 1
        if sz > 0:
            self.data = self.rawdata[1:sz+1]

        log.d("idx %d" % self.idx)
        log.dumpBytes("data", self.data)
        return common.ERR_NONE

    def toString(self):
        msg = super(CanFrameConsecutive, self).toString()
        return "%s idx %d" % (msg,  self.idx )


def parse2CanFrame(id = 0, data = None, type = TYPE_STANDARD, maxLen = MAX_LEN, ft = FRAME_TYPE_RAW):
    log.d("parse2CanFrame 0x%x" % id)
    cf = None
    if data is not None and len(data) > 0:
        log.dumpBytes("data: ", data)
        datatype = ((data[0] >> 4) & 0x0F)
        log.d("Data type %d" % datatype)
        log.d("Frame type %d" % ft)
        if ft == FRAME_TYPE_EXTEND:
            log.d("Extend frame")
            switcher = {
                FRAME_SF:CanFrameSF(id = id, type = type, maxLen = maxLen),
                FRAME_FIRST:CanFrameFirst(id = id, type = type, maxLen = maxLen),
                FRAME_FLOW:CanFrameFlow(id = id, type = type, maxLen = maxLen),
                FRAME_CONSECUTIVE:CanFrameConsecutive(id = id, type = type, maxLen = maxLen)
            }

            cf =  switcher.get(datatype, None)
            if cf is not None:
                if cf.parse(data) != common.ERR_NONE:
                    cf = None # parse failed
            else:
                log.e("Unknow datatype %d" % datatype)
        else:
            log.d("Raw can frame")
            cf = CanFrame(id = id, type = type, maxLen = maxLen)
            if cf.parse(data) != common.ERR_NONE:
                cf = None # parse failed
    else:
        log.e("Parse cf failed, no data")
    return cf


def canMsg2Frames(canmsg):
    log.d("canMsg2Frames 0x%x" % canmsg.id)
    import can_msg_fac
    canFrames = []
    sz = len(canmsg.data)
    log.d("data sz %d" % sz)
    if sz > 0:
        log.dumpBytes("data msg: ", canmsg.data)
    if canmsg.msgType == can_msg_fac.CAN_MSG_TYPE_DIAG:
        if sz >= MAX_LEN: # 1 bytes for PCI, so max is only 7 bytes
            log.d("parse canmsg into multi frames")
            firstFrame = CanFrameFirst(id = canmsg.id, type = canmsg.type)
            n = firstFrame.build(canmsg.data)
            canFrames.append(firstFrame)
            idx = 1
            while n < sz:
                consecutiveFrame = CanFrameConsecutive(id = canmsg.id, type = canmsg.type, idx = idx)
                n += consecutiveFrame.build(canmsg.data[n:])
                canFrames.append(consecutiveFrame)
                idx = idx + 1
        else:
            log.d("single frame")
            frame = CanFrameSF(id = canmsg.id, type = canmsg.type)
            frame.build(canmsg.data)
            canFrames.append(frame)
    elif canmsg.msgType == can_msg_fac.CAN_MSG_TYPE_RAW:
            frame = CanFrame(id = canmsg.id, type = canmsg.type)
            frame.build(canmsg.data)
            canFrames.append(frame)
    else:
        log.e("Unsupported message type %d" % canmsg.msgType)
    
    log.i("convert %d bytes into %d frames" % (sz, len(canFrames)))
    for frame in canFrames:
        log.printBytes("frame %s" % frame.toString(), frame.rawdata)
    
    return canFrames
