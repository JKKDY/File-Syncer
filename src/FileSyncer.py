from enum import IntEnum
from pathlib import Path
from threading import Thread

from src.Config import get_logger, ConnectionsList, DirectoriesList, Sessions, Config, get_uuid, NICKNAME_KEY
from src.FileTracker import FileTracker
from src.Server import Server, Callbacks
from src.ui import UiBackend, UI_Code
logger_name, logger = get_logger(__name__)



class FileSyncer(Config):
    def __init__(self, config_path:Path):
        super().__init__(config_path)
        logger.info("Filesyncer start")
        self.connections = ConnectionsList(self.data_path/"connections.json")
        self.directories = DirectoriesList(self.data_path/"directories.json")
        self.sessions = Sessions(self.data_path/"sessions.json")
        self.uuid = get_uuid(self.data_path)
        
        self.file_tracker = FileTracker(self.directories, self.logging_settings, self.data_path)
        
        callbacks = Callbacks(self.update_uuid, self.update_status)
        self.server = Server(self.hostname, self.ip, self.port, self.uuid, self.file_tracker, self.sessions, \
            self.connections, self.directories, self.logging_settings, callbacks)
        self.server_thread = Thread(target=self.server.start_server, name = "server_thread")   
        
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
        
    def start_server(self):
        self.server_thread.start()
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback): 
        self.shut_down()
    
    def shut_down(self):
        self.ui.shut_down()
        self.server.shut_down()
        self.server_thread.join()
        self.file_tracker.shut_down()
        logger.info("Filesyncer end")
        
        
    def get_uuids(self): return list(self.connections.keys())
        
    def get_uuid_info(self, uuid): return self.connections[uuid].to_dict()
     
    def get_uuid_status(self, uuid): return 2 if uuid in self.server.clients else 0 
    
    
    def get_directories(self): return list(self.directories.keys())
    
    def get_directory_info(self, directory): return self.directories[directory].to_dict() 
    
    def get_directory_graph(self, directory): return self.file_tracker[directory].to_dict()
    
        
    def add_connection(self, hostname, port, name): return self.connections.new_connection(hostname, port, name)
        
    def connect(self, uuid): return self.server.connect(uuid)
    
    def disconnect(self, uuid): self.server.close_connection(uuid)
    
    def sync(self, uuid, local, remote): self.server.clients[uuid].sync(local, remote)
        
        
    def update_uuid(self, old_uuid, new_uuid): self.ui.notify(UI_Code.UPDATE_UUID, old_uuid, new_uuid)
        
    def update_status(self, uuid): self.ui.notify(UI_Code.UPDATE_STATUS, uuid, self.get_uuid_status(uuid))

    