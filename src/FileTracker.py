
import datetime
import glob
import json
import logging
import os
import pickle
import time
from hashlib import sha1
from pathlib import Path
from threading import Thread

from imohash import hashfile

from src.Config import DATE_TIME_FORMAT, DEFAULT_TIME, DIR_IGNORE_KEY, get_logger
from src.utils import hash_word, now, rel_path
from src.Codes import CONFLICT_TYPE, RESOLVE_POLICY

logger_name, logger = get_logger(__name__)




class DirectoryElement:
    """ Base class for file/folder """
    def __init__(self, rel_path:Path, dir_path:Path):
        self.dir_path = dir_path
        self.locations = {DEFAULT_TIME:rel_path} # will be used later for when file movement detection is implemented
        self.logger = logging.getLogger(f"{logger_name}.{hash_word(dir_path)}")
        self._deleted = DEFAULT_TIME
        self._created = DEFAULT_TIME
                 
    def location(self, time=now(), prev=False) -> Path:
        """returns location at *time* (relative to dir_path)"""
        times = sorted(list(self.locations.keys()) + [time])
        return self.locations[times[times.index(time)-(1+int(prev))]]
    
    def created(self, time=now()) -> None:
        self._deleted = DEFAULT_TIME
        self._created = time
    
    def deleted(self, time=now()) -> None:
        self._deleted = time
        self._created = DEFAULT_TIME
        
    def update(self): raise NotImplementedError # to override
    
    def is_modified(self): raise NotImplementedError # to override
    
    @property
    def rel_path(self) -> Path: return self.location()
        
    @property
    def last_modif_time(self) -> datetime.datetime: raise NotImplementedError # to override
    
    @property
    def full_path(self) -> Path: return self.dir_path / self.location()
    
    @property
    def exists(self) -> bool: return self._deleted == DEFAULT_TIME
    
    @property
    def name(self) -> str: return self.__repr__()
    
    def __repr__(self):
        return self.full_path.name
    
    
    
class File(DirectoryElement):
    def __init__(self, rel_path, dir_path, update_on_creation=True):
        super().__init__(rel_path, dir_path)
        self.hash = 0
        if update_on_creation: self.update()
        
    @property
    def last_modif_time(self) -> datetime.datetime: 
        return max(datetime.datetime.utcfromtimestamp(self.full_path.stat().st_mtime), self._created)
    
    def update(self):
        if not self.exists: self.created()
        # update hash if file has been modified since last update
        if (new_hash := hashfile(self.full_path)) != self.hash:
            self.hash = new_hash
            
    def is_modified(self, time) -> bool:
        """ returns boolean value wether file has been modified during the time span between now and *time*"""
        if self.full_path.exists(): return self.last_modif_time > time
        else: return self._deleted > time  # self._created > time #? shouldnt it be self._deleted?
            
   
   
   
   


#######################
#       FOLDER
#######################
class Folder(DirectoryElement):
    def __init__(self, rel_path:Path, dir_path:Path, ign_ptn, update_on_creation=True):
        super().__init__(rel_path, dir_path)
        self.ignore_patterns = ign_ptn
        self.folders = {}
        self.files = {}
        if update_on_creation: self.update()
    
    def is_in_ignore(self, path:Path, is_file=None) -> bool:  # is_file currently not in use
        rel = rel_path(path, self.dir_path)
        for pattern in self.ignore_patterns:
            if rel.match(pattern): return True
        return False
    
    def deleted(self) -> None:
        super().deleted()
        for file in self.files.values(): file.deleted()
        for folder in self.folders.values(): folder.deleted()
        
    @property
    def last_modif_time(self) -> datetime.datetime: 
        return max(self._created, *[obj.last_modif_time for obj in {**self.folders, **self.files}.values()])
    
    def is_modified(self, time) -> bool:
        # creating a folder also counts as modifying it
        if self._created > time: return True
        # check if any subfolders  or files have been modified
        for dir_element in {**self.folders, **self.files}.values():
            if dir_element.is_modified(time): return True
        return False 
    
    def update_ign_ptn(self, ign_ptn):
        self.ignore_patterns = ign_ptn
        for _, folder in self.folders.items():
            folder.update_ign_ptn(ign_ptn)
    
    def update(self):
        """ updates state (= _created, _deleted) of self and folders/files"""
        # check if file self been created
        if not self.exists: self.created()
        
        # check if file/folder has been deleted from disk but has not been registered yet
        for dir_element in {**self.folders, **self.files}.values():
            if not dir_element.full_path.exists() and dir_element.exists:
                dir_element.deleted()
                self.logger.info(f"'{dir_element.location()}' deleted")
        
        # update files    
        for file in filter(lambda f: f.is_file(), self.full_path.iterdir()):
            rel_path = self.location() / file.name
            if not self.is_in_ignore(file):
                if rel_path in self.files:  
                    self.files[rel_path].update()
                else:  
                    self.files[rel_path] = File(rel_path, self.dir_path) 
                    self.logger.info(f"File '{rel_path}' created")
            elif rel_path in self.files:
                del self.files[rel_path]
                self.logger.info(f"File '{rel_path}' is now ignored")
        
        # update folders
        for folder in filter(lambda f: f.is_dir(), self.full_path.iterdir()):
            rel_path = self.location() / folder.name
            if not self.is_in_ignore(folder): 
                if rel_path in self.folders:  
                    self.folders[rel_path].update()
                else:
                    self.folders[rel_path] = Folder(rel_path, self.dir_path, self.ignore_patterns)
            elif rel_path in self.folders:
                del self.folders[rel_path]
                self.logger.info(f"Folder '{rel_path}' is now ignored")
                        
    def merge(self, other, last_time_synced, conflict_callback) -> None:
        """
        Merges this folder and another folder
        
        Parameters:
            other (Folder): folder to be merged with this folder (=self)
            last_time_synced (datetime.datetime): last time self and other were synced 
            conflict_callback (function): function called when there is a conflict
        """   
        # update_on_creation is set to false since the files/folders must be downloaded first
        for file in other.files:
            if not self.is_in_ignore(file, is_file=True):
                if other.files[file].exists:
                
                    if file not in self.files:
                        # self does not contain *file*
                        self.files[file] = File(other.files[file].rel_path, self.dir_path, False)
                        
                    elif self.files[file].hash != other.files[file].hash and other.files[file].is_modified(last_time_synced): 
                        # self contains *file* but their contents are different and other.file has been modified since last sync
                        if self.files[file].is_modified(last_time_synced):
                            # both have been modifed since last sync -> conflict
                            conflict_callback(self, other, self.files[file].rel_path, False, file, CONFLICT_TYPE.MODIF_CONFLICT) 
                        else:
                            self.files[file] = File(other.files[file].rel_path, self.dir_path, False)
                            
                else: # other.file has been deleted
                    if file in self.files:
                        if self.files[file].is_modified(last_time_synced):
                            # other.file has been deleted but self.file has been modified -> conflict
                            conflict_callback(self, other,  self.files[file].rel_path, False, file, CONFLICT_TYPE.DELETE_CONFLICT)
                        else:
                            self.files[file].deleted()
                            
        for folder in other.folders:
            if not self.is_in_ignore(folder, is_file=False):
                if other.folders[folder].exists:
                    
                    if folder not in self.folders:
                        # self does not contain *folder*
                        self.folders[folder] = Folder(other.folders[folder].location(), self.dir_path, self.ignore_patterns,False)
                    
                    # merge subfolders aswell
                    self.folders[folder].merge(other.folders[folder], last_time_synced, conflict_callback)
                    
                else: # other.folder has been deleted
                    if folder in self.folders: 
                        if self.folders[folder].is_modified(last_time_synced):
                            # other.folder has been deleted but self.folder has been modified -> conflict
                            conflict_callback(self, other, self.folders[folder].rel_path , True, folder, CONFLICT_TYPE.DELETE_CONFLICT)
                        else:
                            self.folders[folder].deleted()
                            
    def to_dict(self):
        return {
            "name": self.name,
            "files":{str(path):file.name for path, file in self.files.items() if file.exists},
            "folders":{str(path):folder.to_dict() for path, folder in self.folders.items() if folder.exists}
        }
                            



#######################
#     DIRECTORY
#######################
class Directory():
    def __init__(self, path:Path, save_folder:Path, dir_ignore, glob_ignore, logging_settings, update_callback):
        self.path = path  # location of the directory on disk
        self.hash = hash_word(self.path)
        self.save_file = save_folder / self.hash  # file where directory Graph is stored
        self.dir_ign_patterns = dir_ignore 
        self.glob_ign_patterns = glob_ignore
        self.logger = logging_settings.create_logger(f"{logger_name}.{self.hash}", f"{self.hash}.log")
        self.update_callback = update_callback
        
        if self.save_file.exists():
            self.root = pickle.loads(self.save_file.read_bytes())
            self.root.update_ign_ptn(self.ignore_patterns)
        else:
            self.root = Folder(Path(), self.path, self.ignore_patterns)
        self.save()
    
    def update_ign_patterns(self, dir_ign=None, glob_ign=None):
        if dir_ign is not None: self.dir_ign_patterns = dir_ign
        if glob_ign is not None: self.glob_ign_patterns = glob_ign
        self.root.update_ign_ptn(self.ignore_patterns)
        self.update(callback=True)
        
    def update(self, callback=False):
        self.logger.info(f"Updating directory {self.path}")
        self.root.update()
        if callback: self.update_callback(str(self.path))
        
    def save(self):
        self.save_file.write_bytes(pickle.dumps(self.root))
        logger.info(f"Save directory tracker @ {self.path}")
    
    def to_dict(self):
        return self.root.to_dict()
    
    def is_in_ignore(self, f):
        return self.root.is_in_ignore(Path(f))
    
    @property
    def ignore_patterns(self): 
        return list(set(self.dir_ign_patterns + self.glob_ign_patterns))
    
    
    


#######################
#     FILE TRACKER
#######################
class FileTracker:
    """Stores tracked/manages tracked directories"""
    def __init__ (self, directories, logging_settings, data_path, glob_ign_ptn, update_callback):
        logger.info("Filetracker online")
        self.directories_list = directories # data on directories to track
        self.logging_settings = logging_settings
        self.save_path = data_path
        self.update_callback = update_callback
        self.global_ign_patterns = glob_ign_ptn
    
        self.directories = {} 
        for dir_path, dir_props in self.directories_list.items():
            self.directories[dir_path] = Directory(Path(dir_path), self.save_path, dir_props[DIR_IGNORE_KEY], self.global_ign_patterns, self.logging_settings, update_callback)
        
        for _, directory in self.directories.items():
            directory.update()
        
    def add_directory(self, path:Path,  name:str, dir_ign_patterns:list) -> None:
        if path in self.directories: raise Exception(f"Already tracking {path}")
        
        self.directories[path] = Directory(path, self.save_path, dir_ign_patterns, self.global_ign_patterns, self.logging_settings, self.update_callback)
        self.directories_list.new_directory(path, name, dir_ign_patterns)
        
        logger.info(f"Tracking directory {path}") 
        
    def update_dir_ignore(self, dir_path, ign_patterns):
        self.directories[dir_path].update_ign_patterns(dir_ign = ign_patterns)
        self.directories_list.update(dir_path, ign_patterns=ign_patterns)
    
    def update_glob_ignore(self, ign_patterns):
        for _, directory in self.directories.items():
            directory.update_ign_patterns(glob_ign=ign_patterns)
    
    def save(self):
        for directory in self.directories.values():
            self.directories_list.update(directory.path, directory.dir_ign_patterns, directory.hash)
            directory.save()
    
    def shut_down(self): 
        self.save()
        logger.info("FileTracker offline")
        
    def __contains__(self, path:os.PathLike) -> bool:
        return Path(path) in self.directories    
        
    def __getitem__(self, path:os.PathLike):
        return self.directories[str(path)]   

    def __iter__(self):
        return iter(self.directories)   
    
    def keys(self):
        return self.directories.keys()

