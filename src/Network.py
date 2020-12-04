import socket
import datetime
import pickle
import io
from math import ceil, log2
from enum import IntEnum

from src.Config import get_logger, DATE_TIME_FORMAT, DEFAULT_TIME
import src.utils as utils


HEADER_SIZE = 8
MAX_RECV_SIZE = 4096
CODE_SIZE = 1  # one byte
ENCODING = "utf-8"


logger_name, logger = get_logger(__name__)

class NT_Enum(IntEnum):
    def __str__(self):
        return self.name
    
    def bytes(self):
        return self.to_bytes(CODE_SIZE, byteorder='big')

class NT_Code(NT_Enum): # (NT = Network)
    END_MSG = 0
    END_CONN = 10
    REQ_DIR_LST = 110
    REQ_DIR_ATTR = 120
    REQ_DIR_GRAPH = 130
    REQ_FILE = 140
    REQ_SYNC = 150
    SYNC_DONE = 200
    
class NT_MSG_TYPE(NT_Enum):
    UNDEF = 0xFF
    CODE = 0x1
    INT = 0x2
    STR = 0x4
    OBJ = 0x8
    FILE = 0x01
    
    

class Socket:
    def __init__(self, sock=None):
        if sock is None:  self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else: self.socket = sock
        self._recv_msg_type = False
        
    def bind(self, ip, port): self.socket.bind((ip, port))    
    def listen(self): self.socket.listen()
    def accept(self): return self.socket.accept()
    def connect(self, host, port): self.socket.connect((host, port)) 
    def close(self): self.socket.close()
    
    def _send(self, type, bytes): 
        self.socket.sendall(type.bytes() + 
                            len(bytes).to_bytes(HEADER_SIZE, byteorder="big") + 
                            bytes + 
                            NT_Code.END_MSG.bytes())
        
    def send_code(self, code):
        self._send(NT_MSG_TYPE.CODE, code.bytes())
        
    def send_int(self, num:int):
        self._send(NT_MSG_TYPE.INT, num.to_bytes(ceil(log2(num)/8), byteorder='big'))

    def send_str(self, msg:str):
        self._send(NT_MSG_TYPE.STR, bytes(str(msg), ENCODING))
        
    def send_obj(self, obj, pickle_obj=True):
        if pickle_obj: obj = pickle.dumps(obj)
        self._send(NT_MSG_TYPE.OBJ, obj)

    def send_file(self, path):
        with open(path, "rb") as file:
            self._send(NT_MSG_TYPE.FILE, file.read())
    
    def send(self, msg):
        assert(not isinstance(msg, io.IOBase))
        if isinstance(msg, NT_Enum): self.send_code(msg)
        elif isinstance(msg, int): self.send_int(msg)
        elif isinstance(msg, str): self.send_str(msg)
        else: self.send_obj(msg)
        
    def send_multi(self, *msgs):
        for msg in msgs: 
            self.send(msg)
        self.send_code(NT_Code.END_MSG)
        
    def _recv_header(self, expected_type):
        if self._recv_msg_type is True: msg_type = NT_MSG_TYPE(int.from_bytes(self.socket.recv(CODE_SIZE), "big"))
        else:  msg_type = NT_MSG_TYPE.UNDEF
        assert(expected_type & msg_type)
        msg_len = int.from_bytes(self.socket.recv(HEADER_SIZE), "big")
        return msg_len

    def _recv_data(self, msglen, file=None): # data should be written to file if specified
        #? maybe use select module
        data = []
        bytes_received = 0
        while bytes_received < msglen:
            receive_size = MAX_RECV_SIZE if msglen - bytes_received > MAX_RECV_SIZE else msglen - bytes_received
            data.append(self.socket.recv(receive_size))
            bytes_received += len(data[-1])
            if file is not None: file.write(data[-1])
        assert(int.from_bytes(self.socket.recv(CODE_SIZE), "big") == NT_Code.END_MSG)
        return b''.join(data)
    
    def recv_code(self):
        msg_len = self._recv_header(NT_MSG_TYPE.CODE)
        return NT_Code(int.from_bytes(self._recv_data(msg_len), byteorder="big"))
    
    def recv_int(self):
        msg_len = self._recv_header(NT_MSG_TYPE.INT)
        return int.from_bytes(self._recv_data(msg_len), byteorder="big")
    
    def recv_str(self):
        msg_len = self._recv_header(NT_MSG_TYPE.STR)
        return self._recv_data(msg_len).decode(ENCODING)
        
    def recv_obj(self, unpickle=True):
        msg_len = self._recv_header(NT_MSG_TYPE.OBJ)
        return pickle.loads(self._recv_data(msg_len)) if unpickle else self._recv_data(msg_len)
        
    def recv_file(self, store_path):
        msg_len = self._recv_header(NT_MSG_TYPE.FILE)
        with open(store_path, "wb") as file:
            self._recv_data(msg_len, file)
    
    def recv(self):
        self._recv_msg_type = False
        msg_type = int.from_bytes(self.socket.recv(CODE_SIZE), byteorder="big")
        data = {
                NT_MSG_TYPE.CODE : self.recv_code,
                NT_MSG_TYPE.INT : self.recv_int,
                NT_MSG_TYPE.STR : self.recv_str,
                NT_MSG_TYPE.OBJ : self.recv_obj
            }[msg_type]()
        self._recv_msg_type = True
        return data
        
    def recv_multi(self):
        ret = []
        while True:
           data = self.recv()
           if data == NT_Code.END_MSG: break
           else: ret.append(data)
        return ret

    