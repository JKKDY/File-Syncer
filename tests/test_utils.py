import sys
import os
from pathlib import Path

src = Path(os.path.realpath(__file__)).parents[1]
sys.path.append(str(src))
this = Path(os.path.realpath(__file__)).parents[0]