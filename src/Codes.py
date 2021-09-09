from enum import IntEnum, auto, Enum

class CONFLICT_POLICY(IntEnum):
    WAIT_FOR_RESOLVE = auto() # wait for user input to proceed
    PROCEED_AND_RECORD = auto() # record conflict and proceed (as long as possible)
    USE_DEFAULT_RESOLVE = auto() # use whatever default resolve policy that has been selected
    
    
class RESOLVE_POLICY(IntEnum):
    KEEP_LOCAL = auto()        
    REPLACE_LOCAL = auto()
    USE_NEWEST = auto()
    CREATE_COPY = auto()
    
    
class CONFLICT_TYPE(Enum):
    MODIF_CONFLICT = auto()
    DELETE_CONFLICT = auto()
    
    
class SYNC_STATUS(IntEnum):
    SYNCING = 1
    NOT_SYNCING = 0
    
class SYNC_RET_CODE(Enum):
    SUCCESS = 1
    LOCAL_DIR_IN_USE = auto()
    REMOTE_DIR_IN_USE = auto()
    HAS_CONFLICT = auto()

