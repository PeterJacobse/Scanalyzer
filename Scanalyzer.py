import os, sys, re, yaml, pint
import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import pyqtgraph.exporters as expts
from lib import GUIFunctions, GUIItems, ScanalyzerGUI, HoverTargetItem, DataProcessing, FileFunctions, SpectrumViewer



class AppWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.parameters_init()
        self.gui_items_init()
        
        self.setWindowTitle("Scanalyzer") # Make the app window
        self.setGeometry(100, 100, 1400, 800) # x, y, width, height

        # Set the central widget of the QMainWindow, then draw a toolbar next to it
        self.setCentralWidget(self.gui.widgets["central"])
        
        main_layout = QtWidgets.QHBoxLayout(self.gui.widgets["central"])
        
        main_layout.addWidget(self.gui.image_view, 3)
        main_layout.addLayout(self.gui.layouts["toolbar"], 1)
        
        # Ensure the central widget and QMainWindow can both receive keyboard focus
        
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setFocus()
        self.activateWindow()

        # Initialize the ImageView
        try: # Read the last scan file from the config yaml file
            with open(self.paths["config_path"], "r") as file:
                yaml_data = yaml.safe_load(file)
                last_file = yaml_data.get("last_file")
                self.load_folder(last_file)
                #self.on_full_scale("both")
        except:
            pass



    def parameters_init(self) -> None:
        # Paths
        script_path = os.path.abspath(__file__) # The full path of Scanalyzer.py, including the filename itself
        script_folder = os.path.dirname(script_path) # The parent directory of Scanalyzer.py
        sys_folder = os.path.join(script_folder, "sys") # The directory of the config file
        lib_folder = os.path.join(script_folder, "lib") # The directory of the Scanalyzer package
        icon_folder = os.path.join(script_folder, "icons") # The directory of the icon files
        config_path = os.path.join(sys_folder, "config.yml") # The path to the configuration file
        data_folder = sys_folder # Set current folder to the config file; read from the config file later to reset it to a data folder
        metadata_file = os.path.join(data_folder, "metadata.yml") # Metadata file that is populated with all the scan and spectroscopy metadata of the files in the data folder
        output_folder_name = "Extracted Files"

        self.paths = {
            "script_path": script_path,
            "script_folder": script_folder,
            "scanalyzer_folder": sys_folder,
            "lib_folder": lib_folder,
            "icon_folder": icon_folder,
            "config_path": config_path,
            "data_folder": lib_folder,
            "metadata_file": metadata_file,
            "output_folder_name": output_folder_name,
            "output_folder": os.path.join(data_folder, output_folder_name),
            "output_file_basename": ""
        }

        # Icons
        icon_files = os.listdir(self.paths["icon_folder"])
        self.icons = {}
        for icon_file in icon_files:
            [icon_name, extension] = os.path.splitext(os.path.basename(icon_file))
            try:
                if extension == ".png": self.icons.update({icon_name: QtGui.QIcon(os.path.join(self.paths["icon_folder"], icon_file))})
            except:
                pass
        self.setWindowIcon(self.icons.get("scanalyzer"))
        
        # Some attributes
        self.files_dict = {}
        self.spec_files = np.array([[]])
        self.image_files = [""]
        self.file_index = 0
        self.max_file_index = -1
        self.selected_file = ""
        self.channels = []
        self.channel = ""
        self.channel_index = 0
        self.max_channel_index = 0
        self.scale_toggle_index = 0
        self.spec_targets = []
        self.ureg = pint.UnitRegistry()
        self.file_functions = FileFunctions()
        self.data = DataProcessing()
        self.gui = ScanalyzerGUI(self.paths["icon_folder"])
        self.gui_functions = GUIFunctions()
        self.gui_items = GUIItems()

    def gui_items_init(self) -> None:
        self.populate_layouts()
        self.connect_keys()

    def populate_layouts(self) -> QtWidgets.QVBoxLayout:
        buttons = self.gui.buttons
        labels = self.gui.labels
        layouts = self.gui.layouts
        comboboxes = self.gui.comboboxes
        radio_buttons = self.gui.radio_buttons
        checkboxes = self.gui.checkboxes
        line_edits = self.gui.line_edits
        groupboxes = self.gui.groupboxes



        layouts["image_processing"].addWidget(labels["background_subtraction"])
        
        # Background subtraction group
        self.bg_button_group = QtWidgets.QButtonGroup(self)
        background_buttons = [radio_buttons[button_name] for button_name in ["bg_none", "bg_plane", "bg_linewise", "bg_inferred"]]
        [self.bg_button_group.addButton(button) for button in self.gui.background_buttons] # Add buttons to the QButtonGroup for exclusive selection
        [layouts["background_buttons"].addWidget(button) for button in background_buttons]
        radio_buttons["bg_none"].setChecked(True)
        layouts["image_processing"].addLayout(layouts["background_buttons"])
        layouts["image_processing"].addWidget(self.gui_items.line_widget("h", 1))

        # Matrix operations
        layouts["image_processing"].addWidget(labels["matrix_operations"])
        matrix_layout = layouts["matrix_processing"]
        [matrix_layout.addWidget(checkboxes[checkbox_name], 0, index) for index, checkbox_name in enumerate(["sobel", "normal", "laplace"])]
        matrix_layout.addWidget(checkboxes["gaussian"], 1, 1)
        matrix_layout.addWidget(line_edits["gaussian_width"], 1, 2)
        matrix_layout.addWidget(checkboxes["fft"], 1, 0)
        matrix_layout.addWidget(comboboxes["projection"], 2, 1)
        layouts["image_processing"].addLayout(matrix_layout)
        layouts["image_processing"].addWidget(self.gui_items.line_widget("h", 1))

        # Limits control group
        layouts["image_processing"].addWidget(labels["limits"])
        limits_layout = layouts["limits"]
        min_line_edits = [line_edits[line_edit_name] for line_edit_name in ["min_full", "min_percentiles", "min_deviations", "min_absolute"]]
        min_radio_buttons = [radio_buttons[button_name] for button_name in ["min_full", "min_percentiles", "min_deviations", "min_absolute"]]
        scale_buttons = [buttons[button_name] for button_name in ["full_data_range", "percentiles", "standard_deviation", "absolute_values"]]            
        max_radio_buttons = [radio_buttons[button_name] for button_name in ["max_full", "max_percentiles", "max_deviations", "max_absolute"]]
        max_line_edits = [line_edits[line_edit_name] for line_edit_name in ["max_full", "max_percentiles", "max_deviations", "max_absolute"]]
        [line_edits[line_edit_name].setEnabled(False) for line_edit_name in ["min_full", "max_full"]]
        
        [limits_layout.addWidget(line_edit, index, 0) for index, line_edit in enumerate(min_line_edits)]
        [limits_layout.addWidget(line_edit, index, 1) for index, line_edit in enumerate(min_radio_buttons)]
        [limits_layout.addWidget(line_edit, index, 2) for index, line_edit in enumerate(scale_buttons)]
        [limits_layout.addWidget(line_edit, index, 3) for index, line_edit in enumerate(max_radio_buttons)]
        [limits_layout.addWidget(line_edit, index, 4) for index, line_edit in enumerate(max_line_edits)]
        layouts["image_processing"].addLayout(limits_layout)

        # The startup default is 100%; set the buttons accordingly (without triggering the redrawing of the scan image)
        [radio_buttons[name].setSilentCheck(True) for name in ["min_full", "max_full", "bg_none"]]
        
        spectra_widgets = [buttons["spec_info"], comboboxes["spectra"], buttons["spec_locations"], buttons["spectrum_viewer"]]
        [layouts["spectra"].addWidget(widget) for widget in spectra_widgets]
        layouts["spectra"].setStretchFactor(comboboxes["spectra"], 4)




        io_layout = layouts["i/o"]
        [io_layout.addWidget(buttons[name], 0, i + 1) for i, name in enumerate(["save_png", "save_hdf5", "info"])]
        [io_layout.addWidget(widget, i, 0) for i, widget in enumerate([line_edits["file_name"], labels["in_output_folder"]])]
        io_layout.addWidget(buttons["output_folder"], 1, 1, 1, 2)
        io_layout.addWidget(buttons["exit"], 1, 3)



        
        group_names = ["scan_summary", "file_chan_dir", "image_processing", "spectra", "i/o"]
        [groupboxes[name].setLayout(layouts[name]) for name in group_names]
        
        
        
        layouts["toolbar"].setContentsMargins(4, 4, 4, 4)
        [layouts["toolbar"].addWidget(groupboxes[name]) for name in group_names]
        layouts["toolbar"].addStretch(1) # Add a stretch at the end to push buttons up

        return

    def connect_keys(self) -> None:
        buttons = self.gui.buttons
        checkboxes = self.gui.checkboxes
        radio_buttons = self.gui.radio_buttons
        comboboxes = self.gui.comboboxes
        line_edits = self.gui.line_edits
        shortcuts = self.gui.shortcuts
        
        # Connect the buttons to their respective functions
        connections = [["previous_file", lambda: self.on_file_index_change(-1)], ["select_file", self.on_select_file], ["next_file", lambda: self.on_file_index_change(1)],
                       ["previous_channel", lambda: self.on_chan_index_change(-1)], ["next_channel", lambda: self.on_chan_index_change(1)], ["direction", self.update_processing_flags],
                       ["folder_name", lambda: self.open_folder("data_folder")],
                       
                       ["full_data_range", lambda: self.on_limits_set("full", "both")], ["percentiles", lambda: self.on_limits_set("percentiles", "both")],
                       ["standard_deviation", lambda: self.on_limits_set("deviations", "both")], ["absolute_values", lambda: self.on_limits_set("absolute", "both")],
                       
                       ["spec_info", self.load_process_display], ["spec_locations", self.on_toggle_spec_locations], ["spectrum_viewer", self.open_spectrum_viewer],
                       
                       ["save_png", self.on_save_png], ["save_hdf5", self.on_save_png], ["output_folder", lambda: self.open_folder("output_folder")], ["info", self.on_info], ["exit", self.on_exit]
                    ]
        
        for connection in connections:
            name = connection[0]
            connected_function = connection[1]
            buttons[name].clicked.connect(connected_function)
            
            #if name in shortcuts.keys():
            #    shortcut = QtGui.QShortcut(shortcuts[name], self.gui)
            #    shortcut.activated.connect(connected_function)
        
        QKey = QtCore.Qt.Key
        QMod = QtCore.Qt.Modifier
        QSeq = QtGui.QKeySequence
        
        [radio_buttons[name].clicked.connect(self.update_processing_flags) for name in ["bg_none", "bg_plane", "bg_linewise"]]
        radio_buttons["bg_none"].setShortcut(QSeq(QKey.Key_0 | QMod.SHIFT))
        radio_buttons["bg_plane"].setShortcut(QSeq(QKey.Key_P | QMod.SHIFT))
        radio_buttons["bg_linewise"].setShortcut(QSeq(QKey.Key_L | QMod.SHIFT))

        # Matrix operations
        [checkboxes[operation].clicked.connect(self.update_processing_flags) for operation in ["sobel", "gaussian", "normal", "fft", "laplace"]]
        checkboxes["sobel"].setShortcut(QSeq(QKey.Key_S | QMod.SHIFT))
        checkboxes["normal"].setShortcut(QSeq(QKey.Key_N | QMod.SHIFT))
        checkboxes["gaussian"].setShortcut(QSeq(QKey.Key_G | QMod.SHIFT))
        checkboxes["fft"].setShortcut(QSeq(QKey.Key_F | QMod.SHIFT))
        checkboxes["laplace"].setShortcut(QSeq(QKey.Key_C | QMod.SHIFT))

        # Limits control group
        toggle_min_shortcut = QtGui.QShortcut(QSeq(QKey.Key_Minus), self)
        toggle_min_shortcut.activated.connect(lambda: self.toggle_limits("min"))
        toggle_max_shortcut = QtGui.QShortcut(QSeq(QKey.Key_Equal), self)
        toggle_max_shortcut.activated.connect(lambda: self.toggle_limits("max"))

        next_projection_shortcut = QtGui.QShortcut(QSeq(QMod.SHIFT | QKey.Key_Down), self)
        next_projection_shortcut.activated.connect(lambda: self.toggle_projections(1))
        next_projection_shortcut = QtGui.QShortcut(QSeq(QMod.SHIFT | QKey.Key_Up), self)
        next_projection_shortcut.activated.connect(lambda: self.toggle_projections(-1))
        
        comboboxes["channels"].currentIndexChanged.connect(self.update_processing_flags)
        comboboxes["projection"].currentIndexChanged.connect(self.update_processing_flags)




        #comboboxes["projection"].currentIndexChanged.connect(self.update_processing_flags)
        #self.gui.line_edits["gaussian_width"].editingFinished.connect(self.update_processing_flags)
        #radio_buttons["bg_none"].setChecked(True)
        #radio_buttons["min_full"].toggled.connect(self.update_processing_flags)
        
        [signal.connect(self.update_processing_flags) for signal in [comboboxes["projection"].currentIndexChanged, line_edits["gaussian_width"].editingFinished]]
        
        exit_shortcuts = [QtGui.QShortcut(QtGui.QKeySequence(keystroke), self) for keystroke in [QKey.Key_Q, QKey.Key_E, QKey.Key_Escape]]
        [exit_shortcut.activated.connect(self.on_exit) for exit_shortcut in exit_shortcuts]
                
        next_projection_shortcut = QtGui.QShortcut(QtGui.QKeySequence(QMod.SHIFT | QKey.Key_Up), self)
        previous_projection_shortcut = QtGui.QShortcut(QtGui.QKeySequence(QKey.Key_Down | QMod.SHIFT), self)
        next_projection_shortcut.activated.connect(lambda: self.toggle_projections(1))
        previous_projection_shortcut.activated.connect(lambda: self.toggle_projections(-11))




        self.hist = self.gui.image_view.getHistogramWidget()
        self.hist_item = self.hist.item
        self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)



        return



    # Button functions
    # File selection
    def on_file_index_change(self, index: int = 1) -> None:
        self.file_index += index
        if self.file_index < 0: self.file_index = self.max_file_index
        if self.file_index > len(self.files_dict.get("scan_files")) - 1: self.file_index = 0
        self.load_process_display(new_scan = True)
        return

    def on_select_file(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open file", self.paths["data_folder"], "SXM files (*.sxm);;Dat files (*.dat);;HDF5 files (*.hdf5)")
        if file_path: self.load_folder(file_path)
        return

    # Channel selection
    def on_chan_index_change(self, index: int = 1) -> None:
        self.channel_index += index
        if self.channel_index < 0: self.channel_index = self.max_channel_index
        if self.channel_index > self.max_channel_index - 1: self.channel_index = 0
        self.channel = self.channels[self.channel_index]
        self.load_process_display(new_scan = True)
        return

    def on_chan_change(self, index: int = 0) -> None:
        self.channel_index = index
        self.channel = self.channels[index]
        self.load_process_display(new_scan = True)

        return

    def on_next_chan(self) -> None:
        self.channel_index += 1
        if self.channel_index > self.max_channel_index: self.channel_index = 0
        self.channel = self.channels[self.channel_index]
        self.load_process_display(new_scan = True)

        return

    # Background changing
    def on_bg_change(self, mode: str = "none") -> None:
        if mode in ["none", "plane", "inferred", "linewise"]:
            self.gui.radio_buttons[f"bg_{mode}"].setChecked(True)
        self.update_processing_flags
        return

    # Routines for loading a new image
    def load_folder(self, file_path: str = "") -> None:
        buttons = self.gui.buttons
        labels = self.gui.labels

        try:
            self.paths["data_folder"] = os.path.dirname(file_path) # Set the folder to the directory of the file
            self.paths["metadata_file"] = os.path.join(self.paths["data_folder"], "metadata.yml") # Set the metadata yaml file accordingly as well
            self.paths["output_folder"] = os.path.join(self.paths["data_folder"], self.paths["output_folder_name"]) # Set the output folder name

            # Create a bare bones dictionary containing the file names and paths of all the scan files and spectroscopy files in the folder
            
            (files_dict, error) = self.file_functions.create_files_dict(self.paths["data_folder"])
            if error: raise
            else: self.files_dict = files_dict
            # Update the dictionary by reading the headers from the metadata file or from the individual dat files if necessary
            # self.read_spectroscopy_headers()
            
            # Match the requested file (full path) to the entry in the scan_files dict to extract the key. The key is an integer and is called self.file_index
            scan_dict = self.files_dict.get("scan_files")
            self.max_file_index = len(scan_dict) - 1
            self.file_index = 0
            for key, value in scan_dict.items():
                if os.path.samefile(value.get("path"), file_path):
                    self.file_index = key
                    break
            if self.file_index > self.max_file_index: self.file_index = 0 # Roll over if the selected file index is too large
            
            # Update folder/contents labels
            try:
                buttons["folder_name"].setText(self.paths["data_folder"])
                if self.max_file_index == 0: labels["number_of_files"].setText("which contains 1 sxm file")
                else: labels["number_of_files"].setText(f"which contains {self.max_file_index + 1} sxm files")
            except Exception as e:
                print(f"Error: {e}")

            # Load the scan file and display it
            
            if self.max_file_index > 0:
                self.load_process_display(new_scan = True)

        except Exception as e:
            print(f"Error loading folder: {e}")
            buttons["select_file"].setText("Select file")
        
        return

    def load_scan(self) -> np.ndarray:
        # Load the sxm file from the list of sxm files. Make the select file button display the file name
        buttons = self.gui.buttons
        labels = self.gui.labels
        comboboxes = self.gui.comboboxes
        
        scan_dict = self.files_dict.get("scan_files")
        try:
            self.gui.buttons["select_file"].setText(scan_dict[self.file_index].get("file_name"))
        except:
            print("Error. Could not retrieve scan.")
            return

        # Load the scan object using nanonispy2
        if self.file_index < 0: self.file_index = self.max_file_index
        if self.file_index > self.max_file_index: self.file_index = 0
        try:
            (self.scan_object, error) = self.file_functions.get_scan(scan_dict[self.file_index].get("path"), units = {"length": "nm", "current": "pA"})
            if error: raise
            
            scan_tensor = self.scan_object.tensor
            self.channels = self.scan_object.channels # Load which channels have been recorded
            if self.channel not in self.channels: # If the requested channel does not exist in the scan, default the requested channel to be the first channel in the list of channels
                self.channel = self.channels[0]
            self.channel_index = np.where(self.channels == self.channel)[0][0]
            self.max_channel_index = len(self.channels) - 1
        except Exception as e:
            print(f"{e}")

        # Update the channel selection box based on the available channels
        comboboxes["channels"].renewItems(self.channels)
        comboboxes["channels"].selectItem(self.channels[self.channel_index])

        # Read the metadata, the metadata file and update if necessary
        try:
            self.read_metadata()
            self.get_end_time()
        except Exception as e:
            print(f"{e}")
        
        # Display scan data in the app
        if self.feedback: self.summary_text = f"STM topographic scan recorded on\n{self.date_time.strftime('%Y/%m/%d   at   %H:%M:%S')}\n\n(V = {self.bias_V:.3f} V; I_fb = {self.setpoint_pA:.3f} pA)\nScan range: {self.scan_range_nm[0]:.3f} nm by {self.scan_range_nm[1]:.3f} nm"
        else: self.summary_text = f"Constant height scan recorded on\n{self.date_time.strftime('%Y/%m/%d   at   %H:%M:%S')}\n\n(V = {self.bias_V:.3f} V)\nScan range: {self.scan_range_nm[0]:.3f} nm by {self.scan_range_nm[1]:.3f} nm"
        labels["scan_summary"].setText(self.summary_text)

        # Find the spectra associated with this scan and make them available for viewing as target items and in the combobox
        #self.find_associated_spectra()

        # Channel / scan direction selection
        selected_scan = scan_tensor[self.channel_index, int(self.data.processing_flags["direction"] == "backward")]
        return selected_scan

    def find_associated_spectra(self) -> None:
        # From the list of spectra (spec_files), select the ones that are associated with the current scan (associated scan name is column 3 in self.spec_files and column 0 in self.sxm_files)
        try:
            #associated_spectra_indices = np.where(self.spec_files[:, 3] == self.sxm_file[0])[0]
            self.associated_spectra = [self.spec_files[index] for index in [0, 1, 2]]
        except:
            self.associated_spectra = []

        # Update the spectra combobox
        #self.comboboxes["spectra"].blockSignals(True)
        #self.comboboxes["spectra"].clear()
        #self.comboboxes["spectra"].addItems([spectrum[0] for spectrum in self.associated_spectra])
        #self.comboboxes["spectra"].blockSignals(False)

        # Remove all spectroscopy targets if there were any
        view_box = self.gui.image_view.getView()
        for target in self.spec_targets:
            view_box.removeItem(target)

        # Get the new targets
        self.spec_targets = []

        for index, data in enumerate(self.associated_spectra):
            try:
                x = data[4]
                y = data[5]

                x_nm = x.to("nm").magnitude
                y_nm = y.to("nm").magnitude

                x_relative_to_frame = x_nm - self.offset_nm[0]
                y_relative_to_frame = y_nm - self.offset_nm[1]

                cos_theta = np.cos(self.angle_deg)
                sin_theta = np.sin(self.angle_deg)

                x_rotated = cos_theta * x_relative_to_frame - sin_theta * y_relative_to_frame
                y_rotated = cos_theta * y_relative_to_frame + sin_theta * x_relative_to_frame

                target_item = HoverTargetItem(pos = [x_rotated, y_rotated], size = 10, tip_text = data[0])
                target_item.setZValue(10)
                
                self.spec_targets.append(target_item)
            except Exception as e:
                print("Error populating the target items")
        
        return

    def process_scan(self, image: np.ndarray) -> np.ndarray:
        (processed_scan, error) = self.data.process_scan(image)
        if error:
            print(f"{error}")
            return

        # Calculate the image statistics and display them
        (self.statistics, error) = self.data.get_image_statistics(processed_scan)
        if error:
            print(f"{error}")
            return
        
        range_tot = self.statistics.get("range_total")
        mean = self.statistics.get("mean")
        standard_deviation = self.statistics.get("standard_deviation")

        unit_label = ""
        if self.channel == "X" or self.channel == "Y" or self.channel == "Z": unit_label = " nm"
        elif self.channel == "Current": unit_label = " pA"
        self.gui.labels["statistics"].setText(f"\nValue range: {round(range_tot, 3)}{unit_label}; Mean ± std dev: {round(mean, 3)} ± {round(standard_deviation, 3)}{unit_label}")
        
        return processed_scan

    def update_limits(self) -> None:
        self.radio_buttons = self.gui.radio_buttons
        
        self.hist_levels = list(self.hist_item.getLevels())
        [min, max] = self.hist_levels
        self.gui.line_edits["min_full"].setText(f"{round(min, 3)}")
        self.gui.line_edits["max_full"].setText(f"{round(max, 3)}")

        # Update the min according to which limit method is selected
        if self.radio_buttons["min_percentiles"].isChecked(): # Percentiles
            if hasattr(self, "statistics"):
                try:
                    min_percentile = float(self.gui.line_edits["min_percentiles"].text())
                    data_sorted = self.statistics.get("data_sorted")
                    n_data = len(data_sorted)

                    min = data_sorted[int(.01 * min_percentile * n_data)]
                except Exception as e:
                    print(f"Error: {e}")
        elif self.radio_buttons["min_absolute"].isChecked(): # Absolute values
            try:
                min = float(self.gui.line_edits["min_absolute"].text())
            except Exception as e:
                print(f"Error: {e}")
        elif self.radio_buttons["min_deviations"].isChecked(): # Standard deviation
            if hasattr(self, "statistics"):
                try:
                    value = float(self.gui.line_edits["min_deviations"].text())
                    min = self.statistics.get("mean") - value * self.statistics.get("standard_deviation")
                except Exception as e:
                    print(f"Error: {e}")
        else:
            pass

        # Update the max according to which limit method is selected
        if self.radio_buttons["max_percentiles"].isChecked(): # Percentiles
            if hasattr(self, "statistics"):
                try:
                    max_percentile = float(self.gui.line_edits["max_percentiles"].text())
                    data_sorted = self.statistics.get("data_sorted")
                    n_data = len(data_sorted)

                    max = data_sorted[int(.01 * max_percentile * n_data)]
                except Exception as e:
                    print(f"Error: {e}")
        elif self.radio_buttons["max_absolute"].isChecked(): # Absoulte values
            try:
                max = float(self.gui.line_edits["max_absolute"].text())
            except Exception as e:
                print(f"Error: {e}")
        elif self.radio_buttons["max_deviations"].isChecked(): # Standard deviation
            if hasattr(self, "statistics"):
                try:
                    value = float(self.gui.line_edits["max_deviations"].text())
                    max = self.statistics.get("mean") + value * self.statistics.get("standard_deviation")
                except Exception as e:
                    print(f"Error: {e}")
        else:
            pass

        # Set the histogram levels and reconnect the histogram widget to dynamic updating
        self.hist_item.setLevels(min, max)
        self.gui.line_edits["min_absolute"].setText(f"{round(min, 3)}") # Update the absolute value boxes
        self.gui.line_edits["max_absolute"].setText(f"{round(max, 3)}")
        try: self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)
        except: pass

    def display(self, scan: np.ndarray) -> None:
        # Show the scan
        try: self.hist_item.sigLevelChangeFinished.disconnect()
        except: pass

        self.gui.image_view.setImage(scan, autoRange = True) # Show the scan in the app
        image_item = self.gui.image_view.getImageItem()
        image_item.setRect(QtCore.QRectF(-self.scan_range_nm[1] / 2, -self.scan_range_nm[1] / 2, self.scan_range_nm[1], self.scan_range_nm[0]))  # Add dimensions to the ImageView object

        if self.data.processing_flags["spec_locations"]:
            view_box = self.gui.image_view.getView()        
            for target in self.spec_targets: view_box.addItem(target)

        # Reset the limits and histogram
        self.gui.image_view.autoRange()
        self.update_limits() # The sigLevelChangeFinished method will be reconnected within self.update_limits() after the new limits are set

    def load_process_display(self, new_scan: bool = False) -> None:
        if new_scan or not hasattr(self, "current_scan"):
            self.current_scan = self.load_scan()
        if isinstance(self.current_scan, np.ndarray):
            processed_scan = self.process_scan(self.current_scan)
            self.display(processed_scan)
        else:
            print("Error. Could not load scan.")
        
        return

    def read_spectroscopy_headers(self):
        # Create a metadata file if it does not yet exist:
        if not os.path.exists(self.paths["metadata_file"]):
            try:
                with open(self.paths["metadata_file"], "w") as file:
                    yaml.safe_dump(self.files_dict, file)
            except Exception as e:
                print(f"Failed to write/parse the metadata file. {e}")

        # Read the scan / spectrum file dictionaries from the metadata file
        try:
            with open(self.paths["metadata_file"], "r") as file:
                metadata_obj = yaml.safe_load(file)
        except Exception as e:
            print(f"Failed to write/parse the metadata file. {e}")
            return
        
        try:
            scan_dict = metadata_obj.get("scan_files")
            spec_dict = metadata_obj.get("spectroscopy_files")

            # Iterate over the spectroscopy metadata in the metadata file, and check whether the keys date_time and position exist
            for entry, data in spec_dict.items():
                file_path = data.get("path")

                if "date_time" in data and "position" in data:
                    pass
                # date_time and position are not present in the metadata file. Go ahead and read them from the spectroscopy file
                else:
                    (header, error) = self.file_functions.get_basic_header(file_path)
                    date_time = header.get("date_time")
                    x = header.get("x")
                    y = header.get("y")
                    z = header.get("z")

                    spec_dict[entry].update({
                        "date_time": date_time.strftime("%Y-%m-%d %H:%M:%S"),
                            "position": {
                                "x (nm)": f"{x:.3f}",
                                "y (nm)": f"{y:.3f}",
                                "z (nm)": f"{z:.3f}"
                            }
                    })

            # Local variable
            files_dict = {
                "scan_files": scan_dict,
                "spectroscopy_files": spec_dict
            }

            # Save the spectroscopy metadata to the metadata yaml file
            try:
                with open(self.paths["metadata_file"], "w") as file:
                    yaml.safe_dump(files_dict, file)
            except Exception as e:
                print(f"Failed to write/parse the metadata file. {e}")

        except Exception as e:
            print(f"Failed to write/parse the metadata file. {e}")
            return

        return

    def read_metadata(self):
        # Read metadata from the scan object file
        if not hasattr(self, "scan_object"):
            print("Error. No scan object available.")
            return

        bias = self.scan_object.bias
        self.bias_V = bias.to("V").magnitude
        offset = self.scan_object.offset
        self.offset_nm = [range_dim.to("nm").magnitude for range_dim in offset]
        angle = self.scan_object.angle
        self.angle_deg = angle.to("degree").magnitude
        scan_range = self.scan_object.scan_range
        self.scan_range_nm = [range_dim.to("nm").magnitude for range_dim in scan_range]
        self.data.processing_flags.update({"scan_range_nm": self.scan_range_nm})
        setpoint = self.scan_object.setpoint
        self.setpoint_pA = setpoint.to("pA").magnitude        
        self.feedback = self.scan_object.feedback # Read whether the scan was recorded in STM feedback
        self.date_time = self.scan_object.date_time


 
        # Create a metadata file if it does not yet exist:
        if not os.path.exists(self.paths["metadata_file"]):
            try:
                with open(self.paths["metadata_file"], "w") as file:
                    yaml.safe_dump(self.files_dict, file)
            except Exception as e:
                print(f"Failed to write/parse the metadata file. {e}")
        
        # Read the scan / spectrum file dictionaries from the metadata file
        try:
            with open(self.paths["metadata_file"], "r") as file:
                metadata_obj = yaml.safe_load(file)
        except Exception as e:
            print(f"Failed to write/parse the metadata file. {e}")
            return
        
        # Update the metadata file information with the metadata read from the scan file
        try:
            scan_dict = metadata_obj.get("scan_files")
            spec_dict = metadata_obj.get("spectroscopy_files")
            file_dict = scan_dict.get(self.file_index)
            
            file_dict.update({
                "bias (V)": f"{self.bias_V:.3f}",
                "setpoint (pA)": f"{self.setpoint_pA:.3f}",
                "feedback": f"{self.feedback}",
                "date_time": self.date_time.strftime("%Y-%m-%d %H:%M:%S"),
                "frame": {
                    "scan_range (nm)": f"({self.scan_range_nm[0]:.3f}, {self.scan_range_nm[1]:.3f})",
                    "offset (nm)": f"({self.offset_nm[0]:.3f}, {self.offset_nm[1]:.3f})",
                    "angle (deg)": f"{self.angle_deg:.3f}"
                }
            })
            scan_dict.update({self.file_index: file_dict})

            new_files_dict = {
                "scan_files": scan_dict,
                "spectroscopy_files": spec_dict
            }          
            try:
                with open(self.paths["metadata_file"], "w") as file:
                    yaml.safe_dump(new_files_dict, file)
            except Exception as e:
                print(f"Failed to write/parse the metadata file. {e}")
                
        except Exception as e:
            print("Error. Failed to update the metadata dictionaries.")

        return

    def get_end_time(self):
        # Read the scan / spectrum file dictionaries from the metadata file
        try:
            with open(self.paths["metadata_file"], "r") as file:
                metadata_obj = yaml.safe_load(file)
        
            scan_dict = metadata_obj.get("scan_files")
            next_index = self.file_index + 1
            if next_index > len(scan_dict) - 1:
                return "EOT"
            next_scan = scan_dict[next_index]

            # Iterate over the spectroscopy metadata in the metadata file, and check whether the keys date_time and position exist
            print(next_scan.keys())
            if "date_time" in next_scan.keys():
                next_date_time = next_scan.get("date_time")
                print(next_date_time)
            else:
                print("No idea")

        except Exception as e:
            print(f"Failed to write/parse the metadata file. {e}")
            return
        
        return



    # Spectroscopy
    def open_spectrum_viewer(self) -> None:
        spec_shape = self.spec_files.shape
        if len(spec_shape) < 2:
            print("Error. No spectroscopy files found in the data folder.")
            return
        
        if spec_shape[0] * spec_shape[1] > 0:
            if not hasattr(self, "second_window") or self.second_window is None: # Create only if not already created:
                self.current_scan = self.load_scan()
                if isinstance(self.current_scan, np.ndarray): processed_scan = self.process_scan(self.current_scan)
                else: processed_scan = np.zeros((2, 2))
                if not hasattr(self, "associated_spectra"): self.associated_spectra = np.array([[]])
                
                self.second_window = SpectrumViewer(processed_scan, self.spec_files, self.associated_spectra, self.paths)
            self.second_window.show()
        else:
            print("Error. No spectroscopy files found in the data folder.")
        
        return

    # Scale limit functions
    def on_limits_set(self, method: str = "full", side: str = "both") -> None:
        radio_buttons = self.gui.radio_buttons
        
        match side:
            case "min": sides = ["min"]
            case "max": sides = ["max"]
            case _: sides = ["min", "max"]
        
        if method in ["full", "percentiles", "deviations", "absolute"]:
            [radio_buttons[f"{min_or_max}_{method}"].setSilentCheck(True) for min_or_max in sides]
        
        self.update_limits()
        return

    def on_full_scale(self, side: str = "both") -> None:
        if side == "min" or side == "both":
            self.radio_buttons["min_full"].setChecked(True)
            self.data.processing_flags["min_selection"] = 0
        if side == "max" or side == "both":
            self.radio_buttons["max_full"].setChecked(True)
            self.data.processing_flags["max_selection"] = 0
        self.load_process_display(new_scan = False)

        return

    def on_percentiles(self, side: str = "both") -> None:
        if side == "min" or side == "both":
            self.radio_buttons["min_percentiles"].setChecked(True)
            self.data.processing_flags["min_selection"] = 1
        if side == "max" or side == "both":
            self.radio_buttons["max_percentiles"].setChecked(True)
            self.data.processing_flags["max_selection"] = 1
        self.load_process_display(new_scan = False)

        return

    def on_standard_deviations(self, side: str = "both") -> None:
        if side == "min" or side == "both":
            self.radio_buttons["min_deviations"].setChecked(True)
            self.data.processing_flags["min_selection"] = 2
        if side == "max" or side == "both":
            self.radio_buttons["max_deviations"].setChecked(True)
            self.data.processing_flags["max_selection"] = 2
        self.load_process_display(new_scan = False)

        return

    def on_absolute_values(self, side: str = "both") -> None:
        if side == "min" or side == "both":
            self.radio_buttons["min_absolute"].setChecked(True)
            self.data.processing_flags["max_selection"] = 3
        if side == "max" or side == "both":
            self.radio_buttons["max_absolute"].setChecked(True)
            self.data.processing_flags["max_selection"] = 3
        self.load_process_display(new_scan = False)

        return

    def histogram_scale_changed(self) -> None:
        (min, max) = self.hist_item.getLevels()
        if hasattr(self, "hist_levels"):
            [min_old, max_old] = self.hist_levels

            if np.abs(max - max_old) > .0000001 * (max_old - min_old): # If the top level was changed (use a tiny threshold)
                self.gui.line_edits["max_absolute"].setText(f"{round(max, 3)}")
                self.radio_buttons["max_absolute"].setChecked(True)
                self.data.processing_flags["max_selection"] = 3

            if np.abs(min - min_old) > .0000001 * (max_old - min_old): # If the bottom level was changed
                self.gui.line_edits["min_absolute"].setText(f"{round(min, 3)}")
                self.radio_buttons["min_absolute"].setChecked(True)
                self.data.processing_flags["min_selection"] = 3

        self.hist_levels = [min, max]

        return

    def toggle_limits(self, side: str = "min") -> None:
        if side not in ["min", "max"]:
            print("Error. No correct side chosen.")
            return
        
        if side == "min":
            self.data.processing_flags["min_selection"] += 1
            if self.data.processing_flags["min_selection"] > 3: self.data.processing_flags["min_selection"] = 0
            sel = self.data.processing_flags["min_selection"]
        else:
            self.data.processing_flags["max_selection"] += 1
            if self.data.processing_flags["max_selection"] > 3: self.data.processing_flags["max_selection"] = 0
            sel = self.data.processing_flags["max_selection"]
        
        match sel:
            case 0: self.on_full_scale(side)
            case 1: self.on_percentiles(side)
            case 2: self.on_standard_deviations(side)
            case _: self.on_absolute_values(side)
        
        return

    # Matrix processing functions
    def toggle_projections(self, index) -> None:
        self.gui.comboboxes["projection"].toggleIndex(index)
        self.update_processing_flags        
        return

    def update_processing_flags(self):
        flags = self.data.processing_flags
        
        checkboxes = self.gui.checkboxes
        buttons = self.gui.buttons
        comboboxes = self.gui.comboboxes
        radio_buttons = self.gui.radio_buttons
        line_edits = self.gui.line_edits
        
        # Gaussian line edit / checkbox interconnected behavior
        try:
            entry = line_edits["gaussian_width"].text()
            
            # Extract the numeric part
            number_matches = re.findall(r"-?\d+\.?\d*", entry)
            numbers = [float(x) for x in number_matches]

            if len(numbers) > 0:
                number = numbers[0]
                flags.update({"gaussian_width_nm": number})
                
                if number == 0: checkboxes["gaussian"].setChecked(False)
            else:
                number = 0
                flags.update({"gaussian_width_nm": number})
                line_edits["gaussian_width"].setText("0 nm")
                checkboxes["gaussian"].setChecked(False)
        except:
            pass
        
        # Background
        bg_methods = ["none", "plane", "linewise"]
        for method in bg_methods:
            if radio_buttons[f"bg_{method}"].isChecked(): flags.update({"background": f"{method}"})
        
        # Limits
        lim_methods = ["full", "percentiles", "deviations", "absolute"]
        for method in lim_methods:
            if radio_buttons[f"min_{method}"].isChecked():
                min_value = line_edits[f"min_{method}"]
                flags.update({"min_method": f"{method}", "min_method_value": f"{min_value}"})
                max_value = line_edits[f"max_{method}"]
                flags.update({"max_method": f"{method}", "max_method_value": f"{max_value}"})

        try:
            direction = "backward" if buttons["direction"].isChecked() else "forward"
            projection = comboboxes["projection"].currentText()
            flags.update({"direction": direction, "projection": projection})
            [flags.update({operation: checkboxes[operation].isChecked()}) for operation in ["sobel", "normal", "laplace", "gaussian", "fft"]]
        except:
            print("Error updating the image processing flags.")

        # File name
        bare_name = f"{self.channel}_{self.file_index + 1:03d}"
        tagged_name = self.data.add_tags_to_file_name(bare_name)
        self.data.processing_flags["file_name"] = tagged_name
        
        # Update paths and line_edits
        self.paths["output_file_basename"] = tagged_name
        self.gui.line_edits["file_name"].setText(os.path.basename(tagged_name))
        self.gui.buttons["output_folder"].setText(self.paths["output_folder_name"])

        # Reload and process the scan with the updated flags
        self.load_process_display()

        return



    # Spectroscopy
    def on_toggle_spec_locations(self) -> None:
        self.data.processing_flags["spec_locations"] = self.gui.buttons["spec_locations"].isChecked()
        self.load_process_display(new_scan = True)    
        return



    # Save button
    def on_save_png(self) -> None:
        # Properly rescale to 0-255
        processed_scan = self.process_scan(self.current_scan)
        
        min_val, max_val = (self.statistics.get("min"), self.statistics.get("max"))
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
                qimg = QtGui.QImage(uint8_array.data, width, height, uint8_array.strides[0], QtGui.QImage.Format.Format_RGB888)
            else:
                height, width = uint8_array.shape
                qimg = QtGui.QImage(uint8_array, width, height, width, QtGui.QImage.Format.Format_Grayscale8)

            output_file_name = os.path.join(self.paths["output_folder"], self.paths["output_file_basename"] + ".png")
            os.makedirs(self.paths["output_folder"], exist_ok = True)
            qimg.save(output_file_name)

            msg_box = QtWidgets.QMessageBox(self)
            msg_box.setWindowTitle("Success")
            msg_box.setText("png file saved")
            QtCore.QTimer.singleShot(1000, msg_box.close)
            msg_box.exec()

            #self.check_exists_box.setText("png already exists!")
            #self.check_exists_box.setStyleSheet("background-color: orange")

        except Exception as e:
            print(f"Error saving the image file: {e}")
            pass

        return

    # Open folders
    def open_folder(self, paths_entry: str = "") -> None:
        if paths_entry in list(self.paths.keys()):
            try: os.startfile(self.paths[paths_entry])
            except: pass        
        return

    # Drag and drop
    def dragEnterEvent(self, event) -> None:
        # 2. Accept the drag if it contains URLs (files)
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event) -> None:
        # 3. Process the dropped files
        for url in event.mimeData().urls():
            file_name = url.toLocalFile()
        event.acceptProposedAction()
        if file_name:
            self.load_folder(file_name)

    # Information popup
    def on_info(self) -> None:
        msg_box = QtWidgets.QMessageBox(self)
        
        msg_box.setWindowTitle("Info")
        msg_box.setText("Scanalyzer (2026)\nby Peter H. Jacobse\nRice University; Lawrence Berkeley National Lab")
        msg_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        msg_box.setIcon(QtWidgets.QMessageBox.Icon.Information)

        #QtCore.QTimer.singleShot(5000, msg_box.close)
        retval = msg_box.exec()

    # Exit
    def closeEvent(self, a0) -> None:
        self.on_exit
    
    def on_exit(self) -> None:
        try: # Save the currently opened scan folder to the config yaml file so it opens automatically on startup next time
            scan_dict = self.files_dict.get("scan_files")
            with open(self.paths["config_path"], "w") as file:
                yaml.safe_dump({"last_file": str(scan_dict[self.file_index].get("path"))}, file)
        except Exception as e:
            print("Failed to save the scan folder to the config.yml file.")
            print(e)
        print("Thank you for using Scanalyzer!")
        QtWidgets.QApplication.instance().quit()



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = AppWindow()
    window.show()
    sys.exit(app.exec())