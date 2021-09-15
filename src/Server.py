import os
import select
import socket
import threading
from threading import Lock

from src.Client import Client
from src.Config import CONN_HOSTNAME_KEY, CONN_PORT_KEY, DATE_TIME_FORMAT, get_logger, temp_uuid
from src.Network import NT_Code, Socket

logger_name, logger = get_logger(__name__)



class Callbacks:
    def __init__(self, status_change, sync_status_change, new_conflict):
        self.status_change = status_change
        self.sync_status_change = sync_status_change
        self.new_conflict = new_conflict
        
        
        

class Server():
    def __init__(self, hostname, ip, port, uuid, file_tracker, sessions, \
        connections, log_settings, callbacks):
        
        self.file_tracker = file_tracker
        self.sessions = sessions    
        self.connections = connections # connection data
        self.logging_settings = log_settings
        self.callbacks = callbacks
        
        self.hostname = hostname
        self.ip = ip
        self.port = port
        self.uuid = uuid
        
        self.connections_in_progress = set()
        self.clients = {}
        self.client_threads = {}
        self.active_syncs = {}
        self.directory_locks = {directory:Lock() for directory in self.file_tracker.keys()} 
        
        self.will_shut_down = False
        self.socket = Socket()
        self.socket.bind(self.ip, self.port)
        
        
    def start_server(self):
        """Start server loop for accepting connections"""
        self.will_shut_down = False
        self.socket.listen()
        logger.info(f"Server online on port {self.port}")
        
        while not self.will_shut_down:
            try:
                # accept incoming connection
                conn = Socket(self.socket.accept()[0]) 
                try:             
                    conn.send_multi(self.uuid, self.file_tracker.dir_info()) 
                    uuid, hostname, port = conn.recv_multi() # recv introduction
                    logger.info(f"Server accepted connection from {uuid}")
                except socket.error as e: # TODO should disconnect client
                    logger.info(f"Failed bilateral connection to {uuid} @ ({hostname}, {port}): {e}")
                    uuid = False
                    
                if uuid: # connection successfully accepted
                    if uuid not in self.clients: # if this server not connected to uuid
                        
                        # if uuid is not know update or create new entry
                        if uuid not in self.connections:
                            if temp_uuid(hostname, port) not in self.connections: # connection has also not been entered by the user 
                                self.connections.new_connection(hostname, port, uuid=uuid) 
                            else: # connection is only known by temporary uuid
                                self.connections.update(temp_uuid(hostname, port), new_uuid=uuid)
                                
                        self.connections.update(uuid, new_hostname=hostname, new_port=port)
                        
                        # establish bilateral connection: connect back to uuid
                        if not self._connect(uuid, hostname, port):
                            pass # bilateral connection was not successful -> TODO: disconnect or smth
                        
                    if uuid not in self.client_threads or not self.client_threads[uuid].is_alive():
                        self.client_threads[uuid] = threading.Thread(target=self.handle_client, args=(uuid,conn), name=str(uuid))
                        self.client_threads[uuid].start()
                        logger.info(f"Start thread {uuid}")
                    
            except socket.error:
                logger.info("Server socket has been closed")
                logger.info("Server offline")
                self.will_shut_down = True        
                
        
    def connect(self, uuid): 
        hostname = self.connections[uuid][CONN_HOSTNAME_KEY]
        port = self.connections[uuid][CONN_PORT_KEY]
        
        # check if already connected or connection attempt in progress
        if uuid in self.clients: return True 
        if (port, hostname) not in self.connections_in_progress: 
            self.connections_in_progress.add((port, hostname))
        else: return None
        
        logger.debug(f"Initiate connection attempt to {uuid} @ ({hostname}, {port})")
        conn_success = self._connect(uuid, hostname, port)
        
        self.connections_in_progress.remove((port, hostname))
        return conn_success
    
    def _connect(self, uuid, hostname, port):
        try:
            print("_connect", uuid, hostname, port)
            # establish connection
            client = Client(self.uuid, self.sessions, self.file_tracker, self.logging_settings, \
                            self.directory_locks, self.callbacks.sync_status_change, self.callbacks.new_conflict)
            server_uuid, dir_info = client.connect(hostname, port)
            
            # tell connection who we are
            client.send_multi(self.uuid, self.hostname, self.port) # send introduction
            self.clients[server_uuid] = client
            
            # update info on connection
            self.connections.update(uuid, new_uuid=server_uuid, new_dir_info=dir_info)
            logger.info(f"Client connected to {client.conn_str()}")
            print("uuid change:", uuid, server_uuid)
                
            self.callbacks.status_change(server_uuid)
            return server_uuid
        except socket.error as e:
            logger.debug(f"Failed connection attempt to {uuid} @ ({hostname}, {port}): {e}")
            self.callbacks.status_change(uuid)
            return False 
            
    def close_connection(self, uuid):
        if uuid in self.clients:
            logger.info(f"Disconnecting from {uuid} @ ({self.connections[uuid][CONN_HOSTNAME_KEY]}, {self.connections[uuid][CONN_PORT_KEY]})")
            self.clients.pop(uuid).close()
            self.callbacks.status_change(uuid)
        
    def shut_down(self):
        self.will_shut_down = True
        logger.debug(f"Active connections at shutdown: {self.clients.keys()}")
        logger.debug(f"Active Threads: {threading.enumerate()}")
        
        for uuid in list(self.clients.keys()): # need to parse to list otherwise "dictionary changed size during iteration" error eccours
            self.close_connection(uuid)
            self.client_threads.pop(uuid).join()
            
        self.socket.close()
        
    
    def handle_client(self, uuid, conn):  
        while True:
            if uuid not in self.clients or self.clients[uuid].connected is False: 
                logger.info(f"Close thread {uuid}")
                break      
            select.select([conn.socket], [], []) # block until until new message
            try:
                code = conn.recv_code()
                {
                    NT_Code.REQ_DIR_LST     : self._fetch_dir_list,
                    NT_Code.REQ_DIR_GRAPH   : self._fetch_dir_graph,
                    NT_Code.REQ_FILE        : self._fetch_file,
                    NT_Code.REQ_SYNC_START  : self._start_sync,
                    NT_Code.REQ_SYNC        : self._sync_back,
                    NT_Code.END_SYNC        : self._end_sync,
                    NT_Code.END_CONN        : self._close_connection
                }[code](uuid, conn)
            except ConnectionResetError:
                self.clients[uuid].logger.info(f"An existing connection was forcibly closed by the remote host @ {uuid}. Will terminate thread")
                break
            except OSError:
                self.clients[uuid].logger.exception(f"OSError in Server.handle_connection @ {uuid}. Will terminate thread")
                break
        self.close_connection(uuid)
            
                
    
    def _close_connection(self, uuid, conn):
        conn.close() # must be closed before client closed connection
        if uuid in self.clients: 
            self.clients[uuid].logger.info(f"Remote host {self.clients[uuid].conn_str()} disconnected")
            self.clients.pop(uuid).close()
            self.callbacks.status_change(uuid)
    
    def _start_sync(self, uuid, conn):
        local_dir = conn.recv_str()
        remote_dir = conn.recv_str()
        locked = self.directory_locks[local_dir].acquire(timeout=3)
        if locked: 
            self.callbacks.sync_status_change(uuid, local_dir, remote_dir, 1)
            self.active_syncs[uuid] = local_dir
        conn.send_int(locked)      
    
    def _end_sync(self, uuid, conn):
        local_dir = conn.recv_str()
        remote_dir = conn.recv_str()
        self.callbacks.sync_status_change(uuid, local_dir, remote_dir, 0)
        self.directory_locks[local_dir].release()
        del self.active_syncs[uuid]
        
    def _sync_back(self, uuid, conn):
        local_dir = conn.recv_str()
        remote_dir = conn.recv_str()
        
        if not self.connections.has_sync(uuid, local_dir, remote_dir):
            self.connections.add_sync(uuid, local_dir, remote_dir)
            
        self.clients[uuid].queue_sync(local_dir, remote_dir, self.connections.get_sync_conflict_policy(uuid, local_dir, remote_dir), \
            self.connections.get_sync_conflict_resolve(uuid, local_dir, remote_dir), False, priority=0)
        
        conn.send_code(NT_Code.END_SYNC)
            
    def _fetch_dir_list(self, uuid, conn):
        conn.send_obj(list(self.file_tracker.directories_list))
        self.clients[uuid].logger.debug(f"Send directory list to {uuid}")
        
    def _fetch_dir_graph(self, uuid, conn):
        directory = conn.recv_str()
        self.file_tracker[directory].update()
        conn.send_obj(self.file_tracker[directory].root)
        self.clients[uuid].logger.debug(f"Send directory graph of '{directory}' to {uuid}")
        
    def _fetch_file(self, uuid, conn):
        directory = conn.recv_str()
        file = conn.recv_str()
        if not self.file_tracker[directory].is_in_ignore(file): #little saftey precaution
            conn.send_file(os.path.join(directory, file))
            self.clients[uuid].logger.debug(f"Send file '{file}' to {uuid}")



