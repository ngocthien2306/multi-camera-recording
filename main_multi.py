import sys
import cv2
import numpy as np
import time
import os
import signal
import multiprocessing as mp
from multiprocessing import Process, Queue, Event, Value
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QComboBox, QGroupBox, QGridLayout, 
                            QSpinBox, QSplitter, QFrame, QCheckBox, QSizePolicy,
                            QScrollArea, QSlider, QFileDialog, QLineEdit)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QSize
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QFont
try:
    from metavision_core.event_io.raw_reader import initiate_device
    from metavision_core.event_io import EventsIterator, LiveReplayEventsIterator, is_live_camera
    from metavision_sdk_core import PeriodicFrameGenerationAlgorithm, ColorPalette
    METAVISION_AVAILABLE = True
except ImportError:
    METAVISION_AVAILABLE = False
    print("Metavision SDK not available. Only RGB cameras are supported.")

# Global variables for IPC
MAX_QUEUE_SIZE = 10  # Maximum frames to queue per camera

def evs_camera_process(camera_id, device_path, frame_queue, command_event, status_value, command_queue=None):
    """Process function for EVS camera processing"""
    if not METAVISION_AVAILABLE:
        print(f"Cannot initialize EVS camera {camera_id}: Metavision SDK not available")
        dummy_frame = np.zeros((480, 640), dtype=np.uint8)
        frame_queue.put((camera_id, dummy_frame))
        status_value.value = 0  # Mark as stopped
        return
        
    try:
        print(f"Opening EVS camera {camera_id}: '{device_path}'")
        status_value.value = 1  # Mark as running
        device = initiate_device("", do_time_shifting=False)
        # Create events iterator
        
        mv_iterator = EventsIterator.from_device(device, start_ts=0, delta_t=1000)
        
        # mv_iterator = EventsIterator(input_path=device_path, delta_t=1000)
        height, width = mv_iterator.get_size()
        print(f"EVS camera {camera_id} opened with resolution: {width}x{height}")
        
        # Check if we should use live replay for recorded files
        if not is_live_camera(device_path):
            mv_iterator = LiveReplayEventsIterator(mv_iterator)
        
        # Create frame generator
        event_frame_gen = PeriodicFrameGenerationAlgorithm(
            sensor_width=width,
            sensor_height=height,
            fps=25,
            palette=ColorPalette.Gray
        )
        
        # Set callback for frame generation
        def on_cd_frame_cb(ts, cd_frame):
            if not command_event.is_set() and not frame_queue.full():
                # Create a copy of the frame for multiprocessing
                frame_copy = cd_frame.copy()
                frame_queue.put((camera_id, frame_copy))
        
        event_frame_gen.set_output_callback(on_cd_frame_cb)
        
        # Process events
        for evs in mv_iterator:
            if command_event.is_set():
                break
            
            if command_queue and not command_queue.empty():
                cmd, arg = command_queue.get()
                if cmd == 'start_recording':
                    # Start raw recording
                    device.get_i_events_stream().log_raw_data(arg)
                    print(f"EVS camera {camera_id} started raw recording to {arg}")
                elif cmd == 'stop_recording':
                    # Stop raw recording
                    device.get_i_events_stream().stop_log_raw_data()
                    print(f"EVS camera {camera_id} stopped raw recording")
                    
            # Process events from camera
            event_frame_gen.process_events(evs)
            
    except Exception as e:
        print(f"Error in EVS camera {camera_id} process: {e}")
        # Send a dummy frame to keep the UI running
        dummy_frame = np.zeros((480, 640), dtype=np.uint8)
        if not frame_queue.full():
            frame_queue.put((camera_id, dummy_frame))
    finally:
        status_value.value = 0  # Mark as stopped
        print(f"EVS camera {camera_id} process stopped")

def rgb_camera_process(camera_id, device_id, frame_queue, command_event, status_value):
    """Process function for RGB camera processing"""
    try:
        print(f"Opening RGB camera {camera_id}, device ID: {device_id}")
        cap = cv2.VideoCapture(device_id)
        
        if not cap.isOpened():
            raise Exception(f"Cannot open RGB camera with device ID {device_id}")
        
        # Set camera properties
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        # Mark process as running
        status_value.value = 1
        
        # Calculate delay based on desired FPS
        fps = 30
        delay = 1.0 / fps
        
        while not command_event.is_set():
            ret, frame = cap.read()
            if ret:
                if not frame_queue.full():
                    frame_queue.put((camera_id, frame.copy()))
            else:
                # Send a dummy frame on error
                dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
                if not frame_queue.full():
                    frame_queue.put((camera_id, dummy_frame))
                print(f"Error reading frame from RGB camera {camera_id}")
            
            # Control frame rate
            time.sleep(delay)
            
    except Exception as e:
        print(f"Error in RGB camera {camera_id} process: {e}")
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        if not frame_queue.full():
            frame_queue.put((camera_id, dummy_frame))
    finally:
        if 'cap' in locals() and cap.isOpened():
            cap.release()
        status_value.value = 0  # Mark as stopped
        print(f"RGB camera {camera_id} process stopped")

class CameraView(QLabel):
    """Widget to display camera feed with scaling options"""
    def __init__(self, camera_id, camera_type):
        super().__init__()
        self.camera_id = camera_id
        self.camera_type = camera_type  # "EVS" or "RGB"
        self.fps = 0
        self.frame_count = 0
        self.last_time = time.time()
        self.original_size = QSize(640, 480)  # Original camera resolution
        self.display_size = QSize(640, 480)   # Current display size
        
        # Setup basic appearance
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(320, 240)
        self.setFixedSize(self.display_size)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setStyleSheet("border: 1px solid #555; background-color: #111;")
        
        # Set placeholder text
        self.setText(f"{self.camera_type} Camera {self.camera_id}\nNo data")
        
        # Information overlay
        self.show_info = True
        self.resolution = "N/A"
        self.status = "Initializing..."
        
        # Frame storage
        self.current_frame = None
    
    def sizeHint(self):
        """Override sizeHint to return display size"""
        return self.display_size
    
    def set_scale(self, scale_factor):
        """Scale the camera view"""
        # Calculate new size based on scale factor
        new_width = int(self.original_size.width() * scale_factor)
        new_height = int(self.original_size.height() * scale_factor)
        
        # Update display size
        self.display_size = QSize(new_width, new_height)
        self.setFixedSize(self.display_size)
        
        # If we have a current frame, update the display
        if hasattr(self, 'current_pixmap'):
            self.setPixmap(self.current_pixmap.scaled(
                self.display_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    
    @pyqtSlot(np.ndarray)
    def update_frame(self, frame):
        """Update the displayed frame"""
        if frame is None or frame.size == 0:
            return
        
        # Store the current frame
        self.current_frame = frame.copy()
        
        # Calculate FPS
        self.frame_count += 1
        current_time = time.time()
        time_diff = current_time - self.last_time
        
        if time_diff >= 1.0:  # Update FPS every second
            self.fps = self.frame_count / time_diff
            self.frame_count = 0
            self.last_time = current_time
            
        # Update resolution info
        if len(frame.shape) == 2:  # Grayscale (EVS)
            h, w = frame.shape
            self.resolution = f"{w}x{h}"
            bytes_per_line = w
            q_img = QImage(frame.data, w, h, bytes_per_line, QImage.Format_Grayscale8)
            self.status = "EVS Active"
        else:  # RGB
            h, w, c = frame.shape
            self.resolution = f"{w}x{h}"
            bytes_per_line = w * c
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.status = "RGB Active"
        
        # Create a painter to draw on the image if info display is enabled
        if self.show_info:
            # Create a copy of the QImage that we can draw on
            img_copy = QImage(q_img)
            painter = QPainter(img_copy)
            
            # Semi-transparent background for text
            painter.fillRect(0, 0, w, 60, QColor(0, 0, 0, 160))
            
            # Set text color and font
            painter.setPen(Qt.white)
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
            
            # Draw camera info
            painter.drawText(10, 20, f"{self.camera_type} Camera {self.camera_id}")
            painter.drawText(10, 40, f"Resolution: {self.resolution}")
            painter.drawText(10, 60, f"FPS: {self.fps:.1f} | {self.status}")
            
            painter.end()
            
            # Convert back to pixmap
            pixmap = QPixmap.fromImage(img_copy)
        else:
            pixmap = QPixmap.fromImage(q_img)
        
        # Store current pixmap for resize events
        self.current_pixmap = pixmap
        
        # Scale the image to fit the label while maintaining aspect ratio
        self.setPixmap(pixmap.scaled(
            self.display_size, Qt.KeepAspectRatio, Qt.SmoothTransformation))
    
    def toggle_info_display(self):
        """Toggle information overlay"""
        self.show_info = not self.show_info
        
        # If we have a current frame, update to reflect the change
        if self.current_frame is not None:
            self.update_frame(self.current_frame)

class CameraManager:
    """Class to manage camera processes"""
    def __init__(self):
        self.evs_cameras = {}  # Dictionary of EVS camera processes by ID
        self.rgb_cameras = {}  # Dictionary of RGB camera processes by ID
        self.frame_queues = {}  # Dictionary of frame queues by (type, ID)
        self.command_events = {}  # Dictionary of command events by (type, ID)
        self.status_values = {}  # Dictionary of status values by (type, ID)
        self.command_queue = {}
        
        
        self.recording = False
        self.recording_path = ""
        self.video_writers = {}  # Store VideoWriter objects for each camera
        
    def add_evs_camera(self, camera_id, device_path=""):
        """Add a new EVS camera"""
        key = ('EVS', camera_id)
        if key in self.command_events:
            self.remove_evs_camera(camera_id)
            
        # Create IPC mechanisms
        frame_queue = Queue(maxsize=MAX_QUEUE_SIZE)
        command_event = Event()
        status_value = Value('i', 0)  # 0=stopped, 1=running
        
        if 'command_queue' not in self.__dict__:
            self.command_queue = {}
            
        self.command_queue[key] = Queue()
        
        # Store references
        self.frame_queues[key] = frame_queue
        self.command_events[key] = command_event
        self.status_values[key] = status_value
        
        process = Process(
            target=evs_camera_process,
            args=(camera_id, device_path, frame_queue, command_event, status_value, self.command_queue[key])
        )
        
        self.evs_cameras[camera_id] = process
        return key
        
    def add_rgb_camera(self, camera_id, device_id=0):
        """Add a new RGB camera"""
        key = ('RGB', camera_id)
        if key in self.command_events:
            self.remove_rgb_camera(camera_id)
            
        # Create IPC mechanisms
        frame_queue = Queue(maxsize=MAX_QUEUE_SIZE)
        command_event = Event()
        status_value = Value('i', 0)  # 0=stopped, 1=running
        
        # Store references
        self.frame_queues[key] = frame_queue
        self.command_events[key] = command_event
        self.status_values[key] = status_value
        
        # Create and start the process
        process = Process(
            target=rgb_camera_process,
            args=(camera_id, device_id, frame_queue, command_event, status_value)
        )
        
        self.rgb_cameras[camera_id] = process
        return key
    
    def remove_evs_camera(self, camera_id):
        """Remove an EVS camera"""
        key = ('EVS', camera_id)
        if key in self.command_events:
            # Signal the process to stop
            self.command_events[key].set()
            
            # Wait for the process to terminate
            if camera_id in self.evs_cameras:
                process = self.evs_cameras[camera_id]
                if process.is_alive():
                    process.join(timeout=1.0)  # Wait up to 1 second
                    if process.is_alive():
                        process.terminate()  # Force terminate if not stopped
                
                # Clean up
                del self.evs_cameras[camera_id]
                
            # Clean up IPC mechanisms
            del self.frame_queues[key]
            del self.command_events[key]
            del self.status_values[key]
            
            
    def start_recording(self, folder_path, tag=""):
        """Start recording from all active cameras"""
        if self.recording:
            return False
        
        # Create timestamp for file naming
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.recording_path = folder_path
        self.recording_tag = tag
        
        try:
            # Create camera-specific subfolders if they don't exist
            for camera_type in ['EVS', 'RGB']:
                camera_dir = os.path.join(folder_path, camera_type)
                if not os.path.exists(camera_dir):
                    os.makedirs(camera_dir)
            
            # Initialize video writers for all active cameras
            for camera_type, cameras in [('EVS', self.evs_cameras), ('RGB', self.rgb_cameras)]:
                for camera_id in cameras.keys():
                    key = (camera_type, camera_id)
                    
                    if self.status_values[key].value == 1:  # Only record running cameras
                        # Determine output file name with tag
                        file_name = f"{camera_type}_{camera_id}_{tag}_{timestamp}.avi"
                        file_path = os.path.join(folder_path, camera_type, file_name)
                        
                        if 'command_queue' not in self.__dict__:
                            self.command_queue = {}
                        
                        if key not in self.command_queue:
                            self.command_queue[key] = Queue()
                        
                        # Get a frame to determine dimensions
                        frame = self.get_frame(camera_type, camera_id)
                        if frame is None:
                            continue
                        
                        # Determine codec and parameters based on camera type
                        if camera_type == 'EVS':
                            raw_filepath = os.path.join(folder_path, 'EVS', f"EVS_{camera_id}_{tag}_{timestamp}.raw")
                            self.command_queue[key].put(('start_recording', raw_filepath))
                            
                            # For EVS (grayscale), use a grayscale codec
                            fourcc = cv2.VideoWriter_fourcc(*'XVID')
                            fps = 25.0
                            if len(frame.shape) == 2:
                                height, width = frame.shape
                                writer = cv2.VideoWriter(file_path, fourcc, fps, (width, height), False)
                            else:
                                height, width, _ = frame.shape
                                writer = cv2.VideoWriter(file_path, fourcc, fps, (width, height), True)
                                
                                
                            self.video_writers[key] = {
                                'writer': writer,
                                'path': file_path,
                                'count': 0,  # Frame counter
                                'type': 'raw'
                            }
                        else:
                            # For RGB cameras
                            fourcc = cv2.VideoWriter_fourcc(*'XVID')
                            fps = 30.0
                            height, width = frame.shape[:2]
                            writer = cv2.VideoWriter(file_path, fourcc, fps, (width, height), True)
                        
                            self.video_writers[key] = {
                                'writer': writer,
                                'path': file_path,
                                'count': 0,  # Frame counter
                                'type': 'video'
                            }
            
            # Set recording state
            self.recording = True
            print(f"Started recording to {folder_path}")
            return True
        
        except Exception as e:
            print(f"Error starting recording: {e}")
            self.stop_recording()
            return False

    def stop_recording(self):
        """Stop recording from all cameras"""
        if not self.recording:
            return
        
        # Release all video writers
        for key, writer_info in self.video_writers.items():
            
            
            writer = writer_info['writer']
            frames = writer_info['count']
            path = writer_info['path']
            
            writer.release()
            
            if writer_info.get("type") == "raw":
                if key in self.command_queue:
                    self.command_queue[key].put(('stop_recording', None))
                    
                path = writer_info['path']
                print(f"Stopped raw recording to {path}")
                
            print(f"Saved video with {frames} frames to {path}")
        
        self.video_writers.clear()
        self.recording = False
        self.recording_path = ""
        print("Recording stopped")

    def record_frame(self, camera_type, camera_id, frame):
        """Record a frame if recording is active"""
        if not self.recording:
            return
        
        key = (camera_type, camera_id)
        if key in self.video_writers and frame is not None:
            writer_info = self.video_writers[key]
            writer = writer_info['writer']
            
            try:
                # For grayscale frames, OpenCV requires correct format
                if camera_type == 'EVS' and len(frame.shape) == 2:
                    writer.write(frame)
                else:
                    writer.write(frame)
                
                # Update frame counter
                writer_info['count'] += 1
            except Exception as e:
                print(f"Error recording frame from {camera_type} camera {camera_id}: {e}")
    
    def remove_rgb_camera(self, camera_id):
        """Remove an RGB camera"""
        key = ('RGB', camera_id)
        if key in self.command_events:
            # Signal the process to stop
            self.command_events[key].set()
            
            # Wait for the process to terminate
            if camera_id in self.rgb_cameras:
                process = self.rgb_cameras[camera_id]
                if process.is_alive():
                    process.join(timeout=1.0)  # Wait up to 1 second
                    if process.is_alive():
                        process.terminate()  # Force terminate if not stopped
                
                # Clean up
                del self.rgb_cameras[camera_id]
                
            # Clean up IPC mechanisms
            del self.frame_queues[key]
            del self.command_events[key]
            del self.status_values[key]
    
    def start_all_cameras(self):
        """Start all camera processes"""
        for camera_id, process in self.evs_cameras.items():
            if not process.is_alive():
                process.start()
                
                time.sleep(5)
                
        for camera_id, process in self.rgb_cameras.items():
            if not process.is_alive():
                process.start()
    
    def stop_all_cameras(self):
        """Stop all camera processes"""
        # Signal all processes to stop
        for key in list(self.command_events.keys()):
            self.command_events[key].set()
        
        # Wait for all processes to terminate
        for camera_id, process in list(self.evs_cameras.items()):
            if process.is_alive():
                process.join(timeout=1.0)
                if process.is_alive():
                    process.terminate()
        
        for camera_id, process in list(self.rgb_cameras.items()):
            if process.is_alive():
                process.join(timeout=1.0)
                if process.is_alive():
                    process.terminate()
        
        # Clear all dictionaries
        self.evs_cameras.clear()
        self.rgb_cameras.clear()
        self.frame_queues.clear()
        self.command_events.clear()
        self.status_values.clear()
    
    def get_frame(self, camera_type, camera_id):
        """Get the latest frame from a camera, non-blocking"""
        key = (camera_type, camera_id)
        if key in self.frame_queues and not self.frame_queues[key].empty():
            # Get the latest frame from the queue
            received_id, frame = self.frame_queues[key].get()
            return frame
        return None
    
    def is_camera_running(self, camera_type, camera_id):
        """Check if a camera is running"""
        key = (camera_type, camera_id)
        if key in self.status_values:
            return self.status_values[key].value == 1
        return False
    
    def cleanup(self):
        """Clean up all resources"""
        self.stop_all_cameras()

class CameraControlPanel(QWidget):
    """Panel for camera configuration controls"""
    layout_changed = pyqtSignal(int, int)  # Rows, Columns
    cameras_changed = pyqtSignal()
    recording_started = pyqtSignal(str)  # Signal with folder path
    recording_stopped = pyqtSignal()
    
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
        
        recording_group = QGroupBox("Recording")
        recording_layout = QVBoxLayout()
        
        # Folder selection button
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Save directory:"))
        self.folder_path_label = QLabel("Not selected")
        self.folder_path_label.setStyleSheet("font-style: italic;")
        folder_layout.addWidget(self.folder_path_label, 1)
        
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.on_browse_clicked)
        folder_layout.addWidget(self.browse_button)
        recording_layout.addLayout(folder_layout)
        
        # Recording buttons
        recording_buttons_layout = QHBoxLayout()
        
        self.start_recording_button = QPushButton("Start Recording")
        self.start_recording_button.clicked.connect(self.on_start_recording_clicked)
        self.start_recording_button.setEnabled(False)
        recording_buttons_layout.addWidget(self.start_recording_button)
        
        self.stop_recording_button = QPushButton("Stop Recording")
        self.stop_recording_button.clicked.connect(self.on_stop_recording_clicked)
        self.stop_recording_button.setEnabled(False)
        recording_buttons_layout.addWidget(self.stop_recording_button)
        
        tag_input_layout = QHBoxLayout()
        self.input_tag = QLineEdit()
        self.input_tag.setPlaceholderText("Please input action tag (walk, sit, ...)")
        tag_input_layout.addWidget(self.input_tag)
        
        
        recording_layout.addLayout(recording_buttons_layout)
        recording_layout.addLayout(tag_input_layout)
        
        recording_group.setLayout(recording_layout)
        
        layout.addWidget(recording_group)
        
        # Add stretch to push everything to the top
        layout.addStretch()
        
        self.setLayout(layout)
        self.setMaximumWidth(350)
    
    def on_start_recording_clicked(self):
        """Handle start recording button click"""
        folder_path = self.folder_path_label.text()
        if folder_path == "Not selected":
            # Show warning dialog
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Recording Error", 
                            "Please select a recording directory first.")
            return
        
        # Get action tag
        tag = self.input_tag.text().strip()
        if not tag:
            # Show warning dialog
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Recording Error", 
                            "Please enter an action tag (e.g., 'walk', 'sit').")
            return
        
        # Signal recording started
        self.recording_started.emit(folder_path)
        
        # Update UI state
        self.start_recording_button.setEnabled(False)
        self.stop_recording_button.setEnabled(True)
        self.browse_button.setEnabled(False)
        self.input_tag.setEnabled(False)

    def on_stop_recording_clicked(self):
        """Handle stop recording button click"""
        # Signal recording stopped
        self.recording_stopped.emit()
        
        # Update UI state
        self.stop_recording_button.setEnabled(False)
        self.start_recording_button.setEnabled(True)
        self.browse_button.setEnabled(True)
        self.input_tag.setEnabled(True)
    
    def on_browse_clicked(self):
        """Handle browse button click"""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Recording Directory")
        if folder_path:
            self.folder_path_label.setText(folder_path)
            # Only allow recording to start if folder is selected and cameras are running
            self.start_recording_button.setEnabled(self.is_running())
            
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
    """Widget to display camera feeds in a grid layout with both horizontal and vertical scrolling"""
    def __init__(self, camera_manager, parent=None):
        super().__init__(parent)
        self.camera_manager = camera_manager
        self.rows = 2
        self.cols = 2
        self.camera_views = {}  # Dictionary of camera views by (type, id)
        self.active_cameras = set()  # Set of active camera keys (type, id)
        
        self.init_ui()
        
        # Create timer for frame updates
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_frames)
        self.update_timer.start(33)  # ~30 FPS
    
    def init_ui(self):
        self.main_layout = QVBoxLayout()
        
        # Add button for toggling info display
        button_layout = QHBoxLayout()
        self.info_button = QPushButton("Toggle Info Display")
        self.info_button.clicked.connect(self.toggle_info_display)
        button_layout.addWidget(self.info_button)
        button_layout.addStretch()
        self.main_layout.addLayout(button_layout)
        
        # Create a scroll area for the camera grid
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)  # Enable horizontal scrollbar
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)    # Enable vertical scrollbar
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        
        # Create the grid widget to hold cameras
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)  # Align to top-left for consistent scrolling
        
        # Add the grid widget to the scroll area
        self.scroll_area.setWidget(self.grid_widget)
        
        # Add the scroll area to the main layout
        self.main_layout.addWidget(self.scroll_area)
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
            if item.widget():
                item.widget().setParent(None)
        
        # Add camera views back in the new grid arrangement
        cameras = list(self.camera_views.values())
        total_cameras = len(cameras)
        
        if total_cameras == 0:
            return
            
        # Get first camera view to calculate dimensions
        first_cam = cameras[0]
        cam_width = first_cam.width() + self.grid_layout.spacing()
        cam_height = first_cam.height() + self.grid_layout.spacing()
        
        # Calculate total rows needed based on layout
        total_rows = max(self.rows, (total_cameras + self.cols - 1) // self.cols)
        
        # Keep track of max column used
        max_col = 0
        
        for idx, camera_view in enumerate(cameras):
            # Calculate row and column based on layout setting
            row = idx // self.cols
            col = idx % self.cols
            max_col = max(max_col, col)
            
            # Add widget to grid
            self.grid_layout.addWidget(camera_view, row, col, Qt.AlignCenter)
            camera_view.show()
        
        # Set minimum size for the grid widget to ensure proper scrolling
        min_width = (max_col + 1) * cam_width
        min_height = total_rows * cam_height
        
        # Ensure minimum size is set to enable proper scrolling
        self.grid_widget.setMinimumSize(min_width, min_height)
    
    def add_camera_view(self, camera_type, camera_id):
        """Add a new camera view to the display area"""
        key = (camera_type, camera_id)
        
        if key not in self.camera_views:
            camera_view = CameraView(camera_id, camera_type)
            self.camera_views[key] = camera_view
            self.active_cameras.add(key)
            
            # Update the grid
            self.update_grid()
            
            return camera_view
        else:
            self.active_cameras.add(key)
            return self.camera_views[key]
    
    def remove_camera_view(self, camera_type, camera_id):
        """Remove a camera view from the display area"""
        key = (camera_type, camera_id)
        
        if key in self.camera_views:
            camera_view = self.camera_views[key]
            camera_view.setParent(None)
            del self.camera_views[key]
            self.active_cameras.discard(key)
            
            # Update the grid
            self.update_grid()
    
    def clear_all_views(self):
        """Remove all camera views"""
        for camera_view in self.camera_views.values():
            camera_view.setParent(None)
        
        self.camera_views.clear()
        self.active_cameras.clear()
        self.update_grid()
    
    def update_frames(self):
        """Update all camera frames from the queues"""
        for key in self.active_cameras:
            camera_type, camera_id = key
            
            # Get new frame if available
            frame = self.camera_manager.get_frame(camera_type, camera_id)
            
            if frame is not None:
                # Record frame if recording is active
                self.camera_manager.record_frame(camera_type, camera_id, frame)
                
                # Update display
                if key in self.camera_views:
                    self.camera_views[key].update_frame(frame)
    
    def toggle_info_display(self):
        """Toggle information display on all camera views"""
        for camera_view in self.camera_views.values():
            camera_view.toggle_info_display()

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

class CameraManagerApp(QMainWindow):
    """Main application window with horizontal and vertical scrolling support"""
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
        
        # Add scale control to the control panel
        scale_group = QGroupBox("Camera Scaling")
        scale_layout = QVBoxLayout()
        
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(25, 150)  # 25% to 150% of original size
        self.scale_slider.setValue(100)      # Start at 100%
        self.scale_slider.setTickInterval(25)
        self.scale_slider.setTickPosition(QSlider.TicksBelow)
        self.scale_slider.valueChanged.connect(self.on_scale_changed)
        
        slider_labels = QHBoxLayout()
        slider_labels.addWidget(QLabel("Smaller"))
        slider_labels.addStretch()
        slider_labels.addWidget(QLabel("Original"))
        slider_labels.addStretch()
        slider_labels.addWidget(QLabel("Larger"))
        
        scale_layout.addWidget(QLabel("Camera View Size:"))
        scale_layout.addWidget(self.scale_slider)
        scale_layout.addLayout(slider_labels)
        
        scale_group.setLayout(scale_layout)
        self.control_panel.layout().insertWidget(self.control_panel.layout().count()-1, scale_group)
        
        # Add scroll controls
        scroll_group = QGroupBox("Scroll Controls")
        scroll_layout = QVBoxLayout()
        
        # Scroll speed slider
        self.scroll_speed_slider = QSlider(Qt.Horizontal)
        self.scroll_speed_slider.setRange(1, 10)
        self.scroll_speed_slider.setValue(5)
        self.scroll_speed_slider.setTickInterval(1)
        self.scroll_speed_slider.setTickPosition(QSlider.TicksBelow)
        
        scroll_speed_labels = QHBoxLayout()
        scroll_speed_labels.addWidget(QLabel("Slow"))
        scroll_speed_labels.addStretch()
        scroll_speed_labels.addWidget(QLabel("Fast"))
        
        # Checkbox to toggle scroll bars
        self.show_h_scrollbar = QCheckBox("Show Horizontal Scrollbar")
        self.show_h_scrollbar.setChecked(True)
        self.show_h_scrollbar.stateChanged.connect(self.on_scrollbar_toggle)
        
        self.show_v_scrollbar = QCheckBox("Show Vertical Scrollbar")
        self.show_v_scrollbar.setChecked(True)
        self.show_v_scrollbar.stateChanged.connect(self.on_scrollbar_toggle)
        
        scroll_layout.addWidget(QLabel("Scroll Speed:"))
        scroll_layout.addWidget(self.scroll_speed_slider)
        scroll_layout.addLayout(scroll_speed_labels)
        scroll_layout.addWidget(self.show_h_scrollbar)
        scroll_layout.addWidget(self.show_v_scrollbar)
        
        scroll_group.setLayout(scroll_layout)
        self.control_panel.layout().insertWidget(self.control_panel.layout().count()-1, scroll_group)
        
        # Create display area
        self.display_area = CameraDisplayArea(self.camera_manager)
        
        # Add widgets to splitter
        splitter.addWidget(self.control_panel)
        splitter.addWidget(self.display_area)
        
        # Set initial splitter sizes
        splitter.setSizes([300, 900])
        
        main_layout.addWidget(splitter)
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        
        
        self.control_panel.recording_started.connect(self.on_recording_started)
        self.control_panel.recording_stopped.connect(self.on_recording_stopped)
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
            QScrollArea {
                background-color: #2D2D30;
                border: none;
            }
            QScrollBar:vertical, QScrollBar:horizontal {
                background-color: #2D2D30;
                border: none;
            }
            QScrollBar:vertical {
                width: 12px;
                margin: 0px;
            }
            QScrollBar:horizontal {
                height: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {
                background-color: #3F3F46;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                min-height: 20px;
            }
            QScrollBar::handle:horizontal {
                min-width: 20px;
            }
            QScrollBar::handle:vertical:hover, QScrollBar::handle:horizontal:hover {
                background-color: #4F4F56;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                height: 0px;
                width: 0px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #3F3F46;
                height: 8px;
                background: #2D2D30;
                margin: 2px 0;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #0E639C;
                border: 1px solid #0E639C;
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background: #1177BB;
            }
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
                border: 1px solid #3F3F46;
                border-radius: 3px;
                background-color: #2D2D30;
            }
            QCheckBox::indicator:checked {
                background-color: #0E639C;
                border: 1px solid #0E639C;
            }
        """)
    
    def on_recording_started(self, folder_path):
        """Handle recording started signal"""
        tag = self.control_panel.input_tag.text().strip()
        self.camera_manager.start_recording(folder_path, tag)

    def on_recording_stopped(self):
        """Handle recording stopped signal"""
        self.camera_manager.stop_recording()
    
    def on_layout_changed(self, rows, cols):
        """Handle layout change from control panel"""
        self.display_area.set_grid_layout(rows, cols)
    
    def on_scale_changed(self, value):
        """Handle scale slider value changes"""
        scale_factor = value / 100.0  # Convert percentage to factor
        
        # Update scale for all camera views
        for key, camera_view in self.display_area.camera_views.items():
            camera_view.set_scale(scale_factor)
        
        # Update the grid layout to accommodate new sizes
        self.display_area.update_grid()
    
    def on_scrollbar_toggle(self):
        """Toggle scrollbar visibility based on checkbox states"""
        # Update horizontal scrollbar
        if self.show_h_scrollbar.isChecked():
            self.display_area.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            self.display_area.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        # Update vertical scrollbar
        if self.show_v_scrollbar.isChecked():
            self.display_area.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        else:
            self.display_area.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    
    def update_cameras(self):
        """Update camera instances based on control panel settings"""
        # Stop existing cameras
        self.camera_manager.stop_all_cameras()
        
        # If we're in running state, create and start new cameras
        if self.control_panel.is_running():
            evs_configs, rgb_configs = self.control_panel.get_camera_configs()
            
            self.display_area.clear_all_views()
            
            for camera_id, device_path in evs_configs:
                camera_key = self.camera_manager.add_evs_camera(camera_id, device_path)
                self.display_area.add_camera_view('EVS', camera_id)
            
            for camera_id, device_id in rgb_configs:
                camera_key = self.camera_manager.add_rgb_camera(camera_id, device_id)
                self.display_area.add_camera_view('RGB', camera_id)
            
            # Apply current scale
            scale_factor = self.scale_slider.value() / 100.0
            for key, camera_view in self.display_area.camera_views.items():
                camera_view.set_scale(scale_factor)
            
            self.camera_manager.start_all_cameras()
            
            # Update recording button state if cameras are running
            folder_path = self.control_panel.folder_path_label.text()
            self.control_panel.start_recording_button.setEnabled(
                folder_path != "Not selected"
            )
            
            # Make sure scrollbar visibility is updated
            self.on_scrollbar_toggle()
        else:
            # Cameras are not running, disable recording
            self.control_panel.start_recording_button.setEnabled(False)
            # If recording was in progress, stop it
            if self.camera_manager.recording:
                self.camera_manager.stop_recording()
                self.control_panel.stop_recording_button.setEnabled(False)
                self.control_panel.input_tag.setEnabled(True)

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