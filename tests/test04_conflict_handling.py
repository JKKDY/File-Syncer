from test_utils import this
from multiprocessing import Process, Event
from time import sleep

import webGUI
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
        print(syncer.sync(uuid, local, remote).wait())
        
        with open(this / "dir1/file_in_dir1.txt", "w") as file: file.write("a"*1000)
        with open(this / "dir2/file_in_dir1.txt", "w") as file: file.write("b"*1000)

        print(syncer.sync(uuid, local, remote).wait())
        
        folders, files = syncer.get_conflicts(uuid, local, remote)

        syncer.resolve_conflict(uuid, this/"dir1", this/"dir2", list(files.keys())[0], False, RESOLVE_POLICY.CREATE_COPY)
        #syncer.resolve_conflict(uuid, this/"dir1", this/"dir2", list(files.keys())[0], False, RESOLVE_POLICY.USE_NEWEST)
        #syncer.resolve_conflict(uuid, this/"dir1", this/"dir2", list(files.keys())[0], False, RESOLVE_POLICY.KEEP_LOCAL)
        #syncer.resolve_conflict(uuid, this/"dir1", this/"dir2", list(files.keys())[0], False, RESOLVE_POLICY.REPLACE_LOCAL)

        print(syncer.sync(uuid, local, remote).wait())
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