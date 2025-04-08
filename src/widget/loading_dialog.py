import sys
import time
from PyQt5.QtWidgets import (QDialog, QProgressBar, QLabel, QVBoxLayout,
                           QHBoxLayout, QPushButton, QApplication)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer

class CameraInitThread(QThread):
    progress_updated = pyqtSignal(int)
    initialization_complete = pyqtSignal()
    
    def __init__(self, camera_count):
        super().__init__()
        self.camera_count = camera_count
        self.is_cancelled = False
    
    def run(self):
        for i in range(self.camera_count):
            if self.is_cancelled:
                break
                
            for j in range(100):
                if self.is_cancelled:
                    break
                
                progress = int((i * 100 + j) / (self.camera_count * 100) * 100)
                self.progress_updated.emit(progress)
                time.sleep(0.05)
        
        if not self.is_cancelled:
            self.initialization_complete.emit()
    
    def cancel(self):
        self.is_cancelled = True


class LoadingDialog(QDialog):
    def __init__(self, camera_count, parent=None):
        super().__init__(parent, Qt.Window)
        self.camera_count = camera_count
        self.total_time = camera_count * 5 
        self.remaining_time = self.total_time
        self.init_ui()
        
        self.init_thread = CameraInitThread(camera_count)
        self.init_thread.progress_updated.connect(self.update_progress)
        self.init_thread.initialization_complete.connect(self.on_initialization_complete)
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_remaining_time)
        self.timer.start(1000)  
        
        self.init_thread.start()
    
    def init_ui(self):
        self.setWindowTitle("Initializing Cameras")
        self.setFixedSize(400, 200)
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.CustomizeWindowHint)
        
        layout = QVBoxLayout()
        
        title_label = QLabel(f"Initializing {self.camera_count} camera(s)")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        self.info_label = QLabel(f"This process will take approximately {self.total_time} seconds")
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)
        
        self.time_label = QLabel(f"Remaining time: {self.total_time} seconds")
        self.time_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.time_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        layout.addWidget(self.progress_bar)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch(1)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C; 
                color: white; 
                border-radius: 4px; 
                padding: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
            QPushButton:pressed {
                background-color: #A5281A;
            }
        """)
        self.cancel_button.clicked.connect(self.cancel_initialization)
        button_layout.addWidget(self.cancel_button)
        
        button_layout.addStretch(1)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
    
    def update_progress(self, value):
        self.progress_bar.setValue(value)
        
        remaining = (100 - value) * self.total_time / 100
        self.remaining_time = max(1, int(remaining))
        self.time_label.setText(f"Remaining time: {self.remaining_time} seconds")
    
    def update_remaining_time(self):
        if self.remaining_time > 0:
            self.remaining_time -= 1
            self.time_label.setText(f"Remaining time: {self.remaining_time} seconds")
    
    def on_initialization_complete(self):
        self.timer.stop()
        self.accept()
    
    def cancel_initialization(self):
        self.init_thread.cancel()
        self.init_thread.wait()
        self.timer.stop()
        self.reject()
    
    def closeEvent(self, event):
        self.cancel_initialization()
        event.accept()