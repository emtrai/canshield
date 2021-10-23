# Author: anhnh @ 2021

from applog import Log
from applog import DEBUG
import common
import can_msg_fac
import os
import traceback

LOG_TAG = "canmsg"

log = Log(LOG_TAG)


MAX_LEN = 8

class CanMsg:
    id = 0
    respid = 0
    type = 0
    data = []
    maxLen = MAX_LEN
    dataIdx = 0
    canFrames = None
    frameIdx = 0
    callback = None
    msgType = can_msg_fac.CAN_MSG_TYPE_RAW

    outfile = None
    arg = None

    def __init__(self, id = 0, type = can_msg_fac.TYPE_STANDARD, msgType = can_msg_fac.CAN_MSG_TYPE_RAW, callback = None):
        self.respid = 0
        self.data = []
        self.maxLen = MAX_LEN
        self.dataIdx = 0
        self.canFrames = None
        self.frameIdx = 0
        self.callback = None
        self.id = id
        self.type = type
        self.msgType = msgType
        self.outfile = None
        self.rawmsg = None
        self.arg = None


    def setCallback(self, callback):
        self.callback = callback

    def intString2ByteArray(self, datas):
        candata = []
        if datas is not None and len(datas) > 0:
            candata = []
            for data in datas:
                data = data.strip()
                if len(data) > 0:
                    candata.append(int(data, 0) & 0xFF)

        return candata
    # canid, can respid, type, maxlen, data,<outpath>
    def parse(self, msg):
        items = msg.split(",")
        ret = common.ERR_FAILED
        noItems = len(items)
        self.rawmsg = msg
        if (noItems > 4):
            self.id = int(items[0].strip(), 0)
            self.respid = int(items[1].strip(), 0)
            self.type = int(items[2].strip(), 0)
            self.maxLen = int(items[3].strip(), 0)
            # check if "<" exist
            splits = items[4].strip().split("<", 1)
            candata = []
            if splits is not None and len(splits) > 1:
                datastr = splits[0].strip()
                if len(datastr) > 0:
                    candata = self.intString2ByteArray(datastr.split(" "))
                
                fpath = splits[1].strip()
                if len(fpath) > 0 and os.path.exists(fpath):
                    try:
                        fileContent = None
                        with open(fpath) as fp:
                            fileContent = fp.read()
                        if fileContent is not None and len(fileContent) > 0:
                            candata.extend(fileContent)
                        ret = common.ERR_NONE
                    except:
                        traceback.print_exc()
                        ret = common.ERR_EXCEPTION
                else:
                    log.e("parse can msg failed, 's' not found" % fpath)
                    ret = common.ERR_INVALID
            else:
                candata = self.intString2ByteArray(items[4].strip().split(" "))
                ret = common.ERR_NONE

            if ret == common.ERR_NONE and len(candata) > 0:
                self.setData(candata)
            else:
                log.e("%s: no data" % self.id)
                ret = common.ERR_NO_DATA if ret == common.ERR_NONE else ret

        else:
            log.e("empty")
            ret = common.ERR_NO_DATA

        if ret == common.ERR_NONE and noItems > 5:
            outfile = items[5].strip()
            if outfile is not None and len(outfile) > 0:
                self.outfile = outfile

        if DEBUG:
            log.d("id 0x%x respid 0x%x maxlen %d" % (self.id, self.respid, self.maxLen))
            log.dumpBytes("can data: ", self.data)
        return ret

    def addData(self, data):
        sz = len(self.data)
        if self.maxLen > 0:
            remain = (self.maxLen - sz) if self.maxLen > sz else sz
        else:
            remain = sz
        if self.data is None or len(self.data) == 0:
            self.data = data[:remain]
        else:
            self.data.extend(data[:remain])
        log.dumpBytes("add data, total: ", self.data)
        # size = len(data)
        # for i in range(MAX_LEN):
        #     if (i < size):
        #         self.data[i] = data[i]
        #     else:
        #         self.data[i] = 0
        
        # self.dataIdx = 0
    
    def setData(self, data):
        self.data = data
        log.dumpBytes("setData: ", self.data)
        self.dataIdx = 0

    def getData(self, nData):
        ret = None
        n = len(self.data)
        if self.dataIdx  <n:
            endidx = self.dataIdx + nData
            if endidx > n:
                endidx = n
            ret = self.data[self.dataIdx:endidx]
            self.dataIdx = endidx
        return ret


    def sendTo(self, candev):
        return candev.send(self)

    def toString(self):
        return "0x%x,0x%x,0x%x,0x%x,%s" % (self.id, self.respid, self.type, self.maxLen, str(self.data))


    def getFrame(self):
        cf = None
        if self.canFrames is not None and self.frameIdx < len(self.canFrames):
            cf = self.canFrames[self.frameIdx]
            self.frameIdx += 1
        else:
            cf = None
        return cf
    def getCurrentIdx(self):
        return self.frameIdx

    def getRemainFrame(self):
        return len(self.canFrames) - self.frameIdx
    

class CanMsgResp(CanMsg):
    canmsg = None
    
    timeout = 0
    maxtimeout = 0
    starttime = 0
    def __init__(self, id=0, canmsg = None):
        super().__init__(id=id)
        self.canmsg = canmsg

        self.timeout = 0
        self.starttime = 0
        self.maxtimeout = 0

    def isTimeout(self):
        if self.canmsg is not None:
            curr = common.current_milli_time()
            return (curr > self.timeout)
        else:
            return True


    def isMaxTimeout(self):
        if self.canmsg is not None:
            curr = common.current_milli_time()
            return (curr > self.maxtimeout)
        else:
            return True


    def isFull(self):
        curlen = len(self.data)
        return curlen >= self.maxLen


