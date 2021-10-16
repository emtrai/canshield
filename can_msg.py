
TYPE_STANDARD = 0

class CanMsg:
    id = 0
    type = 0
    maxLen = 8
    data = []

    def __init__(self):
        self.id = 0
        self.type = 0
        self.maxLen = 8
        self.data = []

    def __init__(self, id = 0, type = TYPE_STANDARD, maxLen = 8):
        self.id = id
        self.type = type
        self.maxLen = maxLen
        self.data = [0] * maxLen

    def addData(self, data):
        size = len(data)
        for i in range(self.maxLen):
            if (i < size):
                self.data[i] = data[i]
            else:
                self.data[i] = 0

    def sendTo(self, candev):
        return candev.send(self)

    def toString(self):
        return "0x%x,0x%x,0x%x,%s" % (self.id, self.type, self.maxLen, str(self.data))
    

