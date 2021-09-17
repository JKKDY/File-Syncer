from test_utils import this
import webGUI
from src.FileSyncer import FileSyncer
from reset_test_env import reset_syncer, reset_dirs
from threading import Thread
import time


if __name__ == '__main__':
    reset_syncer()
    reset_dirs()
    with FileSyncer(this / "Syncer1/config.json") as syncer:
        syncer.start_server()
        syncer.add_directory(this/"dir1", name="dir1", ignore_patterns=["*.ign"])
        def add():
            #time.sleep(0.7)
            syncer.add_directory(this/"dir2", name="dir2")
        t = Thread(target=add)
        t.start()
        webGUI.start(syncer.ui_port)
        t.join()

