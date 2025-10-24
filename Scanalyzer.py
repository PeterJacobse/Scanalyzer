import os
import sys
import yaml
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QToolButton, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QFileDialog,
    QButtonGroup, QComboBox, QRadioButton, QGroupBox, QLineEdit, QFrame, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from pathlib import Path
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from PyQt6.QtGui import QImage, QDragEnterEvent, QDropEvent, QDragMoveEvent, QShortcut, QKeySequence
from scanalyzer.image_functions import get_scan, image_gradient, background_subtract, get_image_statistics, spec_times
from datetime import datetime
from time import sleep



class SpectroscopyWindow(QMainWindow):
    def __init__(self, processed_scan):
        super().__init__()
        self.setWindowTitle("Spectrum viewer")
        self.setGeometry(200, 200, 700, 450)
        
        # Add ImageView
        self.image_view = pg.ImageView()

        layout = QVBoxLayout()
        label = QLabel("Spectrum viewer")
        layout.addWidget(label)

        # Set the central widget of the QMainWindow
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.addWidget(self.image_view, 3)

        exit_button = QPushButton("Exit Spectrum viewer")
        exit_button.clicked.connect(self.close) # Connect to the window's close method
        main_layout.addWidget(exit_button)

        # Show the scan        
        self.image_view.setImage(processed_scan, autoRange = True)  # Show the scan in the app
        image_item = self.image_view.getImageItem()
        #image_item.setRect(QtCore.QRectF(0, 0, self.scan_range[1], self.scan_range[0]))  # Add dimensions to the ImageView object
        self.image_view.autoRange()



class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scanalyzer by Peter H. Jacobse") # Make the app window
        self.setGeometry(100, 100, 1400, 800) # x, y, width, height

        # Add ImageView
        pg.setConfigOptions(imageAxisOrder = "row-major")
        self.image_view = pg.ImageView(view = pg.PlotItem())
        self.hist = self.image_view.getHistogramWidget()
        self.hist_item = self.hist.item
        self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)

        # Initialize parameters
        self.parameters_init()
        
        # Set the central widget of the QMainWindow
        central_widget = QWidget()
        self.setCentralWidget(central_widget)        
        main_layout = QHBoxLayout(central_widget)
        main_layout.addWidget(self.image_view, 3)
        main_layout.addLayout(self.draw_buttons(), 1)

        # Activate buttons and keys
        self.connect_buttons()
        self.connect_keys()
        
        # Ensure the central widget can receive keyboard focus
        central_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        central_widget.setFocus()

        # Ensure the main window also accepts focus and is active
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()
        self.activateWindow()
        self.channel_box.dropEvent

        # Initialize the ImageView
        try: # Read the last scan file from the config yaml file
            with open(self.scanalyzer_folder + "\\config.yml", "r") as file:
                config = yaml.safe_load(file)
                last_file = config.get("last_file")
                self.load_folder(last_file)
        except:  # Display the dummy scan
            self.folder = self.scanalyzer_folder
            self.sxm_file = self.scanalyzer_folder + "dummy_scan.sxm"
            self.load_folder(self.sxm_file)



    def parameters_init(self): # Initialize default parameters
        # I/O paths
        self.script_path = os.path.abspath(__file__) # The full path of Scanalyzer.py
        self.script_folder = os.path.dirname(self.script_path) # The parent directory of Scanalyzer.py
        self.scanalyzer_folder = self.script_folder + "\\scanalyzer" # The directory of the Scanalyzer package
        self.folder = self.scanalyzer_folder # Set current folder to Scanalyzer folder
        self.output_folder_name = "Extracted Files" # Set output folder for saving images
        self.output_folder = self.folder + "\\" + self.output_folder_name
        
        self.sxm_files = []
        self.spec_files = []
        self.spec_times = []
        self.image_files = [""]
        self.file_index = 0
        self.max_file_index = -1
        self.selected_file = ""
        self.file_label = "Select file"
        self.png_file_name = ""
        self.scan_tensor = []
        self.channels = []
        self.channel = ""
        self.channel_index = 0
        self.max_channel_index = 0
        self.scan_direction = "forward"
        self.background_subtraction = "none"
        self.scale_toggle_index = 0
        self.min_percentile = 2
        self.max_percentile = 98
        self.min_std_dev = 2
        self.max_std_dev = 2
        self.min_selection = 0
        self.max_selection = 0

    def draw_buttons(self):

        def draw_summary_group(): # Scan summary group
            scan_summary_group = QGroupBox("Scan summary")
            scan_summary_layout = QVBoxLayout()
            scan_summary_layout.setSpacing(1)
            
            self.scan_summary_label = QLabel("Scanalyzer by Peter H. Jacobse") # Only for initialization
            self.scan_summary_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            scan_summary_layout.addWidget(self.scan_summary_label)

            self.statistics_info = QLabel("Statistics")
            self.statistics_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
            scan_summary_layout.addWidget(self.statistics_info)

            scan_summary_group.setLayout(scan_summary_layout)
        
            return scan_summary_group
        
        def draw_file_chan_dir_group(): # File/Channel/Direction group
            file_chan_dir_group = QGroupBox("File / Channel / Direction")
            fcd_layout = QVBoxLayout()
            fcd_layout.setSpacing(1)

            # Row 1: "Load file"
            file_selected_label = QLabel("Load file:")
            file_selected_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fcd_layout.addWidget(file_selected_label)

            # Row 2: file navigation
            file_nav_hbox = QHBoxLayout()
            [self.previous_file_button, self.file_select_button, self.next_file_button] = file_toggle_buttons = [QToolButton(), QPushButton(self.file_label), QToolButton()]
            self.previous_file_button.setArrowType(Qt.ArrowType.LeftArrow)
            self.previous_file_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            self.next_file_button.setArrowType(Qt.ArrowType.RightArrow)
            self.next_file_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            for button in file_toggle_buttons: file_nav_hbox.addWidget(button)        
            fcd_layout.addLayout(file_nav_hbox)

            # Row 3: "in folder"
            in_folder_label = QLabel("in folder (click or \"N\" opens in explorer)")
            in_folder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fcd_layout.addWidget(in_folder_label)
            
            # Row 4: folder name
            self.folder_name_button = QPushButton(self.folder)
            fcd_layout.addWidget(self.folder_name_button)

            # Row 5: "which contains n sxm files" 
            if self.max_file_index == 0: self.contains_n_files_label = QLabel(f"which contains 1 sxm file")
            else: self.contains_n_files_label = QLabel(f"which contains {self.max_file_index + 1} sxm files")
            self.contains_n_files_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fcd_layout.addWidget(self.contains_n_files_label)

            # Row 6: "Channel selected"
            channel_selected_box = QLabel("Channel selected:")
            channel_selected_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fcd_layout.addWidget(channel_selected_box)

            # Row 7: channel navigation
            channel_hbox = QHBoxLayout()
            [self.previous_chan_button, self.channel_box, self.next_chan_button] = channel_toggle_buttons = [QToolButton(), QComboBox(), QToolButton()]
            self.previous_chan_button.setArrowType(Qt.ArrowType.DownArrow)
            self.previous_chan_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            self.channel_box.addItems(["Channels"])
            self.next_chan_button.setArrowType(Qt.ArrowType.UpArrow)
            self.next_chan_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
            for button in channel_toggle_buttons: channel_hbox.addWidget(button)
            fcd_layout.addLayout(channel_hbox)

            # Direction button
            direction_hbox = QHBoxLayout()
            self.direction_button = QPushButton()
            self.direction_button.setCheckable(True)
            self.direction_button.setChecked(self.scan_direction == "backward") # checked == True -> backward, checked == False -> forward
            self.direction_button.setText("Direction: backward" if self.direction_button.isChecked() else "Direction: forward")

            direction_hbox.addWidget(self.direction_button)
            fcd_layout.addLayout(direction_hbox)
            file_chan_dir_group.setLayout(fcd_layout)

            self.fcd_buttons = file_toggle_buttons + [self.folder_name_button] + channel_toggle_buttons + [self.direction_button]

            return file_chan_dir_group

        def draw_image_processing_group(): # Image processing group            
            im_proc_group = QGroupBox("Image processing")
            im_proc_layout = QVBoxLayout()
            im_proc_layout.setSpacing(1)
            
            back_sub_label = QLabel("Background subtraction")
            back_sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            im_proc_layout.addWidget(back_sub_label)
            
            # Background subtraction group
            bg_layout = QGridLayout()
            [self.bg_none_radio, self.bg_plane_radio, self.bg_inferred_radio, self.bg_linewise_radio] = background_buttons = [QRadioButton("None"), QRadioButton("Plane"), QRadioButton("Inferred"), QRadioButton("lineWise")]
            # Group them for exclusive selection
            self.bg_button_group = QButtonGroup(self)
            [self.bg_button_group.addButton(button) for button in background_buttons]
            
            # Set default according to self.background_subtraction
            if self.background_subtraction == "plane":
                self.bg_plane_radio.setChecked(True)
            elif self.background_subtraction == "inferred":
                self.bg_inferred_radio.setChecked(True)
            elif self.background_subtraction == "linewise":
                self.bg_linewise_radio.setChecked(True)
            else:
                self.bg_none_radio.setChecked(True)
            
            # Add radio buttons to the layout
            bg_layout.addWidget(self.bg_none_radio, 0, 0)
            bg_layout.addWidget(self.bg_plane_radio, 0, 1)
            bg_layout.addWidget(self.bg_inferred_radio, 1, 0)
            bg_layout.addWidget(self.bg_linewise_radio, 1, 1)
            im_proc_layout.addLayout(bg_layout)

            # Create the horizontal line separator
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)  # Set the shape to a horizontal line
            line.setLineWidth(1) # Optional: Set the line width
            im_proc_layout.addWidget(line) # Add the line to the QVBoxLayout



            # Matrix operations
            back_sub_label = QLabel("Matrix operations")
            back_sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            im_proc_layout.addWidget(back_sub_label)

            matrix_layout = QGridLayout()
            matrix_layout.setSpacing(1)
            [self.sobel_button, self.normal_button, self.laplace_button, self.gauss_button, self.fft_button] = matrix_buttons = [QCheckBox("soBel (d/dx + i d/dy)"), QCheckBox("Normal_z"), QCheckBox("laplaCe (∇2)"), QCheckBox("Gaussian"), QCheckBox("Fft")]
            [button.setEnabled(False) for button in matrix_buttons]

            gaussian_width_label = QLabel("width (nm):")
            gaussian_width_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.gaussian_width_box = QLineEdit("1")

            matrix_layout.addWidget(self.sobel_button, 0, 0)
            matrix_layout.addWidget(self.normal_button, 0, 1)
            matrix_layout.addWidget(self.laplace_button, 0, 2)
            matrix_layout.addWidget(self.gauss_button, 1, 0)
            matrix_layout.addWidget(gaussian_width_label, 1, 1)
            matrix_layout.addWidget(self.gaussian_width_box, 1, 2)
            matrix_layout.addWidget(self.fft_button, 2, 1)
            im_proc_layout.addLayout(matrix_layout)

            # Add another line
            line = QFrame()
            line.setFrameShape(QFrame.Shape.HLine)
            line.setLineWidth(1)
            im_proc_layout.addWidget(line)



            # Histogram control group: put the statistics/info label here
            limits_label = QLabel("Set limits (toggle using the - and = buttons)")
            limits_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            im_proc_layout.addWidget(limits_label)

            limits_layout = QGridLayout()
            limits_layout.setSpacing(1)            
            [self.min_range_box, self.min_range_set, self.full_scale_button, self.max_range_set, self.max_range_box] = range_boxes = [QLineEdit(), QRadioButton(), QPushButton("by fUll data range"), QRadioButton(), QLineEdit()]
            [box.setEnabled(False) for box in [self.min_range_box, self.max_range_box]]

            [self.min_percentile_box, self.min_percentile_set, self.set_percentile_button, self.max_percentile_set, self.max_percentile_box] = percentile_boxes = [QLineEdit(), QRadioButton(), QPushButton("by data Range percentiles"), QRadioButton(), QLineEdit()]
            self.min_percentile_box.setText(str(self.min_percentile))
            self.max_percentile_box.setText(str(self.max_percentile))

            [self.min_std_dev_box, self.min_std_dev_set, self.set_std_dev_button, self.max_std_dev_set, self.max_std_dev_box] = std_dev_boxes = [QLineEdit(), QRadioButton(), QPushButton("by standard deViations"), QRadioButton(), QLineEdit()]
            self.min_std_dev_box.setText(str(self.min_std_dev))
            self.max_std_dev_box.setText(str(self.max_std_dev))

            [self.min_abs_val_box, self.min_abs_val_set, self.set_abs_val_button, self.max_abs_val_set, self.max_abs_val_box] = abs_val_boxes = [QLineEdit(), QRadioButton(), QPushButton("by Absolute values"), QRadioButton(), QLineEdit()]
            self.min_abs_val_box.setText("0")
            self.max_abs_val_box.setText("1")

            [limits_layout.addWidget(range_boxes[index], 0, index) for index in range(len(range_boxes))]
            [limits_layout.addWidget(percentile_boxes[index], 1, index) for index in range(len(percentile_boxes))]
            [limits_layout.addWidget(std_dev_boxes[index], 2, index) for index in range(len(std_dev_boxes))]
            [limits_layout.addWidget(abs_val_boxes[index], 3, index) for index in range(len(abs_val_boxes))]

            # Min and max buttons are exclusive
            self.min_button_group = QButtonGroup(self)
            [self.min_button_group.addButton(button) for button in [self.min_range_set, self.min_percentile_set, self.min_std_dev_set, self.min_abs_val_set]]
            self.max_button_group = QButtonGroup(self)
            [self.max_button_group.addButton(button) for button in [self.max_range_set, self.max_percentile_set, self.max_std_dev_set, self.max_abs_val_set]]
            
            im_proc_layout.addLayout(limits_layout)
            im_proc_group.setLayout(im_proc_layout)

            return im_proc_group
        
        def draw_associated_spectra_group(): # Associated spectra dropdown menu
            spectra_group = QGroupBox("Associated spectra")
            spectra_vbox = QVBoxLayout()
            spectra_vbox.setSpacing(1)

            self.spectra_box = QComboBox()
            spectra_vbox.addWidget(self.spectra_box)

            self.open_spectrum_button = QPushButton("Open spectrum viewer")
            spectra_vbox.addWidget(self.open_spectrum_button)

            spectra_group.setLayout(spectra_vbox)

            return spectra_group

        def draw_io_group(): # I/O group
            io_group = QGroupBox("I/O")
            io_box = QGridLayout()
            io_box.setSpacing(1)
            io_box.setColumnStretch(0, 1)
            io_box.setColumnStretch(1, 1)

            # Make I/O buttons
            (self.save_button, self.exit_button, self.open_folder_button) = (QPushButton("Save image"), QPushButton("EXit Scanalyzer"), QPushButton("open ouTput folder"))
            self.save_button.setText("Save image as")
            self.png_file_box = QLineEdit()
            self.png_file_box.setAlignment(Qt.AlignmentFlag.AlignLeft)
            in_output_folder_label = QLabel("in output folder")
            in_output_folder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.output_folder_box = QPushButton()
            self.check_exists_box = QPushButton()

            io_box.addWidget(self.save_button, 0, 0)
            io_box.addWidget(self.png_file_box, 0, 1)
            io_box.addWidget(in_output_folder_label, 1, 0)
            io_box.addWidget(self.output_folder_box, 1, 1)
            io_box.addWidget(self.check_exists_box, 2, 0)
            io_box.addWidget(self.open_folder_button, 2, 1)
            io_box.addWidget(self.exit_button, 3, 1)

            io_group.setLayout(io_box)

            return io_group

        # Make the buttons. Overal layout is a QVBoxLayout
        button_layout = QVBoxLayout()
        button_layout.setSpacing(1)
        button_layout.setContentsMargins(4, 4, 4, 4)
        [button_layout.addWidget(group) for group in [draw_summary_group(), draw_file_chan_dir_group(), draw_image_processing_group(), draw_associated_spectra_group(), draw_io_group()]]
        button_layout.addStretch(1) # Add a stretch at the end to push buttons up

        return button_layout

    def connect_buttons(self):
        # File_chan_dir group
        # File toggling
        self.previous_file_button.clicked.connect(self.on_previous_file)
        self.file_select_button.clicked.connect(self.on_file_select)
        self.next_file_button.clicked.connect(self.on_next_file)

        # Open folder in file explorer
        self.folder_name_button.clicked.connect(lambda: os.startfile(self.folder))
        
        # Channel toggling
        self.previous_chan_button.clicked.connect(self.on_previous_chan)
        self.channel_box.currentIndexChanged.connect(self.on_chan_change)
        self.next_chan_button.clicked.connect(self.on_next_chan)

        # Direction
        self.direction_button.toggled.connect(self.on_direction_toggled)



        # Image processing group
        # Background subtraction toggle buttons
        self.bg_none_radio.toggled.connect(lambda checked: self.on_bg_change("none") if checked else None)
        self.bg_plane_radio.toggled.connect(lambda checked: self.on_bg_change("plane") if checked else None)
        self.bg_inferred_radio.toggled.connect(lambda checked: self.on_bg_change("inferred") if checked else None)
        self.bg_inferred_radio.toggled.connect(lambda checked: self.on_bg_change("linewise") if checked else None)
        self.bg_inferred_radio.setEnabled(False)
        self.bg_linewise_radio.setEnabled(False)

        # Histogram control group
        self.min_range_set.clicked.connect(lambda: self.on_full_scale("min"))
        self.full_scale_button.clicked.connect(lambda: self.on_full_scale("both"))
        self.max_range_set.clicked.connect(lambda: self.on_full_scale("max"))



        # Associated spectra group
        self.open_spectrum_button.clicked.connect(self.load_spectroscopy_window)

        # I/O group
        self.save_button.clicked.connect(self.on_save)
        self.check_exists_box.clicked.connect(self.on_save)
        self.exit_button.clicked.connect(self.on_exit)
        self.open_folder_button.clicked.connect(lambda: os.startfile(self.output_folder))
    
    def connect_keys(self):
        # File_chan_dir group
        # File toggling
        previous_file_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Left), self)
        previous_file_shortcut.activated.connect(self.on_previous_file)
        select_file_shortcut = QShortcut(QKeySequence(Qt.Key.Key_L), self)
        select_file_shortcut.activated.connect(self.on_file_select)
        next_file_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Right), self)
        next_file_shortcut.activated.connect(self.on_next_file)
        
        # Channel toggling
        previous_channel_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Down), self)
        previous_channel_shortcut.activated.connect(self.on_previous_chan)
        next_channel_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        next_channel_shortcut.activated.connect(self.on_next_chan)

        # Direction
        direction_toggle_shortcut = QShortcut(QKeySequence(Qt.Key.Key_D), self)
        direction_toggle_shortcut.activated.connect(self.on_toggle_direction)



        # Image processing group
        # Background subtraction toggle buttons
        background_none_shortcut = QShortcut(QKeySequence(Qt.Key.Key_N), self)
        background_none_shortcut.activated.connect(lambda: self.on_bg_change("none"))
        background_plane_shortcut = QShortcut(QKeySequence(Qt.Key.Key_P), self)
        background_plane_shortcut.activated.connect(lambda: self.on_bg_change("plane"))
        background_inferred_shortcut = QShortcut(QKeySequence(Qt.Key.Key_I), self)
        background_inferred_shortcut.activated.connect(lambda: self.on_bg_change("inferred"))
        background_linewise_shortcut = QShortcut(QKeySequence(Qt.Key.Key_W), self)
        background_linewise_shortcut.activated.connect(lambda: self.on_bg_change("linewise"))

        # Associated spectra group
        open_spectrum_shortcut = QShortcut(QKeySequence(Qt.Key.Key_O), self)
        open_spectrum_shortcut.activated.connect(self.load_spectroscopy_window)

        # I/O group
        save_file_shortcut = QShortcut(QKeySequence(Qt.Key.Key_S), self)
        save_file_shortcut.activated.connect(self.on_save)
        exit_shortcuts = [QShortcut(QKeySequence(keystroke), self) for keystroke in [Qt.Key.Key_Q, Qt.Key.Key_X, Qt.Key.Key_E, Qt.Key.Key_Escape]]
        [exit_shortcut.activated.connect(self.on_exit) for exit_shortcut in exit_shortcuts]
        output_folder_shortcut = QShortcut(QKeySequence(Qt.Key.Key_T), self)
        output_folder_shortcut.activated.connect(lambda: os.startfile(self.output_folder))

    # Button functions
    def on_previous_file(self):
        self.file_index -= 1
        if self.file_index < 0: self.file_index = self.max_file_index
        self.load_image()

    def on_file_select(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open file", self.folder, "SXM files (*.sxm)")
        if file_name: self.load_folder(file_name)

    def on_next_file(self):
        self.file_index += 1
        if self.file_index > self.max_file_index: self.file_index = 0
        self.load_image()



    def on_toggle_direction(self):
        # Toggle the button's checked state; the toggled handler will update internal state and UI
        try:
            current = self.direction_button.isChecked()
            self.direction_button.setChecked(not current)
        except Exception:
            # fallback: directly toggle scan_direction and update
            self.scan_direction = "backward" if self.scan_direction == "forward" else "forward"
            try:
                if hasattr(self, 'image_files') and not (len(self.image_files) == 0 or (len(self.image_files) == 1 and self.image_files[0] == "")):
                    self.load_image()
            except Exception:
                pass
            self.direction_button.setText(self.scan_direction)

    def on_direction_toggled(self, checked: bool):
        # Update scan_direction based on the checked state and refresh UI
        self.scan_direction = "backward" if checked else "forward"
        # Update the button text to reflect the state
        try:
            self.direction_button.setText("Direction: backward" if checked else "Direction: forward")
        except Exception:
            pass
        # Always reload image to reflect direction change
        self.load_image()

    def on_scale_toggle(self):
        """Set the histogram widget levels to the image statistics min/max."""
        try:
            if not hasattr(self, "hist") or self.hist is None:
                self.statistics_info.setText("No histogram available")
                return
            # Use the computed statistics if available
            if not hasattr(self, "statistics"):
                self.statistics_info.setText("No image statistics available")
                return
            
            lo = float(self.statistics.min)
            hi = float(self.statistics.max)

            # Change the new toggle index
            if self.scale_toggle_index == 0:
                # Toggle index 1 (min to zero) does not work if lo > 0
                if lo < 0: self.scale_toggle_index = 1
                else: self.scale_toggle_index = 2
            elif self.scale_toggle_index == 1:
                # Toggle index 2 (zero to max) does not work if hi < 0
                if hi > 0: self.scale_toggle_index = 2
                else: self.scale_toggle_index = 0
            else: self.scale_toggle_index = 0
            
            match self.scale_toggle_index: # Reset the toggle buttons and set the image histogram levels
                case 0:
                    self.scale_toggle_button.setText("Toggle limits: min - max")
                    self.hist.setLevels(lo, hi)
                case 1:
                    self.scale_toggle_button.setText("Toggle limits: min - 0")
                    self.hist.setLevels(lo, 0)
                case 2:
                    self.scale_toggle_button.setText("Toggle limits: 0 - max")
                    self.hist.setLevels(0, hi)
            
        except:
            pass

    def on_bg_change(self, mode: str):
        if mode in ["none", "plane", "inferred", "linewise"]:
            self.background_subtraction = mode
            if mode == "none": self.bg_none_radio.setChecked(True)
            elif mode == "plane": self.bg_plane_radio.setChecked(True)
            elif mode == "inferred": self.bg_inferred_radio.setChecked(True)
            else: self.bg_linewise_radio.setChecked(True)
            
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
    def load_folder(self, file_name):
        try:
            self.folder = os.path.dirname(file_name) # Set the folder to the directory of the file
            self.sxm_files = np.array([str(file) for file in Path(self.folder).glob("*.sxm")]) # Read all the sxm files
            self.max_file_index = len(self.sxm_files) - 1
            self.file_index = np.where([os.path.samefile(sxm_file, file_name) for sxm_file in self.sxm_files])[0][0]
            self.output_folder = self.folder + "\\" + self.output_folder_name

            if self.file_index > self.max_file_index: self.file_index = 0
            self.sxm_file = self.sxm_files[self.file_index]

            # Read all the spectroscopy files in the same folder and create a list of spectroscopy times
            [self.spec_files, self.spec_times] = spec_times(self.folder)

            self.file_label = os.path.basename(self.sxm_file) # The file label is the file name without the directory path
            # Update folder/contents labels
            try:
                self.folder_name_button.setText(self.folder)
                if self.max_file_index == 0: self.contains_n_files_label.setText(f"which contains 1 sxm file")
                else: self.contains_n_files_label.setText(f"which contains {self.max_file_index + 1} sxm files")
            except Exception as e:
                print(f"Error: {e}")

            if self.max_file_index > -1: self.load_image() # Load the image if there is a file
        except:
            print("Error loading files")
            self.file_label = "Select file"
        
        self.file_select_button.setText(self.file_label)

    def load_image(self):
        self.sxm_file = self.sxm_files[self.file_index]
        self.file_label = os.path.basename(self.sxm_file)
        self.file_select_button.setText(self.file_label) # Make the select file button display the file name

        # Load the scan object using nanonispy2
        self.scan_object = get_scan(self.sxm_file, units = {"length": "nm", "current": "pA"})
        scan_tensor = self.scan_object.scan_tensor
        self.channels = self.scan_object.channels # Load which channels have been recorded
        if self.channel not in self.channels: # If the requested channel does not exist in the scan, default the requested channel to be the first channel in the list of channels
            self.channel = self.channels[0]
        self.channel_index = np.where(self.channels == self.channel)[0][0]
        self.max_channel_index = len(self.channels) - 1

        # Update the channel selection box based on the available channels
        self.channel_box.blockSignals(True)
        self.channel_box.clear()
        self.channel_box.addItems(self.channels)
        self.channel_box.setCurrentIndex(self.channel_index)
        self.channel_box.blockSignals(False)

        # Read the header and save the scan parameters
        self.bias = self.scan_object.bias
        self.scan_range = [round(dimension, 3) for dimension in self.scan_object.scan_range]
        self.feedback = self.scan_object.feedback # Read whether the scan was recorded in STM feedback
        self.setpoint = round(self.scan_object.setpoint, 3)
        self.scan_time = self.scan_object.date_time

        # Display scan data in the app
        if self.feedback:
            self.summary_text = f"STM topographic scan recorded on\n{self.scan_time.strftime('%Y/%m/%d   at   %H:%M:%S')}\n\n(V = {self.bias} V; I_fb = {self.setpoint} pA)\nScan range: {self.scan_range[0]} nm by {self.scan_range[1]} nm"
        else:
            self.summary_text = f"Constant height scan recorded on\n{self.scan_time.strftime('%Y/%m/%d   at   %H:%M:%S')}\n\n(V = {self.bias} V)\nScan range: {self.scan_range[0]} nm by {self.scan_range[1]} nm"
        self.scan_summary_label.setText(self.summary_text)

        # Determine when the next scan was recorded, then calculate which spectra were recorded within the time interval between this scan and the next one
        if self.file_index < self.max_file_index:
            next_sxm_file = self.sxm_files[self.file_index + 1]
            next_scan = get_scan(next_sxm_file)
            next_scan_time = next_scan.date_time
        else:
            next_scan_time = datetime(2999, 12, 31, 23, 59, 59)        
        spectra_in_interval = [self.scan_time < spec_time < next_scan_time for spec_time in self.spec_times]
        self.associated_spectra_indices = np.where(spectra_in_interval)[0]
        self.associated_spectra = np.array([self.spec_files[index] for index in self.associated_spectra_indices])
        
        self.spectra_box.blockSignals(True)
        self.spectra_box.clear()
        self.spectra_box.addItems(self.associated_spectra)
        self.spectra_box.blockSignals(False)



        # Channel / scan direction selection
        # Pick the correct frame out of the scan tensor based on channel and scan direction
        if self.scan_direction == "backward": self.selected_scan = scan_tensor[self.channel_index, 1]
        else: self.selected_scan = scan_tensor[self.channel_index, 0]

        # Determine background subtraction mode from radio buttons and apply it
        mode = self.background_subtraction
        self.processed_scan = background_subtract(self.selected_scan, mode = mode)

        # Update displayed png filename (show basename)
        if self.scan_direction == "backward":
            self.png_file_name = f"Img{self.file_index + 1:03d}_{self.channel}_bwd.png"
        else:
            self.png_file_name = f"Img{self.file_index + 1:03d}_{self.channel}_fwd.png"
        self.png_file_box.setText(os.path.basename(self.png_file_name))
        self.output_folder_box.setText(self.output_folder_name)
        if os.path.exists(self.output_folder + "\\" + self.png_file_name):
            self.check_exists_box.setText("png already exists!")
            self.check_exists_box.setStyleSheet("background-color: orange")
        else:
            self.check_exists_box.setText("ok to save")
            self.check_exists_box.setStyleSheet("background-color: green")

        # Apply matrix operations



        # Calculate the image statistics and display them
        self.statistics = get_image_statistics(self.processed_scan)
        rounded_min = round(self.statistics.min, 3)
        rounded_max = round(self.statistics.max, 3)
        
        self.min_range_box.setText(f"{rounded_min}")
        self.max_range_box.setText(f"{rounded_max}")

        if self.channel == "X" or self.channel == "Y" or self.channel == "Z":
            self.statistics_info.setText(f"\nValue range: {round(self.statistics.range_total, 3)} nm; Mean ± std dev: {round(self.statistics.mean, 3)} ± {round(self.statistics.standard_deviation, 3)} nm")
        elif self.channel == "Current":
            self.statistics_info.setText(f"\nValue range: {round(self.statistics.range_total, 3)} pA; Mean ± std dev: {round(self.statistics.mean, 3)} ± {round(self.statistics.standard_deviation, 3)} pA")
        else:
            self.statistics_info.setText(f"\nValue range: {round(self.statistics.range_total, 3)}; Mean ± std dev: {round(self.statistics.mean, 3)} ± {round(self.statistics.standard_deviation, 3)}")

        # Show the scan
        self.image_view.setImage(self.processed_scan, autoRange = True)  # Show the scan in the app
        image_item = self.image_view.getImageItem()
        image_item.setRect(QtCore.QRectF(0, 0, self.scan_range[1], self.scan_range[0]))  # Add dimensions to the ImageView object
        self.image_view.autoRange()

        # Get the new histogram levels
        self.hist_levels = list(self.hist_item.getLevels())

    def load_spectroscopy_window(self):
        if not hasattr(self, "second_window") or self.second_window is None: # Create only if not already created:
            self.second_window = SpectroscopyWindow(self.processed_scan)
        self.second_window.show()

    # Scale limit functions
    def on_full_scale(self, side: str = "both"):
        (min, max) = self.hist_item.getLevels()
        if side == "min":
            if hasattr(self, "statistics") and hasattr(self.statistics, "min"):
                self.min_selection = 0
                self.hist_item.setLevels(self.statistics.min, max)
        elif side == "max":
            if hasattr(self, "statistics") and hasattr(self.statistics, "max"):
                self.max_selection = 0
                self.hist_item.setLevels(min, self.statistics.max)
        elif side == "both":
            if hasattr(self, "statistics") and hasattr(self.statistics, "min") and hasattr(self.statistics, "max"):
                self.min_selection = 0
                self.max_selection = 0
                self.hist_item.setLevels(self.statistics.min, self.statistics.max)
        
        if self.min_selection == 0: self.min_range_set.setChecked(True)
        if self.max_selection == 0: self.max_range_set.setChecked(True)

    def histogram_scale_changed(self):
        (min, max) = self.hist_item.getLevels()
        if hasattr(self, "hist_levels"):
            [min_old, max_old] = self.hist_levels
            if np.abs(min - min_old) < np.abs(max - max_old):
                self.max_abs_val_box.setText(f"{round(max, 3)}")
                self.max_abs_val_set.setChecked(True)
            else:
                self.min_abs_val_box.setText(f"{round(min, 3)}")
                self.min_abs_val_set.setChecked(True)
        else:
            self.max_abs_val_box.setText(f"{round(max, 3)}")
            self.max_abs_val_set.setChecked(True)
            self.min_abs_val_box.setText(f"{round(min, 3)}")
            self.min_abs_val_set.setChecked(True)
        self.hist_levels = [min, max]



    # Save button
    def on_save(self):
        # Properly rescale to 0-255
        if self.hist is not None:
            min_val, max_val = self.hist.getLevels()
        else:
            min_val, max_val = (self.statistics.min, self.statistics.max)
        denom = max_val - min_val if max_val != min_val else 1
        rescaled_array = (self.processed_scan - min_val) / denom
        rescaled_array = np.clip(rescaled_array, 0, 1)  # Ensure within [0,1]
        uint8_array = (255 * rescaled_array).astype(np.uint8)

        try:
            output_file_name = self.output_folder + "\\" + self.png_file_name
            qimg = QImage(uint8_array, np.shape(uint8_array)[1], np.shape(uint8_array)[0], np.shape(uint8_array)[1], QImage.Format.Format_Grayscale8)
            os.makedirs(self.output_folder, exist_ok = True)
            qimg.save(output_file_name)

            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Success")
            msg_box.setText("png file saved")
            QTimer.singleShot(1000, msg_box.close)
            msg_box.exec()

            self.check_exists_box.setText("png already exists!")
            self.check_exists_box.setStyleSheet("background-color: orange")
        except Exception as e:
            print(e)
            pass

    # Exit button
    def on_exit(self):
        try: # Save the currently opened scan folder to the config yaml file so it opens automatically on startup next time
            with open(self.scanalyzer_folder + "\\config.yml", "w") as file:
                yaml.safe_dump({"last_file": str(self.sxm_file)}, file)
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