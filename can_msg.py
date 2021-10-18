from applog import Log
import common

LOG_TAG = "canmsg"

log = Log(LOG_TAG)


TYPE_STANDARD = 0

MAX_LEN = 8

class CanMsg:
    id = 0
    respid = 0
    type = 0
    data = []
    maxLen = MAX_LEN
    timeout = 0
    starttime = 0
    dataIdx = 0
    canFrames = None
    frameIdx = 0
    callback = None

    def __init__(self):
        self.id = 0
        self.respid = 0
        self.type = 0
        self.data = []
        self.maxLen = MAX_LEN
        self.timeout = 0
        self.starttime = 0
        self.dataIdx = 0
        self.canFrames = None
        self.frameIdx = 0
        self.callback = None


    def __init__(self, id = 0, type = TYPE_STANDARD):
        self.__init__()
        self.id = id
        self.type = type

    @staticmethod
    def parse(msg):
        ret = common.ERR_NO_DATA
        if msg is not None and len(msg) > 0:
            canmsg = CanMsg()
            ret = canmsg.parse(msg)
        return ret

    def parse(self, msg):
        items = msg.split(",")
        ret = common.ERR_FAIED
        if (len(items) > 3):
            self.id = int(items[0].strip(), 0)
            self.respid = int(items[1].strip(), 0)
            self.type = int(items[2].strip(), 0)
            datas = items[3].strip().split(" ")
            if len(datas) > 0:
                candata = []
                for data in datas:
                    data = data.strip()
                    if len(data) > 0:
                        candata.append(int(data, 0))
                if len(candata) > 0:
                    self.addData(candata)
                    ret = common.ERR_NONE
                else:
                    log.e("%s: no data" % self.id)
                    ret = common.ERR_NO_DATA
            else:
                log.e("%s: no data" % self.id)
                ret = common.ERR_NO_DATA
        else:
            log.e("empty")
            ret = common.ERR_NO_DATA
        return ret

    def addData(self, data):
        self.data.append(data)
        # size = len(data)
        # for i in range(MAX_LEN):
        #     if (i < size):
        #         self.data[i] = data[i]
        #     else:
        #         self.data[i] = 0
        
        # self.dataIdx = 0
    
    def setData(self, data):
        self.data = data
        
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
        return "0x%x,0x%x,0x%x,%s" % (self.id, self.type, MAX_LEN, str(self.data))

    def getFrame(self):
        cf = self.canFrames[self.frameIdx]
        self.frameIdx += 1
        return cf
    def getRemainFrame(self):
        return len(self.canFrames) - self.frameIdx
    

class CanMsgResp(CanMsg):
    canmsg = None
    
    def __init__(self, id=0, canmsg = None):
        super().__init__(id=id)
        self.canmsg = canmsg

    def isTimeout(self):
        if self.canmsg is not None:
            curr = common.current_milli_time()
            return (curr > self.canmsg.timeout)
        else:
            return True

