import eel
from tkinter import Tk     # from tkinter import Tk for Python 3.x
from tkinter.filedialog import askdirectory
from src.ui import UiFrontend, UI_Code




def keys(d, ret = []):
    for k,v in d.items():
        if isinstance(v, dict): ret = ret + keys(v, ret)
        ret.append(k)
    return ret


# TODO: add debug logging

@eel.expose
def get_uuids(): return webgui.request(UI_Code.REQ_UUIDS) 
@eel.expose 
def get_uuid_info(uuid): return webgui.request(UI_Code.REQ_UUID_INFO, uuid)
@eel.expose
def get_uuid_status(uuid): return webgui.request(UI_Code.REQ_UUID_STATUS, uuid)  # https://stackoverflow.com/questions/2535055/check-if-remote-host-is-up-in-python

@eel.expose
def get_directories(): return webgui.request(UI_Code.REQ_DIRS)
@eel.expose
def get_dir_info(directory): return webgui.request(UI_Code.REQ_DIR_INFO, directory)
@eel.expose
def get_dir_graph(dir_path): return webgui.request(UI_Code.REQ_DIR_GRAPH, dir_path)
@eel.expose
def add_directory(dir_path, name, ign_patterns): webgui.request(UI_Code.ADD_DIR, dir_path, name, ign_patterns)

@eel.expose
def add_connection(hostname, port, name): return webgui.request(UI_Code.ADD_CONNECTION, hostname, port, name)
@eel.expose
def connect(uuid): return webgui.request(UI_Code.UUID_CONNECT, uuid)
@eel.expose
def disconnect(uuid): webgui.request(UI_Code.UUID_DISCONNECT, uuid)

@eel.expose
def get_conflicts(uuid, local, remote): 
    files, folders =  webgui.request(UI_Code.UUID_REQ_CONFLICTS, uuid, local, remote)
    files = {str(path):conflict.__dict__ for path, conflict in files.items()}
    folders = {str(path):conflict.__dict__ for path, conflict in folders.items()}
    return files, folders
@eel.expose
def resolve_conflicts(uuid, local_dir, remote_dir, rel_path, is_dir, resolve_policy): 
    webgui.request(UI_Code.UUID_RESOLVE_CONFLICT, uuid, local_dir, remote_dir, rel_path, is_dir, resolve_policy)

@eel.expose
def add_Sync(uuid, local, remote, loc_ign, sync_ign, policy, default, auto_sync, bidirectional):
    webgui.request(UI_Code.UUID_ADD_SYNC, uuid, local, remote)
@eel.expose
def sync(uuid, local, remote): webgui.request(UI_Code.UUID_SYNC, uuid, local, remote)


@eel.expose
def ask_dir_path():
    Tk().withdraw() 
    return askdirectory()
    

class WebGUI(UiFrontend):
    def __init__(self, port):
        eel.init('web')
        super().__init__(port, {
            UI_Code.NOTF_UUID_CHANGE : lambda *args: eel.uuid_change(*args)(),
            UI_Code.NOTF_UPDATE_UUID_INFO : lambda *args: eel.update_uuid_info(*args)(),
            UI_Code.NOTF_UPDATE_STATUS : lambda *args: eel.update_status(*args)(),
            UI_Code.NOTF_UPDATE_DIR_GRAPH : lambda *args: eel.update_directory_graph(*args)(),
            UI_Code.NOTF_NEW_CONNECTION : lambda *args: eel.new_connection(*args)(),
            UI_Code.NOTF_UPDATE_SYNC_STATE : lambda *args: eel.update_sync_state(*args)(),
            UI_Code.NOTF_NEW_DIRECTORY : lambda *args: eel.new_directory(*args)(),
            UI_Code.NOTF_NEW_CONFLICT : lambda *args: self.new_conflict(*args),
            UI_Code.NOTF_DEL_CONFLICT : lambda *args: eel.delete_conflict(*args)(),
            UI_Code.NOTF_NEW_SYNC : lambda *args : eel.new_sync(*args)()
        }) 
        
    def new_conflict(self, uuid, local, remote, path, is_dir, conflict):
        eel.new_conflict(uuid, local, remote, path, is_dir, conflict.__dict__)()
        
    def start(self, eel_port, block):
        self.start_event_loop()
        try: eel.start('index.html', mode='chrome', port=eel_port, block=block, cmdline_args=['--disable-extensions', '--disable-plugins'])
        except SystemExit: print("GUI closed")
            
        

def start(server_port, eel_port=0, block=True):
    global webgui
    webgui = WebGUI(server_port)
    webgui.start(eel_port, block)
    webgui.close()

