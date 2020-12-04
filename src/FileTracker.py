
import datetime
import json
import logging
import os
import pickle
import time
from hashlib import sha1
from pathlib import Path

from src.utils import now, hash_word, rel_path, hash_file
from src.Config import get_logger, DATE_TIME_FORMAT, DEFAULT_TIME, IGNORE_KEY


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
        
    def update(self):
        raise NotImplementedError # to override
        
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
            
        def update(self):
            if not self.exists: self.created()
            # update hash if file has been modified since last update
            if (new_hash := hash_file(self.full_path)) != self.hash:
                self.hash = new_hash
                
        def is_modified(self, time) -> bool:
            """ returns boolean value wether file has been modified during the time span between now and *time*"""
            if self.full_path.exists():
                return max(datetime.datetime.utcfromtimestamp(self.full_path.stat().st_mtime), self._created) > time
            else: 
                return self._created > time #? shouldnt it be self._deleted?
            
   
   
# Pröblem:
# Update is slow with big directories
# implement multithreading: on start one thread per directory
# when updating check (sub) folder size and depth and use a dedicated thread if it reaches a certain threshold         
    
class Folder(DirectoryElement):
    def __init__(self, rel_path:Path, dir_path:Path, in_ignore_fkt, update_on_creation=True):
        super().__init__(rel_path, dir_path)
        self.is_in_ignore = in_ignore_fkt
        self.folders = {}
        self.files = {}
        if update_on_creation: self.update()
        
    def deleted(self) -> None:
        super().deleted()
        for file in self.files.values(): file.deleted()
        for folder in self.folders.values(): folder.deleted()
        
    def is_modified(self, time) -> bool:
        # creating a folder also counts as modifying it
        if self._created > time: return True
        # check if any subfolders  or files have been modified
        for dir_element in {**self.folders, **self.files}.values():
            if dir_element.is_modified(time): return True
        return False 
    
    def update(self):
        """ updates state (= _created, _deleted) of self and folders/files"""
        # check if file self been created
        if not self.exists: self.created()
        
        # check if file/folder has been deleted from disk but has not been registered yet
        for dir_element in {**self.folders, **self.files}.values():
            if not dir_element.full_path.exists() and dir_element.exists:
                dir_element.deleted()
                self.logger.info(f"'{dir_element.location()}' deleted")
                
        # check if files/folders reated & modified        
        for dir_element in self.full_path.iterdir():
            if not self.is_in_ignore(dir_element):
                rel_path = self.location() / dir_element.name
                
                if dir_element.is_dir():
                    if rel_path in self.folders:  
                        self.folders[rel_path].update()
                    else:  
                        self.folders[rel_path] = Folder(rel_path, self.dir_path, self.is_in_ignore)
                        if logging: self.logger.info(f"Folder '{rel_path}' created")
                
                elif dir_element.is_file():
                    if rel_path in self.files:  
                        self.files[rel_path].update()
                    else:  
                        self.files[rel_path] = File(rel_path, self.dir_path) 
                        self.logger.info(f"File '{rel_path}' created")
                        
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
                        self.files[file] = File(other.files[file].location(), self.dir_path, False)
                        
                    elif self.files[file].hash != other.files[file].hash and other.files[file].is_modified(last_time_synced): 
                        # self contains *file* but their contents are different and other.file has been modified since last sync
                        if self.files[file].is_modified(last_time_synced):
                            # both have been modifed since last sync -> conflict
                            conflict_callback(self, other, file, False)      
                        else:
                            self.files[file] = File(other.files[file].location(), self.dir_path, False)
                            
                else: # other.file has been deleted
                    if file in self.files:
                        if self.files[file].is_modified(last_time_synced):
                            # other.file has been deleted but self.file has been modified -> conflict
                            conflict_callback(self, other, file, False)
                        else:
                            self.files[file].deleted()
                            
        for folder in other.folders:
            if not self.is_in_ignore(folder, is_file=False):
                if other.folders[folder].exists:
                    
                    if folder not in self.folders:
                        # self does not contain *folder*
                        self.folders[folder] = Folder(other.folders[folder].location(), self.dir_path, self.is_in_ignore,False)
                    
                    # merge subfolders aswell
                    self.folders[folder].merge(other.folders[folder], last_time_synced, conflict_callback)
                    
                else: # other.folder has been deleted
                    if folder in self.folders: 
                        if self.folders[folder].is_modified(last_time_synced):
                            # other.folder has been deleted but self.folder has been modified -> conflict
                            conflict_callback(self, other, folder, True)
                        else:
                            self.folders[folder].deleted()
                            
    def to_dict(self):
        return {
            "name": self.name,
            "files":{str(path):file.name for path, file in self.files.items() if file.exists},
            "folders":{str(path):folder.to_dict() for path, folder in self.folders.items() if folder.exists}
        }
                            




class Directory():
    def __init__(self, path:Path, save_folder:Path, ignore, logging_settings):
        self.path = path  # location of the directory on disk
        self.hash = hash_word(self.path)
        self.save_file = save_folder / self.hash  # file where directory Graph is stored
        self.ignore_patterns = ignore
        self.logger = logging_settings.create_logger(f"{logger_name}.{self.hash}", f"{self.hash}.log")
        
        if self.save_file.exists():
            self.root = pickle.loads(self.save_file.read_bytes())
            self.update()
        else:
            self.root = Folder(Path(), self.path, self.is_in_ignore)
        self.save()
        
    def update(self):
        self.root.update()
        
    def save(self):
        self.save_file.write_bytes(pickle.dumps(self.root))
        logger.info(f"Save directory tracker @ {self.path}")
        
    def is_in_ignore(self, path:Path, is_file=None) -> bool:  # is_file currently not in use
        rel = rel_path(path, self.path)
        for pattern in self.ignore_patterns:
            if rel.match(pattern): return True
        return False
    
    def to_dict(self):
        return self.root.to_dict()
    
    
    

    
class FileTracker:
    """Stores tracked/manages tracked directories"""
    def __init__ (self, directories, logging_settings, data_path):
        logger.info("Filetracker online")
        self.directories_list = directories
        self.logging_settings = logging_settings
        self.save_path = data_path
    
        self.directories = {}
        for dir_path, dir_props in self.directories_list.items():
            self.directories[dir_path] = Directory(Path(dir_path), self.save_path, dir_props[IGNORE_KEY], self.logging_settings)


    def add_directory(self, path:Path,  name:str, ignore_patterns:list) -> None:
        if path in self.directories: raise Exception(f"Already tracking {path}")
        
        self.directories[path] = Directory(path, self.save_path, ignore_patterns, self.logging_settings)
        self.directories_list.new_directory(path, name, ignore_patterns)
        
        logger.info(f"Tracking directory {path}") 
    
    def save(self):
        for directory in self.directories.values():
            self.directories_list.update(directory.path, directory.ignore_patterns, directory.hash)
            directory.save()
    
    def shut_down(self): 
        self.save()
        logger.info("FileTracker offline")
        
    def __contains__(self, path:os.PathLike) -> bool:
        return Path(path) in self.directories    
        
    def __getitem__(self, path:os.PathLike):
        return self.directories[str(path)]   

