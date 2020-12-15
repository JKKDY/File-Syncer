import datetime
import os
import threading
import time
from hashlib import md5, sha1
from pathlib import Path


def now():
    return datetime.datetime.utcnow()



# creates a nested dictionary from given keys (in order of given keys)
def create_nested_dict(keys, default_value=None):
     return default_value if keys == [] else {keys[0]: create_nested_dict(keys[1:], default_value)}

def update_with_nested_dict(keys, dictionary, default_value = None):
    if keys[0] not in dictionary: dictionary[keys[0]] = create_nested_dict(keys[1:], default_value)
    elif len(keys) == 1: return
    else: update_with_nested_dict(keys[1:], dictionary[keys[0]], default_value)
         
         
         
         
# hash a word
def hash_word(word):
    return sha1(str(word).encode()).hexdigest()[:20]


def abs_path(path:os.PathLike, base_path:os.PathLike) -> Path:
    if os.path.isabs(path): return path
    else: return Path(os.path.join(base_path, path))
    
def rel_path(path:os.PathLike, base_path:os.PathLike) -> Path:
    if os.path.isabs(path): return Path(os.path.relpath(path, base_path))
    else: return path
    
    

# from https://medium.com/greedygame-engineering/an-elegant-way-to-run-periodic-tasks-in-python-61b7c477b679
class RepeatedJob(threading.Thread):
    """Repeats *execute* every *interval* seconds"""
    def __init__(self, interval, execute, name, args=[], kwargs={}):
        threading.Thread.__init__(self)
        self.daemon = False
        self.name = name
        self.stopped = threading.Event()
        self.interval = interval
        self.execute = execute
        self.args = args
        self.kwargs = kwargs
        
    def stop(self):
        self.stopped.set()
        self.join()
        
    def run(self):
        while not self.stopped.wait(self.interval):
            self.execute(*self.args, **self.kwargs)



class Timer: # for benchmark purposes
    def start(self):
        self.start_time = time.time()
        
    def stop(self):
        return time.time - self.start_time()
