

import sys
import cv2
import numpy as np
import threading
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QComboBox, QGroupBox, QGridLayout, 
                            QSpinBox, QSplitter, QFrame, QCheckBox)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QThread, QSize
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import QSizePolicy

try:
    from metavision_core.event_io import EventsIterator, LiveReplayEventsIterator, is_live_camera
    from metavision_sdk_core import PeriodicFrameGenerationAlgorithm, ColorPalette
    METAVISION_AVAILABLE = True
except ImportError:
    METAVISION_AVAILABLE = False
    print("Metavision SDK not available. Only RGB cameras are supported.")

class EVSCameraThread(QThread):
    """Thread to handle EVS camera processing"""
    frame_ready = pyqtSignal(np.ndarray, int)  # Signal: frame data, camera ID
    
    def __init__(self, camera_id, device_path=""):
        super().__init__()
        self.camera_id = camera_id
        self.device_path = device_path
        self.running = False
        self.fps = 25
    
    def run(self):
        if not METAVISION_AVAILABLE:
            print(f"Cannot initialize EVS camera {self.camera_id}: Metavision SDK not available")
            dummy_frame = np.zeros((480, 640), dtype=np.uint8)
            self.frame_ready.emit(dummy_frame, self.camera_id)
            return
            
        try:
            print(f"Opening EVS camera {self.camera_id}: '{self.device_path}'")
            
            # Create events iterator
            mv_iterator = EventsIterator(input_path=self.device_path, delta_t=1000)
            height, width = mv_iterator.get_size()
            print(f"EVS camera {self.camera_id} opened with resolution: {width}x{height}")
            
            # Check if we should use live replay for recorded files
            if not is_live_camera(self.device_path):
                mv_iterator = LiveReplayEventsIterator(mv_iterator)
            
            # Create frame generator
            event_frame_gen = PeriodicFrameGenerationAlgorithm(
                sensor_width=width,
                sensor_height=height,
                fps=self.fps,
                palette=ColorPalette.Gray
            )
            
            # Set callback for frame generation
            def on_cd_frame_cb(ts, cd_frame):
                if self.running:
                    self.frame_ready.emit(cd_frame.copy(), self.camera_id)
            
            event_frame_gen.set_output_callback(on_cd_frame_cb)
            
            # Mark thread as running
            self.running = True
            
            # Process events
            for evs in mv_iterator:
                if not self.running:
                    break
                # Process events from camera
                event_frame_gen.process_events(evs)
                
        except Exception as e:
            print(f"Error in EVS camera {self.camera_id}: {e}")
            # Emit a dummy frame to keep the UI running
            dummy_frame = np.zeros((480, 640), dtype=np.uint8)
            self.frame_ready.emit(dummy_frame, self.camera_id)
        finally:
            self.running = False
            print(f"EVS camera {self.camera_id} thread stopped")
    
    def stop(self):
        self.running = False
        self.wait()

class RGBCameraThread(QThread):
    """Thread to handle RGB camera processing"""
    frame_ready = pyqtSignal(np.ndarray, int)  # Signal: frame data, camera ID
    
    def __init__(self, camera_id, device_id=0):
        super().__init__()
        self.camera_id = camera_id
        self.device_id = device_id
        self.running = False
        self.fps = 30
    
    def run(self):
        try:
            print(f"Opening RGB camera {self.camera_id}, device ID: {self.device_id}")
            cap = cv2.VideoCapture(self.device_id)
            
            if not cap.isOpened():
                raise Exception(f"Cannot open RGB camera with device ID {self.device_id}")
            
            # Set camera properties
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            
            # Mark thread as running
            self.running = True
            
            # Calculate delay based on desired FPS
            delay = 1.0 / self.fps
            
            while self.running:
                ret, frame = cap.read()
                if ret:
                    self.frame_ready.emit(frame, self.camera_id)
                else:
                    # Emit a dummy frame on error
                    dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                    self.frame_ready.emit(dummy_frame, self.camera_id)
                    print(f"Error reading frame from RGB camera {self.camera_id}")
                
                # Control frame rate
                time.sleep(delay)
                
        except Exception as e:
            print(f"Error in RGB camera {self.camera_id}: {e}")
            dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            self.frame_ready.emit(dummy_frame, self.camera_id)
        finally:
            if 'cap' in locals() and cap.isOpened():
                cap.release()
            self.running = False
            print(f"RGB camera {self.camera_id} thread stopped")
    
    def stop(self):
        self.running = False
        self.wait()

class CameraView(QLabel):
    """Widget to display camera feed"""
    def __init__(self, camera_id, camera_type):
        super().__init__()
        self.camera_id = camera_id
        self.camera_type = camera_type  # "EVS" or "RGB"
        
        # Setup basic appearance
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet("border: 1px solid #555; background-color: #111;")
        
        # Set placeholder text
        self.setText(f"{self.camera_type} Camera {self.camera_id}\nNo data")
    
    @pyqtSlot(np.ndarray)
    def update_frame(self, frame):
        """Update the displayed frame"""
        if frame is None or frame.size == 0:
            return
            
        # Convert color for different camera types
        if len(frame.shape) == 2:  # Grayscale (EVS)
            h, w = frame.shape
            bytes_per_line = w
            q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
        else:  # RGB
            h, w, c = frame.shape
            bytes_per_line = w * c
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        
        # Scale the image to fit the label while maintaining aspect ratio
        pixmap = QPixmap.fromImage(q_img)
        self.setPixmap(pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

class CameraManager:
    """Class to manage camera instances"""
    def __init__(self):
        self.evs_cameras = {}  # Dictionary of EVS camera threads by ID
        self.rgb_cameras = {}  # Dictionary of RGB camera threads by ID
        
    def add_evs_camera(self, camera_id, device_path=""):
        """Add a new EVS camera"""
        if camera_id in self.evs_cameras:
            self.remove_evs_camera(camera_id)
            
        camera_thread = EVSCameraThread(camera_id, "")
        self.evs_cameras[camera_id] = camera_thread
        return camera_thread
        
    def add_rgb_camera(self, camera_id, device_id=0):
        """Add a new RGB camera"""
        if camera_id in self.rgb_cameras:
            self.remove_rgb_camera(camera_id)
            
        camera_thread = RGBCameraThread(camera_id, device_id)
        self.rgb_cameras[camera_id] = camera_thread
        return camera_thread
    
    def remove_evs_camera(self, camera_id):
        """Remove an EVS camera"""
        if camera_id in self.evs_cameras:
            self.evs_cameras[camera_id].stop()
            del self.evs_cameras[camera_id]
    
    def remove_rgb_camera(self, camera_id):
        """Remove an RGB camera"""
        if camera_id in self.rgb_cameras:
            self.rgb_cameras[camera_id].stop()
            del self.rgb_cameras[camera_id]
    
    def start_all_cameras(self):
        """Start all camera threads"""
        for camera in self.evs_cameras.values():
            if not camera.isRunning():
                camera.start()
                
        for camera in self.rgb_cameras.values():
            if not camera.isRunning():
                camera.start()
    
    def stop_all_cameras(self):
        """Stop all camera threads"""
        for camera in self.evs_cameras.values():
            camera.stop()
            
        for camera in self.rgb_cameras.values():
            camera.stop()
    
    def cleanup(self):
        """Clean up all resources"""
        self.stop_all_cameras()
        self.evs_cameras.clear()
        self.rgb_cameras.clear()

class CameraControlPanel(QWidget):
    """Panel for camera configuration controls"""
    layout_changed = pyqtSignal(int, int)  # Rows, Columns
    cameras_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.evs_camera_count = 0
        self.rgb_camera_count = 0
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel("Camera Configuration")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # EVS Cameras Group
        evs_group = QGroupBox("EVS Cameras")
        evs_layout = QVBoxLayout()
        
        # EVS camera count
        evs_count_layout = QHBoxLayout()
        evs_count_layout.addWidget(QLabel("Count:"))
        self.evs_count_spinbox = QSpinBox()
        self.evs_count_spinbox.setRange(0, 8)
        self.evs_count_spinbox.setValue(self.evs_camera_count)
        self.evs_count_spinbox.valueChanged.connect(self.on_evs_count_changed)
        evs_count_layout.addWidget(self.evs_count_spinbox)
        evs_layout.addLayout(evs_count_layout)
        
        # EVS camera settings container (will be populated dynamically)
        self.evs_settings_widget = QWidget()
        self.evs_settings_layout = QVBoxLayout()
        self.evs_settings_widget.setLayout(self.evs_settings_layout)
        evs_layout.addWidget(self.evs_settings_widget)
        
        evs_group.setLayout(evs_layout)
        layout.addWidget(evs_group)
        
        # RGB Cameras Group
        rgb_group = QGroupBox("RGB Cameras (Webcam)")
        rgb_layout = QVBoxLayout()
        
        # RGB camera count
        rgb_count_layout = QHBoxLayout()
        rgb_count_layout.addWidget(QLabel("Count:"))
        self.rgb_count_spinbox = QSpinBox()
        self.rgb_count_spinbox.setRange(0, 8)
        self.rgb_count_spinbox.setValue(self.rgb_camera_count)
        self.rgb_count_spinbox.valueChanged.connect(self.on_rgb_count_changed)
        rgb_count_layout.addWidget(self.rgb_count_spinbox)
        rgb_layout.addLayout(rgb_count_layout)
        
        # RGB camera settings container (will be populated dynamically)
        self.rgb_settings_widget = QWidget()
        self.rgb_settings_layout = QVBoxLayout()
        self.rgb_settings_widget.setLayout(self.rgb_settings_layout)
        rgb_layout.addWidget(self.rgb_settings_widget)
        
        rgb_group.setLayout(rgb_layout)
        layout.addWidget(rgb_group)
        
        # Layout Configuration Group
        layout_group = QGroupBox("Display Configuration")
        layout_config = QVBoxLayout()
        
        # Grid layout selection
        grid_layout = QHBoxLayout()
        grid_layout.addWidget(QLabel("Camera layout:"))
        self.layout_combo = QComboBox()
        self.layout_combo.addItems(["1x1", "1x2", "2x1", "2x2", "3x2", "3x3", "4x4"])
        self.layout_combo.currentIndexChanged.connect(self.on_layout_changed)
        grid_layout.addWidget(self.layout_combo)
        layout_config.addLayout(grid_layout)
        
        # Auto layout checkbox
        auto_layout = QHBoxLayout()
        self.auto_layout_checkbox = QCheckBox("Auto-adjust layout")
        self.auto_layout_checkbox.setChecked(True)
        self.auto_layout_checkbox.stateChanged.connect(self.on_auto_layout_changed)
        auto_layout.addWidget(self.auto_layout_checkbox)
        layout_config.addLayout(auto_layout)
        
        layout_group.setLayout(layout_config)
        layout.addWidget(layout_group)
        
        # Control buttons
        buttons_layout = QHBoxLayout()
        
        self.start_button = QPushButton("Start")
        self.start_button.clicked.connect(self.on_start_clicked)
        buttons_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.on_stop_clicked)
        self.stop_button.setEnabled(False)
        buttons_layout.addWidget(self.stop_button)
        
        layout.addLayout(buttons_layout)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        self.setLayout(layout)
        self.setMaximumWidth(350)
    
    def update_evs_settings(self):
        """Update EVS camera settings widgets"""
        # Clear existing widgets
        while self.evs_settings_layout.count():
            item = self.evs_settings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add widgets for each camera
        for i in range(self.evs_camera_count):
            camera_layout = QHBoxLayout()
            camera_layout.addWidget(QLabel(f"Camera {i+1}:"))
            
            # Device path input
            device_input = QComboBox()
            if METAVISION_AVAILABLE:
                device_input.addItem(f"/dev/event-camera{i}")
                device_input.addItem(f"")  # Empty for auto-detection
                device_input.setEditable(True)
            else:
                device_input.addItem("Metavision SDK not available")
                device_input.setEnabled(False)
            
            camera_layout.addWidget(device_input)
            
            self.evs_settings_layout.addLayout(camera_layout)
    
    def update_rgb_settings(self):
        """Update RGB camera settings widgets"""
        # Clear existing widgets
        while self.rgb_settings_layout.count():
            item = self.rgb_settings_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add widgets for each camera
        for i in range(self.rgb_camera_count):
            camera_layout = QHBoxLayout()
            camera_layout.addWidget(QLabel(f"Camera {i+1}:"))
            
            # Device ID input
            device_input = QSpinBox()
            device_input.setRange(0, 10)
            device_input.setValue(i)
            
            camera_layout.addWidget(device_input)
            
            self.rgb_settings_layout.addLayout(camera_layout)
    
    def on_evs_count_changed(self, value):
        """Handle change in EVS camera count"""
        self.evs_camera_count = value
        self.update_evs_settings()
        self.auto_update_layout()
        self.cameras_changed.emit()
    
    def on_rgb_count_changed(self, value):
        """Handle change in RGB camera count"""
        self.rgb_camera_count = value
        self.update_rgb_settings()
        self.auto_update_layout()
        self.cameras_changed.emit()
    
    def on_layout_changed(self, index):
        """Handle layout selection change"""
        layout_text = self.layout_combo.currentText()
        rows, cols = map(int, layout_text.split('x'))
        self.layout_changed.emit(rows, cols)
    
    def on_auto_layout_changed(self, state):
        """Handle auto layout checkbox change"""
        is_auto = (state == Qt.Checked)
        self.layout_combo.setEnabled(not is_auto)
        if is_auto:
            self.auto_update_layout()
    
    def auto_update_layout(self):
        """Automatically select an appropriate layout based on camera count"""
        if not self.auto_layout_checkbox.isChecked():
            return
            
        total_cameras = self.evs_camera_count + self.rgb_camera_count
        
        if total_cameras <= 1:
            self.layout_combo.setCurrentText("1x1")
        elif total_cameras <= 2:
            self.layout_combo.setCurrentText("1x2")
        elif total_cameras <= 4:
            self.layout_combo.setCurrentText("2x2")
        elif total_cameras <= 6:
            self.layout_combo.setCurrentText("3x2")
        elif total_cameras <= 9:
            self.layout_combo.setCurrentText("3x3")
        else:
            self.layout_combo.setCurrentText("4x4")
        
        # Force layout update
        layout_text = self.layout_combo.currentText()
        rows, cols = map(int, layout_text.split('x'))
        self.layout_changed.emit(rows, cols)
    
    def on_start_clicked(self):
        """Handle start button click"""
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        # Other UI elements disabled for consistency
        self.evs_count_spinbox.setEnabled(False)
        self.rgb_count_spinbox.setEnabled(False)
        
        self.cameras_changed.emit()
    
    def on_stop_clicked(self):
        """Handle stop button click"""
        self.stop_button.setEnabled(False)
        self.start_button.setEnabled(True)
        # Re-enable UI elements
        self.evs_count_spinbox.setEnabled(True)
        self.rgb_count_spinbox.setEnabled(True)
        
        self.cameras_changed.emit()
    
    def get_camera_configs(self):
        """Get configuration for all cameras"""
        evs_configs = []
        rgb_configs = []
        
        # Get EVS camera configs
        for i in range(self.evs_camera_count):
            layout_item = self.evs_settings_layout.itemAt(i)
            if layout_item:
                layout = layout_item.layout()
                if layout and layout.count() > 1:
                    device_input = layout.itemAt(1).widget()
                    if isinstance(device_input, QComboBox):
                        device_path = device_input.currentText()
                        evs_configs.append((i, device_path))
        
        # Get RGB camera configs
        for i in range(self.rgb_camera_count):
            layout_item = self.rgb_settings_layout.itemAt(i)
            if layout_item:
                layout = layout_item.layout()
                if layout and layout.count() > 1:
                    device_input = layout.itemAt(1).widget()
                    if isinstance(device_input, QSpinBox):
                        device_id = device_input.value()
                        rgb_configs.append((i, device_id))
        
        return evs_configs, rgb_configs
    
    def is_running(self):
        """Check if cameras should be running"""
        return self.stop_button.isEnabled()

class CameraDisplayArea(QWidget):
    """Widget to display camera feeds in a grid layout"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.rows = 2
        self.cols = 2
        self.camera_views = {}  # Dictionary of camera views by (type, id)
        
        self.init_ui()
    
    def init_ui(self):
        self.main_layout = QVBoxLayout()
        
        # Create grid layout for camera views
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(5)
        
        # Create placeholder to hold the grid
        self.grid_widget = QWidget()
        self.grid_widget.setLayout(self.grid_layout)
        
        self.main_layout.addWidget(self.grid_widget)
        self.setLayout(self.main_layout)
    
    def set_grid_layout(self, rows, cols):
        """Set the grid layout dimensions"""
        if self.rows == rows and self.cols == cols:
            return
            
        self.rows = rows
        self.cols = cols
        
        # Re-arrange existing camera views
        self.update_grid()
    
    def update_grid(self):
        """Update the grid layout with current camera views"""
        # Clear existing grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            # Don't delete the widgets, we'll reuse them
            item.widget().setParent(None)
        
        # Add camera views back in the new grid arrangement
        cameras = list(self.camera_views.values())
        for idx, camera_view in enumerate(cameras):
            if idx >= self.rows * self.cols:
                camera_view.hide()  # Hide cameras that don't fit
                continue
                
            row = idx // self.cols
            col = idx % self.cols
            self.grid_layout.addWidget(camera_view, row, col)
            camera_view.show()
    
    def add_camera_view(self, camera_type, camera_id):
        """Add a new camera view to the display area"""
        key = (camera_type, camera_id)
        
        if key not in self.camera_views:
            camera_view = CameraView(camera_id, camera_type)
            self.camera_views[key] = camera_view
            
            # Update the grid
            self.update_grid()
            
            return camera_view
        else:
            return self.camera_views[key]
    
    def remove_camera_view(self, camera_type, camera_id):
        """Remove a camera view from the display area"""
        key = (camera_type, camera_id)
        
        if key in self.camera_views:
            camera_view = self.camera_views[key]
            camera_view.setParent(None)
            del self.camera_views[key]
            
            # Update the grid
            self.update_grid()
    
    def clear_all_views(self):
        """Remove all camera views"""
        for camera_view in self.camera_views.values():
            camera_view.setParent(None)
        
        self.camera_views.clear()
        self.update_grid()

class CameraManagerApp(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self.camera_manager = CameraManager()
        self.init_ui()
    
    def init_ui(self):
        # Set window properties
        self.setWindowTitle("Camera Manager")
        self.setMinimumSize(1200, 800)
        
        # Create main widget and layout
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Create control panel
        self.control_panel = CameraControlPanel()
        self.control_panel.layout_changed.connect(self.on_layout_changed)
        self.control_panel.cameras_changed.connect(self.update_cameras)
        
        # Create display area
        self.display_area = CameraDisplayArea()
        
        # Add widgets to splitter
        splitter.addWidget(self.control_panel)
        splitter.addWidget(self.display_area)
        
        # Set initial splitter sizes
        splitter.setSizes([300, 900])
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        # Set dark theme
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #2D2D30;
                color: #E6E6E6;
            }
            QGroupBox {
                border: 1px solid #3F3F46;
                border-radius: 5px;
                margin-top: 1ex;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 3px;
            }
            QPushButton {
                background-color: #0E639C;
                border: none;
                border-radius: 3px;
                padding: 5px;
                color: white;
            }
            QPushButton:hover {
                background-color: #1177BB;
            }
            QPushButton:pressed {
                background-color: #0D5789;
            }
            QPushButton:disabled {
                background-color: #3F3F46;
                color: #9D9D9D;
            }
            QComboBox, QSpinBox {
                background-color: #3F3F46;
                border: 1px solid #1F1F1F;
                border-radius: 3px;
                padding: 3px;
                color: #E6E6E6;
            }
            QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 15px;
                border-left-width: 1px;
                border-left-color: #1F1F1F;
                border-left-style: solid;
            }
            QLabel {
                color: #E6E6E6;
            }
            QSplitter::handle {
                background-color: #3F3F46;
            }
        """)
    
    def on_layout_changed(self, rows, cols):
        """Handle layout change from control panel"""
        self.display_area.set_grid_layout(rows, cols)
    
    def update_cameras(self):
        """Update camera instances based on control panel settings"""
        # Stop existing cameras
        self.camera_manager.stop_all_cameras()
        
        # If we're in running state, create and start new cameras
        if self.control_panel.is_running():
            evs_configs, rgb_configs = self.control_panel.get_camera_configs()
            
            # Clear existing camera views
            self.display_area.clear_all_views()
            
            # Setup EVS cameras
            for camera_id, device_path in evs_configs:
                # Create camera thread
                camera_thread = self.camera_manager.add_evs_camera(camera_id, device_path)
                
                # Create and connect camera view
                camera_view = self.display_area.add_camera_view("EVS", camera_id)
                camera_thread.frame_ready.connect(
                    lambda frame, cid, view=camera_view: 
                    view.update_frame(frame) if view and cid == view.camera_id else None
                )
            
            # Setup RGB cameras
            for camera_id, device_id in rgb_configs:
                # Create camera thread
                camera_thread = self.camera_manager.add_rgb_camera(camera_id, device_id)
                
                # Create and connect camera view
                camera_view = self.display_area.add_camera_view("RGB", camera_id)
                camera_thread.frame_ready.connect(
                    lambda frame, cid, view=camera_view: 
                    view.update_frame(frame) if view and cid == view.camera_id else None
                )
            
            # Start all cameras
            self.camera_manager.start_all_cameras()
    
    def closeEvent(self, event):
        """Handle window close event"""
        # Clean up camera resources
        self.camera_manager.cleanup()
        event.accept()

def main():
    app = QApplication(sys.argv)
    window = CameraManagerApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()