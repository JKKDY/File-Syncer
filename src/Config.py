from datetime import datetime
import json
import logging
import os
import socket
from logging.handlers import RotatingFileHandler
from pathlib import Path
from threading import Event
from uuid import uuid1

from src.utils import hash_word, now, update_with_nested_dict
from src.Codes import CONFLICT_POLICY, RESOLVE_POLICY


DATE_TIME_FORMAT = "%Y-%m-%d %H:%M:%S.%f"
DEFAULT_TIME = datetime.min

ROOT_LOGGER_NAME = "FS_root" # FS for FileSyncer


CONN_PORT_KEY = "port"
CONN_HOSTNAME_KEY = "hostname"
CONN_NAME_KEY = "name"
CONN_SYNCS_KEY = "syncs"
CONN_DIR_KEY = "directories"
CONN_AUTO_CONNECT_KEY = "auto_connect"

SYNC_AUTO_KEY = "auto_sync"
SYNC_BIDIR_KEY = "bidirectional"
SYNC_LOC_IGN_KEY = "local_ignore"
SYNC_SYNCED_IGN_KEY = "synced_ignore"
SYNC_CONFLICT_POLICY_KEY = "conflict_policy"
SYNC_RESOLVE_POLICY_KEY = "default_resolve_policy"

DIR_NAME_KEY = "name"
DIR_IGNORE_KEY = "ignore"
DIR_HASH_KEY = "hash"

SESS_START_KEY = "start"
SESS_END_KEY = "end"
SESS_SYNCED_KEY = "synced"

CFG_PORT_KEY = "port"
CFG_UI_PORT_KEY = "ui_port"
CFG_GLOB_IGN_KEY = "global_ign_patterns"
CFG_SYNC_RATE_KEY = "default_sync_rate"
CFG_PING_RATE_KEY = "default_ping_rate"
CFG_SYNC_OK_TIMEOUT_KEY = "check_sync_ok_timeout"



def get_logger(name):
    logger_name = f"{ROOT_LOGGER_NAME}.{name}"
    return logger_name, logging.getLogger(logger_name)



#! important: auto save only triggers with dict. with other data containers it will not trigger a save
#? this dct wrapper class isnt even necessary? -> look into later if it can be eliminated 
class DictWrapper:
    def __init__(self, auto_save, save_event=None,):
        self._content = dict()
        self.save_event = save_event
        self.auto_save = auto_save
        
    def __getitem__(self, key):
        return self._content[key]
    
    def __setitem__(self, key, value):
        self.save_event.wait()
        self._content[key] = value  
        if self.auto_save: self.save()   
        
    def __delitem__(self, key):
        self.save_event.wait()
        del self._content[key] 
        if self.auto_save: self.save() 

    def __iter__(self):
        return iter(self._content)
    
    def __contains__(self, key):
        return key in self._content
    
    def __repr__(self):
        return str(self._content)
    
    def keys(self):
        return self._content.keys()

    def items(self):
        return self._content.items()

    def values(self):
        return self._content.values()
    
    def save(self):
        raise NotImplementedError
    
    def to_dict(self) -> dict:
        return {key: (value.to_dict() if isinstance(value, DictWrapper) else value) for key,value in self._content.items()}
    
    
    

class JSON_Data(DictWrapper):
    def __init__(self, data, parent, auto_save):
        super().__init__(auto_save, parent.save_event)
        self.parent = parent
        for key, value in data.items():
             self._content[key] = JSON_Data(value, self, auto_save) if isinstance(value, dict) else value
    
    def save(self):
        self.parent.save()
        

        
    
    
class JSON_File(DictWrapper):
    def __init__(self, path:Path, auto_save=True):
        super().__init__(auto_save=auto_save)
        self.save_event = Event()  # event for signaling saving in progress
        self.save_event.set()
        self.path = path
        
        # if path does not exist or is empty create and write {}
        if not self.path.is_file() or os.stat(self.path).st_size == 0: 
            self.path.write_text("{}")
            
        self.file = self.path.open("r+")
        self._content = JSON_Data(json.load(self.file), self, self.auto_save)
    
    def save(self):
        if self.save_event.isSet: # save_event is true when file is being saved
            self.save_event.clear()
            self.file.seek(0) #reset file position to the beginning
            self.file.write(json.dumps(self.to_dict(), indent=4, sort_keys=True))
            self.file.truncate() # remove remaining part
            self.save_event.set()

   
   
   

   

def temp_uuid(hostname, port):
    return f"temp-{hostname}-{port}"

class ConnectionsList(JSON_File):
    def __init__(self, path:Path, new_conn_callback, uuid_change_callback, uuid_update_callback, new_sync_callback):
        super().__init__(path)
        self.uuid_change_callback = uuid_change_callback
        self.uuid_update_callback = uuid_update_callback
        self.new_conn_callback = new_conn_callback
        self.new_sync_callback = new_sync_callback
    
    def new_connection(self, hostname, port, nick_name="", auto_connect=-1, uuid=None):
        if uuid is None: uuid = temp_uuid(hostname, port) # create temporary uuid
        self[uuid] = JSON_Data({
            CONN_PORT_KEY: int(port),
            CONN_HOSTNAME_KEY: hostname,
            CONN_NAME_KEY: hostname if nick_name=="" else nick_name,
            CONN_SYNCS_KEY: {},
            CONN_DIR_KEY: {},
            CONN_AUTO_CONNECT_KEY: auto_connect
        }, self, self.auto_save)
        self.new_conn_callback(uuid)
        return uuid
    
    def has_sync(self, uuid, local_dir, remote_dir):
        if local_dir in self[uuid][CONN_SYNCS_KEY] and remote_dir in self[uuid][CONN_SYNCS_KEY][local_dir]: 
            return True
        else: return False
        
    def get_sync_conflict_policy(self, uuid, local_dir, remote_dir):
        return self[uuid][CONN_SYNCS_KEY][local_dir][remote_dir][SYNC_CONFLICT_POLICY_KEY]
    
    def get_sync_conflict_resolve(self, uuid, local_dir, remote_dir):
        return self[uuid][CONN_SYNCS_KEY][local_dir][remote_dir][SYNC_RESOLVE_POLICY_KEY]

    def add_sync(self, uuid, local_dir, remote_dir, policy=CONFLICT_POLICY.PROCEED_AND_RECORD, resolve=RESOLVE_POLICY.CREATE_COPY, auto_sync=-1, bidirectional=True):
        if local_dir not in self[uuid][CONN_SYNCS_KEY]: self[uuid][CONN_SYNCS_KEY][local_dir] = {}
        self[uuid][CONN_SYNCS_KEY][local_dir][remote_dir] = {
            SYNC_BIDIR_KEY:bidirectional,
            SYNC_AUTO_KEY: auto_sync,
            SYNC_CONFLICT_POLICY_KEY: policy,
            SYNC_RESOLVE_POLICY_KEY: resolve,
            SYNC_LOC_IGN_KEY: [],
            SYNC_SYNCED_IGN_KEY: []
        }
        self.new_sync_callback(uuid, local_dir, remote_dir, self[uuid][CONN_SYNCS_KEY][local_dir][remote_dir])
        
    def delete_sync(self, uuid, local, remote):
        del self[uuid][CONN_SYNCS_KEY][local][remote]
        
    def update(self, uuid, new_uuid=None, new_hostname=None, new_port=None, new_dir_info=None):
        if new_hostname is not None: self[uuid][CONN_HOSTNAME_KEY] = new_hostname
        if new_port is not None: self[uuid][CONN_PORT_KEY] = new_port
        if new_dir_info is not None: self[uuid][CONN_DIR_KEY] = JSON_Data(new_dir_info, self[uuid], self.auto_save)
        if uuid != new_uuid and new_uuid is not None:
            self[new_uuid] = self[uuid] 
            del self[uuid]
            self.uuid_change_callback(uuid, new_uuid)
        
        x = new_uuid if new_uuid is not None else uuid
        self.uuid_update_callback(x, self[x][CONN_HOSTNAME_KEY], self[x][CONN_PORT_KEY], self[x][CONN_DIR_KEY].to_dict())
            
        
    
        
    
    
class DirectoriesList(JSON_File):
    def __init__(self, path:Path):
        super().__init__(path)
    
    def add_directory(self, path, name, ignore_patterns):
        self[str(path)] = JSON_Data({
            DIR_IGNORE_KEY: ignore_patterns,
            DIR_HASH_KEY: hash_word(path),
            DIR_NAME_KEY: str(name if name != "" else path)
        }, self, self.auto_save)
        
    def update(self, path, ign_patterns=None, hash=None):
        if ign_patterns is not None: self[str(path)][DIR_IGNORE_KEY] = ign_patterns
        if hash is not None: self[str(path)][DIR_HASH_KEY] = hash
        
    def dir_info(self): # returns paths & names of directories
        return {str(path):directory[DIR_NAME_KEY] for path, directory in self.items()}
            
       
        
class Sessions(JSON_File):
    def __init__(self, path:Path):
        super().__init__(path)
        
    def start(self, uuid):
        if uuid not in self: self[uuid] = [] # first time connecting
        self[uuid].insert(0, {SESS_START_KEY: now().strftime(DATE_TIME_FORMAT)})
        self.save() # list wont trigger auto_save
    
    def end(self, uuid):
        self[uuid][0][SESS_END_KEY] = now().strftime(DATE_TIME_FORMAT)
        self.save() # list wont trigger auto_save
        
    def add_sync(self, uuid, local_dir, remote_dir):
        try:
            self[uuid][0][SESS_SYNCED_KEY][local_dir][remote_dir].insert(0, now().strftime(DATE_TIME_FORMAT))
        except KeyError: # first time remote_dir and local_dir are syncing
            update_with_nested_dict([SESS_SYNCED_KEY, local_dir, remote_dir], self[uuid][0])
            self[uuid][0][SESS_SYNCED_KEY][local_dir][remote_dir] = [now().strftime(DATE_TIME_FORMAT)]
        self.save() # list wont trigger auto_save
               
    def last_sync(self, uuid, local_dir, remote_dir):
        for session in self[uuid]:
            try: 
                return datetime.strptime(session[SESS_SYNCED_KEY][local_dir][remote_dir][0], DATE_TIME_FORMAT)
            except (KeyError, ValueError):
                pass
        return DEFAULT_TIME
                




class Config(JSON_File):
    class LoggingSettings:
        def __init__(self, logs_path:Path):
            self.logs_path = logs_path
            self.logging_level = logging.DEBUG #logging.INFO 
            
            #TODO add filter such that FS_root is not eliminated from logger names in log files, see:https://stackoverflow.com/questions/46954855/python-logging-format-how-to-print-only-the-last-part-of-logger-name
            self.formater = logging.Formatter("[{asctime}] [{levelname:<6}] {name} : {message}", style="{")
            
            self.root_handler = RotatingFileHandler(self.logs_path / "main.log", encoding='utf-8', maxBytes=1e+6)
            self.root_handler.setFormatter(self.formater)
            self.root_handler.setLevel(self.logging_level)
            
            self.root_logger = logging.getLogger(ROOT_LOGGER_NAME) # FS for FileSyncer
            self.root_logger.setLevel(self.logging_level)
            self.root_logger.addHandler(self.root_handler)
            
        def create_logger(self, name, file_name):
            logger = logging.getLogger(name)
            logger.setLevel(self.logging_level)
            logger.propagate = False
            
            handler = RotatingFileHandler(self.logs_path / file_name, encoding="utf-8",  maxBytes=1e+6)
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(self.formater)
            
            if len(logger.handlers) == 0: logger.addHandler(handler)
            return logger
            
        def default_handler(self, file_name):
            handler = RotatingFileHandler(self.logs_path / file_name, maxBytes=1e+6)
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(self.formater)
            return handler
        
    def __init__(self, path:Path):
        super().__init__(path)
         
        self.data_path = Path(self.path.parent / self["data_path"] if not os.path.isabs(self["data_path"]) else self["data_path"])
        self.logs_path = Path(self.path.parent / self["logs_path"] if not os.path.isabs(self["logs_path"]) else self["logs_path"])
        
        self.data_path.mkdir(parents=True, exist_ok=True)
        self.logs_path.mkdir(parents=True, exist_ok=True)
            
        self.logging_settings = self.LoggingSettings(self.logs_path)
        
        self.hostname = socket.gethostname()
        self.ip = socket.gethostbyname(self.hostname)
        self.port = self[CFG_PORT_KEY]
        self.ui_port = self[CFG_UI_PORT_KEY]
        
        # self.default_ping_rate = self[CFG_PING_RATE_KEY] # check if connection is still alive 
        # self.default_sync_rate = self[CFG_SYNC_RATE_KEY]
        self.auto_connect_rate = self["default_connect_rate"] # how often to try connect to other connections
        self.sync_ok_timeout = self[CFG_SYNC_OK_TIMEOUT_KEY]
        
        self.global_ign_patterns = self[CFG_GLOB_IGN_KEY]
            


def get_uuid(data_path:Path):
    uuid_file = data_path / "UUID"
    if not uuid_file.is_file():
        uuid_file.write_text(str(uuid1()))
    return uuid_file.read_text()
    
