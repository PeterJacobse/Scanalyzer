import os, sys, re, yaml
import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
from lib import ScanalyzerGUI, HoverTargetItem, DataProcessing, FileFunctions, Spectralyzer



class Scanalyzer(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.parameters_init()
        self.gui = ScanalyzerGUI()
        self.connect_buttons()

        # Initialize the ImageView from the last session
        (yaml_data, error) = self.file_functions.load_yaml(self.paths["config_path"])
        if not error: last_file = yaml_data.get("last_file", None)
        if last_file: self.load_folder(last_file)
        
        self.gui.show()



    def parameters_init(self) -> None:
        # Paths
        scanalyzer_path = os.path.abspath(__file__) # The full path of Scanalyzer.py, including the filename itself
        scanalyzer_folder = os.path.dirname(scanalyzer_path) # The parent directory of Scanalyzer.py
        
        sys_folder = os.path.join(scanalyzer_folder, "sys") # The directory of the config file
        config_path = os.path.join(sys_folder, "config.yml") # The path to the configuration file
        
        lib_folder = os.path.join(scanalyzer_folder, "lib") # The directory of the Scanalyzer package
        spectralyzer_path = os.path.join(lib_folder, "Spectralyzer.py") # The path to Spectralyzer
        
        icon_folder = os.path.join(scanalyzer_folder, "icons") # The directory of the icon files
        
        data_folder = sys_folder # Set current folder to the config file; read from the config file later to reset it to a data folder
        metadata_file = os.path.join(data_folder, "metadata.yml") # Metadata file that is populated with all the scan and spectroscopy metadata of the files in the data folder
        output_folder_name = "Extracted Files"

        self.paths = {
            "scanalyzer_path": scanalyzer_path,
            "scanalyzer_folder": scanalyzer_folder,
            "spectralyzer_path": spectralyzer_path,
            "spectralyzer_folder": lib_folder,
            "sys_folder": sys_folder,
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
        
        # Some attributes
        self.files_dict = {}
        self.spec_files = np.array([[]])
        self.image_files = [""]
        self.file_index = 0
        self.selected_file = ""
        self.channels = []
        self.channel = ""
        self.spec_targets = []
        self.file_functions = FileFunctions()
        self.data = DataProcessing()

    def connect_buttons(self) -> None:
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
            
            if name in shortcuts.keys():
                shortcut = QtGui.QShortcut(shortcuts[name], self.gui)
                shortcut.activated.connect(connected_function)
        
        QKey = QtCore.Qt.Key
        QMod = QtCore.Qt.Modifier
        QSeq = QtGui.QKeySequence
        QShc = QtGui.QShortcut
        
        # Background
        [radio_buttons[name].clicked.connect(self.update_processing_flags) for name in ["bg_none", "bg_plane", "bg_linewise", "min_absolute", "min_deviations", "min_percentiles", "min_full", "max_absolute", "max_deviations", "max_percentiles", "max_full"]]
        radio_buttons["bg_none"].setShortcut(QSeq(QKey.Key_0))
        radio_buttons["bg_plane"].setShortcut(QSeq(QKey.Key_P))
        radio_buttons["bg_linewise"].setShortcut(QSeq(QKey.Key_L))

        # Matrix operations
        [checkboxes[operation].clicked.connect(self.update_processing_flags) for operation in ["sobel", "gaussian", "normal", "fft", "laplace", "rotation", "offset"]]
        checkboxes["sobel"].setShortcut(QSeq(QMod.SHIFT | QKey.Key_S))
        checkboxes["normal"].setShortcut(QSeq(QMod.SHIFT | QKey.Key_N))
        checkboxes["gaussian"].setShortcut(QSeq(QMod.SHIFT | QKey.Key_G))
        checkboxes["fft"].setShortcut(QSeq(QMod.SHIFT | QKey.Key_F))
        checkboxes["laplace"].setShortcut(QSeq(QMod.SHIFT | QKey.Key_L))
        checkboxes["offset"].setShortcut(QSeq(QMod.SHIFT | QKey.Key_O))
        checkboxes["rotation"].setShortcut(QSeq(QMod.SHIFT | QKey.Key_R))

        # Limits control group
        toggle_min_shortcut = QShc(QSeq(QKey.Key_Minus), self.gui)
        toggle_min_shortcut.activated.connect(lambda: self.on_limits_set("toggle", "min"))
        toggle_max_shortcut = QShc(QSeq(QKey.Key_Equal), self.gui)
        toggle_max_shortcut.activated.connect(lambda: self.on_limits_set("toggle", "max"))

        next_projection_shortcut = QShc(QSeq(QMod.SHIFT | QKey.Key_Down), self.gui)
        next_projection_shortcut.activated.connect(lambda: self.toggle_projections(1))
        next_projection_shortcut = QShc(QSeq(QMod.SHIFT | QKey.Key_Up), self.gui)
        next_projection_shortcut.activated.connect(lambda: self.toggle_projections(-1))
        
        comboboxes["channels"].currentIndexChanged.connect(self.update_processing_flags)
        comboboxes["projection"].currentIndexChanged.connect(self.update_processing_flags)
        line_edits["gaussian_width"].editingFinished.connect(self.gaussian_width_edited)
        
        direction_shortcut = QShc(QSeq(QKey.Key_X), self.gui)
        direction_shortcut.activated.connect(self.toggle_direction)
        
        exit_shortcuts = [QShc(QSeq(keystroke), self.gui) for keystroke in [QKey.Key_Q, QKey.Key_E, QKey.Key_Escape]]
        [exit_shortcut.activated.connect(self.on_exit) for exit_shortcut in exit_shortcuts]

        self.hist = self.gui.image_view.getHistogramWidget()
        self.hist_item = self.hist.item
        self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)
        
        self.gui.dataDropped.connect(self.on_receive_filename)

        return



    # Selection and toggling
    def on_file_index_change(self, index: int = 1) -> None:
        scan_dict = self.files_dict.get("scan_files")
        self.file_index += index
        if self.file_index < 0: self.file_index = len(scan_dict) - 1
        if self.file_index > len(self.files_dict.get("scan_files")) - 1: self.file_index = 0
        self.load_process_display(new_scan = True)
        return

    def on_select_file(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Open file", self.paths["data_folder"], "SXM files (*.sxm);;Dat files (*.dat);;HDF5 files (*.hdf5)")
        if file_path: self.load_folder(file_path)
        return

    def on_receive_filename(self, file_name) -> None:
        if os.path.exists(file_name): self.load_folder(file_name)
        
        return

    # Channel selection
    def on_chan_index_change(self, index: int = 1) -> None:
        self.gui.comboboxes["channels"].toggleIndex(index)
        self.update_processing_flags()
        return

    # Direction
    def toggle_direction(self) -> None:
        self.gui.buttons["direction"].setChecked(not self.gui.buttons["direction"].isChecked())
        self.update_processing_flags()
        return

    # Projections
    def toggle_projections(self, index) -> None:
        self.gui.comboboxes["projection"].toggleIndex(index)
        self.update_processing_flags()
        return



    # Routines for loading a new image
    def load_folder(self, file_path: str = "") -> None:
        buttons = self.gui.buttons
        labels = self.gui.labels
        
        self.files_dict = {}

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
            self.file_index = 0
            for key, value in scan_dict.items():
                if os.path.samefile(value.get("path"), file_path):
                    self.file_index = key
                    break
            if self.file_index > len(scan_dict) - 1: self.file_index = 0 # Roll over if the selected file index is too large
            
            # Update folder/contents labels
            try:
                buttons["folder_name"].setText(self.paths["data_folder"])
                if len(scan_dict) == 1: labels["number_of_files"].setText("which contains 1 sxm file")
                else: labels["number_of_files"].setText(f"which contains {len(scan_dict)} sxm files")
            except Exception as e:
                print(f"Error: {e}")

            
            
            # Continue with loading the scan file and displaying it in the gui
            if len(scan_dict) > 0: self.load_process_display(new_scan = True)

        except Exception as e:
            print(f"Error loading folder: {e}")
            buttons["select_file"].setText("Select file")
        
        return

    def load_process_display(self, new_scan: bool = False) -> None:
        if new_scan or not hasattr(self, "current_scan"):
            (self.current_scan, channel, frame, error) = self.load_scan_file()
            self.frame = frame
        
        if isinstance(self.current_scan, np.ndarray):
            (processed_scan, statistics, limits, error) = self.process_scan(self.current_scan)
            if not error:
                self.display(processed_scan, limits, self.frame)
            else:
                print("Error. Could not load scan.")
        else:
            print("Error. Could not load scan.")
        return

    def load_scan_file(self) -> tuple[np.ndarray, str, dict, bool | str]:
        # Load the sxm file from the list of sxm files. Make the select file button display the file name
        labels = self.gui.labels
        comboboxes = self.gui.comboboxes

        # Scan dict is the subdict of files_dict
        scan_dict = self.files_dict.get("scan_files")
        try:
            scan_file_entry = scan_dict[self.file_index]
            self.gui.buttons["select_file"].setText(scan_file_entry.get("file_name"))
        except:
            print("Error. Could not retrieve scan.")
            return

        # Use the global variabls file_index to extract the path of the requested scan from the dict
        if self.file_index < 0: self.file_index = len(scan_dict) - 1
        if self.file_index > len(scan_dict) - 1: self.file_index = 0
        scan_file_path = scan_file_entry.get("path")



        # Load the scan object using nanonispy2. Update the channels combobox according to the channels present in the scan
        try:
            (scan_object, error) = self.file_functions.get_scan(scan_file_path, units = {"length": "nm", "current": "pA"})
            if error: raise

            channels = scan_object.channels
            comboboxes["channels"].renewItems(channels)
        except Exception as e:
            print(f"{e}")

        # Read the metadata, the metadata file and update if necessary
        try:
            self.read_metadata(scan_object)
            self.get_end_time()
            pass
        except Exception as e:
            print(f"{e}")

        # Find the spectra associated with this scan and make them available for viewing as target items and in the combobox
        #self.find_associated_spectra()
        
        
        
        # Extract the image from the scan object using the processing flags available in the data object        
        (image, selected_channel, frame, error) = self.data.pick_image_from_scan_object(scan_object)
        comboboxes["channels"].selectItem(selected_channel)
        if error:
            print(f"{error}")
            return

        return (image, selected_channel, frame, error)

    def find_associated_spectra(self) -> None:
        # From the list of spectra (spec_files), select the ones that are associated with the current scan (associated scan name is column 3 in self.spec_files and column 0 in self.sxm_files)
        try:
            #associated_spectra_indices = np.where(self.spec_files[:, 3] == self.sxm_file[0])[0]
            self.associated_spectra = [self.spec_files[index] for index in [0, 1, 2]]
        except:
            self.associated_spectra = []

        # Update the spectra combobox
        self.comboboxes["spectra"].renewItems([spectrum[0] for spectrum in self.associated_spectra])

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

    def process_scan(self, image: np.ndarray) -> tuple[np.ndarray, dict, list, bool | str]:
        (processed_scan, statistics, limits, error) = self.data.process_scan(image)
        
        channel = self.data.processing_flags["channel"]
        
        if channel == "X" or channel == "Y" or channel == "Z": unit_label = " nm"
        elif channel == "Current": unit_label = " pA"
        else: unit_label = ""
        self.gui.labels["statistics"].setText(f"\nValue range: {round(statistics.get("range_total"), 3)}{unit_label}; Mean ± std dev: {round(statistics.get("mean"), 3)} ± {round(statistics.get("standard_deviation"), 3)}{unit_label}")
        
        return (processed_scan, statistics, limits, error)

    def display(self, scan: np.ndarray, limits: list, frame: dict) -> None:
        # Disable the histogram widget from triggering anything
        try: self.hist_item.sigLevelChangeFinished.disconnect()
        except: pass
            
        # Upload the scan image to the pyqtgraph ImageView    
        try:
            scan_range_nm = frame.get("scan_range_nm")
            angle_deg = frame.get("angle_deg")
            offset_nm = frame.get("offset_nm")
            
            w = scan_range_nm[0]
            h = scan_range_nm[1]
            x = offset_nm[0]
            y = offset_nm[1]                
            
            self.gui.image_view.setImage(scan, autoRange = True) # Show the scan in the app
            image_item = self.gui.image_view.getImageItem()
            if self.data.processing_flags["offset"] == True:
                image_item.setRect(QtCore.QRectF(x - w / 2, y - h / 2, w, h)) # Add dimensions to the ImageView object
            else:
                image_item.setRect(QtCore.QRectF(- w / 2, - h / 2, w, h)) # Add dimensions to the ImageView object
            if self.data.processing_flags["rotation"] == True:
                image_item.setRotation(angle_deg)
            else:
                image_item.setRotation(0)
            self.gui.image_view.autoRange()
        except:
            pass
        
        # Spectroscopy locations
        if self.data.processing_flags["spec_locations"]:
            view_box = self.gui.image_view.getView()        
            for target in self.spec_targets: view_box.addItem(target)

        # Reset the limits and histogram
        self.hist_levels = list(self.hist_item.getLevels())
        [min_hist, max_hist] = self.hist_levels
        self.gui.line_edits["min_full"].setText(f"{min_hist:E}")
        self.gui.line_edits["max_full"].setText(f"{max_hist:E}")
        
        if isinstance(limits, list) or isinstance(limits, np.ndarray):
            min = limits[0]
            max = limits[1]
            self.hist_item.setLevels(min, max)
        
        self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)

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

    def read_metadata(self, scan_object):
        bias = scan_object.bias
        bias_V = bias.to("V").magnitude
        
        offset = scan_object.offset
        offset_nm = [range_dim.to("nm").magnitude for range_dim in offset]
        
        angle = scan_object.angle
        angle_deg = angle.to("degree").magnitude
        
        scan_range = scan_object.scan_range
        scan_range_nm = [range_dim.to("nm").magnitude for range_dim in scan_range]
        self.data.processing_flags.update({"scan_range_nm": scan_range_nm})
        
        setpoint = scan_object.setpoint
        setpoint_pA = setpoint.to("pA").magnitude        
        
        feedback = scan_object.feedback # Read whether the scan was recorded in STM feedback
        date_time = scan_object.date_time

        # Display scan data in the app
        if feedback: self.summary_text = f"STM topographic scan recorded on\n{date_time.strftime('%Y/%m/%d   at   %H:%M:%S')}\n\n(V = {bias_V:.3f} V; I_fb = {setpoint_pA:.3f} pA)\nScan range: {scan_range_nm[0]:.3f} nm by {scan_range_nm[1]:.3f} nm"
        else: self.summary_text = f"Constant height scan recorded on\n{date_time.strftime('%Y/%m/%d   at   %H:%M:%S')}\n\n(V = {bias_V:.3f} V)\nScan range: {scan_range_nm[0]:.3f} nm by {scan_range_nm[1]:.3f} nm"
        self.gui.labels["scan_summary"].setText(self.summary_text)


 
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
                "bias (V)": f"{bias_V:.3f}",
                "setpoint (pA)": f"{setpoint_pA:.3f}",
                "feedback": f"{feedback}",
                "date_time": date_time.strftime("%Y-%m-%d %H:%M:%S"),
                "frame": {
                    "scan_range (nm)": f"({scan_range_nm[0]:.3f}, {scan_range_nm[1]:.3f})",
                    "offset (nm)": f"({offset_nm[0]:.3f}, {offset_nm[1]:.3f})",
                    "angle (deg)": f"{angle_deg:.3f}"
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
            if "date_time" in next_scan.keys():
                next_date_time = next_scan.get("date_time")
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
                self.current_scan = self.load_scan_file()
                if isinstance(self.current_scan, np.ndarray): processed_scan = self.process_scan(self.current_scan)
                else: processed_scan = np.zeros((2, 2))
                if not hasattr(self, "associated_spectra"): self.associated_spectra = np.array([[]])
                
                self.spectralyzer = Spectralyzer(processed_scan, self.spec_files, self.associated_spectra, self.paths)
            self.spectralyzer.show()
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
        
        if method == "toggle":
            pass
        
        self.update_processing_flags()
        return

    def histogram_scale_changed(self) -> None:
        (min, max) = self.hist_item.getLevels()
        if hasattr(self, "hist_levels"):
            [min_old, max_old] = self.hist_levels

            if np.abs(max - max_old) > .0000001 * (max_old - min_old): # If the top level was changed (use a tiny threshold)
                self.gui.line_edits["max_absolute"].setText(f"{round(max, 3)}")
                self.gui.radio_buttons["max_absolute"].setChecked(True)
                self.data.processing_flags["max_selection"] = 3

            if np.abs(min - min_old) > .0000001 * (max_old - min_old): # If the bottom level was changed
                self.gui.line_edits["min_absolute"].setText(f"{round(min, 3)}")
                self.gui.radio_buttons["min_absolute"].setChecked(True)
                self.data.processing_flags["min_selection"] = 3

        self.hist_levels = [min, max]

        return

    # Update all the processing flags
    def gaussian_width_edited(self):
        flags = self.data.processing_flags
        g_le = self.gui.line_edits["gaussian_width"]
        g_cb = self.gui.checkboxes["gaussian"]
        
        # Gaussian line edit / checkbox interconnected behavior
        try:
            entry = g_le.text()
            
            # Extract the numeric part
            number_matches = re.findall(r"-?\d+\.?\d*", entry)
            numbers = [float(x) for x in number_matches]

            if len(numbers) < 1: # Not a number: reset to zero and uncheck the checkbox
                g_le.setText("0 nm")
                g_cb.setChecked(False)
                flags.update({"gaussian_width_nm": 0})

            else:
                number = numbers[0]
                if number < .00001: # The number that was entered was zero
                    g_le.setText("0 nm")
                    g_cb.setChecked(False)
                    flags.update({"gaussian_width_nm": 0})
                else: # A non-zero number was entered
                    g_cb.setChecked(True)
                    flags.update({"gaussian_width_nm": number})
        except:
            pass
        self.update_processing_flags()

    def update_processing_flags(self):
        flags = self.data.processing_flags
        
        checkboxes = self.gui.checkboxes
        buttons = self.gui.buttons
        comboboxes = self.gui.comboboxes
        radio_buttons = self.gui.radio_buttons
        line_edits = self.gui.line_edits
        

        
        # Background
        bg_methods = ["none", "plane", "linewise"]
        for method in bg_methods:
            if radio_buttons[f"bg_{method}"].isChecked(): flags.update({"background": f"{method}"})
        [flags.update({operation: checkboxes[operation].isChecked()}) for operation in ["rotation", "offset"]]
        
        # Limits
        lim_methods = ["full", "percentiles", "deviations", "absolute"]
        for method in lim_methods:
            if radio_buttons[f"min_{method}"].isChecked():
                min_value = float(line_edits[f"min_{method}"].text())
                flags.update({"min_method": f"{method}", "min_method_value": f"{min_value}"})
            if radio_buttons[f"max_{method}"].isChecked():
                max_value = float(line_edits[f"max_{method}"].text())
                flags.update({"max_method": f"{method}", "max_method_value": f"{max_value}"})

        # Channel, direction, projection
        try:
            channel = comboboxes["channels"].currentText()
            direction = "backward" if buttons["direction"].isChecked() else "forward"
            projection = comboboxes["projection"].currentText()
            flags.update({"channel": channel, "direction": direction, "projection": projection})
        except:
            print("Error updating the image processing flags.")
        
        # Operations
        try: [flags.update({operation: checkboxes[operation].isChecked()}) for operation in ["sobel", "normal", "laplace", "gaussian", "fft"]]
        except: pass

        # File name
        bare_name = f"{channel}_{self.file_index + 1:03d}"
        tagged_name = self.data.add_tags_to_file_name(bare_name)
        self.data.processing_flags["file_name"] = tagged_name
        
        # Update paths and line_edits
        self.paths["output_file_basename"] = tagged_name
        self.gui.line_edits["file_name"].setText(os.path.basename(tagged_name))
        self.gui.buttons["output_folder"].setText(self.paths["output_folder_name"])

        # Reload and process the scan with the updated flags
        self.load_process_display(new_scan = True)

        return



    # Spectroscopy
    def on_toggle_spec_locations(self) -> None:
        self.data.processing_flags["spec_locations"] = self.gui.buttons["spec_locations"].isChecked()
        self.load_process_display(new_scan = True)    
        return



    # Save button
    def on_save_png(self) -> None:
        # Properly rescale to 0-255
        (processed_scan, statistics, limits, error) = self.data.process_scan(self.current_scan)
        
        [min_val, max_val] = [float(self.data.processing_flags.get("min_limit")), float(self.data.processing_flags.get("max_limit"))]
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

            msg_box = QtWidgets.QMessageBox(self.gui)
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

    # Information popup
    def on_info(self) -> None:
        msg_box = QtWidgets.QMessageBox(self.gui)
        
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
        scan_dict = self.files_dict.get("scan_files")
        data = {"last_file": str(scan_dict[self.file_index].get("path"))}
        save_path = self.paths["config_path"], "w"
        
        error = self.file_functions.save_yaml(data, save_path)        
        print("Thank you for using Scanalyzer!")
        QtWidgets.QApplication.instance().quit()



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = Scanalyzer()
    sys.exit(app.exec())
