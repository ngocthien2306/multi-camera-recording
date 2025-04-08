# styles.py
class Styles:
    MAIN_COLOR = "#2196F3"
    DANGER_COLOR = "#f44336"
    BG_COLOR = "#f0f0f0"
    BORDER_COLOR = "#cccccc"
    TEXT_COLOR = "#444444"

    TITLE_LABEL = """
        QLabel {
            color: #2196F3;
            font-size: 24px;
            font-weight: bold;
            padding: 10px;
            background-color: #f8f9fa;
            border-radius: 4px;
            border-bottom: 3px solid #2196F3;
            qproperty-alignment: AlignCenter;
            min-height: 30px;
            margin: 10px 0;
        }
    """

    GROUP_BOX = """
        QGroupBox {
            background-color: #f0f0f0;
            border: 2px solid #cccccc;
            border-radius: 6px;
            margin-top: 10px;
            padding: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            padding: 0 5px;
            color: #444444;
        }
    """

    BUTTON = """
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1976D2;
        }
        QPushButton:pressed {
            background-color: #0D47A1;
        }
    """

    STOP_BUTTON = BUTTON.replace("#2196F3", "#f44336")

    TEXTBOX = """
        QLineEdit {
            padding: 8px;
            border: 2px solid #cccccc;
            border-radius: 4px;
            background-color: white;
        }
        QLineEdit:focus {
            border-color: #2196F3;
        }
    """

    LABEL = "QLabel { color: #444444; font-weight: bold; }"

    DISPLAY_WIDGET = """
        QWidget {
            background-color: black;
            border: 2px solid #444444;
            border-radius: 6px;
        }
    """
    
    # Modify DISPLAY_TITLE to match TITLE_LABEL height
    DISPLAY_TITLE = """
        QLabel {
            color: white;
            font-size: 20px;
            font-weight: bold;
            padding: 10px;
            background-color: #333333;
            border-radius: 4px;
            margin-bottom: 5px;
            qproperty-alignment: AlignCenter;
            min-height: 30px;
            margin: 10px 0;
        }
    """
    # Add disabled state to STOP_BUTTON
    STOP_BUTTON = BUTTON.replace("#2196F3", "#f44336") + """
        QPushButton:disabled {
            background-color: #9E9E9E;
            color: #EEEEEE;
        }
    """

    STOP_BUTTON = """
        QPushButton {
            background-color: #f44336;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #e53935;  /* A slightly darker/more intense red */
        }
        QPushButton:pressed {
            background-color: #c62828;  /* An even darker red for pressed state */
        }
        QPushButton:disabled {
            background-color: #9E9E9E;
            color: #EEEEEE;
        }
    """


class StyleSheetCSV:
    # Colors
    BACKGROUND_COLOR = "#F5F5F5"
    CARD_COLOR = "#FFFFFF"
    PRIMARY_COLOR = "#2196F3"    # Blue
    DANGER_COLOR = "#F44336"     # Red
    SUCCESS_COLOR = "#4CAF50"    # Green
    WARNING_COLOR = "#FFC107"    # Yellow/Orange
    PURPLE_COLOR = "#9C27B0"     # Purple
    
    # Button Styles
    CONVERT_BUTTON = """
        QPushButton {
            background-color: #9C27B0;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #7B1FA2;
        }
        QPushButton:pressed {
            background-color: #6A1B9A;
        }
        QPushButton:disabled {
            background-color: #BDBDBD;
        }
    """
    
    LOAD_BUTTON = """
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #388E3C;
        }
        QPushButton:pressed {
            background-color: #2E7D32;
        }
        QPushButton:disabled {
            background-color: #BDBDBD;
        }
    """
    
    PLAY_BUTTON = """
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1976D2;
        }
        QPushButton:pressed {
            background-color: #1565C0;
        }
        QPushButton:disabled {
            background-color: #BDBDBD;
        }
    """  # Material Design Green
    
    # Existing styles
    GROUP_BOX = """
        QGroupBox {
            font-size: 16px;
            font-weight: bold;
            border: none;
            color: #455A64;
            background-color: white;
            border-radius: 12px;
            margin-top: 20px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            padding: 0 10px;
            left: 15px;
            top: -10px;
        }
    """
    
    BUTTON = """
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1976D2;
        }
        QPushButton:pressed {
            background-color: #0D47A1;
        }
        QPushButton:disabled {
            background-color: #BDBDBD;
        }
    """
    
    STOP_BUTTON = """
        QPushButton {
            background-color: #F44336;
            color: white;
            border: none;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #D32F2F;
        }
        QPushButton:pressed {
            background-color: #B71C1C;
        }
        QPushButton:disabled {
            background-color: #BDBDBD;
        }
    """
    
    TEXTBOX = """
        QLineEdit {
            padding: 8px;
            border: 1px solid #BDBDBD;
            border-radius: 6px;
            background-color: white;
            font-size: 14px;
        }
        QLineEdit:focus {
            border: 2px solid #2196F3;
        }
    """
    
    RADIO_BUTTON = """
        QRadioButton {
            font-size: 14px;
            color: #455A64;
        }
        QRadioButton::indicator {
            width: 16px;
            height: 16px;
        }
    """
    
    # New styles for CSV analysis window
    LABEL = """
        QLabel {
            font-size: 14px;
            color: #455A64;
            padding: 4px;
        }
    """
    
    TITLE_LABEL = """
        QLabel {
            font-size: 20px;
            font-weight: bold;
            color: #455A64;
        }
    """
    
    DISPLAY_TITLE = """
        QLabel {
            font-size: 18px;
            font-weight: bold;
            color: #455A64;
        }
    """
    
    DISPLAY_WIDGET = """
        QWidget {
            background-color: black;
            border-radius: 8px;
        }
    """
    
    PROGRESS_BAR = """
        QProgressBar {
            border: 1px solid #BDBDBD;
            border-radius: 6px;
            text-align: center;
            padding: 2px;
            background-color: white;
            height: 20px;
        }
        QProgressBar::chunk {
            background-color: #2196F3;
            border-radius: 5px;
        }
    """

class StyleSheetMain:
    # Add new style for radio buttons
    RADIO_BUTTON = """
        QRadioButton {
            font-size: 14px;
            color: #455A64;
            padding: 5px;
        }
        QRadioButton::indicator {
            width: 18px;
            height: 18px;
        }
        QRadioButton::indicator:checked {
            background-color: #2962FF;
            border: 2px solid #2962FF;
            border-radius: 9px;
        }
        QRadioButton::indicator:unchecked {
            background-color: white;
            border: 2px solid #455A64;
            border-radius: 9px;
        }
    """
    # Color palette
    PRIMARY_COLOR = "#2962FF"
    GREEN_COLOR = "#4CAF50"
    SECONDARY_COLOR = "#455A64"
    BACKGROUND_COLOR = "#F5F5F5"
    CARD_COLOR = "#FFFFFF"
    BORDER_COLOR = "#E0E0E0"
    
    # Common styles
    TITLE_LABEL = """
        QLabel {
            color: #1A237E;
            font-size: 24px;
            font-weight: bold;
            padding: 10px;
        }
    """
    
    # New styles for CSV analysis window
    LABEL = """
        QLabel {
            font-size: 14px;
            color: #455A64;
            padding: 4px;
        }
    """
    PROGRESS_BAR = """
        QProgressBar {
            border: 1px solid #BDBDBD;
            border-radius: 6px;
            text-align: center;
            padding: 2px;
            background-color: white;
            height: 20px;
        }
        QProgressBar::chunk {
            background-color: #2196F3;
            border-radius: 5px;
        }
    """

    GROUP_BOX = """
        QGroupBox {
            background-color: #FFFFFF;
            border: 2px solid #E0E0E0;
            border-radius: 8px;
            margin-top: 2ex;  /* Increased margin for title */
            font-size: 16px;
            font-weight: bold;
            padding-top: 10px;  /* Add padding at top */
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            padding: 8px 12px;  /* Increased padding */
            color: #1A237E;
            background-color: transparent;
        }
    """
    
    BUTTON = f"""
        QPushButton {{
            background-color: {PRIMARY_COLOR};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px;
            font-size: 14px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: #1565C0;
        }}
        QPushButton:disabled {{
            background-color: #BDBDBD;
        }}
    """
    
    BUTTON_ANA = f"""
        QPushButton {{
            background-color: {GREEN_COLOR};
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px;
            font-size: 14px;
            font-weight: bold;
        }}
        QPushButton:hover {{
            background-color: #00C853;
        }}
        QPushButton:disabled {{
            background-color: #BDBDBD;
        }}
    """

    STOP_BUTTON = """
        QPushButton {
            background-color: #F44336;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 10px;
            font-size: 14px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #D32F2F;
        }
        QPushButton:disabled {
            background-color: #BDBDBD;
        }
    """
    
    TEXTBOX = """
        QLineEdit {
            padding: 8px;
            border: 2px solid #E0E0E0;
            border-radius: 4px;
            background-color: white;
            font-size: 14px;
        }
        QLineEdit:focus {
            border: 2px solid #2962FF;
        }
    """
    
    DISPLAY_TITLE = """
        QLabel {
            color: #1A237E;
            font-size: 20px;
            font-weight: bold;
            padding: 10px;
            background-color: #FFFFFF;
            border-radius: 4px;
        }
    """
    
    DISPLAY_WIDGET = """
        QWidget {
            background-color: #000000;
            border: 2px solid #E0E0E0;
            border-radius: 8px;
        }
    """



class RawViewerStyles:
    # Colors
    PRIMARY_COLOR = "#2196F3"
    DANGER_COLOR = "#F44336"
    SUCCESS_COLOR = "#4CAF50"
    BACKGROUND_COLOR = "#F5F5F5"
    CARD_COLOR = "#FFFFFF"
    BORDER_COLOR = "#E0E0E0"
    TEXT_COLOR = "#444444"
    DARK_BLUE = "#1A237E"
    
    # Group Box Style
    GROUP_BOX = """
        QGroupBox {
            font-weight: bold;
            border: 2px solid #cccccc;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 10px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
        }
    """
    
    # Button Styles
    BUTTON = """
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #1976D2;
        }
        QPushButton:pressed {
            background-color: #0D47A1;
        }
        QPushButton:disabled {
            background-color: #BDBDBD;
        }
    """
    
    START_BUTTON = """
        QPushButton {
            background-color: #4CAF50;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #388E3C;
        }
        QPushButton:pressed {
            background-color: #2E7D32;
        }
        QPushButton:disabled {
            background-color: #BDBDBD;
        }
    """
    
    STOP_BUTTON = """
        QPushButton {
            background-color: #F44336;
            color: white;
            border: none;
            border-radius: 4px;
            padding: 8px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #D32F2F;
        }
        QPushButton:pressed {
            background-color: #B71C1C;
        }
        QPushButton:disabled {
            background-color: #BDBDBD;
        }
    """
    
    # Text Input Style
    TEXTBOX = """
        QLineEdit {
            padding: 8px;
            border: 2px solid #cccccc;
            border-radius: 4px;
            background-color: white;
        }
        QLineEdit:focus {
            border-color: #2196F3;
        }
    """
    
    # Label Styles
    LABEL = """
        QLabel {
            color: #444444;
            font-weight: bold;
        }
    """
    
    TITLE_LABEL = """
        QLabel {
            color: #1A237E;
            font-size: 24px;
            font-weight: bold;
            padding: 10px;
        }
    """
    
    DISPLAY_TITLE = """
        QLabel {
            color: #1A237E;
            font-size: 20px;
            font-weight: bold;
            padding: 10px;
            background-color: #FFFFFF;
            border-radius: 4px;
        }
    """
    
    # Widget Styles
    DISPLAY_WIDGET = """
        QWidget {
            
            border: 2px solid #444444;
            border-radius: 6px;
        }
    """
    
    CARD_FRAME = """
        QFrame {
            background-color: white;
            border-radius: 12px;
        }
    """
    
    # Slider Style
    SLIDER = """
        QSlider::groove:horizontal {
            border: 1px solid #bbb;
            background: white;
            height: 10px;
            border-radius: 4px;
        }

        QSlider::sub-page:horizontal {
            background: #2196F3;
            border: 1px solid #777;
            height: 10px;
            border-radius: 4px;
        }

        QSlider::add-page:horizontal {
            background: #fff;
            border: 1px solid #777;
            height: 10px;
            border-radius: 4px;
        }

        QSlider::handle:horizontal {
            background: #1976D2;
            border: 1px solid #777;
            width: 18px;
            margin-top: -5px;
            margin-bottom: -5px;
            border-radius: 9px;
        }
    """
    
    # Progress Bar Style
    PROGRESS_BAR = """
        QProgressBar {
            border: 1px solid #BDBDBD;
            border-radius: 6px;
            text-align: center;
            padding: 2px;
            background-color: white;
            height: 20px;
        }
        QProgressBar::chunk {
            background-color: #2196F3;
            border-radius: 5px;
        }
    """