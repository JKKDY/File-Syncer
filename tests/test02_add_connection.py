from test_utils import this
from multiprocessing import Process
from time import sleep

import webGUI
from src.FileSyncer import FileSyncer
from reset_test_env import reset_syncer


def syncer1():
    with FileSyncer(this / "Syncer1/config.json") as syncer:
        syncer.start_server()
        syncer.add_new_connection("Surface", 20000, "Surface")
        print("UUIDs: ", syncer.get_uuids())
        print("Connections: " , syncer.get_connections())
        syncer.connect(syncer.get_uuids()[0])

        webGUI.start(syncer.ui_port, 55000)
        
def syncer2():
    with FileSyncer(this / "Syncer2/config.json") as syncer:
        syncer.start_server()
        webGUI.start(syncer.ui_port, 60000)
        
        
if __name__ == '__main__':
    reset_syncer()
    p1 = Process(target=syncer1, args=())
    p2 = Process(target=syncer2, args=())
    p1.start()
    p2.start()

    p1.join()
    p2.join()