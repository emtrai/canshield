from applog import Log
import common

TAG = "canframe"

log = Log(TAG)



MAX_LEN = 8

FRAME_SF = 0
FRAME_FIRST = 1
FRAME_CONSECUTIVE = 2
FRAME_FLOW = 3

TYPE_STANDARD = 0


class CanFrame:
    id = 0
    type = TYPE_STANDARD
    maxLen = 0
    frametype = 0
    rawdata = None
    data = None
    def __init__(self, id = 0, type = TYPE_STANDARD, maxLen = MAX_LEN):
        self.id = id
        self.frametype = FRAME_SF
        self.rawdata = None
        self.data = None
        self.type = type
        self.maxLen = maxLen
    
    def parse(self, rawdata):
        log.d("CanFrame: Parse")
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

    def build(self, data):
        self.rawdata = []
        sz = len(data)
        self.rawdata.append(len(data) & 0x0F)
        
        self.rawdata.append(data)
        sz = len(self.rawdata)
        if sz < self.maxLen:
            remain = self.maxLen - sz
            self.rawdata[sz:] = [0]*remain
        return common.ERR_NONE


class CanFrameFirst(CanFrame):
    datalen = 0
    def __init__(self, id = 0, type = TYPE_STANDARD, maxLen = MAX_LEN):
        super(CanFrameFirst, self).__init__(id, type, maxLen)
        self.frametype = FRAME_FIRST
        self.datalen = 0

    def parse(self, rawdata):
        self.rawdata = rawdata
        sz = (self.rawdata[0] & 0xFFFF) << 8
        sz = sz | (self.rawdata[1] & 0xFF)
        self.datalen = sz
        sz = len(self.rawdata) - 2
        sz = self.datalen if self.datalen < sz else sz
        if sz > 0:
            self.data = self.rawdata[1:sz+2]

        return common.ERR_NONE

    def build(self, data):
        self.rawdata = []
        sz = len(data)
        self.rawdata.append((0x1 << 4) |  (((sz & 0xFF00) >> 8) & 0x0F))
        self.rawdata.append(sz & 0xFF)
        
        self.rawdata.append(data)
        sz = len(self.rawdata)
        if sz < self.maxLen:
            remain = self.maxLen - sz
            self.rawdata[sz:] = [0]*remain
        return common.ERR_NONE

FLAG_FLOW_CONT = 0
FLAG_FLOW_WAIT = 1
FLAG_FLOW_ABORT = 2
class CanFrameFlow(CanFrame):
    flag = 0
    blocksize = 0
    separatetime = 0
    def __init__(self, id = 0, type = TYPE_STANDARD, maxLen = MAX_LEN):
        
        super(CanFrameFlow, self).__init__(id, type, maxLen)
        self.frametype = FRAME_FLOW
        self.flag = 0
        self.separatetime = 0
        self.blocksize = 0

    def buildFlow(self, flag = 0, blocksize = 0, separatetime = 0):
        log.d("build Flow %d %d %d" %(flag, blocksize, separatetime))
        ret = common.ERR_FAILED
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
        log.d("Parse flow: ", rawdata)
        self.flag = rawdata[0] & 0x0F
        self.blocksize = rawdata[1]
        self.separatetime = rawdata[2]
        log.d("Flow %d %d %d" %(self.flag, self.blocksize, self.separatetime))


class CanFrameConsecutive(CanFrameFirst):
    idx = 0
    def __init__(self, id = 0, idx = 0, type = 0, maxLen = MAX_LEN):
        super(CanFrameConsecutive, self).__init__(id, type, maxLen)
        self.frametype = FRAME_CONSECUTIVE
        self.idx = idx


def parse2CanFrame(id = 0, data = None, type = TYPE_STANDARD, maxLen = MAX_LEN):
    log.d("parse2CanFrame 0x%x", id)
    cf = None
    if data is not None and len(data) > 0:
        log.dumpBytes("data: ", data)
        datatype = ((data[0] >> 4) & 0x0F)
        log.d("Data type %d" % datatype)

        switcher = {
            FRAME_SF:CanFrame(id = id, type = type, maxLen = maxLen),
            FRAME_FIRST:CanFrameFirst(d = id, type = type, maxLen = maxLen),
            FRAME_FLOW:CanFrameFlow(d = id, type = type, maxLen = maxLen),
            FRAME_CONSECUTIVE:CanFrameConsecutive(id = id, type = type, maxLen = maxLen)
        }

        cf =  switcher.get(datatype, None)
        if cf is not None:
            if cf.parse(data) != common.ERR_NONE:
                cf = None # parse failed
        else:
            log.e("Unknow datatype %d" % datatype)
    else:
        log.e("Parse cf failed, no data")
    return cf


def canMsg2Frames(canmsg):
    canFrames = []
    sz = len(canmsg.data)
    if sz > MAX_LEN:
        firstFrame = CanFrameFirst(id = canmsg.id, type = canmsg.type)
        n = firstFrame.build(canmsg.data)
        canFrames.append(firstFrame)
        idx = 1
        while n < sz:
            consecutiveFrame = CanFrameConsecutive(id = canmsg.id, type = canmsg.type, idx = idx)
            n += consecutiveFrame.build(canmsg.data[n:])
            canFrames.append(firstFrame)
            idx = idx + 1
    else:
        frame = CanFrame(id = canmsg.id, type = canmsg.type)
        frame.build(canmsg.data)
        canFrames.append(frame)

    return canFrames
