import datetime
import logging
import os
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
    
    def sync(self, local_dir, remote_dir, bi_directional_sync=True, time_out=None, add_to_queue=True):
        self.logger.debug(f"Add to queue: sync local directory '{local_dir}' with remote directory '{remote_dir}'")
        self.sync_queue.add_sync(local_dir, remote_dir, bi_directional_sync, time_out)
    
    def resolve_conflict(self, local_folder, remote_folder, path, is_dir):
        print("AAAAAAAAAAAAAA conflict")
        
    def _sync_directories(self, local_dir, remote_dir, bi_directional_sync, time_out):
        self.logger.info(f"Now syncing local directory '{local_dir}' with remote directory '{remote_dir}'")

        self.file_tracker[local_dir].update()
        local_graph = copy.deepcopy(self.file_tracker[local_dir].root)
        remote_graph = self.req_dir_graph(remote_dir)
        last_sync_time = self.sessions.last_sync(self.server_uuid, local_dir, remote_dir)
        
        local_graph.merge(remote_graph, last_sync_time, self.resolve_conflict)
        
        def create(graph): # graph = merged graph; this is how the directory being synced should look like
            for file in graph.files.values():
                if file.exists and (not file.full_path.exists() or hash_file(file.full_path) != file.hash):
                    self.req_file(remote_dir, file.location(), local_dir, file.location())
                elif not file.exists and file.full_path.exists():
                    file.full_path.unlink()
                    self.logger.info(f"Delete file '{file.location()}' in '{local_dir}'")
            for folder in graph.folders.values():
                if folder.exists:
                    if not folder.full_path.exists():
                        folder.full_path.mkdir()
                        self.logger.info(f"Created folder '{folder.location()}' in '{local_dir}'")
                    create(folder)
                elif folder.full_path.exists():
                    shutil.rmtree(folder.full_path)
                    self.logger.info(f"Delete folder '{folder.location()}' in '{local_dir}'")
        create(local_graph)
        
        self.file_tracker[local_dir].update()
        
        if bi_directional_sync:
            self.send_code(NT_Code.REQ_SYNC)
            self.send_str(remote_dir)
            self.send_str(local_dir)
            # self.send_obj(time_out)
            
        self.sessions.add_sync(self.server_uuid, local_dir, remote_dir)
        self.logger.info("Sync Done")  
                        
                        




