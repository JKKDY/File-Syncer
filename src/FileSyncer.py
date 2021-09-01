import time
from enum import IntEnum
from pathlib import Path
from threading import Thread

from src.Config import get_logger, ConnectionsList, DirectoriesList, Sessions, Config, get_uuid, CFG_GLOB_IGN_KEY, CONN_AUTO_CONNECT_KEY
from src.FileTracker import FileTracker
from src.Server import Server, Callbacks
from src.ui import UiBackend, UI_Code
from src.utils import RepeatedJob
from src.Codes import CONFLICT_POLICY, RESOLVE_POLICY

logger_name, logger = get_logger(__name__)



# TODO: add encryption 
# TODO: sync optimization; check if files have been moved/renamed etc
# TODO: rotating filehandler for logger
# TODO: conflict handling


class FileSyncer(Config):
    def __init__(self, config_path:Path):
        super().__init__(config_path)
        logger.info("Filesyncer start") 
        self.connections_list = ConnectionsList(self.data_path/"connections.json", new_conn_clback=self.new_connection_callback)
        self.directories_list = DirectoriesList(self.data_path/"directories.json")
        self.sessions = Sessions(self.data_path/"sessions.json")
        self.uuid = get_uuid(self.data_path)
        self.will_shut_down = False
        
        self.file_tracker = FileTracker(self.directories_list, self.logging_settings, self.data_path, \
                                        self.global_ign_patterns, self.update_directory_graph_callback, self.new_directory_callback)
        
        server_callbacks = Callbacks(self.update_uuid_callback, self.update_status_callback, self.update_sync_status_callback, self.new_conflict_callback)
        self.server = Server(self.hostname, self.ip, self.port, self.uuid, self.file_tracker, self.sessions, \
            self.connections_list, self.logging_settings, server_callbacks)
        self.server_thread = Thread(target=self.server.start_server, name ="server_thread") 
        
        self.auto_connect_thread = RepeatedJob(self.auto_connect_rate, target=self._auto_connect, name="auto_connect_thread")  
        
        self.ui = UiBackend(self.ui_port, {
            UI_Code.REQ_UUIDS : self.get_uuids,
            UI_Code.REQ_UUID_INFO : self.get_uuid_info,
            UI_Code.REQ_UUID_STATUS : self.get_uuid_status,
            UI_Code.REQ_DIRS : self.get_directories,
            UI_Code.REQ_DIR_INFO : self.get_directory_info,
            UI_Code.REQ_DIR_GRAPH : self.get_directory_graph,
            UI_Code.ADD_CONNECTION : self.add_new_connection,
            UI_Code.UUID_CONNECT : self.connect,
            UI_Code.UUID_DISCONNECT : self.disconnect,
            UI_Code.UUID_SYNC : self.sync, 
            UI_Code.UUID_RESOLVE_CONFLICT : self.resolve_conflict
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
        self.server.shut_down()
        self.stop_auto_connect()
        self.server_thread.join()
        self.file_tracker.shut_down()
        self.ui.shut_down() # is called last incase ui callbacks are triggered while shutting down
        logger.info("Filesyncer end")
        
    def _auto_connect(self):
        for uuid in self.connections_list:
            if self.connections_list[uuid][CONN_AUTO_CONNECT_KEY] is True and uuid not in self.server.clients:
                self.connect(uuid)
        
        
    # auto functions
    def start_auto_connect(self):
        self.auto_connect_thread.start()
        
    def stop_auto_connect(self):
        self.auto_connect_thread.stop()
        self.auto_connect_thread.join()
                  
    def start_auto_sync(self, exclude):
        raise NotImplementedError
    
    def stop_auto_sync(self):
        raise NotImplementedError
        
        
    # query uuids          
    def get_uuids(self): 
        return list(self.connections_list.keys())
        
    def get_uuid_info(self, uuid): 
        return self.connections_list[uuid].to_dict()
     
    def get_uuid_status(self, uuid): 
        return 2 if uuid in self.server.clients else 0 
    
    
    # edit lists
    def add_directory(self, directory, name="", ignore_patterns=[]):
        self.file_tracker.add_directory(directory, name, ignore_patterns)
    
    def delete_directory(self, directory):
        raise NotImplementedError
    
    def add_sync(self, uuid, local, remote, conflict_policy=CONFLICT_POLICY.PROCEED_AND_RECORD, default_resolve=RESOLVE_POLICY.CREATE_COPY, auto_sync=-1, bidirectional=True):
        self.connections_list.add_sync(uuid, local, remote, conflict_policy, default_resolve, auto_sync, bidirectional)
    
    def delete_sync(self, uuid, local, remote):
        self.connections_list.delete_sync(uuid, local, remote)

    
    # directory info 
    def get_directories(self): 
        return list(self.directories_list.keys())
    
    def get_directory_info(self, directory): 
        return self.directories_list[directory].to_dict() 
    
    def get_directory_graph(self, directory): 
        return self.file_tracker[directory].to_dict()
    

    # update ignore patterns
    def update_global_ignore(self, patterns): 
        self.file_tracker.update_glob_ignore(patterns)
        self[CFG_GLOB_IGN_KEY] = patterns
        
    def update_directory_ignore(self, directory, patterns): 
        self.file_tracker.update_dir_ignore(directory, patterns)
    
    
    # connection API
    def add_new_connection(self, hostname, port, name): 
        return self.connections_list.new_connection(hostname, port, name)
    
    def get_connections(self):
        return self.connections_list.to_dict()
        
    def connect(self, uuid): 
        return self.server.connect(uuid)
    
    def disconnect(self, uuid): 
        self.server.close_connection(uuid)
    
    def sync(self, uuid, local_dir, remote_dir, conflict_policy=CONFLICT_POLICY.PROCEED_AND_RECORD, default_resolve=RESOLVE_POLICY.CREATE_COPY, bidirectional=True, priority=-1): 
        self.server.clients[uuid].queue_sync(local_dir, remote_dir, conflict_policy, default_resolve, bidirectional, priority)
    
    def resolve_conflict(self, uuid, local_dir, remote_dir, rel_path, is_dir, resolve_policy):
        self.server.clients[uuid].resolve_conflict(local_dir, remote_dir, rel_path, is_dir, resolve_policy)
        
    def get_conflict_info(self, uuid, local_dir, remote_dir, rel_path, is_dir):
        return self.server.clients[uuid].get_conflict_info(local_dir, remote_dir, rel_path, is_dir)
    
    
    # callbacks
    def update_uuid_callback(self, old_uuid, new_uuid): 
        self.ui.notify(UI_Code.NOTF_UPDATE_UUID, old_uuid, new_uuid)
        
    def update_status_callback(self, uuid): 
        self.ui.notify(UI_Code.NOTF_UPDATE_STATUS, uuid, self.get_uuid_status(uuid)) 
    
    def update_directory_graph_callback(self, directory): 
        self.ui.notify(UI_Code.NOTF_UPDATE_DIR_GRAPH, directory, self.file_tracker[directory].to_dict())
    
    def new_connection_callback(self, uuid): 
        self.ui.notify(UI_Code.NOTF_NEW_CONNECTION, uuid)
        
    def new_directory_callback(self, dir_path):
        self.ui.notify(UI_Code.NOTF_NEW_DIRECTORY, dir_path)
    
    def update_sync_status_callback(self, uuid, local, remote, state): 
        self.ui.notify(UI_Code.NOTF_UPDATE_SYNC_STATE, uuid, local, remote, state)
        
    def new_conflict_callback(self, uuid, local, remote, obj, conflict_type): #obj either a file or  folder
        self.ui.notify(UI_Code.NOTF_NEW_CONFLICT, uuid, local, remote, obj, conflict_type)

