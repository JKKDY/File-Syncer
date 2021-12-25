from enum import IntEnum, auto, Enum

class CONFLICT_POLICY(IntEnum):
    WAIT_FOR_RESOLVE = 1 # wait for user input to proceed
    PROCEED_AND_RECORD = 2 # record conflict and proceed (as long as possible)
    USE_DEFAULT_RESOLVE = 3 # use whatever default resolve policy that has been selected
    
    
class RESOLVE_POLICY(IntEnum):
    USE_LOCAL = 1       
    USE_REMOTE = 2
    USE_NEWEST = 3
    KEEP_ALL = 4
    
    
class CONFLICT_TYPE(IntEnum):
    MODIF_CONFLICT = auto()
    DELETE_CONFLICT = auto()
    
    
class SYNC_STATUS(IntEnum):
    SYNCING = 1
    NOT_SYNCING = 0
    
class SYNC_RET_CODE(IntEnum):
    SUCCESS = 1
    LOCAL_DIR_IN_USE = 2
    REMOTE_DIR_IN_USE = 3
    HAS_CONFLICT = 4

