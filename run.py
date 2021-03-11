from pathlib import Path
from src.FileSyncer import FileSyncer

import webGUI

# auto connect: -1=default_rate, 0=no, n>0=try connect every n seconds

import time
from threading import Thread
if __name__ == "__main__":
    with FileSyncer(Path("config.json")) as syncer:
        syncer.start_server()
        t1 = Thread(target=syncer.connect, args=["3c8fd4fd-1981-11eb-a7f5-70bc105d2bbd"])
        t2 = Thread(target=syncer.connect, args=["3c8fd4fd-1981-11eb-a7f5-70bc105d2bbd"])
        t1.start()
        # time.sleep(0.001)
        t2.start()
        t1.join()
        t2.join()
        webGUI.start() 
        # syncer.auto_connect()


