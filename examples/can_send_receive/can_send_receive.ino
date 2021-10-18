// demo: CAN-BUS Shield, receive data with interrupt mode
// when in interrupt mode, the data coming can't be too fast, must >20ms, or else you can use check mode
// loovee, 2014-6-13

#include <SPI.h>

#define CAN_2515
// #define CAN_2518FD

// Set SPI CS Pin according to your hardware

#if defined(SEEED_WIO_TERMINAL) && defined(CAN_2518FD)
// For Wio Terminal w/ MCP2518FD RPi Hat：
// Channel 0 SPI_CS Pin: BCM 8
// Channel 1 SPI_CS Pin: BCM 7
// Interupt Pin: BCM25
const int SPI_CS_PIN  = BCM8;
const int CAN_INT_PIN = BCM25;
#else

// For Arduino MCP2515 Hat:
// the cs pin of the version after v1.1 is default to D9
// v0.9b and v1.0 is default D10
const int SPI_CS_PIN = 10;
const int CAN_INT_PIN = 2;
#endif


#ifdef CAN_2518FD
#include "mcp2518fd_can.h"
mcp2518fd CAN(SPI_CS_PIN); // Set CS pin
#endif

#ifdef CAN_2515
#include "mcp2515_can.h"
mcp2515_can CAN(SPI_CS_PIN); // Set CS pin
#endif


#define TAG_DELIMITER ':'
#define TAG_LOG "log"
#define TAG_CONFIG "cfg"
#define TAG_RESP "rsp"
#define TAG_SEND "snd"
#define TAG_CAN "can"
#define TAG_MASK "msk"
#define TAG_FILTER "flt"

#define VAL_DELIMITER ','

#define DELIMITER ','
#define END_IN_STRING '\n'
#define MAX_IN_STRING_LEN 128

#define ERR_NONE (0)
#define ERR_FAILED (-1)
#define ERR_INPUT_INVALID (-2)
#define ERR_INPUT_INVALID (-2)

//#define DEBUG_ENABLE

#ifdef DEBUG_ENABLE
#define LOGD(data) do{ resplog(data); \
                    } while(0)
#define LOGDV(data) do{ resplogV(data); \
                    } while(0)
#else// !DEBUG_ENABLE
#define LOGD(data) void()
#define LOGDV(data) void()
#endif //DEBUG_ENABLE


#define MAX_ARG_NUM 10

unsigned char flagRecv = 0;
unsigned char len = 0;
unsigned char buf[8];
char str[20];

void printTag(const char* tag){
  if (tag != NULL){
    SERIAL_PORT_MONITOR.print(tag);
    SERIAL_PORT_MONITOR.print(TAG_DELIMITER);
  }
}

void resp(const char* tag, const char* data, unsigned char newline = 1){
  printTag(tag);
  SERIAL_PORT_MONITOR.print(data);
  if (newline){
    SERIAL_PORT_MONITOR.println();
  }
}

void respVal(const char* tag, long val, unsigned char type=DEC, unsigned char newline = 1){
  printTag(tag);
  SERIAL_PORT_MONITOR.print(val, type);
  if (newline){
    SERIAL_PORT_MONITOR.println();
  }
}

void resplogHigh(const char* data, unsigned char newline = 1){
  resp(TAG_LOG, data, newline);
}

void resplogHigh2(const char* data, int val, unsigned type=DEC){
  printTag(TAG_LOG);
  SERIAL_PORT_MONITOR.print(data);
  SERIAL_PORT_MONITOR.print(val, type);
  SERIAL_PORT_MONITOR.println();
}
void resplogHigh3(const char* msg, const char* data, int len=8, unsigned type=HEX){
  int i = 0;
  printTag(TAG_LOG);
  if (msg != NULL){
    SERIAL_PORT_MONITOR.print(msg);
  }
  for (i = 0; i < len; i++){
    SERIAL_PORT_MONITOR.print(data[i] & 0xFF, type);
    SERIAL_PORT_MONITOR.print(" ");
  }
  SERIAL_PORT_MONITOR.println();
}

void resplog(const char* data, unsigned char newline = 1){
#ifdef DEBUG_ENABLE
  resplogHigh(data, newline);
#endif //DEBUG_ENABLE
}

void resplog2(const char* data, int val, unsigned type=DEC){
#ifdef DEBUG_ENABLE
  resplogHigh2(data, val, type);
#endif //DEBUG_ENABLE
}
void resplog3(const char* msg, const char* data, int len=8, unsigned type=HEX){
#ifdef DEBUG_ENABLE
  resplogHigh3(msg, data, len, type);
#endif //DEBUG_ENABLE
}

void resplogV(long val, unsigned char type=DEC, unsigned char newline = 1){
#ifdef DEBUG_ENABLE
  respVal(TAG_LOG, val, type, newline);
#endif //DEBUG_ENABLE
}


void respErr(int err){
  respVal(TAG_RESP, (int)err, DEC);
}

void respCAN(const char* data){
 resp(TAG_CAN, data, 1);
}



String tag = "";
String value = "";
int inStringCnt = 0;
unsigned char isVal = 0;

unsigned char num_args = 0;

String args[MAX_ARG_NUM];


void resetInput(){
  LOGD("resetInput");
  tag = "";
  value = "";
  inStringCnt = 0;
  isVal = 0;
  num_args = 0;
}
int getInput(){
  
  int ret = 0;
  if (Serial.available())  {
    char c = Serial.read();
    if (c == END_IN_STRING){
      LOGD("End string");
      LOGD(tag.c_str());
      LOGD(value.c_str());
      LOGDV(inStringCnt);
      ret = inStringCnt;
      return ret;
    }

    if (isVal == 0){
      if (c == TAG_DELIMITER){
        isVal = 1;
        value = "";
      }
      else
      {
        tag += c;
      }
    }
    else{
      value += c;
    }
    inStringCnt++;   
    if (inStringCnt >= MAX_IN_STRING_LEN){
      ret = ERR_INPUT_INVALID;
      LOGD("Max, out with error");
      resetInput();
    }
  }
  return ret;
}


int parseInput(){
  LOGD("Parse Input:");
  LOGD(value.c_str());
  if (value.length() > 0){
    int i = 0;
    int idx = 0;
    num_args = 0;
    args[idx] = "";
    for (i = 0; i < value.length(); i++){
      if (value[i] != VAL_DELIMITER){
        args[idx] += value[i];
      }
      else{
        LOGD(args[idx].c_str());
        idx++;
        args[idx] = "";
      }
    }
    num_args = (args[idx].length() > 0)?idx + 1:idx;
  }
  LOGD("num_args:");
  LOGDV(num_args);
  return num_args;
}

void setMask(unsigned int mask){
    resplogHigh2("setMask ", mask, HEX);
    CAN.init_Mask(0, 0, mask);                         // there are 2 mask in mcp2515, you need to set both of them
    CAN.init_Mask(1, 0, mask);
}

void setFilter(unsigned int filter){
    resplogHigh2("setFilter ", filter, HEX);
    CAN.init_Filt(0, 0, filter);                          // there are 6 filter in mcp2515
    CAN.init_Filt(1, 0, filter);                          // there are 6 filter in mcp2515

    CAN.init_Filt(2, 0, filter);                          // there are 6 filter in mcp2515
    CAN.init_Filt(3, 0, filter);                          // there are 6 filter in mcp2515
    CAN.init_Filt(4, 0, filter);                          // there are 6 filter in mcp2515
    CAN.init_Filt(5, 0, filter);                          // there are 6 filter in mcp2515
}
//#define SERIAL_SPEED 115200
#define SERIAL_SPEED 921600
void setup() {
    SERIAL_PORT_MONITOR.begin(SERIAL_SPEED);
    while (!SERIAL_PORT_MONITOR) {
        ; // wait for serial port to connect. Needed for native USB port only
    }
    SERIAL_PORT_MONITOR.setTimeout(200);
    attachInterrupt(digitalPinToInterrupt(CAN_INT_PIN), MCP2515_ISR, FALLING); // start interrupt
    while (CAN_OK != CAN.begin(CAN_500KBPS, MCP_8MHz)) {             // init can bus : baudrate = 500k
        resplog("CAN init fail, retry...");
        delay(100);
    }
    setMask(0x600);
    setFilter(0x600);
    resplog("CAN init ok!");
}

void MCP2515_ISR() {
    flagRecv = 1;
}

#define MAX_DATA_SIZE 8
uint32_t id;
uint8_t  type; // bit0: ext, bit1: rtr
byte cdata[MAX_DATA_SIZE] = {0};
/* Displayed type:
 *
 * 0x00: standard data frame
 * 0x02: extended data frame
 * 0x30: standard remote frame
 * 0x32: extended remote frame
 */
static const byte type2[] = {0x00, 0x02, 0x30, 0x32};

void canReceive(){
    if (flagRecv) {
        LOGD("interrupt raised");
        flagRecv = 0;                   // clear flag
        if (CAN_MSGAVAIL != CAN.checkReceive()) {
            return;
        }
        
        LOGD("parse can receive");
        static char prbuf[32 + MAX_DATA_SIZE * 3];
        int i, n = 0;
    

        memset(cdata, 0, sizeof(cdata));
        memset(prbuf, 0, sizeof(prbuf));
        // read data, len: data length, buf: data buf
        CAN.readMsgBuf(&len, cdata);
    
        id = CAN.getCanId();
        type = (CAN.isExtendedFrame() << 0) |
               (CAN.isRemoteRequest() << 1);


        n += sprintf(prbuf, "0x%08lX,0x%02X,0x%02X,", (unsigned long)id, type2[type], len);

        for (i = 0; i < len; i++) {
            n += sprintf(prbuf + n, "0x%02X ", cdata[i]);
        }
        respCAN(prbuf);
    }
}


void canSend(){
  if (num_args > 3){
    id = strtol(args[0].c_str(), 0, 16);
    type = strtol(args[1].c_str(), 0, 16);
    len = strtol(args[2].c_str(), 0, 16);
    
    if (args[3].length() > 0){
      String* candata = &args[3];
      int i = 0;
      int idx = 0;
      int num_args = 0;
      memset(cdata, 0, sizeof(cdata));
      char* command = strtok(candata->c_str(), " ");
      while (command != 0)
      {
          cdata[idx] = strtol(command, 0, 16);
          idx++;
          if (idx > MAX_DATA_SIZE)
            break;
          // Find the next command in input string
          command = strtok(0, " ");
      }
      if (idx > 0){
        resplogHigh2("send 0x", id, HEX);
//        resplogHigh3("send data ", cdata, MAX_DATA_SIZE, HEX);
        resplogHigh3("send data ", cdata, MAX_DATA_SIZE, HEX);
        int ret = CAN.sendMsgBuf(id, type, len, cdata);
        resplogHigh2("ret", ret);
      }
      else{
        resplog("no data to send");
      }
    }
  }
}


static const byte testdta[MAX_DATA_SIZE] = {0x02, 0x19, 0x01, 0, 0, 0, 0, 0};
static long testid = 0x00;
void sendTest(){
  resplog3("Send test data: ", testdta);
  int ret = CAN.sendMsgBuf(testid, 0, 8, testdta);
  resplogV(ret);
  
  delay(1000);
}
void loop() {
//  SERIAL_PORT_MONITOR.println("loop");

//  sendTest();
  canReceive();
  int ret = getInput();
  if (ret > 0){
    ret = parseInput();
    if (ret > 0){
      if (tag == TAG_CAN){
        canSend();
      }
      else
      if (tag == TAG_MASK && num_args > 0){
        int mask = strtol(args[0].c_str(), 0, 16);
        setMask(mask);
      }
      else
      if (tag == TAG_FILTER && num_args > 0){
        int mask = strtol(args[0].c_str(), 0, 16);
        setFilter(mask);
      }
//#ifdef DEBUG
//    {
//      int i = 0;
//      for (i = 0; i < ret; i++){
//        LOGD(args[i].c_str());
//      }
//    }
//#endif
    }
    else{
      // no input, do nothing
    }
    resetInput();
  }
  else if (ret < 0){ // faild
    
  }
  else{
    // do nothing
  }

}

/*********************************************************************************************************
    END FILE
*********************************************************************************************************/
