# canshield
Can shield sample code

```
usage: can.py [-h] [--dev DEV] [--port PORT] [--speed SPEED] [--script SCRIPT] [--cmd CMD] [--canid CANID] [--flow FLOW]

Test can

optional arguments:
  -h, --help       show this help message and exit
  --dev DEV        CAN device to be used
  --port PORT      Port config
  --speed SPEED    Speed config
  --script SCRIPT  Text to contains CAN message
  --cmd CMD        Command to be used
  --canid CANID    canid[,respid] : Can id to be used, and response can id if any
  --flow FLOW      [name],[script file] : flow <name> to be run with script if any
```

# Prerequisite
pip3 install multiprocessing
pip3 install pyserial
pip3 install threading
