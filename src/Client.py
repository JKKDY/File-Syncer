import datetime
import logging
import os
import pickle
import select
import shutil
import socket
from collections import deque
from threading import Event
import copy


from src.Config import get_logger, DEFAULT_TIME
from src.utils import update_with_nested_dict, hash_file
from src.Network import Socket, NT_Code
    

logger_name, logger = get_logger(__name__)



     
class SyncQueue:
    def __init__(self, sync_func):
        self.queue = deque()
        self.sync_func = sync_func
        self.running_event = Event()
        self.running_event.set()
        
    def add_sync(self, *args, **kwargs):
        if ((args, kwargs)) not in self.queue:
            self.queue.append((args, kwargs))
            if self.running_event.is_set():
                self.run_next()
            self.running_event.wait()
     
    def run_next(self):
        self.running_event.clear()
        while self.queue:
            args, kwargs = self.queue.popleft()
            self.sync_func(*args, **kwargs)
        self.running_event.set()
        
    


class Client(Socket):
    def __init__(self, uuid, sessions, file_tracker, log_settings):
        super().__init__()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.uuid = uuid
        self.file_tracker = file_tracker
        self.sync_queue = SyncQueue(self._sync_directories)
        self.sessions = sessions
        self.logging_settings = log_settings
        
        # will be initilized in self.connect
        self.logger = None 
        self.server_hostname = None
        self.server_port = None
        self.server_uuid = None
        self.connected = False
        
    def connect(self, hostname, port):
        self.server_hostname, self.server_port = hostname, port
        super().connect(hostname, port)
        self.connected = True  
        
        uuid, dir_info = self.recv_multi()
        self.server_uuid = uuid
        self.sessions.start(self.server_uuid)
        
        self.logger = self.logging_settings.create_logger(f"{logger_name}.Client->{self.server_uuid}", f"traffic@{self.server_uuid}.log")
        self.logger.info("Start session")
        self.logger.info(f"Client connected to {self.conn_str()}")
        return uuid, dir_info
    
    def close(self):
        if self.connected:
            self.connected = False
            self.send_code(NT_Code.END_CONN)
            self.logger.info(f"Client disconnected from {self.conn_str()}")
            self.sessions.end(self.server_uuid)
            self.logger.info("End session")
            logger.info(f"Shut down Client connected to {self.conn_str()}")
        super().close()
        self.logger.info("Client socket closed")  
    
    def conn_str(self): # used for logging
        return f"{self.server_uuid} @ (hostname: {self.server_hostname}, port: {self.server_port})"
   
    def sync(self, local_dir, remote_dir, bi_directional_sync=True, time_out=None, auto_sync=0, add_to_queue=True):
        self.logger.debug(f"Add to queue: sync local directory '{local_dir}' with remote directory '{remote_dir}'")
        self.sync_queue.add_sync(local_dir, remote_dir, bi_directional_sync, time_out, auto_sync)
    
    def resolve_conflict(self, local_folder, remote_folder, path, is_dir):
        ...
        
    def _sync_directories(self):
        print("syncing...")
        
    
    def req_dir_list(self):
        ...
        
    def req_dir_attributes(self, remote_dir:str):
        ...
        
    def req_file(self, remote_dir:str, remote_file:str, local_dir:str, local_file:str):
        ...
    
    def req_dir_graph(self, remote_dir):
        ...