from pathlib import Path
from src.FileSyncer import FileSyncer

import webGUI


import time
from threading import Thread
if __name__ == "__main__":
    with FileSyncer(Path("config.json")) as syncer:
        syncer.start_server()
        syncer.start_auto_connect()
        webGUI.start(7000, 55000)        



