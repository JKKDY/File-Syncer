import eel
from src.ui import UiFrontend, UI_Code



def keys(d, ret = []):
    for k,v in d.items():
        if isinstance(v, dict): ret = ret + keys(v, ret)
        ret.append(k)
    return ret


# TODO: add debug logging
# TODO: make seperate process for test purposes


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
def add_connection(hostname, port, name): return webgui.request(UI_Code.ADD_CONNECTION, hostname, port, name)
@eel.expose
def connect(uuid): return webgui.request(UI_Code.UUID_CONNECT, uuid)
@eel.expose
def disconnect(uuid): webgui.request(UI_Code.UUID_DISCONNECT, uuid)
@eel.expose
def sync(uuid, local, remote): webgui.request(UI_Code.UUID_SYNC, uuid, local, remote)


class WebGUI(UiFrontend):
    def __init__(self, port):
        eel.init('web')
        super().__init__(port, {
            UI_Code.NOTF_UUID_CHANGE : lambda *args: eel.uuid_change(*args)(),
            UI_Code.NOTF_UPDATE_UUID_INFO : lambda *args: eel.update_uuid_info(*args)(),
            UI_Code.NOTF_UPDATE_STATUS : lambda *args: eel.update_status(*args)(),
            UI_Code.NOTF_UPDATE_DIR_GRAPH : lambda *args: eel.update_directory_graph(*args)(),
            UI_Code.NOTF_NEW_CONNECTION: lambda *args: eel.new_connection(*args)(),
            UI_Code.NOTF_UPDATE_SYNC_STATE: lambda *args: eel.update_sync_state(*args)(),
            UI_Code.NOTF_NEW_DIRECTORY: lambda *args: eel.new_directory(*args)(),
            UI_Code.NOTF_NEW_SYNC : lambda *args : eel.new_sync(*args)()
        }) 
        
    def start(self, eel_port, block):
        self.start_event_loop()
        try: eel.start('index.html', mode='chrome', port=eel_port, block=block, cmdline_args=['--disable-extensions', '--disable-plugins'])
        except SystemExit: print("GUI closed")
            
        

def start(server_port, eel_port=0, block=True):
    global webgui
    webgui = WebGUI(server_port)
    webgui.start(eel_port, block)
    webgui.close()

