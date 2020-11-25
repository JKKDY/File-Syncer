import socket
from enum import IntEnum, auto
import pickle
from threading import Thread, Lock, Event


CODE_SIZE = 1
HEADER_SIZE = 8


STATUS_DISCONNECTED = 0
STATUS_AVAILABLE = 1
STATUS_CONNECTED = 2
STATUS_PENDING = 3
    

class UI_Code(IntEnum):
    REQ_UUIDS = auto()
    REQ_UUID_NAME = auto()
    REQ_UUID_INFO = auto()
    REQ_UUID_STATUS = auto()
    REQ_DIRS = auto()
    REQ_DIR_GRAPH = auto()
    REQ_DIR_IGN_PATTERS = auto()
    
    UPDATE_UUID = auto()
    UPDATE_STATUS = auto()
    
    ADD_CONNECTION = auto()
    UUID_CONNECT = auto()
    UUID_DISCONNECT = auto()
    
    BEGINN_REQ = auto()
    END_REQ = auto()
    UI_CLOSE = auto()
    
    def __str__(self):
        return self.name
    
    def bytes(self):
        return self.to_bytes(CODE_SIZE, byteorder='big')
    
    
    
    
class Socket:
    def __init__(self, sock=None):
        if sock is None: self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else: self.socket = sock
        self.lock = Lock()
    
    def send_code(self, code):
        self.socket.sendall(code.bytes())
        
    def recv_code(self):
        ret = int.from_bytes(self.socket.recv(CODE_SIZE), "big")
        return ret
        
    def send(self, *data):
        pickle_data = pickle.dumps(data)
        self.socket.sendall(len(pickle_data).to_bytes(HEADER_SIZE, "big") + pickle_data)
    
    def recv(self):
        b = self.socket.recv(HEADER_SIZE)
        size = int.from_bytes(b, "big")
        data = pickle.loads(self.socket.recv(size))
        return data
    
    def close(self): self.socket.close()
    def connect(self, port): self.socket.connect(("localhost", port))
    def bind(self, port): self.socket.bind(("localhost", port))
    def get_port(self): return self.socket.getsockname()[1]
    
    
    
    
    
# Problem:
# cannot handle multiple concurrent requests
# reqests are handled sequentially i.e a request must be finished 
# before antoher one can be started.
# Consequence of this can be seen when initializing mulitple connections
# over UI at the same time: UI will seem unresponsive
    
    
class UiBackend:
    def __init__(self, port, callbacks):
        self.port = port
        self.callbacks = callbacks
        self.shutdown = False
        self.connected = False
        
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind(("localhost", port))
        
        self.req_socket = None # handles requests from UI
        self.notif_socket = None # notifies UI 
        
        self.thread = Thread(target=self._start_main_loop, name="ui_server_thread")
    
    def recv(self): return self.req_socket.recv()
    def send(self, *data): self.req_socket.send(*data)
        
    def start(self):
        self.thread.start()
        
    def _start_main_loop(self):
        while not self.shutdown:
            try:
                self.socket.listen(2)
                self.req_socket = Socket(self.socket.accept()[0]) # handles requests from frontend
                self.notif_socket = Socket(self.socket.accept()[0]) # notifes fronend
                self.connected = True
            except socket.error as e:
                print("shut start loop", e)
                self.connected = False
                return
            
            while True:
                try:
                    code = self.req_socket.recv_code()
                    if code == UI_Code.UI_CLOSE: break
                    args = self.req_socket.recv()
                    fkt = self.callbacks[code]
                    self.req_socket.send(fkt(*args) if args !=() else fkt())
                except socket.error as e:
                    print("shut down event loop", e)
                    break
            self.connected = False
            
    def notify(self, code, *data):
        if self.connected:
            self.notif_socket.send_code(code)
            self.notif_socket.send(*data)
        
    def shut_down(self):
        self.shutdown = True
        self.socket.close()
        if self.req_socket is not None and self.notif_socket is not None:
            if self.connected: self.notif_socket.send_code(UI_Code.UI_CLOSE)
            self.req_socket.close()
            self.notif_socket.close()
        
        

        
        
        

class UiFrontend:
    def __init__(self, port, callbacks):
        self.callbacks = callbacks
        self.lock = Lock()
        self.ready = Event()
        self.req_socket = Socket() # sends requests to backend
        self.notif_socket = Socket() # handles notifications from backend
        self.req_socket.connect(port)
        self.notif_socket.connect(port)
        self.event_thread = Thread(target=self.event_loop)
        self.ready.set()

    def recv(self): return self.notif_socket.recv()
    def send(self, *data): self.notif_socket.send(*data)
        
    def request(self, code, *args):
        with self.lock:
            self.ready.wait()
            self.req_socket.send_code(code)
            self.req_socket.send(*args)
            return self.req_socket.recv()[0]
        
    def start_event_loop(self, blocking=False):
        self.event_thread.start()
        if blocking: self.event_thread.join()
        
    def event_loop(self):
        while True:
            try:
                code = self.notif_socket.recv_code()
                if code == UI_Code.UI_CLOSE: break
                args = self.notif_socket.recv()
                fkt = self.callbacks[code]
                fkt(*args) if args !=() else fkt()
            except socket.error:
                print("shut down event loop")
                break
        
    def close(self):
        self.req_socket.send_code(UI_Code.UI_CLOSE)
        self.req_socket.close()
        self.event_thread.join()
        
