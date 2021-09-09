import copy
import os

from pathlib import Path
from threading import Event, Thread

from imohash import hashfile
from send2trash import send2trash

from src.Config import DEFAULT_TIME, get_logger
from src.Network import NT_Code, Socket
from src.utils import copy_name, NestedDict
from src.Codes import CONFLICT_POLICY, RESOLVE_POLICY, SYNC_STATUS, SYNC_RET_CODE

logger_name, logger = get_logger(__name__)




class SyncQueue:
    class SyncEvent:
        def __init__(self) -> None:
            self.event = Event()
            self.ret = None
        
        def done(self, ret):
            self.ret = ret
            self.event.set()
            
        def wait(self):
            self.event.wait()
            return self.ret
            
    def __init__(self, sync_func):
        self.queue = []
        self.sync_func = sync_func
        self.running_thread = Thread()
        
    def add_sync(self, priority, *args, **kwargs):
        if ((args, kwargs)) not in self.queue:
            sync_event = self.SyncEvent()
            if priority == -1:  self.queue.append((sync_event, args, kwargs))
            else:  self.queue.insert(min(priority, len(self.queue)), (sync_event, args, kwargs))  # low priority number = high priority
            if self.running_thread.is_alive(): self.running_thread.join()
            else: self.run_next()
            return sync_event
     
    def run_next(self):     
        def run():
            while self.queue:
                event, args, kwargs = self.queue.pop(0)
                event.done(self.sync_func(*args, **kwargs))
                    
        self.running_thread = Thread(target=run)
        self.running_thread.run()
     
        
    
    
class Conflicts:
    class Conflict:
        def __init__(self,  local_obj, remote_obj, conflict_type) -> None:
            self.conflict_type = conflict_type
            self.local_modif_time = local_obj.last_modif_time
            self.remote_modif_time = remote_obj.last_modif_time
            self.local_hash = local_obj.hash
            self.remote_hash = remote_obj.hash
            self.resolve_policy=False
            
    def __init__(self) -> None:
        self.conflicts = NestedDict()
        self.resolve_events = NestedDict()
        
    def new_sync(self, local_dir, remote_dir):
        for key, conflict in self.conflicts[local_dir][remote_dir].items():
            if not conflict.resolve_policy:
                del self.conflicts[local_dir][remote_dir][key]

    def register_conflict(self, local_dir:str, remote_dir:str, is_dir:bool, local_dir_elem, remote_dir_elem, conflict_type) -> None:
        self.conflicts[local_dir][remote_dir][(local_dir_elem.rel_path, is_dir)] = self.Conflict(local_dir_elem, remote_dir_elem, conflict_type)
        self.resolve_events[local_dir][remote_dir][(local_dir_elem.rel_path, is_dir)] = Event()

    def resolve_conflict(self, local_dir:str, remote_dir:str, rel_path:Path, is_dir:bool, resolve_policy):
        self.conflicts[local_dir][remote_dir][(rel_path, is_dir)].resolve_policy = resolve_policy # using tuple as key to avoid double loops
        self.resolve_events[local_dir][remote_dir][(rel_path, is_dir)].set()
        
    def is_resolved(self, local_dir, remote_dir, local_obj, remote_obj, rel_path, is_dir):
        try: 
            conflict = self.conflicts[local_dir][remote_dir][(rel_path, is_dir)] 
            if conflict.local_hash == local_obj.hash and conflict.remote_hash == remote_obj.hash:
                return conflict.resolve_policy
            else:
                return False
        except AttributeError: 
            return False
    
    def wait_for_resolve(self, local_dir:str, remote_dir:str, rel_path:Path, is_dir):
        self.resolve_events[local_dir][remote_dir][(rel_path, is_dir)].wait()
        return self.conflicts[local_dir][remote_dir][(rel_path, is_dir)].resolve_policy
        
    def has_unresolved_conflicts(self, local_dir, remote_dir):
        for key, conflict in self.conflicts[local_dir][remote_dir].items():
            if conflict.resolve_policy is False:
                return False
        return True
            
    def reset_sync_conflicts(self, local_dir, remote_dir):
        self.conflicts[local_dir][remote_dir] = NestedDict()
        
    def get_conflicts(self, local_dir, remote_dir):
        folders, files = {}, {}
        for key, conflict in self.conflicts[local_dir][remote_dir].items():
            (folders  if key[1] is True else files)[key[0]] = conflict
        return folders, files


class Client(Socket):
    def __init__(self, uuid, sessions, file_tracker, log_settings, directory_locks, sync_status_callback, new_conflict_callback):
        super().__init__()
        self.uuid = uuid
        self.file_tracker = file_tracker
        self.sync_queue = SyncQueue(self._sync)
        self.sessions = sessions
        self.logging_settings = log_settings
        self.directory_locks = directory_locks
        self.sync_status_callback = sync_status_callback
        self.new_conflict_callback = new_conflict_callback
        self.conflicts = Conflicts()
        
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
        self.logger.info(f"Client connected to {self.conn_str()}")
        return uuid, dir_info
    
    def close(self):
        if self.connected:
            self.connected = False
            try: self.send_code(NT_Code.END_CONN)
            except ConnectionResetError: pass
            self.logger.info(f"Client disconnected from {self.conn_str()}")
            self.sessions.end(self.server_uuid)
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
    
    def queue_sync(self, local_dir, remote_dir, conflict_policy, default_resolve, bi_directional_sync, priority=-1): #priority: -1: queue at last, 0: queue first
        # TODO implement priority system
        self.logger.debug(f"Add to queue: sync local directory '{local_dir}' with remote directory '{remote_dir}'")
        return self.sync_queue.add_sync(priority, str(local_dir), str(remote_dir), conflict_policy, default_resolve, bi_directional_sync)
    
    
    def get_conflicts(self, local_dir, remote_dir):
        return self.conflicts.get_conflicts(str(local_dir), str(remote_dir))
    
    def resolve_conflict(self, local_dir_path, remote_dir_path, rel_path, is_dir, resolve_policy):
        self.conflicts.resolve_conflict(str(local_dir_path), str(remote_dir_path), Path(rel_path), is_dir, resolve_policy)
        
        
    def _sync(self, local_dir, remote_dir, conflict_policy, default_resolve, bi_directional_sync):
        self.logger.info(f"Now syncing local directory '{local_dir}' with remote directory '{remote_dir}'")
        
        if ret:=self._init_sync(local_dir, remote_dir) is not True: return ret

        self.file_tracker[local_dir].update()
        local_graph = copy.deepcopy(self.file_tracker[local_dir].root)
        remote_graph = self.req_dir_graph(remote_dir)
        last_sync_time = self.sessions.last_sync(self.server_uuid, local_dir, remote_dir)
        
        self.conflicts.new_sync(local_dir, remote_dir)
        local_graph.merge(remote_graph, last_sync_time, self._create_conflict_handler(local_dir, remote_dir, conflict_policy, default_resolve))
        if not self.conflicts.has_unresolved_conflicts(local_dir, remote_dir):
            self._end_sync(local_dir, remote_dir)
            self.logger.info(f"Aborted Sync due to: {SYNC_RET_CODE.HAS_CONFLICT}")
            return SYNC_RET_CODE.HAS_CONFLICT
        
        def create(graph): # graph = merged graph; this is how the directory being synced should look like
            for file in graph.files.values():
                # if doesnt exist yet or contents are different, download file
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
        self.conflicts.reset_sync_conflicts(local_dir, remote_dir)
        
        self._end_sync(local_dir, remote_dir)
        
        if bi_directional_sync:
            self.logger
            self.send_code(NT_Code.REQ_SYNC)
            self.send_str(remote_dir)
            self.send_str(local_dir)
            if code:=self.recv_code() != NT_Code.END_SYNC: raise Exception("expected NT_Code.END_SYNC, got ", code)
        
        self.sessions.add_sync(self.server_uuid, local_dir, remote_dir)
        self.logger.info("Sync Done")  
        
        return SYNC_RET_CODE.SUCCESS
    
    def _init_sync(self, local_dir, remote_dir):
        # check if local_dir is available for syncing
        if not self.directory_locks[local_dir].acquire(timeout=3): 
            self.logger.info(f"Aborted Sync due to: {SYNC_RET_CODE.LOCAL_DIR_IN_USE}")
            return SYNC_RET_CODE.LOCAL_DIR_IN_USE
        
        # check if remote dir is available for syncing
        self.send_code(NT_Code.REQ_SYNC_START) 
        self.send_str(remote_dir)
        self.send_str(local_dir)
        if not self.recv_int():
            self.logger.info(f"Aborted Sync due to: {SYNC_RET_CODE.REMOTE_DIR_IN_USE}")
            return SYNC_RET_CODE.REMOTE_DIR_IN_USE
        
        self.sync_status_callback(self.server_uuid, local_dir, remote_dir, SYNC_STATUS.SYNCING)
        return True
    
    def _end_sync(self, local_dir, remote_dir):
        self.send_code(NT_Code.END_SYNC)
        self.send_str(remote_dir)
        self.send_str(local_dir)
        self.directory_locks[local_dir].release()
        self.sync_status_callback(self.server_uuid, local_dir, remote_dir, SYNC_STATUS.NOT_SYNCING)
        
    def _create_conflict_handler(self, local_dir, remote_dir, conflict_policy, default_resolve): # local and remote are the folders being synced    
        def handle_conflict(local_folder, remote_folder, name, remote_obj, is_dir, conflict_type): # local_dir and remote_dir are the folders where the conflict is happening    
            local = local_folder.folders if is_dir else local_folder.files
            remote = remote_folder.folders if is_dir else remote_folder.files
            rel_path = local[name].rel_path
            self.logger.info(f"New conflict:  relative path: '{rel_path}', conflict type: {conflict_type}")

            def resolve_conflict(resolve_policy): # name is file or folder name
                if resolve_policy is RESOLVE_POLICY.REPLACE_LOCAL:
                    local[name] = remote_obj
                if resolve_policy is RESOLVE_POLICY.USE_NEWEST:
                    if remote[name].last_modif_time > local[name].last_modif_time: 
                        local[name] = remote_obj
                if resolve_policy is RESOLVE_POLICY.CREATE_COPY:
                    ending = "" if is_dir else "." + str(name).split(".")[-1]
                    copy = copy_name(str(name)[:-len(ending)], ending, local)    
                    (Path(local_dir) / rel_path).rename((Path(local_dir) / rel_path).parents[0] / copy)
                    local[name] = remote_obj
                        
            if resolution := self.conflicts.is_resolved(local_dir, remote_dir, local[name], remote[name], rel_path, is_dir):
                resolve_conflict(resolution)
            elif conflict_policy is CONFLICT_POLICY.PROCEED_AND_RECORD:
                self.conflicts.register_conflict(local_dir, remote_dir, is_dir, local[name], remote[name], conflict_type)
            elif conflict_policy is CONFLICT_POLICY.WAIT_FOR_RESOLVE:
                raise NotImplementedError
                self.conflicts.register_conflict(local_dir, remote_dir, is_dir, local[name], remote[name], conflict_type)
                resolve_conflict(self.conflicts.wait_for_resolve())
            elif conflict_policy is CONFLICT_POLICY.USE_DEFAULT_RESOLVE:
                resolve_conflict(default_resolve)

        return handle_conflict    
                        
                        