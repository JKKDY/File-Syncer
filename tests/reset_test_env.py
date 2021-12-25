import shutil
import os
import json
from pathlib import Path
import os


parent = Path(os.path.realpath(__file__)).parents[1]
this = Path(os.path.realpath(__file__)).parents[0]

def reset_syncer():
    for s in ["Syncer1", "Syncer2"]:
        shutil.rmtree(this/s, ignore_errors=True)
        (this/s/"data").mkdir(parents=True)
        with open(this/s/"data"/"UUID", "w") as uuid:
            uuid.write(s)
            
        shutil.copyfile(this/ "templates" / s / "config.json", this / s / "config.json")

        with open(this / s /"config.json", "r+") as file:
            data = json.load(file)
            data["data_path"] = str(this / s / data["data_path"])
            data["logs_path"] = str(this / s / data["logs_path"])
            file.seek(0)
            file.write(json.dumps(data, indent=4, sort_keys=True))
            file.truncate()

    
def reset_dirs():
    for d in ["dir1", "dir2"]:
        shutil.rmtree(this/d, ignore_errors=True)
        shutil.copytree(this/"templates"/d, this/d)    
    

    
if __name__ == "__main__":
    reset_syncer()
    reset_dirs()
