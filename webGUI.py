import eel
from src.ui import UiFrontend, UI_Code




@eel.expose
def get_uuids(): return webgui.request(UI_Code.REQ_UUIDS) 
@eel.expose
def get_uuid_name(uuid): return webgui.request(UI_Code.REQ_UUID_NAME, uuid)
@eel.expose
def get_uuid_info(uuid): return webgui.request(UI_Code.REQ_UUID_INFO, uuid)
@eel.expose
def get_uuid_status(uuid): return webgui.request(UI_Code.REQ_UUID_STATUS, uuid)  # https://stackoverflow.com/questions/2535055/check-if-remote-host-is-up-in-python

@eel.expose
def add_connection(hostname, port, name): return webgui.request(UI_Code.ADD_CONNECTION, hostname, port, name)
@eel.expose
def connect(uuid): return webgui.request(UI_Code.UUID_CONNECT, uuid)
@eel.expose
def disconnect(uuid): webgui.request(UI_Code.UUID_DISCONNECT, uuid)


def foo():pass


class WebGUI(UiFrontend):
    def __init__(self, port):
        eel.init('web')
        super().__init__(port, {
            UI_Code.UPDATE_UUID : lambda *args: eel.update_uuid(*args)(),
            UI_Code.UPDATE_STATUS : lambda *args: eel.update_status(*args)()
        }) 
        
    def start(self):
        self.start_event_loop()
        eel.start('index.html', port=60000)
        

def start(port=7000):
    global webgui
    webgui = WebGUI(7000)
    webgui.start()
    webgui.close()


if __name__ == "__main__":
    start()
