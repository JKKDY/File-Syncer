import eel
from src.ui import UiFrontend, UI_Code



def keys(d, ret = []):
    for k,v in d.items():
        if isinstance(v, dict): ret + keys(v, ret)
        ret.append(k)
    return ret




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
            UI_Code.NOTF_UPDATE_UUID : lambda *args: eel.update_uuid(*args)(),
            UI_Code.NOTF_UPDATE_STATUS : lambda *args: eel.update_status(*args)(),
            UI_Code.NOTF_UPDATE_DIR_GRAPH : lambda *args: eel.update_directory_graph(*args)(),
            UI_Code.NOTF_NEW_CONNECTION: lambda *args: eel.new_connection(*args)()
        }) 
        
    def start(self):
        self.start_event_loop()
        eel.start('index.html', port=55000)
        

def start(port=7000):
    global webgui
    webgui = WebGUI(7000)
    webgui.start()
    webgui.close()


if __name__ == "__main__":
    start()
