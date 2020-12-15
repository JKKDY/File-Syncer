from pathlib import Path
from src.FileSyncer import FileSyncer

import webGUI

# auto connect: -1=default_rate, 0=no, n>0=try connect every n seconds


if __name__ == "__main__":
    with FileSyncer(Path("config.json")) as syncer:
        syncer.start_server()
        webGUI.start() 


