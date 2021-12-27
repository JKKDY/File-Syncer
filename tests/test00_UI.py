from test_utils import this
from multiprocessing import Process
from time import sleep

import webGUI
from src.FileSyncer import FileSyncer
from reset_test_env import reset_syncer, reset_dirs


def syncer1():
    with FileSyncer(this / "Syncer1/config.json") as syncer:
        syncer.start_server()
        syncer.add_new_connection("Surface", 20000, "Surface")
        syncer.add_directory(this/"dir1", name="dir1", ignore_patterns=["*.ign"])
        syncer.add_sync(syncer.get_uuids()[0], this/"dir1", this/"dir2", auto_sync=723856, local_ignores=["local1", "local2"], synced_ignores=["synced1", "synced2"])
        with open(this/"dir1/file in dir2.txt", "w") as file:
            file.write("kjsfkjdskjbfkjb")
        webGUI.start(syncer.ui_port, 55000)
        
def syncer2():
    with FileSyncer(this / "Syncer2/config.json") as syncer:
        syncer.start_server()
        syncer.add_new_connection("Surface", 10000, "Surface")
        syncer.add_directory(this/"dir2", name="dir2", ignore_patterns=["*.ign"])
        webGUI.start(syncer.ui_port, 60000)
        
        
        
if __name__ == '__main__':
    reset_syncer()
    reset_dirs()
    p1 = Process(target=syncer1, args=())
    #p2 = Process(target=syncer2, args=())
    p1.start()
    #p2.start()

    p1.join()
    #p2.join()