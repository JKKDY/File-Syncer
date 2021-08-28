import datetime
import os
import threading
import time
from contextlib import contextmanager
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
    
    
class NestedDict:
    def __init__(self, d={}) -> None:
        self.dict = {key:(dict(value) if isinstance(value, dict) else value) for key, value in d.items()}
        
    def __getitem__(self, key):
        if key not in self.dict: self.dict[key] = NestedDict()
        elif isinstance(self.dict[key], dict): self.dict[key] = NestedDict(self.dict[key])
        return self.dict[key]
    
    def __setitem__(self, key, val):
        if isinstance(val, dict): self.dict[key] = NestedDict(val)
        else: self.dict[key] = val
    
    def __delitem__(self, key):
        del self.dict[key]
        
    def __contains__(self, key):
        return key in self.dict
    
    def __iter__(self):
        return iter(self.dict)   
        
    def to_dict(self):
        return {key:(value.to_dict() if isinstance(value, NestedDict) else value) for key, value in self.dict.items()}
    
    def keys(self):
        return self.directories.keys()
         
         
         
         
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
    def __init__(self, interval, target, name, args=[], kwargs={}):
        threading.Thread.__init__(self)
        self.daemon = False
        self.name = name
        self.stopped = threading.Event()
        self.interval = interval
        self.execute = target
        self.args = args
        self.kwargs = kwargs
        
    def stop(self):
        self.stopped.set()
        if self.is_alive(): self.join()
        
    def run(self):
        while not self.stopped.wait(self.interval):
            self.execute(*self.args, **self.kwargs)
            
            
            

# https://stackoverflow.com/questions/16740104/python-lock-with-statement-and-timeout
@contextmanager
def acquire_timeout(lock, timeout):
    result = lock.acquire(timeout=timeout)
    yield result
    if result:
        lock.release()



class Timer: # for benchmark purposes
    def start(self):
        self.start_time = time.time()
        
    def stop(self):
        return time.time - self.start_time()
    
    
    
def copy_name(name, ending, container, it=0):
    if new_name := name + "_copy" + ending in container:
        return copy_name(name, f" ({it})" + ending, container, it=it+1)
    else: return new_name
    
    