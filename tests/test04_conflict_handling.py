from test_utils import this
from multiprocessing import Process, Event
from time import sleep

import webGUI
import os
from src.FileSyncer import FileSyncer
from src.Codes import RESOLVE_POLICY
from reset_test_env import reset_syncer, reset_dirs

e1 = Event()
e2 = Event()


def syncer1(e1, e2):
    with FileSyncer(this / "Syncer1/config.json") as syncer:
        syncer.start_server()
        syncer.add_new_connection("Surface", 20000, "Surface")
        e2.wait()
        print(syncer.connect(syncer.get_uuids()[0]))
        
        uuid = "Syncer2"
        local =  this/"dir1"
        remote =  this/"dir2"
        syncer.add_directory(this/"dir1", name="dir1", ignore_patterns=["*.ign"])
        print(f"\n Result: {str(syncer.sync(uuid, local, remote).wait())} \n")
        
        #with open(this / "dir1/file_in_dir1.txt", "w") as file: file.write("a"*1000)
        with open(this / "dir2/file_in_dir1.txt", "w") as file: file.write("b"*1000)
        os.remove(this / "dir1/file_in_dir1.txt")

        print(f"\n Result: {str(syncer.sync(uuid, local, remote).wait())} \n")
        
        files, folders = syncer.get_conflicts(uuid, local, remote)
        print(files, folders)

        syncer.resolve_conflict(uuid, this/"dir1", this/"dir2", list(files.keys())[0], False, RESOLVE_POLICY.KEEP_ALL)
        #syncer.resolve_conflict(uuid, this/"dir1", this/"dir2", list(files.keys())[0], False, RESOLVE_POLICY.USE_NEWEST)
        #syncer.resolve_conflict(uuid, this/"dir1", this/"dir2", list(files.keys())[0], False, RESOLVE_POLICY.USE_LOCAL)
        #syncer.resolve_conflict(uuid, this/"dir1", this/"dir2", list(files.keys())[0], False, RESOLVE_POLICY.USE_REMOTE)

        print(f"\n Result: {str(syncer.sync(uuid, local, remote).wait())} \n")
        e1.set()
        print("Sync done")
        #webGUI.start(syncer.ui_port)
        
def syncer2(e1, e2):
    with FileSyncer(this / "Syncer2/config.json") as syncer:
        syncer.start_server()
        syncer.add_directory(this/"dir2", name="dir2", ignore_patterns=["*.ign"])
        e2.set()
        e1.wait()
        #webGUI.start(syncer.ui_port)

        
        
if __name__ == '__main__':
    reset_syncer()
    reset_dirs()
    p1 = Process(target=syncer1, args=(e1, e2))
    p2 = Process(target=syncer2, args=(e1, e2))
    p1.start()
    p2.start()

    p1.join()
    p2.join()