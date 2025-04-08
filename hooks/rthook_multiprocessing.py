import os
import sys
import multiprocessing

if os.environ.get("CAMERA_SUBPROCESS") == "1":
    multiprocessing.freeze_support()
    sys.frozen = 'camera_subprocess' 