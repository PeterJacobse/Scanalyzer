import os
import sys
import yaml
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QToolButton, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QFileDialog, QButtonGroup, QComboBox, QRadioButton, QGroupBox
from PyQt6.QtGui import QPixmap, QIcon, QImage
from PyQt6.QtCore import Qt, QSize
from pathlib import Path
import pyqtgraph as pg
from scanalyzer.image_functions import get_scan, image_gradient, background_subtract
from PIL import Image



class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scanalyzer") # Make the app window
        self.setGeometry(100, 100, 900, 600) # x, y, width, height

        # Initialize default parameters
        self.image_files = [""]
        self.file_index = 0
        self.max_file_index = 0
        self.selected_file = ""
        self.file_label = "Select file"
        self.scan_tensor = []
        self.channels = []
        self.channel = ""
        self.channel_index = 0
        self.max_channel_index = 0
        self.scan_direction = "forward"
        self.background_subtraction = "none"
        
        self.script_path = os.path.abspath(__file__) # The full path of Scanalyzer.py
        self.script_folder = os.path.dirname(self.script_path) # The parent directory of Scanalyzer.py
        self.scanalyzer_folder = self.script_folder + "\\scanalyzer" # The directory of the scanalyzer package
        self.selected_scan = self.load_dummy_image() # Default dummy image
        
        try: # Read the last scan file from the config yaml file
            with open(self.scanalyzer_folder + "\\config.yml", "r") as f:
                config = yaml.safe_load(f)
                last_file = config.get("last_file")
                self.load_file(last_file)
        except:
            print("Failed to load the last scan folder from the config.yml file.")
            self.folder = self.scanalyzer_folder



        # Set the central widget of the QMainWindow
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Add ImageView
        pg.setConfigOptions(imageAxisOrder = "row-major")
        self.image_view = pg.ImageView(view = pg.PlotItem())
        


        # Buttons
        # Make file toggling/selecting buttons
        self.previous_file_button, self.file_select_button, self.next_file_button = (QToolButton(), QPushButton(self.file_label), QToolButton())
        self.previous_file_button.setArrowType(Qt.ArrowType.LeftArrow)
        self.previous_file_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.previous_file_button.clicked.connect(self.on_previous_file)
        self.file_select_button.clicked.connect(self.on_file_select)
        self.next_file_button.setArrowType(Qt.ArrowType.RightArrow)
        self.next_file_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.next_file_button.clicked.connect(self.on_next_file)

        # Make channel toggling/selecting buttons
        self.previous_chan_button, self.channel_box, self.next_chan_button = (QToolButton(), QComboBox(), QToolButton())
        self.previous_chan_button.setArrowType(Qt.ArrowType.DownArrow)
        self.previous_chan_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.previous_chan_button.clicked.connect(self.on_previous_chan)
        self.channel_box.addItems(["Channels"])
        self.channel_box.currentIndexChanged.connect(self.on_chan_change)
        self.next_chan_button.setArrowType(Qt.ArrowType.UpArrow)
        self.next_chan_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.next_chan_button.clicked.connect(self.on_next_chan)

        # Direction toggle button (above the other buttons)
        self.direction_button = QPushButton(f"Direction: {self.scan_direction}")
        self.direction_button.setCheckable(True)
        self.direction_button.setChecked(self.scan_direction == "backward")
        self.direction_button.clicked.connect(self.on_toggle_direction)

        # Background subtraction radio buttons (none, plane, inferred)
        self.bg_none_radio = QRadioButton("none")
        self.bg_plane_radio = QRadioButton("plane")
        self.bg_inferred_radio = QRadioButton("inferred")

        # Group them for exclusive selection
        self.bg_button_group = QButtonGroup(self)
        self.bg_button_group.addButton(self.bg_none_radio)
        self.bg_button_group.addButton(self.bg_plane_radio)
        self.bg_button_group.addButton(self.bg_inferred_radio)
        
        # Set default according to self.background_subtraction
        if self.background_subtraction == "plane":
            self.bg_plane_radio.setChecked(True)
        elif self.background_subtraction == "inferred":
            self.bg_inferred_radio.setChecked(True)
        else:
            self.bg_none_radio.setChecked(True)
        
        # Connect toggle signals
        self.bg_none_radio.toggled.connect(lambda checked: self.on_bg_change("none") if checked else None)
        self.bg_plane_radio.toggled.connect(lambda checked: self.on_bg_change("plane") if checked else None)
        self.bg_inferred_radio.toggled.connect(lambda checked: self.on_bg_change("inferred") if checked else None)

        # Make I/O buttons
        self.save_button, self.exit_button = (QPushButton("Save image"), QPushButton("Exit app"))
        self.save_button.clicked.connect(self.on_save)
        self.exit_button.clicked.connect(self.on_exit)


        # --- Fix button overlap: Redesign button layout ---
        button_layout = QVBoxLayout()
        button_layout.setSpacing(12)
        button_layout.setContentsMargins(10, 10, 10, 10)



        # Regroup File, Channel, and Direction into one group box
        file_chan_dir_group = QGroupBox("File / Channel / Direction")
        fcd_vbox = QVBoxLayout()

        # File navigation
        file_nav_hbox = QHBoxLayout()
        file_nav_hbox.addWidget(self.previous_file_button)
        file_nav_hbox.addWidget(self.file_select_button)
        file_nav_hbox.addWidget(self.next_file_button)
        fcd_vbox.addWidget(QLabel("File Selected:"))
        fcd_vbox.addLayout(file_nav_hbox)
        fcd_vbox.addWidget(QLabel("in folder"))
        fcd_vbox.addWidget(QLabel(self.folder))
        fcd_vbox.addWidget(QLabel(f"which contains {self.max_file_index} sxm files"))

        # Channel navigation
        channel_hbox = QHBoxLayout()
        channel_hbox.addWidget(self.previous_chan_button)
        channel_hbox.addWidget(self.channel_box)
        channel_hbox.addWidget(self.next_chan_button)
        fcd_vbox.addSpacing(8)
        fcd_vbox.addLayout(channel_hbox)

        # Direction button
        direction_hbox = QHBoxLayout()
        direction_hbox.addStretch(1)
        direction_hbox.addWidget(self.direction_button)
        direction_hbox.addStretch(1)
        fcd_vbox.addSpacing(8)
        fcd_vbox.addLayout(direction_hbox)

        file_chan_dir_group.setLayout(fcd_vbox)
        button_layout.addWidget(file_chan_dir_group)

        # Background subtraction group
        bg_group = QGroupBox("Background subtraction")
        bg_hbox = QHBoxLayout()
        bg_hbox.setContentsMargins(6, 6, 6, 6)
        bg_hbox.addWidget(self.bg_none_radio)
        bg_hbox.addWidget(self.bg_plane_radio)
        bg_hbox.addWidget(self.bg_inferred_radio)
        bg_group.setLayout(bg_hbox)
        button_layout.addWidget(bg_group)

        # Save and Exit buttons
        io_hbox = QHBoxLayout()
        io_hbox.addWidget(self.save_button)
        io_hbox.addWidget(self.exit_button)
        button_layout.addLayout(io_hbox)

        # Add a stretch at the end to push buttons up
        button_layout.addStretch(1)
        


        # Right column: metadata + buttons
        right_column = QVBoxLayout()
        self.metadata_label = QLabel("")
        self.metadata_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        right_column.addWidget(self.metadata_label)
        right_column.addLayout(button_layout)



        # Combine nested layouts: image view and left column
        main_layout.addWidget(self.image_view, 3)
        main_layout.addLayout(right_column, 1)
        
        # Ensure the central widget can receive keyboard focus
        central_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        central_widget.setFocus()

        # Ensure the main window also accepts focus and is active
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()
        self.activateWindow()

        # Display some initial dummy data
        self.image_view.setImage(self.load_dummy_image())
        self.channel_box.dropEvent



    # The dummy image is the Scanalyzer background picture
    def load_dummy_image(self):
        dummy_image_path = self.scanalyzer_folder + "\\Scanalyzer_drawing.png"
        if os.path.exists(dummy_image_path):
            try:
                img = Image.open(dummy_image_path)
                data = np.array(img)[:, :, 0]
            except Exception as e:
                data = np.random.rand((100, 100))
        return data

    # Key event handler
    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key.Key_Left: self.on_previous_file()
        if key == Qt.Key.Key_F: self.on_file_select()
        if key == Qt.Key.Key_Right: self.on_next_file()
        if key == Qt.Key.Key_Down: self.on_previous_chan()
        if key == Qt.Key.Key_Up: self.on_next_chan()
        if key == Qt.Key.Key_S: self.on_save()
        if key == Qt.Key.Key_D: self.on_toggle_direction()
        # Background subtraction shortcuts: P -> plane, I -> inferred, N -> none
        if key == Qt.Key.Key_P: self.on_bg_change("plane")
        if key == Qt.Key.Key_I: self.on_bg_change("inferred")
        if key == Qt.Key.Key_N: self.on_bg_change("none")
        if key == Qt.Key.Key_Q or key == Qt.Key.Key_X or key == Qt.Key.Key_E or key == Qt.Key.Key_Escape: self.on_exit()
        super().keyPressEvent(event)



    # Button functions
    def on_previous_file(self):
        self.file_index -= 1
        if self.file_index < 0: self.file_index = self.max_file_index
        self.load_image()

    def on_file_select(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open file", "", "SXM files (*.sxm)")
        if file_name: self.load_file(file_name)
    
    def on_toggle_direction(self):
        # Toggle between forward and backward
        self.scan_direction = "backward" if self.scan_direction == "forward" else "forward"
        try:
            if hasattr(self, 'image_files') and not (len(self.image_files) == 0 or (len(self.image_files) == 1 and self.image_files[0] == "")):
                self.load_image()
        except: # Toggle back if an error occurs
            self.scan_direction = "backward" if self.scan_direction == "forward" else "forward"
            self.load_image()
        self.direction_button.setText(f"&Direction: {self.scan_direction}")

    def on_bg_change(self, mode: str):
        """Handler for background subtraction radio buttons."""
        self.background_subtraction = mode
        # Optionally reload the image to apply background subtraction
        try:
            if hasattr(self, 'image_files') and not (len(self.image_files) == 0 or (len(self.image_files) == 1 and self.image_files[0] == "")):
                # reload current image to reflect background change
                self.load_image()
        except Exception as e:
            print(f"Error reloading image after background change: {e}")

    def on_next_file(self):
        self.file_index += 1
        if self.file_index > self.max_file_index: self.file_index = 0
        self.load_image()



    # Channel buttons
    def on_previous_chan(self):
        self.channel_index -= 1
        if self.channel_index < 0: self.channel_index = self.max_channel_index
        self.channel = self.channels[self.channel_index]
        self.load_image()

    def on_chan_change(self, index):
        self.channel_index = index
        self.channel = self.channels[index]
        self.load_image()

    def on_next_chan(self):
        self.channel_index += 1
        if self.channel_index > self.max_channel_index: self.channel_index = 0
        self.channel = self.channels[self.channel_index]
        self.load_image()



    # Routine for loading a new image
    def load_file(self, file_name):
        try:
            self.folder = os.path.dirname(file_name) # Set the folder to the directory of the file
            self.sxm_files = np.array([str(file) for file in Path(self.folder).glob("*.sxm")]) # Read all the sxm files
            self.max_file_index = len(self.sxm_files) - 1
            self.file_index = np.where([os.path.samefile(sxm_file, file_name) for sxm_file in self.sxm_files])[0][0]
            
            if self.file_index > self.max_file_index: self.file_index = 0
            self.selected_file = self.sxm_files[self.file_index]
            self.file_label = os.path.basename(self.selected_file) # The file label is the file name without the directory path
            
            self.load_image()
        except:
            print("Error loading files")
            self.file_label = "Select file"
        
        self.file_select_button.setText(self.file_label)

    def load_image(self):
        self.selected_file = self.sxm_files[self.file_index]
        self.file_label = os.path.basename(self.selected_file)
        self.file_select_button.setText(self.file_label) # Make the select file button display the file name

        self.scan_object = get_scan(self.selected_file) # Load the scan data
        self.channels = self.scan_object.channels # Load which channels have been recorded
        if self.channel not in self.channels: # If the requested channel does not exist in the scan, default the requested channel to be the first channel in the list of channels
            self.channel = self.channels[0]
        self.channel_index = np.where(self.channels == self.channel)[0][0]
        self.max_channel_index = len(self.channels) - 1
    
        # Pick the correct frame out of the scan tensor based on channel and scan direction
        if self.scan_direction == "backward": self.selected_scan = self.scan_object.scan_tensor[self.channel_index, 1]
        else: self.selected_scan = self.scan_object.scan_tensor[self.channel_index, 0]
        # Determine background subtraction mode from radio buttons
        if self.bg_none_radio.isChecked():
            mode = "none"
        elif self.bg_plane_radio.isChecked():
            mode = "plane"
        elif self.bg_inferred_radio.isChecked():
            mode = "inferred"
        else:
            mode = self.background_subtraction  # fallback
        self.processed_scan = background_subtract(self.selected_scan, mode = mode)
        self.image_view.setImage(self.processed_scan) # Show the scan in the app

        # Update the channel selection box based on the available channels
        self.channel_box.blockSignals(True)
        self.channel_box.clear()
        self.channel_box.addItems(self.channels)
        self.channel_box.setCurrentIndex(self.channel_index)
        self.channel_box.blockSignals(False)

        # Read the header and save the scan parameters
        self.bias = self.scan_object.bias
        self.scan_range = self.scan_object.scan_range_nm
        self.feedback = self.scan_object.feedback
        self.setpoint = self.scan_object.setpoint_pA

        if self.feedback:
            self.metadata_label.setText(f"STM topographic scan\nV = {self.bias} V\nI_fb = {self.setpoint} pA\nScan range: {self.scan_range} nm\nChannel: {self.channel}\nScan direction: {self.scan_direction}")
        else:
            self.metadata_label.setText(f"Constant height scan\nV = {self.bias} V\nScan range: {self.scan_range}\nChannel: {self.channel} nm\nScan direction: {self.scan_direction}")

    # Save button
    def on_save(self):
        print("SAVED!")

    # Exit button
    def on_exit(self):
        print(self.scanalyzer_folder + "\\config.yml")
        try: # Save the scan folder to the config yaml file so it opens automatically on startup next time
            with open(self.scanalyzer_folder + "\\config.yml", "w") as f:
                yaml.safe_dump({"last_file": self.selected_file}, f)
        except Exception as e:
            print("Failed to save the scan folder to the config.yml file.")
            print(e)
        print("Thank you for using Scanalyzer!")
        QApplication.instance().quit()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AppWindow()
    window.show()
    sys.exit(app.exec())