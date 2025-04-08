import sys
import multiprocessing as mp
from PyQt5.QtWidgets import QApplication
from src.app import CameraManagerApp

      
def ensure_mp_fork():
    """
    Ensure multiprocessing uses 'fork' method on Unix systems 
    or 'spawn' on Windows for proper PyQt integration
    """
    if sys.platform.startswith('win'):
        # Windows requires 'spawn'
        mp.set_start_method('spawn', force=True)
    else:
        # Unix-like systems can use 'fork'
        mp.set_start_method('fork', force=True)


def main():
    app = QApplication(sys.argv)
    window = CameraManagerApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()