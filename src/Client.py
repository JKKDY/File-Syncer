import copy
import datetime
import logging
import os
import select
import shutil
import socket
import time
from collections import deque
from threading import Event
from send2trash import send2trash 

from imohash import hashfile

from src.Config import DEFAULT_TIME, get_logger
from src.Network import NT_Code, Socket
from src.utils import update_with_nested_dict

logger_name, logger = get_logger(__name__)



     
class SyncQueue:
    def __init__(self, sync_func):
        self.queue = []
        self.sync_func = sync_func
        self.running_event = Event()
        self.running_event.set()
        
    def add_sync(self, priority, *args, **kwargs):
        if ((args, kwargs)) not in self.queue:
            self._add_sync(priority, args, kwargs)
            if self.running_event.is_set():
                self.run_next()
            self.running_event.wait()
            
    def _add_sync(self, priority, args, kwargs):
        if priority == -1:  self.queue.append((args, kwargs))
        else:  self.queue.insert(min(priority, len(self.queue)), (args, kwargs))
     
    def run_next(self):
        self.running_event.clear()
        while self.queue:
            args, kwargs = self.queue.pop(0)
            if not self.sync_func(*args, **kwargs): # return=False -> syncing is rn not possble , try again later
                if len(self.queue) == 0: time.sleep(0.05) # so were not attempting to sync 1000s of time per second
                self.running_event.set()
                self._add_sync(0, args, kwargs)
        self.running_event.set()
        
    


class Client(Socket):
    def __init__(self, uuid, sessions, file_tracker, log_settings, directory_locks, sync_status_callback):
        super().__init__()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.uuid = uuid
        self.file_tracker = file_tracker
        self.sync_queue = SyncQueue(self._sync)
        self.sessions = sessions
        self.logging_settings = log_settings
        self.directory_locks = directory_locks
        self.sync_status_callback = sync_status_callback
        
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
            try: self.send_code(NT_Code.END_CONN)
            except ConnectionResetError: pass
            self.logger.info(f"Client disconnected from {self.conn_str()}")
            self.sessions.end(self.server_uuid)
            self.logger.info("End session")
            logger.info(f"Shut down Client connected to {self.conn_str()}")
        super().close()
        self.logger.info("Client socket closed")  
    
    
    def conn_str(self): # used for logging
        return f"{self.server_uuid} @ (hostname: {self.server_hostname}, port: {self.server_port})"
       
       
    def req_dir_list(self): # is not used anywhere?
        self.send_code(NT_Code.REQ_DIR_LST)
        self.logger.debug(f"Receive directory list")
        return self.recv_obj()        
        
    def req_file(self, remote_dir:str, remote_file:str, local_dir:str, local_file:str):
        self.send_code(NT_Code.REQ_FILE)
        self.send_str(remote_dir)
        self.send_str(remote_file)
        self.recv_file(os.path.join(local_dir, local_file))
        self.logger.info(f"Download file '{local_file}' in '{local_dir}'")
    
    def req_dir_graph(self, remote_dir):
        self.send_code(NT_Code.REQ_DIR_GRAPH)
        self.send_str(remote_dir)
        self.logger.debug(f"Receive directory graph")
        return self.recv_obj()    
    
    def queue_sync(self, local_dir, remote_dir, bi_directional_sync=True, priority=-1): #priority: -1: queue at last, 0: queue first
        # TODO implement priority system
        self.logger.debug(f"Add to queue: sync local directory '{local_dir}' with remote directory '{remote_dir}'")
        self.sync_queue.add_sync(priority, local_dir, remote_dir, bi_directional_sync)
    
    def resolve_conflict(self, local_folder, remote_folder, path, is_dir):
        print(f"Conflict: \n local folder: {local_folder} \n remote_folder: {remote_folder} \n path: {path}")
        
    def _sync(self, local_dir, remote_dir, bi_directional_sync):
        self.logger.info(f"Now syncing local directory '{local_dir}' with remote directory '{remote_dir}'")
        
        if not self._init_sync(local_dir, remote_dir): return False

        self.file_tracker[local_dir].update()
        local_graph = copy.deepcopy(self.file_tracker[local_dir].root)
        remote_graph = self.req_dir_graph(remote_dir)
        last_sync_time = self.sessions.last_sync(self.server_uuid, local_dir, remote_dir)
        
        local_graph.merge(remote_graph, last_sync_time, self.resolve_conflict)
        
        def create(graph): # graph = merged graph; this is how the directory being synced should look like
            for file in graph.files.values():
                if file.exists and (not file.full_path.exists() or hashfile(file.full_path) != file.hash):
                    self.req_file(remote_dir, file.location(), local_dir, file.location())
                elif not file.exists and file.full_path.exists():
                    send2trash(str(file.full_path))
                    self.logger.info(f"Delete file '{file.location()}' in '{local_dir}'")
            for folder in graph.folders.values():
                if folder.exists:
                    if not folder.full_path.exists():
                        folder.full_path.mkdir()
                        self.logger.info(f"Created folder '{folder.location()}' in '{local_dir}'")
                    create(folder)
                elif folder.full_path.exists():
                    send2trash(str(folder.full_path))
                    self.logger.info(f"Delete folder '{folder.location()}' in '{local_dir}'")
        create(local_graph)
        
        self.file_tracker[local_dir].update(callback=True)
                
        self.directory_locks[local_dir].release()
        self.sync_status_callback(self.server_uuid, local_dir, remote_dir, 0)
        
        self.send_code(NT_Code.END_SYNC)
        self.send_str(remote_dir)
        self.send_str(local_dir)
        
        if bi_directional_sync:
            self.send_code(NT_Code.REQ_SYNC)
            self.send_str(remote_dir)
            self.send_str(local_dir)
            
        self.sessions.add_sync(self.server_uuid, local_dir, remote_dir)
        self.logger.info("Sync Done")  
        
        return True
    
    
    def _init_sync(self, local_dir, remote_dir):
        # check if local_dir is available for syncing
        if not self.directory_locks[local_dir].acquire(timeout=3): 
            self.logger.info(f"Local directory {local_dir} is in use")
            return False
        
        # check if remote dir is available for syncing
        self.send_code(NT_Code.REQ_SYNC_START) 
        self.send_str(remote_dir)
        self.send_str(local_dir)
        if not self.recv_int():
            self.logger.info(f"Server @ {self.server_uuid} is busy")
            return False
        
        self.sync_status_callback(self.server_uuid, local_dir, remote_dir, 1)
        return True
                        
                        