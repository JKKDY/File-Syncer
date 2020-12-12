import socket
import os
import pickle
import threading
import select
import datetime
import logging
from pathlib import Path

from src.FileTracker import FileTracker
from src.Config import get_logger, temp_uuid, DATE_TIME_FORMAT, PORT_KEY, HOSTNAME_KEY, SYNCS_KEY
from src.Client import Client
from src.Network import Socket, NT_Code, NT_MSG_TYPE


logger_name, logger = get_logger(__name__)



class Callbacks:
    def __init__(self, uuid_change, status_change):
        self.uuid_change = uuid_change
        self.status_change = status_change


class Server():
    def __init__(self, hostname, ip, port, uuid, file_tracker, sessions, connections, \
        directories, log_settings, callbacks):
        self.file_tracker = file_tracker
        self.sessions = sessions
        self.connections = connections
        self.directories = directories
        self.logging_settings = log_settings
        self.hostname = hostname
        self.ip = ip
        self.port = port
        self.uuid = uuid
        self.callbacks = callbacks
        self.clients = {}
        self.client_threads = {}
        self.will_shut_down = False
        self.socket = Socket()
        # self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.ip, self.port)
        
    def connect(self, uuid):        
        assert(uuid not in self.clients)
        hostname = self.connections[uuid][HOSTNAME_KEY]
        port = self.connections[uuid][PORT_KEY]
        logger.info(f"Initiate connection to {uuid} @ ({hostname}, {port})")
        return self._connect(uuid, hostname, port)

    
    def _connect(self, uuid, hostname, port):
        try:
            client = Client(self.uuid, self.sessions, self.file_tracker, self.logging_settings)
            server_uuid, dir_info = client.connect(hostname, port)
            self.clients[server_uuid] = client
            client.send_multi(self.uuid, self.hostname, self.port) # send introduction
            self.connections.update(uuid, new_uuid=server_uuid, new_dir_info=dir_info)
            logger.info(f"Client connected to {client.conn_str()}")
            if uuid is not server_uuid: # uuid has changed
                self.callbacks.uuid_change(uuid, server_uuid)
            self.callbacks.status_change(server_uuid)
            return server_uuid
        except socket.error as e:
            logger.info(f"Failed connection attempt to {uuid} @ ({hostname}, {port}): {e}")
            self.callbacks.status_change(uuid)
            return False
            

    def start_server(self):
        """Start server loop for accepting connections"""
        self.will_shut_down = False
        self.socket.listen()
        logger.info(f"Server online on port {self.port}")
        
        while not self.will_shut_down:
            try:
                conn = Socket(self.socket.accept()[0]) 
                try:             
                    conn.send_multi(self.uuid, self.directories.info())
                    uuid, hostname, port = conn.recv_multi() # recv introduction
                    logger.info(f"Server accepted connection from {uuid}")
                except socket.error as e: # TODO should disconnect client
                    logger.info(f"Failed bilateral connection to {uuid} @ ({hostname}, {port}): {e}")
                    uuid = False
                    
                if uuid: # connection was successful
                    if uuid not in self.clients: # if this server not connected to uuid
                        if uuid not in self.connections: # if uuid not known
                            if temp_uuid(hostname, port) not in self.connections: # if connection has also not been entered by the user 
                                self.connections.new_connection(hostname, port, uuid=uuid) 
                            else: # if connection is only known by temporary uuid
                                self.connections.update(temp_uuid(hostname, port), new_uuid=uuid)
                        self.connections.update(uuid, new_hostname=hostname, new_port=port)
                        if not self._connect(uuid, hostname, port):
                            pass # bilateral connection was not successful -> disconnect or smth
                    if uuid not in self.client_threads or not self.client_threads[uuid].is_alive():
                        self.client_threads[uuid] = threading.Thread(target=self.handle_client, args=(uuid,conn), name=str(uuid))
                        self.client_threads[uuid].start()
                        logger.info(f"Start thread {uuid}")
                    
            except socket.error:
                logger.info("Server socket has been closed")
                logger.info("Server offline")
                self.will_shut_down = True        
    
    
    def handle_client(self, uuid, conn):        
        while True:
            if uuid not in self.clients or self.clients[uuid].connected is False: 
                logger.info(f"Close thread {uuid}")
                break      
            select.select([conn.socket], [], []) # block until until new message
            try:
                code = conn.recv_code()
                {
                    NT_Code.REQ_DIR_LST  : self.fetch_dir_list,
                    NT_Code.REQ_DIR_GRAPH: self.fetch_dir_graph,
                    NT_Code.REQ_FILE     : self.fetch_file,
                    NT_Code.REQ_SYNC     : self.sync_dir,
                    NT_Code.END_CONN     : self._close_connection
                }[code](uuid, conn)
            except OSError:
                self.clients[uuid].logger.exception(f"OSError in handle_connection @ {uuid}. Will terminate")
                break
                    
    def _close_connection(self, uuid, conn):
        conn.close() # must be closed before client closed connection
        if uuid in self.clients: 
            self.clients.pop(uuid).close()
            self.callbacks.status_change(uuid)
        

    def close_connection(self, uuid):
        logger.info(f"Disconnecting from {uuid} @ ({self.connections[uuid][HOSTNAME_KEY]}, {self.connections[uuid][PORT_KEY]})")
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
             
            
    def fetch_dir_list(self, uuid, conn):
        conn.send_obj(list(self.file_tracker.directories_list))
        self.clients[uuid].logger.debug(f"Send directory list to {uuid}")
        
    def fetch_dir_graph(self, uuid, conn):
        directory = conn.recv_str()
        self.file_tracker[directory].update()
        conn.send_obj(self.file_tracker[directory].root)
        self.clients[uuid].logger.debug(f"Send directory graph to {uuid}")
        
    def fetch_file(self, uuid, conn):
        directory = conn.recv_str()
        file = conn.recv_str()
        if not self.file_tracker[directory].is_in_ignore(file): #little saftey precaution
            conn.send_file(os.path.join(directory, file))
            self.clients[uuid].logger.debug(f"Send directory changes to {uuid}")
        
    def sync_dir(self, uuid, conn):
        local_dir = conn.recv_str()
        remote_dir = conn.recv_str()
        
        if not self.connections.has_sync(uuid, local_dir, remote_dir):
            self.connections.add_sync(uuid, local_dir, remote_dir)
            
        self.clients[uuid].sync(local_dir, remote_dir, False)
        
        
    
    
        
        