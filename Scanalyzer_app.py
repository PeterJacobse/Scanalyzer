import os
import sys
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QToolButton, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QFileDialog
from PyQt6.QtGui import QPixmap, QIcon, QImage
from PyQt6.QtCore import Qt, QSize
from pathlib import Path
import pyqtgraph as pg
import nanonispy2 as nap



class ImageFunctions:
    def __init__(self):
        pass

    def get_scan(self, file_name, crop_unfinished: bool = True):
        if not os.path.exists(file_name):
            print(f"Error: File \"{file_name}\" does not exist.")
            return
        else:
            self.scan_data = nap.read.Scan(file_name) # Read the scan data
            self.channels = np.array([key for key in self.scan_data.signals.keys()])
            self.scans = [self.scan_data.signals[key] for key in self.channels]
            self.scan_header = self.scan_data.header
            self.header_keys = [key for key in self.scan_header.keys()]
            self.header_values = [self.scan_header[key] for key in self.header_keys]
            self.up_or_down = self.scan_header.get("scan_dir", "down")
            
            # Stack the forward and backward scans for each channel in a big tensor. Flip the backward scan
            self.all_scans = np.stack([np.stack((np.array(self.scan_data.signals[channel]["forward"], dtype = float), np.flip(np.array(self.scan_data.signals[channel]["backward"], dtype = float), axis = 1))) for channel in self.channels])
            if self.up_or_down == "up": all_scans = np.flip(all_scans, axis = 2) # Flip the scan if it recorded down to up

            if crop_unfinished:
                # Determine which rows should be cropped off in an uncompleted scan
                self.masked_array = np.isnan(self.all_scans[0, 1]) # The backward scan has more NaN values because the scan always starts in the forward direction
                self.nan_counts = np.array([sum([int(self.masked_array[j, i]) for i in range(len(self.masked_array))]) for j in range(len(self.masked_array[0]))])
                self.good_rows = np.where(self.nan_counts == 0)[0]
                self.all_scans_processed = np.array([[self.all_scans[channel, 0, self.good_rows], self.all_scans[channel, 1, self.good_rows]] for channel in range(len(self.channels))])
            else: self.all_scans_processed = self.all_scans

            self.angle = float(self.scan_header.get("scan_angle", 0))
            self.pixels = np.shape(self.all_scans_processed[0, 0])
            self.date = self.scan_header.get("rec_date", "00.00.1900")
            self.time = self.scan_header.get("rec_time", "00:00:00")
            self.center = self.scan_header.get("scan_offset", np.array([0, 0], dtype = float))
            self.size = self.scan_header.get("scan_range", np.array([1E-7, 1E-7], dtype = float))
            self.bias = self.scan_data.header.get("bias", 0)

            return self.all_scans_processed



class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scanalyzer") # Make the app window
        self.setGeometry(100, 100, 900, 600) # x, y, width, height

        # Initialize default parameters
        script_path = os.path.abspath(__file__) # The default folder is the directory of the app
        self.folder = os.path.dirname(script_path)
        self.file_label = "Select file"
        self.image_files = [""]
        self.index = 0
        self.max_index = 0
        self.selected_file = ""
        self.scans = []
        self.channel = ""
        self.background_subtraction = "plane"

        # Initialize an image
        self.image_functions = ImageFunctions()
        self.image_data = np.random.rand(100, 100) * 255  # 100x100 grayscale image

        # Set the central widget of the QMainWindow
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Add ImageView
        self.image_view = pg.ImageView()
        
        button_layout = QGridLayout()
        # Buttons
        # File toggling/selecting
        self.previous_button = QToolButton()
        self.previous_button.setArrowType(Qt.ArrowType.LeftArrow)
        self.previous_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.previous_button.clicked.connect(self.on_previous)
        button_layout.addWidget(self.previous_button, 0, 0)

        self.file_button = QPushButton()
        self.file_button.setText(self.file_label)
        self.file_button.clicked.connect(self.on_file_select)
        button_layout.addWidget(self.file_button, 0, 1)

        self.next_button = QToolButton()
        self.next_button.setArrowType(Qt.ArrowType.RightArrow)
        self.next_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.next_button.clicked.connect(self.on_next)
        button_layout.addWidget(self.next_button, 0, 2)

        # Channel toggling/selecting
        self.previous_chan_button = QToolButton()
        self.previous_chan_button.setArrowType(Qt.ArrowType.UpArrow)
        self.previous_chan_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.previous_chan_button.clicked.connect(self.on_previous_chan)
        button_layout.addWidget(self.previous_button, 1, 1)

        self.channel_button = QPushButton()
        self.channel_button.setText(self.file_label)
        self.channel_button.clicked.connect(self.on_chan_select)
        button_layout.addWidget(self.file_button, 2, 1)

        self.next_chan_button = QToolButton()
        self.next_chan_button.setArrowType(Qt.ArrowType.DownArrow)
        self.next_chan_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.next_chan_button.clicked.connect(self.on_next_chan)
        button_layout.addWidget(self.next_chan_button, 3, 1)

        # Exit button
        self.exit_button = QPushButton("Exit app")
        self.exit_button.clicked.connect(self.on_exit)
        button_layout.addWidget(self.exit_button, 4, 1)

        # Combine nested layouts
        main_layout.addWidget(self.image_view, 3)
        main_layout.addLayout(button_layout, 1)
        
        # Ensure the central widget can receive keyboard focus
        central_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        central_widget.setFocus()

        # Ensure the main window also accepts focus and is active
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()
        self.activateWindow()

        # Display some initial dummy data
        self.display_dummy_image()

    def display_dummy_image(self):
        data = np.random.rand(200, 200) * 255  # Example 200x200 image data
        self.image_view.setImage(data)



    # Key event handler
    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key.Key_Left:
            self.on_previous()
        elif key == Qt.Key.Key_F or Qt.Key.Key_S:
            self.on_file_select()
        elif key == Qt.Key.Key_Right:
            self.on_next()
        elif (modifiers & Qt.KeyboardModifier.ControlModifier) and key == Qt.Key.Key_Q or key == Qt.Key.Key_Escape:
            self.label.setText("You pressed Ctrl+Q! Exiting...")
            self.on_exit()
        super().keyPressEvent(event)



    # Button functions
    def on_previous(self):
        self.index -= 1
        if self.index < 0: self.index = self.max_index - 1
        self.load_image()

    def on_file_select(self):
        # getOpenFileName returns a tuple: (filename, filter_selected)
        file_name, _ = QFileDialog.getOpenFileName(self, "Open file", "", "SXM files (*.sxm)")

        if file_name: # Check if a file was selected
            self.folder = os.path.dirname(file_name)
            print(f"Selected folder: {self.folder}")
            self.image_files = [str(file) for file in Path(self.folder).glob("*.sxm")]
            self.max_index = len(self.image_files)
            if self.index > self.max_index - 1: self.index = 0
            self.selected_file = self.image_files[self.index]
            self.file_label = os.path.basename(self.selected_file)
        if self.max_index < 1: # No scans detected; revert button text to select file
            self.file_label = "Select file"
            self.file_button.setText(self.file_label)
        else: self.load_image()

    def on_next(self):
        self.index += 1
        if self.index > self.max_index - 1: self.index = 0
        self.load_image()


    # Channel buttons
    def on_previous_chan(self):
        self.channel -= 1
        if self.channel < 0: self.channel = 2
        self.load_image()

    def on_chan_select(self):
        # getOpenFileName returns a tuple: (filename, filter_selected)
        file_name, _ = QFileDialog.getOpenFileName(self, "Open file", "", "SXM files (*.sxm)")

        if file_name: # Check if a file was selected
            self.folder = os.path.dirname(file_name)
            print(f"Selected folder: {self.folder}")
            self.image_files = [str(file) for file in Path(self.folder).glob("*.sxm")]
            self.max_index = len(self.image_files)
            if self.index > self.max_index - 1: self.index = 0
            self.selected_file = self.image_files[self.index]
            self.file_label = os.path.basename(self.selected_file)
        if self.max_index < 1: # No scans detected; revert button text to select file
            self.file_label = "Select file"
            self.file_button.setText(self.file_label)
        else: self.load_image()

    def on_next_chan(self):
        self.index += 1
        if self.index > self.max_index - 1: self.index = 0
        self.load_image()


    
    def on_exit(self):
        print("Bye!")
        QApplication.instance().quit()
    
    def load_image(self, crop_unfinished = True):
        self.selected_file = self.image_files[self.index]
        self.file_label = os.path.basename(self.selected_file)
        self.file_button.setText(self.file_label)

        self.scans = self.image_functions.get_scan(self.selected_file)
        print(self.scans[0, :2, :2])



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AppWindow()
    window.show()
    sys.exit(app.exec())