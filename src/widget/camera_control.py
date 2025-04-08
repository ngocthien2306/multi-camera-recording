import time
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QComboBox, QGroupBox, QGridLayout, 
                            QSpinBox, QFrame, QCheckBox, QSizePolicy,
                            QScrollArea, QFileDialog, QLineEdit)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot, QSize
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor
import cv2
import numpy as np

from src.widget.bias_control import BiasSettingsDialog

try:
    from metavision_core.event_io.raw_reader import initiate_device
    METAVISION_AVAILABLE = True
except ImportError:
    METAVISION_AVAILABLE = False
    print("Metavision SDK not available. Only RGB cameras are supported.")



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
            
            # Add settings button
            settings_button = QPushButton("Settings")
            settings_button.setFixedWidth(80)
            settings_button.clicked.connect(lambda checked, camera_id=i: self.open_bias_settings(camera_id))
            camera_layout.addWidget(settings_button)
            
            self.evs_settings_layout.addLayout(camera_layout)
        
    def open_bias_settings(self, camera_id):
        """Open bias settings dialog for a specific camera"""
        if not hasattr(self, 'bias_dialogs'):
            self.bias_dialogs = {}
        
        # Get device information from camera manager if available
        device_info = None
        key = ('EVS', camera_id)
        if hasattr(self, 'camera_manager') and key in self.camera_manager.device_info_queues:
            # Check if device information is available
            device_info_queue = self.camera_manager.device_info_queues[key]
            if not device_info_queue.empty():
                device_info = device_info_queue.get()
        
        # Create new dialog if it doesn't exist
        if camera_id not in self.bias_dialogs:
            dialog = BiasSettingsDialog(camera_id, device_info)
            dialog.bias_changed.connect(self.forward_bias_change)
            self.bias_dialogs[camera_id] = dialog
        
        # Show the dialog
        self.bias_dialogs[camera_id].show()
        self.bias_dialogs[camera_id].raise_()
        self.bias_dialogs[camera_id].activateWindow()

    def forward_bias_change(self, bias_name, value, camera_id):
        """Forward bias change signal to main app"""
        # Signal to parent to update the bias
        if hasattr(self, 'camera_manager') and self.camera_manager is not None:
            self.camera_manager.update_camera_bias(bias_name, value, camera_id)
            
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
