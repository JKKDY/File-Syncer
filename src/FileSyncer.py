import time
from enum import IntEnum
from pathlib import Path
from threading import Thread

from src.Config import get_logger, ConnectionsList, DirectoriesList, Sessions, Config, get_uuid, \
    CFG_GLOB_IGN_KEY, CONN_AUTO_CONNECT_KEY
from src.FileTracker import FileTracker
from src.Server import Server, Callbacks
from src.ui import UiBackend, UI_Code
from src.utils import RepeatedJob

logger_name, logger = get_logger(__name__)



# TODO: add encryption (diffie-hellman, RSA ...)
# TODO: sync optimization; check if files have been moved/renamed etc
# TODO: rotating filehandler for logger
# TODO: no conflict handling


class FileSyncer(Config):
    def __init__(self, config_path:Path):
        super().__init__(config_path)
        logger.info("Filesyncer start") 
        self.connections = ConnectionsList(self.data_path/"connections.json", new_conn_clback=self.new_connection_callback)
        self.directories = DirectoriesList(self.data_path/"directories.json")
        self.sessions = Sessions(self.data_path/"sessions.json")
        self.uuid = get_uuid(self.data_path)
        self.will_shut_down = False
        
        self.file_tracker = FileTracker(self.directories, self.logging_settings, self.data_path, \
                                        self.global_ign_patterns, self.update_directory_graph_callback)
        
        server_callbacks = Callbacks(self.update_uuid_callback, self.update_status_callback, self.update_sync_status_callback)
        self.server = Server(self.hostname, self.ip, self.port, self.uuid, self.file_tracker, self.sessions, \
            self.connections, self.directories, self.logging_settings, server_callbacks)
        self.server_thread = Thread(target=self.server.start_server, name ="server_thread") 
        
        self.auto_connect_thread = RepeatedJob(self.auto_connect_rate, target=self._auto_connect, name="auto_connect_thread")  
        
        self.ui = UiBackend(self.ui_port, {
            UI_Code.REQ_UUIDS : self.get_uuids,
            UI_Code.REQ_UUID_INFO : self.get_uuid_info,
            UI_Code.REQ_UUID_STATUS : self.get_uuid_status,
            UI_Code.REQ_DIRS : self.get_directories,
            UI_Code.REQ_DIR_INFO : self.get_directory_info,
            UI_Code.REQ_DIR_GRAPH : self.get_directory_graph,
            UI_Code.ADD_CONNECTION : self.add_connection,
            UI_Code.UUID_CONNECT : self.connect,
            UI_Code.UUID_DISCONNECT : self.disconnect,
            UI_Code.UUID_SYNC : self.sync
        })
        self.ui.start()
    
    
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback): 
        self.shut_down()
        
        
        
    def start_server(self):
        self.server_thread.start()
    
    def shut_down(self):
        self.will_shut_down = True
        self.ui.shut_down()
        self.server.shut_down()
        self.stop_auto_connect()
        self.server_thread.join()
        self.file_tracker.shut_down()
        logger.info("Filesyncer end")
        
        
        
    def start_auto_connect(self):
        self.auto_connect_thread.start()
        
    def stop_auto_connect(self):
        self.auto_connect_thread.stop()
        
    def _auto_connect(self):
        for uuid in self.connections:
            if self.connections[uuid][CONN_AUTO_CONNECT_KEY] is True and uuid not in self.server.clients:
                self.connect(uuid)
        
        
                     
    def get_uuids(self): 
        return list(self.connections.keys())
        
    def get_uuid_info(self, uuid): 
        return self.connections[uuid].to_dict()
     
    def get_uuid_status(self, uuid): 
        return 2 if uuid in self.server.clients else 0 
    
    
    
    def add_directory(self, directory):
        pass
    
    def delete_directory(self, directory):
        pass


    
    def get_directories(self): 
        return list(self.directories.keys())
    
    def get_directory_info(self, directory): 
        return self.directories[directory].to_dict() 
    
    def get_directory_graph(self, directory): 
        return self.file_tracker[directory].to_dict()
    
    
    
    def update_global_ignore(self, patterns): 
        self.file_tracker.update_glob_ignore(patterns)
        self[CFG_GLOB_IGN_KEY] = patterns
        
    def update_directory_ignore(self, directory, patterns): 
        self.file_tracker.update_dir_ignore(directory, patterns)
    
    
        
    def add_connection(self, hostname, port, name): 
        return self.connections.new_connection(hostname, port, name)
        
    def connect(self, uuid): 
        return self.server.connect(uuid)
    
    def disconnect(self, uuid): 
        self.server.close_connection(uuid)
    
    def sync(self, uuid, local, remote, bidirectional=True, priority=-1): 
        self.server.clients[uuid].queue_sync(local, remote, bidirectional, priority)
        
    
    
    def update_uuid_callback(self, old_uuid, new_uuid): 
        self.ui.notify(UI_Code.NOTF_UPDATE_UUID, old_uuid, new_uuid)
        
    def update_status_callback(self, uuid): 
        self.ui.notify(UI_Code.NOTF_UPDATE_STATUS, uuid, self.get_uuid_status(uuid)) 
    
    def update_directory_graph_callback(self, directory): 
        self.ui.notify(UI_Code.NOTF_UPDATE_DIR_GRAPH, directory, self.file_tracker[directory].to_dict())
    
    def new_connection_callback(self, uuid): 
        self.ui.notify(UI_Code.NOTF_NEW_CONNECTION, uuid)
    
    def update_sync_status_callback(self, uuid, local, remote, state): 
        self.ui.notify(UI_Code.NOTF_UPDATE_SYNC_STATE, uuid, local, remote, state)

   