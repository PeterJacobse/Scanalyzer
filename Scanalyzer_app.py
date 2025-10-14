import os
import sys
import yaml
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QToolButton, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QFileDialog, QButtonGroup, QComboBox, QRadioButton, QGroupBox, QLineEdit
from PyQt6.QtCore import Qt, QSize, QByteArray
from pathlib import Path
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtWidgets
from PyQt6.QtGui import QImage, QImageWriter
from scanalyzer.image_functions import get_scan, image_gradient, background_subtract, get_image_statistics
from datetime import datetime



class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scanalyzer by Peter H. Jacobse") # Make the app window
        self.setGeometry(100, 100, 1200, 800) # x, y, width, height

        # Add ImageView
        pg.setConfigOptions(imageAxisOrder = "row-major")
        self.image_view = pg.ImageView(view = pg.PlotItem())
        self.script_path = os.path.abspath(__file__) # The full path of Scanalyzer.py
        self.script_folder = os.path.dirname(self.script_path) # The parent directory of Scanalyzer.py
        self.scanalyzer_folder = self.script_folder + "\\scanalyzer" # The directory of the scanalyzer package
        self.folder = self.scanalyzer_folder
        self.output_folder_name = "Extracted Files"
        self.output_folder = self.folder + "\\" + self.output_folder_name

        # Initialize default parameters
        self.image_files = [""]
        self.file_index = 0
        self.max_file_index = 0
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
        
        # Set the central widget of the QMainWindow
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # draw buttons and right-column layout
        right_column = self.draw_buttons()

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



    def draw_buttons(self):
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

        # Direction toggle button (above the other buttons) - show 'forward'/'backward' text
        self.direction_button = QPushButton()
        self.direction_button.setCheckable(True)
        # checked == True -> backward, checked == False -> forward
        self.direction_button.setChecked(self.scan_direction == "backward")
        # initialize text
        self.direction_button.setText("backward" if self.direction_button.isChecked() else "forward")
        # use toggled signal to update state and UI
        self.direction_button.toggled.connect(self.on_direction_toggled)

        # Background subtraction radio buttons (none, plane, inferred)
        self.bg_none_radio = QRadioButton("None")
        self.bg_plane_radio = QRadioButton("Plane")
        self.bg_inferred_radio = QRadioButton("Inferred")

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
        button_layout.setContentsMargins(8, 8, 8, 8)

        # Scan summary
        scan_summary_group = QGroupBox("Scan summary")
        summary_vbox = QVBoxLayout()
        self.metadata_label = QLabel("Hi")
        self.metadata_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        summary_vbox.addWidget(self.metadata_label)
        scan_summary_group.setLayout(summary_vbox)
        button_layout.addWidget(scan_summary_group)

        # Regroup File, Channel, and Direction into one group box
        file_chan_dir_group = QGroupBox("File / Channel / Direction")
        fcd_vbox = QVBoxLayout()

        # File navigation
        file_nav_hbox = QHBoxLayout()
        file_nav_hbox.addWidget(self.previous_file_button)
        file_nav_hbox.addWidget(self.file_select_button)
        file_nav_hbox.addWidget(self.next_file_button)
        file_selected_label = QLabel("File Selected:")
        file_selected_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fcd_vbox.addWidget(file_selected_label)
        fcd_vbox.addLayout(file_nav_hbox)
        in_folder_label = QLabel("in folder")
        in_folder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fcd_vbox.addWidget(in_folder_label)
        self.folder_name_label = QLabel(self.folder)
        self.folder_name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fcd_vbox.addWidget(self.folder_name_label)
        if self.max_file_index == 0: self.contains_n_files_label = QLabel(f"which contains 1 sxm file")
        else: self.contains_n_files_label = QLabel(f"which contains {self.max_file_index + 1} sxm files")
        self.contains_n_files_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fcd_vbox.addWidget(self.contains_n_files_label)
        channel_selected_box = QLabel("Channel selected:")
        channel_selected_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        fcd_vbox.addWidget(channel_selected_box)

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

        # Histogram control group: put the statistics/info label here
        hist_group = QGroupBox("Histogram control")
        hist_vbox = QVBoxLayout()
        self.info_label = QLabel("Statistics")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hist_vbox.addWidget(self.info_label)

        # Full scale button: set histogram levels to the image statistics min/max
        self.full_scale_button = QPushButton("Full scale")
        self.full_scale_button.clicked.connect(self.on_full_scale)
        hist_vbox.addWidget(self.full_scale_button)

        # Tie min/max buttons
        tie_hbox = QHBoxLayout()
        self.tie_min_zero_button = QPushButton("Tie min to 0")
        self.tie_min_zero_button.clicked.connect(self.on_tie_min_zero)
        self.tie_max_zero_button = QPushButton("Tie max to 0")
        self.tie_max_zero_button.clicked.connect(self.on_tie_max_zero)
        tie_hbox.addWidget(self.tie_min_zero_button)
        tie_hbox.addWidget(self.tie_max_zero_button)
        hist_vbox.addLayout(tie_hbox)
        hist_group.setLayout(hist_vbox)
        button_layout.addWidget(hist_group)

        # I/O group: Save and Exit rows
        io_group = QGroupBox("I/O")
        io_box = QGridLayout()
        io_box.setColumnStretch(0, 1)
        io_box.setColumnStretch(1, 1)

        # Save row: save button + png filename label
        self.save_button.setText("Save image as")
        self.png_file_box = QLineEdit()
        self.png_file_box.setAlignment(Qt.AlignmentFlag.AlignLeft)
        in_output_folder_label = QLabel("in output folder")
        in_output_folder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.output_folder_box = QLineEdit()
        self.check_exists_box = QPushButton()
        #self.check_exists_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.check_exists_box.clicked.connect(self.on_save)

        io_box.addWidget(self.save_button, 0, 0)
        io_box.addWidget(self.png_file_box, 0, 1)
        io_box.addWidget(in_output_folder_label, 1, 0)
        io_box.addWidget(self.output_folder_box, 1, 1)
        io_box.addWidget(self.check_exists_box, 2, 0)
        io_box.addWidget(self.exit_button, 2, 1)        

        io_group.setLayout(io_box)
        button_layout.addWidget(io_group)

        # Add a stretch at the end to push buttons up
        button_layout.addStretch(1)



        right_column = QVBoxLayout()
        #right_column.addWidget(scan_summary_group)
        right_column.addLayout(button_layout)

        # Populate initial metadata text
        self.metadata_label.setText("Scanalyzer by Peter H. Jacobse")

        return right_column

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
        if key == Qt.Key.Key_D:
            # toggle the pushbutton state so the UI and internal state stay in sync
            try:
                current = self.direction_button.isChecked()
                self.direction_button.setChecked(not current)
            except Exception:
                # fallback
                self.on_toggle_direction()
        # Background subtraction shortcuts: P -> plane, I -> inferred, N -> none
        if key == Qt.Key.Key_N:
            self.bg_none_radio.setChecked(True)
            self.on_bg_change("none")
        if key == Qt.Key.Key_P:
            self.bg_plane_radio.setChecked(True)
            self.on_bg_change("plane")
        if key == Qt.Key.Key_I:
            self.bg_inferred_radio.setChecked(True)
            self.on_bg_change("inferred")
        if key == Qt.Key.Key_Q or key == Qt.Key.Key_X or key == Qt.Key.Key_E or key == Qt.Key.Key_Escape: self.on_exit()
        super().keyPressEvent(event)



    # Button functions
    def on_previous_file(self):
        self.file_index -= 1
        if self.file_index < 0: self.file_index = self.max_file_index
        self.load_image()

    def on_file_select(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open file", "", "SXM files (*.sxm)")
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
            self.direction_button.setText("backward" if checked else "forward")
        except Exception:
            pass
        # Always reload image to reflect direction change
        self.load_image()

    def on_full_scale(self):
        """Set the histogram widget levels to the image statistics min/max."""
        try:
            if not hasattr(self, 'hist') or self.hist is None:
                self.info_label.setText("No histogram available")
                return
            # Use the computed statistics if available
            if hasattr(self, 'statistics'):
                lo = float(self.statistics.min)
                hi = float(self.statistics.max)
            else:
                # fallback: try query image min/max
                arr = getattr(self, 'processed_scan', None) or getattr(self, 'selected_scan', None)
                if arr is None:
                    self.info_label.setText("No image to compute full scale")
                    return
                import numpy as _np
                lo = float(_np.nanmin(arr))
                hi = float(_np.nanmax(arr))
            # Avoid degenerate levels
            if hi - lo == 0:
                hi = lo + 1.0
            try:
                self.hist.setLevels(lo, hi)
            except:
                pass
        except:
            pass

    def on_tie_min_zero(self):
        """Set the histogram min level to 0, keep current max (or statistics.max)."""
        try:
            if not hasattr(self, 'hist') or self.hist is None:
                self.info_label.setText("No histogram available")
                return
            cur_min, cur_max = self.hist.getLevels() if self.hist is not None else (None, None)
            # determine current max fallback
            if cur_max is None and hasattr(self, 'statistics'):
                cur_max = float(self.statistics.max)
            if cur_max is None:
                arr = getattr(self, 'processed_scan', None) or getattr(self, 'selected_scan', None)
                if arr is None:
                    self.info_label.setText("No image to compute levels")
                    return
                import numpy as _np
                cur_max = float(_np.nanmax(arr))
            # set min to 0
            try:
                self.hist.setLevels(0.0, float(cur_max))
            except:
                pass
        except:
            pass

    def on_tie_max_zero(self):
        """Set the histogram max level to 0, keep current min (or statistics.min)."""
        try:
            if not hasattr(self, 'hist') or self.hist is None:
                self.info_label.setText("No histogram available")
                return
            cur_min, cur_max = self.hist.getLevels() if self.hist is not None else (None, None)
            # determine current min fallback
            if cur_min is None and hasattr(self, 'statistics'):
                cur_min = float(self.statistics.min)
            if cur_min is None:
                arr = getattr(self, 'processed_scan', None) or getattr(self, 'selected_scan', None)
                if arr is None:
                    self.info_label.setText("No image to compute levels")
                    return
                import numpy as _np
                cur_min = float(_np.nanmin(arr))
            # set max to 0
            try:
                self.hist.setLevels(float(cur_min), 0.0)
            except:
                pass
        except:
            pass

    def on_bg_change(self, mode: str):
        self.background_subtraction = mode
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

            self.file_label = os.path.basename(self.sxm_file) # The file label is the file name without the directory path
            # Update folder/contents labels
            try:
                self.folder_name_label.setText(self.folder)
                if self.max_file_index == 0: self.contains_n_files_label.setText(f"which contains 1 sxm file")
                else: self.contains_n_files_label.setText(f"which contains {self.max_file_index + 1} sxm files")
            except Exception:
                pass

            self.load_image()
        except:
            print("Error loading files")
            self.file_label = "Select file"
        
        self.file_select_button.setText(self.file_label)

    def load_image(self):
        self.sxm_file = self.sxm_files[self.file_index]
        self.file_label = os.path.basename(self.sxm_file)
        self.file_select_button.setText(self.file_label) # Make the select file button display the file name

        # Load the scan object using nanonispy
        self.scan_object = get_scan(self.sxm_file)
        scan_tensor = self.scan_object.scan_tensor_nm_pA # Use self.scan_object.scan_tensor if no reunitization to nm and pA is desired
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
        self.scan_range = self.scan_object.scan_range_nm
        self.feedback = self.scan_object.feedback
        self.setpoint = self.scan_object.setpoint_pA
        self.dt_object = self.scan_object.date_time

        # Display scan data in the app
        if self.feedback:
            self.summary_text = f"STM topographic scan recorded on\n{self.dt_object.strftime('%Y/%m/%d   at   %H:%M:%S')}\n\n(V = {self.bias} V; I_fb = {self.setpoint} pA)\nScan range: {self.scan_range[0]} nm by {self.scan_range[1]} nm"
        else:
            self.summary_text = f"Constant height scan recorded on\n{self.dt_object.strftime('%Y/%m/%d   at   %H:%M:%S')}\n\n(V = {self.bias} V)\nScan range: {self.scan_range[0]} nm by {self.scan_range[1]} nm"
        self.metadata_label.setText(self.summary_text)



        # Channel / scan direction selection
        # Pick the correct frame out of the scan tensor based on channel and scan direction
        if self.scan_direction == "backward": self.selected_scan = scan_tensor[self.channel_index, 1]
        else: self.selected_scan = scan_tensor[self.channel_index, 0]

        # Determine background subtraction mode from radio buttons
        """
        if self.bg_none_radio.isChecked():
            mode = "none"
        elif self.bg_plane_radio.isChecked():
            mode = "plane"
        elif self.bg_inferred_radio.isChecked():
            mode = "inferred"
        else:
            mode = self.background_subtraction  # fallback
        """
        mode = self.background_subtraction
        self.processed_scan = background_subtract(self.selected_scan, mode = mode)

        if self.scan_direction == "backward":
            self.png_file_name = f"Img{self.file_index + 1:03d}_{self.channel}_bwd.png"
        else:
            self.png_file_name = f"Img{self.file_index + 1:03d}_{self.channel}_fwd.png"

        # Update displayed png filename (show basename)
        self.png_file_box.setText(os.path.basename(self.png_file_name))
        self.output_folder_box.setText(self.output_folder_name)
        if os.path.exists(self.output_folder + "\\" + self.png_file_name):
            self.check_exists_box.setText("png already exists!")
            self.check_exists_box.setStyleSheet("background-color: orange")
        else:
            self.check_exists_box.setText("ok to save")
            self.check_exists_box.setStyleSheet("background-color: green")

        # Calculate the image statistics
        self.statistics = get_image_statistics(self.processed_scan)
        if self.channel == "X" or self.channel == "Y" or self.channel == "Z":
            self.info_label.setText(f"range of values:\n({round(self.statistics.min, 3)} to {round(self.statistics.max, 3)}) nm\nmean ± std dev: {round(self.statistics.mean, 3)} ± {round(self.statistics.standard_deviation, 3)} nm")
        elif self.channel == "Current":
            self.info_label.setText(f"range of values:\n({round(self.statistics.min, 3)} to {round(self.statistics.max, 3)}) pA\nmean ± std dev: {round(self.statistics.mean, 3)} ± {round(self.statistics.standard_deviation, 3)} pA")
        else:
            self.info_label.setText(f"range of values:\n({round(self.statistics.min, 3)} to {round(self.statistics.max, 3)})\nmean ± std dev: {round(self.statistics.mean, 3)} ± {round(self.statistics.standard_deviation, 3)}")

        # Show the scan        
        self.image_view.setImage(self.processed_scan, autoRange=True)  # Show the scan in the app
        image_item = self.image_view.getImageItem()
        image_item.setRect(QtCore.QRectF(0, 0, self.scan_range[0], self.scan_range[1]))  # Add dimensions to the ImageView object
        self.image_view.autoRange()
        # Get the histogram LUT
        self.hist = self.image_view.getHistogramWidget()

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
            self.check_exists_box.setText("png already exists!")
            self.check_exists_box.setStyleSheet("background-color: orange")

            # writer = QImageWriter(output_file_name, b"png")
            # writer.setText(str(self.summary_text), "Metadata")
            #if writer.write(qimg):
            #    print("Done adding metadata")
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