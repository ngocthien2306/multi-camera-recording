import json
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QPushButton, QGroupBox, 
                            QSpinBox, QFrame,
                            QScrollArea, QSlider, QFileDialog, QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal

from src.utils.biases import CameraBiasManager, CameraSensorType
from src.utils.styles import AnnotationStyles, Styles

class BiasSlider(QWidget):
    """Widget displaying a bias adjustment slider with label and value"""
    bias_changed = pyqtSignal(str, int)  # Bias name, new value
    
    def __init__(self, bias_info, parent=None):
        super().__init__(parent)
        self.bias_info = bias_info
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Title and description
        title_layout = QHBoxLayout()
        name_label = QLabel(f"<b>{self.bias_info.name}</b>")
        title_layout.addWidget(name_label)
        title_layout.addStretch()
        
        # Display value
        self.value_label = QLabel(f"{self.bias_info.value}")
        self.value_label.setAlignment(Qt.AlignRight)
        title_layout.addWidget(self.value_label)
        
        layout.addLayout(title_layout)
        
        # Description
        if self.bias_info.description:
            desc_label = QLabel(self.bias_info.description)
            desc_label.setStyleSheet("color: #AAAAAA; font-size: 11px;")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)
        
        # Slider or SpinBox
        slider_layout = QHBoxLayout()
        
        # Display minimum value
        min_label = QLabel(f"{self.bias_info.min_val}")
        min_label.setAlignment(Qt.AlignLeft)
        slider_layout.addWidget(min_label)
        
        # SpinBox for direct input
        self.spin_box = QSpinBox()
        self.spin_box.setRange(self.bias_info.min_val, self.bias_info.max_val)
        self.spin_box.setValue(self.bias_info.value)
        self.spin_box.valueChanged.connect(self.on_value_changed)
        self.spin_box.setEnabled(self.bias_info.modifiable)
        
        # Slider
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(self.bias_info.min_val, self.bias_info.max_val)
        self.slider.setValue(self.bias_info.value)
        self.slider.valueChanged.connect(self.on_slider_changed)
        self.slider.setEnabled(self.bias_info.modifiable)
        
        slider_layout.addWidget(self.slider)
        
        # Display maximum value
        max_label = QLabel(f"{self.bias_info.max_val}")
        max_label.setAlignment(Qt.AlignRight)
        slider_layout.addWidget(max_label)
        
        # Add SpinBox on the right
        slider_layout.addWidget(self.spin_box)
        
        layout.addLayout(slider_layout)
        
        # Disable if not modifiable
        if not self.bias_info.modifiable:
            self.setEnabled(False)
    
    def on_slider_changed(self, value):
        """Handle slider value change"""
        self.spin_box.setValue(value)
        self.value_label.setText(f"{value}")
        self.bias_changed.emit(self.bias_info.name, value)
    
    def on_value_changed(self, value):
        """Handle direct value input change"""
        self.slider.setValue(value)
        self.value_label.setText(f"{value}")
        self.bias_changed.emit(self.bias_info.name, value)
    
    def get_bias_value(self):
        """Get current bias value"""
        return self.slider.value()
    
class EnhancedBiasControlWidget(QWidget):
    """Bias control widget with automatic camera type detection"""
    bias_changed = pyqtSignal(str, int)  # Bias name, new value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.camera_type = CameraSensorType.UNKNOWN
        self.bias_sliders = {}
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Camera information
        info_group = QGroupBox("Camera Information")
        info_layout = QVBoxLayout()
        
        self.camera_type_label = QLabel("Camera type: Unidentified")
        self.camera_resolution_label = QLabel("Resolution: Unidentified")
        
        info_layout.addWidget(self.camera_type_label)
        info_layout.addWidget(self.camera_resolution_label)
        
        info_group.setLayout(info_layout)
        main_layout.addWidget(info_group)
        
        # Create scroll area for biases
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        
        self.bias_widget = QWidget()
        self.bias_layout = QVBoxLayout(self.bias_widget)
        
        scroll_area.setWidget(self.bias_widget)
        main_layout.addWidget(scroll_area)
        
        # Button layout cho nút Default Values
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)  # Không có margin
        
        # Default values button - full width
        self.default_button = QPushButton("Set Default Values")
        self.default_button.setMinimumHeight(40) 
        self.default_button.setStyleSheet(AnnotationStyles.OUTLINE_BUTTON_STYLE)
        self.default_button.clicked.connect(self.reset_to_defaults)
        button_layout.addWidget(self.default_button)
        
        main_layout.addLayout(button_layout)
    
    def setup_from_info(self, device_info):
        """Setup UI based on device information dictionary"""
        # Clear current biases
        while self.bias_layout.count():
            item = self.bias_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.bias_sliders.clear()
        
        # Get camera type and resolution from info
        self.camera_type = device_info.get('camera_type', CameraSensorType.UNKNOWN)
        resolution = device_info.get('resolution', (0, 0))
        
        # Update camera information
        self.camera_type_label.setText(f"Camera type: {self.camera_type}")
        self.camera_resolution_label.setText(f"Resolution: {resolution[0]}x{resolution[1]}")
        
        # Get bias information
        biases_info = device_info.get('biases', {})
        
        # Create control UI for each bias
        for bias_name, bias_info in biases_info.items():
            # Only display adjustable biases or important biases
            important_biases = ["bias_diff", "bias_diff_on", "bias_diff_off", 
                                "bias_fo", "bias_hpf", "bias_refr"]
                               
            if bias_info.modifiable or bias_name in important_biases:
                bias_slider = BiasSlider(bias_info)
                bias_slider.bias_changed.connect(self.on_bias_changed)
                self.bias_layout.addWidget(bias_slider)
                self.bias_sliders[bias_name] = bias_slider
                
                # Add separator between biases
                if bias_name != list(biases_info.keys())[-1]:
                    line = QFrame()
                    line.setFrameShape(QFrame.HLine)
                    line.setFrameShadow(QFrame.Sunken)
                    line.setStyleSheet("background-color: #3F3F46;")
                    self.bias_layout.addWidget(line)
    

    def on_bias_changed(self, bias_name, value):
        """Handle bias value change - emit signal immediately"""
        # Forward the signal to parent without waiting for "Apply"
        self.bias_changed.emit(bias_name, value)
        
    def apply_bias_settings(self, bias_settings):
        """Apply loaded bias settings to bias sliders"""
        for bias_name, value in bias_settings.items():
            if bias_name in self.bias_sliders:
                self.bias_sliders[bias_name].slider.setValue(value)
        
        # Optional: Apply all biases immediately
        self.apply_all_biases()

    def get_bias_settings(self):
        """Get current bias settings from sliders"""
        bias_settings = {}
        for bias_name, bias_slider in self.bias_sliders.items():
            bias_settings[bias_name] = bias_slider.get_bias_value()
        return bias_settings
        
    def reset_to_defaults(self):
        """Reset all biases to default values"""
        default_values = CameraBiasManager.get_bias_limits(self.camera_type)
        
        for bias_name, bias_slider in self.bias_sliders.items():
            if bias_name in default_values:
                default_value = default_values[bias_name][0]  # Get default value
                bias_slider.slider.setValue(default_value)
    
    def apply_all_biases(self):
        """Apply all bias changes"""
        # Send signal for all current biases
        for bias_name, bias_slider in self.bias_sliders.items():
            value = bias_slider.get_bias_value()
            self.bias_changed.emit(bias_name, value)
                    
class BiasSettingsDialog(QWidget):
    bias_changed = pyqtSignal(str, int, int)  # Bias name, new value, camera ID
    
    def __init__(self, camera_id, device_info=None, parent=None):
        super().__init__(parent, Qt.Window)
        self.camera_id = camera_id
        self.device_info = device_info
        self.setWindowTitle(f"EVS Camera {camera_id} Bias Settings")
        self.setGeometry(100, 100, 500, 800)
        self.setup_ui()
       
    def add_load_save_buttons(self):
        """Add load and save buttons and close button to the bias settings dialog"""
        buttons_container = QVBoxLayout()
        buttons_container.setSpacing(10)
        
        # Layout cho nút Load và Save - mỗi nút chiếm 1/2 màn hình
        load_save_layout = QHBoxLayout()
        load_save_layout.setSpacing(10)  # Khoảng cách giữa các nút
        load_save_layout.setContentsMargins(0, 0, 0, 0)  # Không có margin
        
        # Nút Load Bias - chiếm 1/2 màn hình bên trái
        self.load_button = QPushButton("Load Bias")
        self.load_button.setMinimumHeight(40)  # Chiều cao tối thiểu
        self.load_button.setStyleSheet(AnnotationStyles.ELEVATED_BUTTON_STYLE)
        self.load_button.clicked.connect(self.load_bias_settings)
        load_save_layout.addWidget(self.load_button, 1)  # Stretch factor 1
        
        # Nút Save Bias - chiếm 1/2 màn hình bên phải
        self.save_button = QPushButton("Save Bias")
        self.save_button.setMinimumHeight(40)  # Chiều cao tối thiểu
        self.save_button.setStyleSheet(AnnotationStyles.GRADIENT_BUTTON_STYLE)
        self.save_button.clicked.connect(self.save_bias_settings)
        load_save_layout.addWidget(self.save_button, 1)  # Stretch factor 1
        
        buttons_container.addLayout(load_save_layout)
        
        close_layout = QHBoxLayout()
        close_layout.setContentsMargins(0, 0, 0, 0)  # Không có margin
        
        close_button = QPushButton("Close")
        close_button.setMinimumHeight(40)  # Chiều cao tối thiểu
        close_button.setStyleSheet(AnnotationStyles.DANGER_BUTTON_STYLE)
        close_button.clicked.connect(self.close)
        close_layout.addWidget(close_button)
        
        buttons_container.addLayout(close_layout)
        
        return buttons_container
    
    def load_bias_settings(self):
        """Load bias settings from a file"""
        # Ensure biases directory exists
        biases_dir = self.ensure_biases_dir()
        
        # Default filename based on camera type
        default_filename = f"{self.get_camera_type()}_bias_settings.json"
        default_path = os.path.join(biases_dir, default_filename)
        
        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Load Bias Settings", 
            default_path,
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            # Load JSON file
            with open(file_path, 'r') as f:
                bias_settings = json.load(f)
            
            # Apply settings to bias controls
            self.bias_widget.apply_bias_settings(bias_settings)
            
            QMessageBox.information(self, "Load Successful", 
                                f"Bias settings loaded from {os.path.basename(file_path)}")
        except Exception as e:
            QMessageBox.warning(self, "Load Error", 
                            f"Failed to load bias settings: {str(e)}")

    def save_bias_settings(self):
        """Save bias settings to a file"""
        # Ensure biases directory exists
        biases_dir = self.ensure_biases_dir()
        
        # Default filename based on camera type
        default_filename = f"{self.get_camera_type()}_bias_settings.json"
        default_path = os.path.join(biases_dir, default_filename)
        
        # Open file dialog
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Bias Settings", 
            default_path,
            "JSON Files (*.json)"
        )
        
        if not file_path:
            return
        
        try:
            # Get current bias settings
            bias_settings = self.bias_widget.get_bias_settings()
            
            # Save to JSON file
            with open(file_path, 'w') as f:
                json.dump(bias_settings, f, indent=4)
            
            QMessageBox.information(self, "Save Successful", 
                                f"Bias settings saved to {os.path.basename(file_path)}")
        except Exception as e:
            QMessageBox.warning(self, "Save Error", 
                            f"Failed to save bias settings: {str(e)}")

    def ensure_biases_dir(self):
        """Ensure biases directory exists and return path"""
        biases_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'biases')
        if not os.path.exists(biases_dir):
            os.makedirs(biases_dir)
        return biases_dir

    def get_camera_type(self):
        """Get camera type string for filename"""
        if self.device_info and 'camera_type' in self.device_info:
            return self.device_info['camera_type']
        return "Unknown"
     
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Add Enhanced Bias Control Widget
        self.bias_widget = EnhancedBiasControlWidget()
        self.bias_widget.bias_changed.connect(self.on_bias_changed)
        main_layout.addWidget(self.bias_widget)
        
        # Setup UI with device info
        if self.device_info:
            self.bias_widget.setup_from_info(self.device_info)
        
        load_save_close_layout = self.add_load_save_buttons()
        main_layout.addLayout(load_save_close_layout)
                
        self.setStyleSheet(Styles.GENERAL)
    
    def on_bias_changed(self, bias_name, value):
        # Forward signal with camera ID
        self.bias_changed.emit(bias_name, value, self.camera_id)
        
    