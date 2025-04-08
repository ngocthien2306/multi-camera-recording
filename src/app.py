
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QGroupBox, 
                            QSplitter, QCheckBox,
                            QSlider, QDialog)
from PyQt5.QtCore import Qt

from src.services.camera_service import CameraManager
from src.utils.styles import Styles
from src.widget.camera_control import CameraControlPanel, CameraDisplayArea
from src.widget.loading_dialog import LoadingDialog

class CameraManagerApp(QMainWindow):
    """Main application window with horizontal and vertical scrolling support"""
    def __init__(self):
        super().__init__()
        self.camera_manager = CameraManager()
        self.init_ui()
    
    def init_ui(self):
        # Set window properties
        self.setWindowTitle("Camera Manager")
        self.setMinimumSize(1800, 1000)
        
        # Create main widget and layout
        central_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Create control panel
        self.control_panel = CameraControlPanel()
        self.control_panel.layout_changed.connect(self.on_layout_changed)
        self.control_panel.cameras_changed.connect(self.update_cameras)
        
        self.control_panel.camera_manager = self.camera_manager
        
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
        
        # scroll_layout.addWidget(QLabel("Scroll Speed:"))
        # scroll_layout.addWidget(self.scroll_speed_slider)
        # scroll_layout.addLayout(scroll_speed_labels)
        # scroll_layout.addWidget(self.show_h_scrollbar)
        # scroll_layout.addWidget(self.show_v_scrollbar)
        
        # scroll_group.setLayout(scroll_layout)
        # self.control_panel.layout().insertWidget(self.control_panel.layout().count()-1, scroll_group)
        
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
        self.setStyleSheet(Styles.GENERAL)
    
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
            total_cameras = len(evs_configs) + len(rgb_configs)
            
            if total_cameras > 0:
                # Add and configure cameras first
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
                
                # Create and show loading dialog
                loading_dialog = LoadingDialog(total_cameras, self, self.camera_manager)
                
                # Show dialog, then start camera initialization in background
                loading_dialog.show()
                loading_dialog.start_camera_initialization()
                
                # Run dialog event loop
                result = loading_dialog.exec_()
                
                if result == QDialog.Rejected:
                    self.control_panel.stop_button.setEnabled(False)
                    self.control_panel.start_button.setEnabled(True)
                    self.control_panel.evs_count_spinbox.setEnabled(True)
                    self.control_panel.rgb_count_spinbox.setEnabled(True)
                    return
                
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
