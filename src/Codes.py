from enum import IntEnum, auto

class CONFLICT_POLICY(IntEnum):
    WAIT_FOR_RESOLVE = auto() # wait for user input to proceed
    PROCEED_AND_RECORD = auto() # record conflict and proceed (as long as possible)
    USE_DEFAULT_RESOLVE = auto() # use whatever default resolve policy that has been selected
    
    
class RESOLVE_POLICY(IntEnum):
    KEEP_LOCAL = auto()        
    REPLACE_LOCAL = auto()
    USE_NEWEST = auto()
    CREATE_COPY = auto()
    
    
class CONFLICT_TYPE(IntEnum):
    MODIF_CONFLICT = auto()
    DELETE_CONFLICT = auto()

