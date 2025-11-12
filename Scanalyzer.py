import os
import sys
import yaml
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QToolButton, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QFileDialog,
    QButtonGroup, QComboBox, QRadioButton, QGroupBox, QLineEdit, QFrame, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore
from PyQt6.QtGui import QImage, QDragEnterEvent, QDropEvent, QDragMoveEvent, QShortcut, QKeySequence
from scanalyzer.image_functions import apply_gaussian, apply_fft, image_gradient, compute_normal, apply_laplace, complex_image_to_colors, background_subtract, get_image_statistics
from scanalyzer.file_functions import read_files, get_scan, get_spectrum
from datetime import datetime



class SpectroscopyWindow(QMainWindow):
    def __init__(self, processed_scan, spec_files, associated_spectra):
        super().__init__()
        self.setWindowTitle("Spectrum viewer")
        self.setGeometry(200, 200, 900, 600)
        self.spec_files = spec_files # Make the spectroscopy file list an attribute of the SpectroscopyWindow class
        self.associated_spectra = associated_spectra
        
        # Spectrum colors
        self.color_list = ["#FFFFFF", "#FFFF00", "#FF90FF", "#00FFFF", "#00FF00", "#A0A0A0", "#FF4040", "#4040FF", "#FFA500", "#9000FF", "#808000", "#008080", "#800080", "#008000", "#A00000", "#0000A0"]
        
        self.draw_layout()
        self.connect_buttons()
        self.connect_keys()
        self.read_spectroscopy_files()
        # Switch on spectra
        for i in range(min(len(self.associated_spectra), len(self.qbox))): self.checkbox[i].setChecked(True)

    def draw_layout(self, toggle_checbox = None):
        # Set the central widget of the QMainWindow
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QGridLayout(central_widget)

        # Spectrum selector
        spectrum_selector_widget = QWidget()
        spectrum_selector_layout = QGridLayout()
        self.checkbox = [QCheckBox(f"({i})") for i in range(10)]
        self.leftarrows = [QToolButton() for _ in range(10)]
        [leftarrow.setArrowType(Qt.ArrowType.LeftArrow) for leftarrow in self.leftarrows]
        [leftarrow.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly) for leftarrow in self.leftarrows]
        self.qbox = [QComboBox() for _ in range(10)]
        self.rightarrows = [QToolButton() for _ in range(10)]
        [rightarrow.setArrowType(Qt.ArrowType.RightArrow) for rightarrow in self.rightarrows]
        [rightarrow.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly) for rightarrow in self.rightarrows]
        [arrow.setEnabled(False) for arrow in self.leftarrows]
        [arrow.setEnabled(False) for arrow in self.rightarrows]
        
        # Put a little star on the spectrum names that are associated with the scan
        spec_labels = self.spec_files[:, 0]
        for i in range(len(spec_labels)):
            if spec_labels[i] in self.associated_spectra: spec_labels[i] = spec_labels[i] + "*"
        [self.qbox[i].setStyleSheet("QComboBox { color: " + self.color_list[i] + "; }") for i in range(len(self.qbox))]
        [box.addItems(self.spec_files[:, 0]) for box in self.qbox]

        # Initialize the comboboxes to the associated spectra if possible
        for combobox_no in range(len(self.qbox)):
            try:
                if combobox_no < len(self.associated_spectra):
                    associated_index = np.where(self.spec_files[:, 0] == self.associated_spectra[combobox_no])
                    self.qbox[combobox_no].setCurrentIndex(associated_index)
                else:
                    if combobox_no < len(self.spec_files):
                        self.qbox[combobox_no].setCurrentIndex(combobox_no)
                    else:
                        pass
            except:
                pass

        [spectrum_selector_layout.addWidget(self.checkbox[i], i, 0) for i in range(len(self.checkbox))]
        [spectrum_selector_layout.addWidget(self.leftarrows[i], i, 1) for i in range(len(self.leftarrows))]
        [spectrum_selector_layout.addWidget(self.qbox[i], i, 2) for i in range(len(self.qbox))]
        [spectrum_selector_layout.addWidget(self.rightarrows[i], i, 3) for i in range(len(self.qbox))]
        spectrum_selector_widget.setLayout(spectrum_selector_layout)
    


        # Main widgets
        main_layout.addWidget(spectrum_selector_widget, 1, 0, 2, 1) # Spectrum selector buttons
        [self.x_channel_box, self.graph_0_widget, self.graph_1_widget] = column_1_widgets = [QComboBox(), pg.PlotWidget(), pg.PlotWidget()]
        [self.exit_button, self.y_channel_0_box, self.y_channel_1_box] = column_2_widgets = [QPushButton("Exit Spectrum viewer"), QComboBox(), QComboBox()]
        self.graph_0 = self.graph_0_widget.getPlotItem() # Get the plotitems corresponding to the plot widgets
        self.graph_1 = self.graph_1_widget.getPlotItem()
        self.x_channel_box.setFixedWidth(500)

        [main_layout.addWidget(column_1_widgets[i], i, 1, alignment = Qt.AlignmentFlag.AlignCenter) for i in range(len(column_1_widgets))]
        [main_layout.addWidget(column_2_widgets[i], i, 2, alignment = Qt.AlignmentFlag.AlignCenter) for i in range(len(column_2_widgets))]

    def connect_buttons(self):
        self.exit_button.clicked.connect(self.close) # Connect to the window's close method

        # Connect all the combobox and checkbox changes to spectrum redrawing
        self.x_channel_box.currentIndexChanged.connect(self.redraw_spectra)
        self.y_channel_0_box.currentIndexChanged.connect(self.redraw_spectra)
        self.y_channel_1_box.currentIndexChanged.connect(self.redraw_spectra)
        [checkbox.clicked.connect(self.redraw_spectra) for checkbox in self.checkbox]
        [combobox.currentIndexChanged.connect(self.redraw_spectra) for combobox in self.qbox]

    def connect_keys(self):
        checkbox_shortcuts = [QShortcut(QKeySequence(keystroke), self) for keystroke in [Qt.Key.Key_0, Qt.Key.Key_1, Qt.Key.Key_2, Qt.Key.Key_3, Qt.Key.Key_4, Qt.Key.Key_5, Qt.Key.Key_6, Qt.Key.Key_7, Qt.Key.Key_8, Qt.Key.Key_9]]
        [checkbox_shortcuts[i].activated.connect(lambda: self.redraw_spectra(toggle_checkbox = i)) for i in range(len(checkbox_shortcuts))]
        
        exit_shortcuts = [QShortcut(QKeySequence(keystroke), self) for keystroke in [Qt.Key.Key_Q, Qt.Key.Key_X, Qt.Key.Key_E, Qt.Key.Key_Escape]]
        [exit_shortcut.activated.connect(self.close) for exit_shortcut in exit_shortcuts]

    def read_spectroscopy_files(self):
        self.spec_objects = [get_spectrum(spec_file[1]) for spec_file in self.spec_files] # Get a spectroscopy object for each spectroscopy file
        all_channels = [] # Find all the channels recorded during all the spectroscopies and combine them into a list called all_channels
        for spec_object in self.spec_objects:
            all_channels.extend(list(spec_object.channels))
        all_channels = list(set(all_channels))
        all_channels = [str(channel) for channel in all_channels]
        [combobox.addItems(all_channels) for combobox in [self.x_channel_box, self.y_channel_0_box, self.y_channel_1_box]]
        # Set the channel toggle boxes to logical values
        try:
            if "Bias calc (V)" in all_channels:
                channel_index = np.where(all_channels == "Bias calc (V)")[0][0]
                self.x_channel_box.setCurrentIndex(channel_index)
            elif "Bias (V)" in all_channels:
                channel_index = np.where(all_channels == "Bias (V)")[0][0]
                self.x_channel_box.setCurrentIndex(channel_index)
            
            if "Current (A)" in all_channels:
                channel_index = np.where(all_channels == "Current (A)")[0][0]
                self.y_channel_1_box.setCurrentIndex(channel_index)
        except:
            pass
                
        self.channels = all_channels

    def redraw_spectra(self, toggle_checkbox = None):
        if type(toggle_checkbox) == int:
            if -1 < toggle_checkbox < 10:
                #self.checkbox[toggle_checkbox].disconnect()
                self.checkbox[toggle_checkbox].setChecked(not self.checkbox[toggle_checkbox].isChecked())
                # self.checkbox[toggle_checkbox].toggled.connect(self.redraw_spectra)

        # Read the QComboboxes and retrieve what channels are requested
        if not hasattr(self, "channels"): return # Return if the channels have not yet been read
        [x_index, y_0_index, y_1_index] = [self.x_channel_box.currentIndex(), self.y_channel_0_box.currentIndex(), self.y_channel_1_box.currentIndex()]
        [x_channel, y_0_channel, y_1_channel] = [self.channels[index] for index in [x_index, y_0_index, y_1_index]]

        # self.graph_0 = self.graph_0_widget.getPlotItem()
        # self.graph_1 = self.graph_1_widget.getPlotItem()
        
        #self.spec_objects[self]
        x_data = np.linspace(-2, 2, 20)
        y_data = np.random.rand(len(x_data))

        [graph.clear() for graph in [self.graph_0, self.graph_1]]
        
        for i in range(len(self.checkbox) - 1, -1, -1):
            color = self.color_list[i]

            if self.checkbox[i].isChecked():
                spec_index = self.qbox[i].currentIndex()
                spec_object = self.spec_objects[spec_index]
                spec_signal = spec_object.signals
                
                try:
                    x_data = spec_signal[x_channel]
                    y_0_data = spec_signal[y_0_channel]
                    self.graph_0.plot(x_data, y_0_data, pen = color)
                except KeyError:
                    pass
                try:
                    x_data = spec_signal[x_channel]
                    y_1_data = spec_signal[y_1_channel]
                    self.graph_1.plot(x_data, y_1_data, pen = color)
                except KeyError:
                    pass



class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scanalyzer by Peter H. Jacobse") # Make the app window
        self.setGeometry(100, 100, 1400, 800) # x, y, width, height

        # Add ImageView
        pg.setConfigOptions(imageAxisOrder = "row-major", antialias = True)
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
                self.on_full_scale("both")
        except:  # Display the dummy scan
            self.folder = self.scanalyzer_folder
            self.sxm_file = [self.scanalyzer_folder + "dummy_scan.sxm", "dummy_scan.sxm", 0, 0]
            self.load_folder(self.sxm_file)
            self.on_full_scale("both")



    def parameters_init(self): # Initialize default parameters
        # I/O paths
        self.script_path = os.path.abspath(__file__) # The full path of Scanalyzer.py
        self.script_folder = os.path.dirname(self.script_path) # The parent directory of Scanalyzer.py
        self.scanalyzer_folder = self.script_folder + "\\scanalyzer" # The directory of the Scanalyzer package
        self.folder = self.scanalyzer_folder # Set current folder to Scanalyzer folder
        self.output_folder_name = "Extracted Files" # Set output folder for saving images
        self.output_folder = self.folder + "\\" + self.output_folder_name
        
        self.sxm_files = np.array([[]])
        self.spec_files = np.array([[]])
        self.image_files = [""]
        self.file_index = 0
        self.max_file_index = -1
        self.selected_file = ""
        self.file_label = "Select file"
        self.png_file_name = ""
        self.channels = []
        self.channel = ""
        self.channel_index = 0
        self.max_channel_index = 0
        self.scan_direction = "forward"
        self.background_subtraction = "none"
        self.scale_toggle_index = 0

        self.min_range_selection = 0
        self.max_range_selection = 0
        self.min_percentile = 2
        self.max_percentile = 98
        self.min_std_dev = 2
        self.max_std_dev = 2
        self.min_selection = 0
        self.max_selection = 0

        self.apply_sobel = False
        self.apply_gaussian = False
        self.apply_laplace = False
        self.apply_fft = False
        self.apply_normal = False

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
            in_folder_label = QLabel("in folder (click or \"1\" opens in explorer)")
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
            self.direction_button.setText("direXion: backward" if self.direction_button.isChecked() else "direXion: forward")

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
            [self.bg_none_radio, self.bg_plane_radio, self.bg_inferred_radio, self.bg_linewise_radio] = background_buttons = [QRadioButton("none (0)"), QRadioButton("Plane"), QRadioButton("Inferred"), QRadioButton("lineWise")]
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
            [self.sobel_button, self.normal_button, self.laplace_button, self.gauss_button, self.fft_button, self.project_complex_box] = matrix_buttons = [QCheckBox("soBel (d/dx + i d/dy)"), QCheckBox("Normal_z"), QCheckBox("laplaCe (∇2)"), QCheckBox("Gaussian"), QCheckBox("Fft"), QComboBox()]
            #self.derivative_button_group = QButtonGroup(self)
            #[self.derivative_button_group.addButton(button) for button in [self.sobel_button, self.normal_button, self.laplace_button]]
            self.project_complex_box.addItems(["re", "im", "abs", "arg (b/w)", "arg (hue)", "complex", "abs^2", "log(abs)"])

            gaussian_width_label = QLabel("width (nm):")
            gaussian_width_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.gaussian_width_box = QLineEdit("1")
            show_label = QLabel("sHow:")
            show_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

            matrix_layout.addWidget(self.sobel_button, 0, 0)
            matrix_layout.addWidget(self.normal_button, 0, 1)
            matrix_layout.addWidget(self.laplace_button, 0, 2)
            matrix_layout.addWidget(self.gauss_button, 1, 0)
            matrix_layout.addWidget(gaussian_width_label, 1, 1)
            matrix_layout.addWidget(self.gaussian_width_box, 1, 2)
            matrix_layout.addWidget(self.fft_button, 2, 0)
            matrix_layout.addWidget(show_label, 2, 1)
            matrix_layout.addWidget(self.project_complex_box, 2, 2)

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

            [self.min_percentile_box, self.min_percentile_set, self.set_percentile_button, self.max_percentile_set, self.max_percentile_box] = percentile_boxes = [QLineEdit(), QRadioButton(), QPushButton("by peRcentiles"), QRadioButton(), QLineEdit()]
            self.min_percentile_box.setText(str(self.min_percentile))
            self.max_percentile_box.setText(str(self.max_percentile))

            [self.min_std_dev_box, self.min_std_dev_set, self.set_std_dev_button, self.max_std_dev_set, self.max_std_dev_box] = std_dev_boxes = [QLineEdit(), QRadioButton(), QPushButton("by standard Deviations"), QRadioButton(), QLineEdit()]
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
            (self.save_button, self.exit_button, self.open_folder_button) = (QPushButton("Save image"), QPushButton("Exit Scanalyzer (E/Q/Esc)"), QPushButton("open ouTput folder"))
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
        self.bg_linewise_radio.toggled.connect(lambda checked: self.on_bg_change("linewise") if checked else None)
        self.bg_inferred_radio.setEnabled(False)

        # Matrix operations
        self.sobel_button.clicked.connect(lambda checked: self.toggle_matrix_processing("sobel", checked))
        self.normal_button.clicked.connect(lambda checked: self.toggle_matrix_processing("normal", checked))
        self.gauss_button.clicked.connect(lambda checked: self.toggle_matrix_processing("gaussian", checked))
        self.gaussian_width_box.editingFinished.connect(lambda: self.toggle_matrix_processing("sobel", self.sobel_button.isChecked()))
        self.laplace_button.clicked.connect(lambda checked: self.toggle_matrix_processing("laplace", checked))
        self.fft_button.clicked.connect(lambda checked: self.toggle_matrix_processing("fft", checked))
        self.project_complex_box.currentTextChanged.connect(lambda: self.toggle_matrix_processing("sobel", self.sobel_button.isChecked()))

        # Limits control group
        self.min_range_set.clicked.connect(lambda: self.on_full_scale("min"))
        self.full_scale_button.clicked.connect(lambda: self.on_full_scale("both"))
        self.max_range_set.clicked.connect(lambda: self.on_full_scale("max"))

        self.min_percentile_box.editingFinished.connect(lambda: self.on_percentiles("min"))
        self.min_percentile_set.clicked.connect(lambda: self.on_percentiles("min"))
        self.set_percentile_button.clicked.connect(lambda: self.on_percentiles("both"))
        self.max_percentile_set.clicked.connect(lambda: self.on_percentiles("max"))
        self.max_percentile_box.editingFinished.connect(lambda: self.on_percentiles("max"))
        
        self.min_std_dev_box.editingFinished.connect(lambda: self.on_standard_deviations("min"))
        self.min_std_dev_set.clicked.connect(lambda: self.on_standard_deviations("min"))
        self.set_std_dev_button.clicked.connect(lambda: self.on_standard_deviations("both"))
        self.max_std_dev_set.clicked.connect(lambda: self.on_standard_deviations("max"))
        self.max_std_dev_box.editingFinished.connect(lambda: self.on_standard_deviations("max"))
        
        self.min_abs_val_box.editingFinished.connect(lambda: self.on_absolute_values("min"))
        self.min_abs_val_set.clicked.connect(lambda: self.on_absolute_values("min"))
        self.set_abs_val_button.clicked.connect(lambda: self.on_absolute_values("both"))
        self.max_abs_val_set.clicked.connect(lambda: self.on_absolute_values("max"))
        self.max_abs_val_box.editingFinished.connect(lambda: self.on_absolute_values("max"))



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

        # Open folder in file explorer
        open_folder_shortcut = QShortcut(QKeySequence(Qt.Key.Key_1), self)
        open_folder_shortcut.activated.connect(lambda: os.startfile(self.folder))
        
        # Channel toggling
        previous_channel_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Down), self)
        previous_channel_shortcut.activated.connect(self.on_previous_chan)
        next_channel_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Up), self)
        next_channel_shortcut.activated.connect(self.on_next_chan)

        # Direction
        direction_toggle_shortcut = QShortcut(QKeySequence(Qt.Key.Key_X), self)
        direction_toggle_shortcut.activated.connect(self.on_toggle_direction)



        # Image processing group
        # Background subtraction toggle buttons
        background_none_shortcut = QShortcut(QKeySequence(Qt.Key.Key_0), self)
        background_none_shortcut.activated.connect(lambda: self.on_bg_change("none"))
        background_plane_shortcut = QShortcut(QKeySequence(Qt.Key.Key_P), self)
        background_plane_shortcut.activated.connect(lambda: self.on_bg_change("plane"))
        background_inferred_shortcut = QShortcut(QKeySequence(Qt.Key.Key_I), self)
        background_inferred_shortcut.activated.connect(lambda: self.on_bg_change("inferred"))
        background_linewise_shortcut = QShortcut(QKeySequence(Qt.Key.Key_W), self)
        background_linewise_shortcut.activated.connect(lambda: self.on_bg_change("linewise"))

        # Matrix operations
        sobel_shortcut = QShortcut(QKeySequence(Qt.Key.Key_B), self)
        sobel_shortcut.activated.connect(lambda: self.toggle_matrix_processing("sobel", not self.sobel_button.isChecked()))
        normal_shortcut = QShortcut(QKeySequence(Qt.Key.Key_N), self)
        normal_shortcut.activated.connect(lambda: self.toggle_matrix_processing("normal", not self.normal_button.isChecked()))
        gauss_shortcut = QShortcut(QKeySequence(Qt.Key.Key_G), self)
        gauss_shortcut.activated.connect(lambda: self.toggle_matrix_processing("gaussian", not self.gauss_button.isChecked()))
        laplace_shortcut = QShortcut(QKeySequence(Qt.Key.Key_C), self)
        laplace_shortcut.activated.connect(lambda: self.toggle_matrix_processing("laplace", not self.laplace_button.isChecked()))
        fft_shortcut = QShortcut(QKeySequence(Qt.Key.Key_F), self)
        fft_shortcut.activated.connect(lambda: self.toggle_matrix_processing("fft", not self.fft_button.isChecked()))
        toggle_projections_shortcut = QShortcut(QKeySequence(Qt.Key.Key_H), self)
        toggle_projections_shortcut.activated.connect(self.toggle_projections)

        # Limits control group
        full_scale_shortcut = QShortcut(QKeySequence(Qt.Key.Key_U), self)
        full_scale_shortcut.activated.connect(lambda: self.on_full_scale("both"))
        percentile_shortcut = QShortcut(QKeySequence(Qt.Key.Key_R), self)
        percentile_shortcut.activated.connect(lambda: self.on_percentiles("both"))
        std_dev_shortcut = QShortcut(QKeySequence(Qt.Key.Key_D), self)
        std_dev_shortcut.activated.connect(lambda: self.on_standard_deviations("both"))
        abs_val_shortcut = QShortcut(QKeySequence(Qt.Key.Key_A), self)
        abs_val_shortcut.activated.connect(lambda: self.on_absolute_values("both"))

        toggle_min_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Minus), self)
        toggle_min_shortcut.activated.connect(lambda: self.toggle_limits("min"))
        toggle_max_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Equal), self)
        toggle_max_shortcut.activated.connect(lambda: self.toggle_limits("max"))

        # Associated spectra group
        open_spectrum_shortcut = QShortcut(QKeySequence(Qt.Key.Key_O), self)
        open_spectrum_shortcut.activated.connect(self.load_spectroscopy_window)

        # I/O group
        save_file_shortcut = QShortcut(QKeySequence(Qt.Key.Key_S), self)
        save_file_shortcut.activated.connect(self.on_save)
        exit_shortcuts = [QShortcut(QKeySequence(keystroke), self) for keystroke in [Qt.Key.Key_Q, Qt.Key.Key_E, Qt.Key.Key_Escape]]
        [exit_shortcut.activated.connect(self.on_exit) for exit_shortcut in exit_shortcuts]
        output_folder_shortcut = QShortcut(QKeySequence(Qt.Key.Key_T), self)
        output_folder_shortcut.activated.connect(lambda: os.startfile(self.output_folder))

    # Button functions
    def on_previous_file(self):
        self.file_index -= 1
        if self.file_index < 0: self.file_index = self.max_file_index
        if hasattr(self, "hist_item"): self.hist_item.sigLevelChangeFinished.disconnect(self.histogram_scale_changed)

        # Update
        self.current_scan = self.load_scan()
        processed_scan = self.process_scan(self.current_scan)
        self.display(processed_scan)
        if hasattr(self, "hist_item"): self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)

    def on_file_select(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open file", self.folder, "SXM files (*.sxm)")
        if file_name: self.load_folder(file_name)

    def on_next_file(self):
        self.file_index += 1
        if self.file_index > self.max_file_index: self.file_index = 0
        if hasattr(self, "hist_item"): self.hist_item.sigLevelChangeFinished.disconnect(self.histogram_scale_changed)

        # Update
        self.current_scan = self.load_scan()
        processed_scan = self.process_scan(self.current_scan)
        self.display(processed_scan)
        if hasattr(self, "hist_item"): self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)



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
            self.direction_button.setText("direXion: backward" if checked else "direXion: forward")
        except Exception:
            pass
        # Always reload image to reflect direction change
        self.current_scan = self.load_scan()
        processed_scan = self.process_scan(self.current_scan)
        self.display(processed_scan)

    def on_bg_change(self, mode: str):
        if mode in ["none", "plane", "inferred", "linewise"]:
            self.background_subtraction = mode
            if mode == "none": self.bg_none_radio.setChecked(True)
            elif mode == "plane": self.bg_plane_radio.setChecked(True)
            elif mode == "inferred": self.bg_inferred_radio.setChecked(True)
            else: self.bg_linewise_radio.setChecked(True)
            
            # Update
            if not hasattr(self, "current_scan"):
                self.current_scan = self.load_scan()
            processed_scan = self.process_scan(self.current_scan)
            self.display(processed_scan)

    # Channel buttons
    def on_previous_chan(self):
        self.channel_index -= 1
        if self.channel_index < 0: self.channel_index = self.max_channel_index
        self.channel = self.channels[self.channel_index]

        # Update
        self.current_scan = self.load_scan()
        processed_scan = self.process_scan(self.current_scan)
        self.display(processed_scan)

    def on_chan_change(self, index):
        self.channel_index = index
        self.channel = self.channels[index]

        # Update
        self.current_scan = self.load_scan()
        processed_scan = self.process_scan(self.current_scan)
        self.display(processed_scan)

    def on_next_chan(self):
        self.channel_index += 1
        if self.channel_index > self.max_channel_index: self.channel_index = 0
        self.channel = self.channels[self.channel_index]

        # Update
        self.current_scan = self.load_scan()
        processed_scan = self.process_scan(self.current_scan)
        self.display(processed_scan)



    # Routines for loading a new image
    def load_folder(self, file_name):
        try:
            self.folder = os.path.dirname(file_name) # Set the folder to the directory of the file
            (self.sxm_files, self.spec_files) = read_files(self.folder) # Read the names and datetimes of all scans (.sxm files) and spectra (.dat files)
            
            self.max_file_index = len(self.sxm_files) - 1
            self.file_index = np.where([os.path.samefile(sxm_file, file_name) for sxm_file in self.sxm_files[:, 1]])[0][0] # Find the number of the specific file that was selected
            if self.file_index > self.max_file_index: self.file_index = 0 # Roll over if the selected file index is too large
            self.output_folder = self.folder + "\\" + self.output_folder_name # Update the output folder name
            self.sxm_file = self.sxm_files[self.file_index] # Apply the index to the list of sxm files to pick the correct sxm file

            self.file_label = self.sxm_file[0] # The file label is the file name without the directory path
            # Update folder/contents labels
            try:
                self.folder_name_button.setText(self.folder)
                if self.max_file_index == 0: self.contains_n_files_label.setText(f"which contains 1 sxm file")
                else: self.contains_n_files_label.setText(f"which contains {self.max_file_index + 1} sxm files")
            except Exception as e:
                print(f"Error: {e}")

            if self.max_file_index > 0:
                self.current_scan = self.load_scan() # Load the image if there is a file
                processed_scan = self.process_scan(self.current_scan)
                self.display(processed_scan)

        except Exception as e:
            print(f"Error loading files: {e}")
            self.file_label = "Select file"
        
        self.file_select_button.setText(self.file_label)

    def load_scan(self):
        self.sxm_file = self.sxm_files[self.file_index]
        self.file_label = self.sxm_file[0]
        self.file_select_button.setText(self.file_label) # Make the select file button display the file name

        # Load the scan object using nanonispy2
        self.scan_object = get_scan(self.sxm_file[1], units = {"length": "nm", "current": "pA"})
        scan_tensor = self.scan_object.tensor
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
        
        try:
            associated_spectra_indices = np.where(self.spec_files[:, 3] == self.sxm_file[0])[0]
            self.associated_spectra = [self.spec_files[index, 0] for index in associated_spectra_indices]
        except:
            self.associated_spectra = []
        self.spectra_box.blockSignals(True)
        self.spectra_box.clear()
        self.spectra_box.addItems(self.associated_spectra)
        self.spectra_box.blockSignals(False)

        # Channel / scan direction selection
        # Pick the correct frame out of the scan tensor based on channel and scan direction
        if self.scan_direction == "backward": selected_scan = scan_tensor[self.channel_index, 1]
        else: selected_scan = scan_tensor[self.channel_index, 0]

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

        return selected_scan
    
    def process_scan(self, scan):
        # Determine background subtraction mode from radio buttons and apply it
        mode = self.background_subtraction
        processed_scan = background_subtract(scan, mode = mode)

        # Apply matrix operations
        if self.apply_sobel: processed_scan = image_gradient(processed_scan, self.scan_range)
        if self.apply_normal: processed_scan = compute_normal(processed_scan, self.scan_range)
        if self.apply_laplace: processed_scan = apply_laplace(processed_scan, self.scan_range)

        gaussian_sigma = float(self.gaussian_width_box.text())
        if self.apply_gaussian: processed_scan = apply_gaussian(processed_scan, sigma = gaussian_sigma, scan_range = self.scan_range)
        if self.apply_fft:
            processed_scan, reciprocal_range = apply_fft(processed_scan, self.scan_range)
            # self.scan_range = reciprocal_range
        
        match self.project_complex_box.currentText():
            case "re": processed_scan = np.real(processed_scan)
            case "im": processed_scan = np.imag(processed_scan)
            case "abs": processed_scan = np.abs(processed_scan)
            case "abs^2": processed_scan = np.abs(processed_scan) ** 2
            case "arg (b/w)": processed_scan = np.angle(processed_scan)
            case "arg (hue)": processed_scan = complex_image_to_colors(processed_scan, saturate = True)
            case "complex": processed_scan = complex_image_to_colors(processed_scan, saturate = False)
            case "log(abs)": processed_scan = np.log(np.abs(processed_scan))
            case _: processed_scan = np.real(processed_scan)

        # Calculate the image statistics and display them
        self.statistics = get_image_statistics(processed_scan)
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
        
        return processed_scan

    def display(self, scan):
        # Show the scan
        self.image_view.setImage(scan, autoRange = True)  # Show the scan in the app
        image_item = self.image_view.getImageItem()
        image_item.setRect(QtCore.QRectF(0, 0, self.scan_range[1], self.scan_range[0]))  # Add dimensions to the ImageView object
        self.image_view.autoRange()

        # Get the new histogram levels
        self.hist_levels = list(self.hist_item.getLevels())



    # Spectroscopy
    def load_spectroscopy_window(self):
        if not hasattr(self, "second_window") or self.second_window is None: # Create only if not already created:
            self.current_scan = self.load_scan()
            processed_scan = self.process_scan(self.current_scan)
            self.second_window = SpectroscopyWindow(processed_scan, self.spec_files, self.associated_spectra)
        self.second_window.show()

    # Scale limit functions
    def on_full_scale(self, side: str = "both"):
        (min, max) = self.hist_item.getLevels() # Read the old levels
        if side == "min":
            if hasattr(self, "statistics") and hasattr(self.statistics, "min"):
                self.min_selection = 0
                self.hist_item.sigLevelChangeFinished.disconnect(self.histogram_scale_changed)
                self.hist_item.setLevels(self.statistics.min, max)
                self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)
        elif side == "max":
            if hasattr(self, "statistics") and hasattr(self.statistics, "max"):
                self.max_selection = 0
                self.hist_item.sigLevelChangeFinished.disconnect(self.histogram_scale_changed)
                self.hist_item.setLevels(min, self.statistics.max)
                self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)
        elif side == "both":
            if hasattr(self, "statistics") and hasattr(self.statistics, "min") and hasattr(self.statistics, "max"):
                self.min_selection = 0
                self.max_selection = 0
                self.hist_item.sigLevelChangeFinished.disconnect(self.histogram_scale_changed)
                self.hist_item.setLevels(self.statistics.min, self.statistics.max)
                self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)
        
        if self.min_selection == 0: self.min_range_set.setChecked(True)
        if self.max_selection == 0: self.max_range_set.setChecked(True)

        (min, max) = self.hist_item.getLevels() # Read the new levels
        self.min_abs_val_box.setText(f"{round(min, 3)}") # Update the absolute value boxes
        self.max_abs_val_box.setText(f"{round(max, 3)}") # Update the absolute value boxes

    def on_percentiles(self, side: str = "both"):
        (min, max) = self.hist_item.getLevels()
        if side == "min":
            if hasattr(self, "statistics") and hasattr(self.statistics, "min") and hasattr(self.statistics, "range_total") and hasattr(self.statistics, "data_sorted"):
                try:
                    min_percentile = float(self.min_percentile_box.text())
                    data_sorted = self.statistics.data_sorted
                    n_data = len(data_sorted)
                    min_value = data_sorted[int(.01 * min_percentile * n_data)]

                    self.hist_item.sigLevelChangeFinished.disconnect(self.histogram_scale_changed)
                    self.hist_item.setLevels(min_value, max)
                    self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)
                    self.min_selection = 1
                except Exception as e:
                    print(f"Error: {e}")
        elif side == "max":
            if hasattr(self, "statistics") and hasattr(self.statistics, "max") and hasattr(self.statistics, "range_total") and hasattr(self.statistics, "data_sorted"):
                try:
                    max_percentile = float(self.max_percentile_box.text())
                    data_sorted = self.statistics.data_sorted
                    n_data = len(data_sorted)
                    max_value = data_sorted[int(.01 * max_percentile * n_data)]

                    self.hist_item.sigLevelChangeFinished.disconnect(self.histogram_scale_changed)
                    self.hist_item.setLevels(min, max_value)
                    self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)
                    self.max_selection = 1
                except Exception as e:
                    print(f"Error: {e}")
        elif side == "both":
            if hasattr(self, "statistics") and hasattr(self.statistics, "min") and hasattr(self.statistics, "max") and hasattr(self.statistics, "range_total") and hasattr(self.statistics, "data_sorted"):
                try:
                    min_percentile = float(self.min_percentile_box.text())
                    max_percentile = float(self.max_percentile_box.text())
                    data_sorted = self.statistics.data_sorted
                    n_data = len(data_sorted)
                    min_value = data_sorted[int(.01 * min_percentile * n_data)]
                    max_value = data_sorted[int(.01 * max_percentile * n_data)]
                    
                    self.hist_item.sigLevelChangeFinished.disconnect(self.histogram_scale_changed)
                    self.hist_item.setLevels(min_value, max_value)
                    self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)
                    self.min_selection = 1
                    self.max_selection = 1
                except Exception as e:
                    print(f"Error: {e}")
        
        if self.min_selection == 1: self.min_percentile_set.setChecked(True)
        if self.max_selection == 1: self.max_percentile_set.setChecked(True)
        
        (min, max) = self.hist_item.getLevels() # Read the new levels
        self.min_abs_val_box.setText(f"{round(min, 3)}") # Update the absolute value boxes
        self.max_abs_val_box.setText(f"{round(max, 3)}") # Update the absolute value boxes
        self.hist_levels = [min, max]

    def on_standard_deviations(self, side: str = "both"):
        (min, max) = self.hist_item.getLevels() # Read the old levels
        if side == "min":
            if hasattr(self, "statistics") and hasattr(self.statistics, "standard_deviation") and hasattr(self.statistics, "mean"):
                try:
                    value = float(self.min_std_dev_box.text())
                    min_value = self.statistics.mean - value * self.statistics.standard_deviation
                    
                    self.hist_item.sigLevelChangeFinished.disconnect(self.histogram_scale_changed)
                    self.hist_item.setLevels(min_value, max)
                    self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)
                    self.min_selection = 2
                except Exception as e:
                    print(f"Error: {e}")
        
        if side == "max":
            if hasattr(self, "statistics") and hasattr(self.statistics, "standard_deviation") and hasattr(self.statistics, "mean"):
                try:
                    value = float(self.max_std_dev_box.text())
                    max_value = self.statistics.mean + value * self.statistics.standard_deviation
                    
                    self.hist_item.sigLevelChangeFinished.disconnect(self.histogram_scale_changed)
                    self.hist_item.setLevels(min, max_value)
                    self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)
                    self.max_selection = 2
                except Exception as e:
                    print(f"Error: {e}")
        
        if side == "both":
            if hasattr(self, "statistics") and hasattr(self.statistics, "standard_deviation") and hasattr(self.statistics, "mean"):
                try:
                    value = float(self.min_std_dev_box.text())
                    min_value = self.statistics.mean - value * self.statistics.standard_deviation
                    value = float(self.max_std_dev_box.text())
                    max_value = self.statistics.mean + value * self.statistics.standard_deviation
                    
                    self.hist_item.sigLevelChangeFinished.disconnect(self.histogram_scale_changed)
                    self.hist_item.setLevels(min_value, max_value)
                    self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)
                    self.min_selection = 2
                    self.max_selection = 2
                except Exception as e:
                    print(f"Error: {e}")
        
        if self.min_selection == 2: self.min_std_dev_set.setChecked(True)
        if self.max_selection == 2: self.max_std_dev_set.setChecked(True)
        
        (min, max) = self.hist_item.getLevels() # Read the new levels
        self.min_abs_val_box.setText(f"{round(min, 3)}") # Update the absolute value boxes
        self.max_abs_val_box.setText(f"{round(max, 3)}") # Update the absolute value boxes
        self.hist_levels = [min, max]
    
    def on_absolute_values(self, side: str = "both"):
        (min, max) = self.hist_item.getLevels()
        if side == "min":
            try:
                min_value = float(self.min_abs_val_box.text())
                self.hist_item.sigLevelChangeFinished.disconnect(self.histogram_scale_changed)
                self.hist_item.setLevels(min_value, max)
                self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)
                self.min_selection = 3
            except Exception as e:
                print(f"Error: {e}")
        
        if side == "max":
            try:
                max_value = float(self.max_abs_val_box.text())
                self.hist_item.sigLevelChangeFinished.disconnect(self.histogram_scale_changed)
                self.hist_item.setLevels(min, max_value)
                self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)
                self.max_selection = 3
            except Exception as e:
                print(f"Error: {e}")
        
        if side == "both":
            try:
                min_value = float(self.min_abs_val_box.text())
                max_value = float(self.max_abs_val_box.text())
                self.hist_item.sigLevelChangeFinished.disconnect(self.histogram_scale_changed)
                self.hist_item.setLevels(min_value, max_value)
                self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)
                self.min_selection = 3
                self.max_selection = 3
            except Exception as e:
                print(f"Error: {e}")
        
        if self.min_selection == 3: self.min_abs_val_set.setChecked(True)
        if self.max_selection == 3: self.max_abs_val_set.setChecked(True)
        self.hist_levels = [min, max]

    def histogram_scale_changed(self):
        (min, max) = self.hist_item.getLevels()
        if hasattr(self, "hist_levels"):
            [min_old, max_old] = self.hist_levels

            if np.abs(max - max_old) > .0000001 * (max_old - min_old): # If the top level was changed (use a tiny threshold)
                self.max_abs_val_box.setText(f"{round(max, 3)}")
                self.max_abs_val_set.setChecked(True)
                self.max_selection = 3

            if np.abs(min - min_old) > .0000001 * (max_old - min_old): # If the bottom level was changed
                self.min_abs_val_box.setText(f"{round(min, 3)}")
                self.min_abs_val_set.setChecked(True)
                self.min_selection = 3

        self.hist_levels = [min, max]

    def toggle_limits(self, side: str = "min"):
        if side not in ["min", "max"]:
            print("Error. No correct side chosen.")
            return
        
        if side == "min":
            self.min_selection += 1
            if self.min_selection > 3: self.min_selection = 0
            sel = self.min_selection
        else:
            self.max_selection += 1
            if self.max_selection > 3: self.max_selection = 0
            sel = self.max_selection
        
        match sel:
            case 0: self.on_full_scale(side)
            case 1: self.on_percentiles(side)
            case 2: self.on_standard_deviations(side)
            case _: self.on_absolute_values(side)

    # Matrix processing functions
    def toggle_matrix_processing(self, operation, checked):
        if operation == "sobel":
            self.sobel_button.setChecked(checked)
            self.apply_sobel = checked
        if operation == "gaussian":
            self.gauss_button.setChecked(checked)
            self.apply_gaussian = checked
        if operation == "fft":
            self.fft_button.setChecked(checked)
            self.apply_fft = checked
        if operation == "laplace":
            self.laplace_button.setChecked(checked)
            self.apply_laplace = checked
        if operation == "normal":
            self.normal_button.setChecked(checked)
            self.apply_normal = checked

        if not hasattr(self, "current_scan"):
            self.current_scan = self.load_scan()
        processed_scan = self.process_scan(self.current_scan)
        self.display(processed_scan)

    def toggle_projections(self):
        try:
            number_of_items = self.project_complex_box.count()
            current_index = self.project_complex_box.currentIndex()
            new_index = current_index + 1
            if new_index > number_of_items - 1: new_index = 0
            self.project_complex_box.setCurrentIndex(new_index)
            
            if not hasattr(self, "current_scan"): self.current_scan = self.load_scan()
            processed_scan = self.process_scan(self.current_scan)
            self.display(processed_scan)

        except Exception as e:
            print(f"{e}")

    # Save button
    def on_save(self):
        # Properly rescale to 0-255
        processed_scan = self.process_scan(self.current_scan)
        
        min_val, max_val = (self.statistics.min, self.statistics.max)
        try:
            if self.hist is not None: min_val, max_val = self.hist.getLevels()
        except Exception as e:
            print(f"Error reading the histogram levels: {e}")
        denom = max_val - min_val if max_val != min_val else 1
        rescaled_array = (processed_scan - min_val) / denom
        rescaled_array = np.clip(rescaled_array, 0, 1)  # Ensure within [0,1]
        uint8_array = (255 * rescaled_array).astype(np.uint8)
        
        try:
            if uint8_array.ndim > 2:
                #rgb_array = np.ascontiguousarray(uint8_array, dtype = np.uint8)
                height, width, channels = uint8_array.shape
                qimg = QImage(uint8_array.data, width, height, uint8_array.strides[0], QImage.Format.Format_RGB888)
            else:
                height, width = uint8_array.shape
                qimg = QImage(uint8_array, width, height, width, QImage.Format.Format_Grayscale8)

            output_file_name = self.output_folder + "\\" + self.png_file_name
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
            print(f"Error saving the image file: {e}")
            pass

    # Exit button
    def on_exit(self):
        try: # Save the currently opened scan folder to the config yaml file so it opens automatically on startup next time
            with open(self.scanalyzer_folder + "\\config.yml", "w") as file:
                yaml.safe_dump({"last_file": str(self.sxm_file[1])}, file)
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