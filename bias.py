from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                           QGroupBox, QPushButton, QLabel, QFileDialog, QSlider, QGridLayout,
                           QFrame, QSplitter, QMessageBox, QListWidget)
from PyQt5.QtGui import QImage, QPainter, QPen, QColor

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QPalette

from styles import RawViewerStyles, Styles

class BiasValue:
    def __init__(self, name, value, limits):
        self.name = name
        self.value = value
        self.limits = limits

class BiasSettings:
    def __init__(self):
        self.biases = {
            "bias_diff": BiasValue("bias_diff", 25, (-25, 23)),
            "bias_diff_off": BiasValue("bias_diff_off", 190, (-35, 190)),
            "bias_diff_on": BiasValue("bias_diff_on", 140, (-85, 140)),
            "bias_fo": BiasValue("bias_fo", 35, (-35, 55)),
            "bias_hpf": BiasValue("bias_hpf", 110, (0, 120)),
        }
    
    @classmethod
    def create_default(cls):
        return cls()

class BiasControlWidget(QWidget):
    bias_changed = pyqtSignal(str, int)  # Bias name, new value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bias_settings = BiasSettings.create_default()
        self.setup_ui()
        
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        
        # Create contrast section
        contrast_group = QGroupBox("Contrast")
        contrast_group.setStyleSheet(Styles.GROUP_BOX)
        contrast_layout = QGridLayout(contrast_group)
        contrast_layout.setColumnStretch(1, 1)  # Make slider column expandable
        
        # Add contrast bias sliders
        row = 0
        for bias_name, display_name in [
            ("bias_diff", "Bias Diff"), 
            ("bias_diff_off", "Bias Diff Off"), 
            ("bias_diff_on", "Bias Diff On")
        ]:
            self.add_bias_slider(contrast_layout, bias_name, display_name, row)
            row += 1
        
        main_layout.addWidget(contrast_group)
        
        # Create bandwidth section
        bandwidth_group = QGroupBox("Bandwidth")
        bandwidth_group.setStyleSheet(Styles.GROUP_BOX)
        bandwidth_layout = QGridLayout(bandwidth_group)
        bandwidth_layout.setColumnStretch(1, 1)  # Make slider column expandable
        
        # Add bandwidth bias sliders
        row = 0
        for bias_name, display_name in [
            ("bias_fo", "Bias FO"), 
            ("bias_hpf", "Bias HPF")
        ]:
            self.add_bias_slider(bandwidth_layout, bias_name, display_name, row)
            row += 1
        
        main_layout.addWidget(bandwidth_group)
        main_layout.addStretch()
        
    def add_bias_slider(self, parent_layout, bias_name, display_name, row):
        bias = self.bias_settings.biases[bias_name]
        min_val, max_val = bias.limits
        
        # Label for bias name
        name_label = QLabel(display_name)
        name_label.setFixedWidth(80)  # Fixed width for all labels
        name_label.setStyleSheet(Styles.LABEL)
        parent_layout.addWidget(name_label, row, 0)
        
        # Create slider
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(bias.value)
        slider.setObjectName(bias_name)
        slider.setStyleSheet(RawViewerStyles.SLIDER)
        slider.valueChanged.connect(lambda val, name=bias_name: self.on_slider_changed(name, val))
        parent_layout.addWidget(slider, row, 1)
        
        # Value label
        value_label = QLabel(str(bias.value))
        value_label.setObjectName(f"{bias_name}_value")
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet(Styles.LABEL)
        value_label.setFixedWidth(50)  # Fixed width for value label
        parent_layout.addWidget(value_label, row, 2)
        
        # Add "-" and "+" buttons
        minus_btn = QPushButton("-")
        minus_btn.setFixedSize(30, 30)
        minus_btn.setStyleSheet(Styles.BUTTON)
        minus_btn.clicked.connect(lambda _, name=bias_name: self.decrease_bias(name))
        
        plus_btn = QPushButton("+")
        plus_btn.setFixedSize(30, 30)
        plus_btn.setStyleSheet(Styles.BUTTON)
        plus_btn.clicked.connect(lambda _, name=bias_name: self.increase_bias(name))
        
        parent_layout.addWidget(minus_btn, row, 3)
        parent_layout.addWidget(plus_btn, row, 4)
        
    def on_slider_changed(self, bias_name, value):
        # Update the bias value
        self.bias_settings.biases[bias_name].value = value
        
        # Update the value label
        value_label = self.findChild(QLabel, f"{bias_name}_value")
        if value_label:
            value_label.setText(str(value))
        
        # Emit signal for bias change
        self.bias_changed.emit(bias_name, value)
        
    def decrease_bias(self, bias_name):
        slider = self.findChild(QSlider, bias_name)
        if slider:
            current_value = slider.value()
            slider.setValue(current_value - 5)  # Decrease by 5
            
    def increase_bias(self, bias_name):
        slider = self.findChild(QSlider, bias_name)
        if slider:
            current_value = slider.value()
            slider.setValue(current_value + 5)  # Increase by 5