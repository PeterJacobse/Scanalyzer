import os, sys, re, yaml, pint
import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import pyqtgraph.exporters as expts
from . import DataProcessing, FileFunctions
from .gui_spectralyzer import SpectralyzerGUI
from datetime import datetime



class Spectralyzer:
    def __init__(self, data_folder_path: str = "", scan_file_name: str = "", scan_image: np.ndarray = np.zeros((2, 2)), scan_frame: dict = {}, spec_targets: list = []):
        super().__init__()
        
        self.scan_file_name = scan_file_name
        self.spec_targets = spec_targets
        self.parameters_init()
        self.gui = SpectralyzerGUI()
        self.show_scan(scan_image, scan_frame)
        
        self.connect_buttons()        
        if os.path.exists(data_folder_path): self.load_folder(data_folder_path)
        self.set_focus_row(0)



    def show(self) -> None:
        self.gui.show()
        return

    def parameters_init(self) -> None:
        # Paths
        spectralyzer_path = os.path.abspath(__file__) # Path of Spectralyzer
        lib_folder = os.path.dirname(spectralyzer_path) # Path of the lib folder
        scanalyzer_folder = os.path.dirname(lib_folder) # The parent directory of Scanalyzer.py
        scanalyzer_path = os.path.join(scanalyzer_folder, "Scanalyzer.py") # The parent directory of Scanalyzer.py
        
        sys_folder = os.path.join(scanalyzer_folder, "sys") # The directory of the config file
        config_path = os.path.join(sys_folder, "config.yml") # The path to the configuration file
        
        icon_folder = os.path.join(scanalyzer_folder, "icons") # The directory of the icon files
        
        data_folder = sys_folder # Set current folder to the config file; read from the config file later to reset it to a data folder
        metadata_file = os.path.join(data_folder, "metadata.yml") # Metadata file that is populated with all the scan and spectroscopy metadata of the files in the data folder
        output_folder_name = "Extracted Files"

        self.paths = {
            "scanalyzer_folder": scanalyzer_folder,
            "scanalyzer_path": scanalyzer_path,
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
        icon_files = os.listdir(icon_folder)
        self.icons = {}
        for icon_file in icon_files:
            [icon_name, extension] = os.path.splitext(os.path.basename(icon_file))
            try:
                if extension == ".png": self.icons.update({icon_name: QtGui.QIcon(os.path.join(icon_folder, icon_file))})
            except:
                pass

        # Some attributes
        self.focus_row = 0
        self.direction_index = 2
        self.view_mode = "dark"
        self.files_dict = {}
        self.spec_list = np.array((0, 3), dtype = object)
        self.file_functions = FileFunctions()
        self.data = DataProcessing()

    def show_scan(self, scan_image: np.ndarray = np.zeros((2, 2)), scan_frame: dict = {}) -> None:
        img = self.gui.image_item
        plot = self.gui.plot_item
        
        img.setImage(scan_image)
        scan_range_nm = scan_frame.get("scan_range_nm", [100, 100])
        [w, h] = scan_range_nm
        img.setRect(-0.5 * w, -0.5 * h, w, h)
        plot.addItem(img)
        
        for target in self.spec_targets:
            plot.addItem(target)
            target.clicked.connect(self.target_clicked)
        
        self.gui.line_edits["scan_file_name"].setText(f"{self.scan_file_name}")
        
        return



    def target_clicked(self, text: str = "") -> None:
        target_index = None
        target_spec_name = text.split("\n")[0]
        
        for row, combobox in self.gui.plot_number_comboboxes.items():
            cbb_index = combobox.currentIndex()
            cbb_spectrum = self.spec_list[cbb_index]
            cbb_spec_name = cbb_spectrum[0]
            
            if cbb_spec_name == ">>" + target_spec_name:
                target_index = int(row)
                break

        if isinstance(target_index, int): self.set_focus_row(target_index)        
        return

    def connect_buttons(self) -> None:
        buttons = self.gui.buttons
        plot_number_comboboxes = self.gui.plot_number_comboboxes

        buttons["save_0"].clicked.connect(lambda: self.on_save_spectrum(0))
        buttons["save_1"].clicked.connect(lambda: self.on_save_spectrum(1))
        buttons["open_folder"].clicked.connect(self.on_select_file)
        buttons["view_folder"].clicked.connect(lambda: self.open_folder("data_folder"))
        buttons["output_folder_0"].clicked.connect(lambda: self.open_folder("output_folder"))
        buttons["output_folder_1"].clicked.connect(lambda: self.open_folder("output_folder"))
        buttons["exit"].clicked.connect(self.on_exit)
        buttons["direction"].clicked.connect(self.toggle_spec_direction)
        buttons["log_abs_0"].clicked.connect(self.update_processing_flags)
        buttons["log_abs_1"].clicked.connect(self.update_processing_flags)
        buttons["differentiate_0"].clicked.connect(self.update_processing_flags)
        buttons["differentiate_1"].clicked.connect(self.update_processing_flags)
        buttons["smooth"].clicked.connect(self.update_processing_flags)
        buttons["view_mode"].clicked.connect(self.change_view_mode)
        
        chan_sel_boxes = [self.gui.channel_selection_comboboxes[name] for name in ["x_axis", "y_axis_0", "y_axis_1"]]
        [combobox.currentIndexChanged.connect(lambda: self.update_processing_flags(toggle_channelbox = False)) for combobox in chan_sel_boxes]
        self.gui.metadata_combobox.selectIndex(3)
        self.gui.metadata_combobox.currentIndexChanged.connect(self.update_processing_flags)
        self.gui.checkboxes["all"].toggled.connect(lambda: self.check_checkbox("all"))
        fr_cbb = self.gui.focus_row_combobox
        fr_cbb.currentIndexChanged.connect(lambda index = fr_cbb.currentIndex(): self.set_focus_row(index, increase = False))
        
        for index in range(len(plot_number_comboboxes)):
            self.gui.consecutives[f"{index}"].clicked.connect(lambda checked, idx = index: self.set_consecutive(idx))
            plot_number_comboboxes[f"{index}"].currentIndexChanged.connect(lambda: self.update_processing_flags(toggle_channelbox = False))
            self.gui.left_arrows[f"{index}"].clicked.connect(lambda checked, idx = index: self.toggle_plot_number(idx, True))
            self.gui.right_arrows[f"{index}"].clicked.connect(lambda checked, idx = index: self.toggle_plot_number(idx, False))

        [self.gui.line_edits[name].editingFinished.connect(lambda: self.update_processing_flags(toggle_channelbox = False)) for name in ["line_width", "opacity"]]
        [self.gui.line_edits[name].editingFinished.connect(lambda: self.update_processing_flags(toggle_channelbox = False)) for name in ["offset_0", "offset_1"]]
        self.gui.line_edits["window"].editingFinished.connect(self.update_processing_flags)

        QKey = QtCore.Qt.Key
        QSeq = QtGui.QKeySequence
        QShc = QtGui.QShortcut

        exit_shortcuts = [QShc(QSeq(keystroke), self.gui) for keystroke in [QKey.Key_Q, QKey.Key_Escape]]
        [exit_shortcut.activated.connect(self.on_exit) for exit_shortcut in exit_shortcuts]

        focus_shortcuts = []
        for index, keystroke in enumerate([QKey.Key_0, QKey.Key_1, QKey.Key_2, QKey.Key_3, QKey.Key_4, QKey.Key_5, QKey.Key_6, QKey.Key_7,
                                           QKey.Key_8, QKey.Key_9, QKey.Key_A, QKey.Key_B, QKey.Key_C, QKey.Key_D, QKey.Key_E, QKey.Key_F]):
            focus_shortcut = QShc(QSeq(keystroke), self.gui)
            focus_shortcut.activated.connect(lambda i = index: self.set_focus_row(i))
            focus_shortcuts.append(focus_shortcut)
        
        toggle_shortcuts = [QShc(QSeq(keystroke), self.gui) for keystroke in [QKey.Key_Up, QKey.Key_Down, QKey.Key_Left, QKey.Key_Right, QKey.Key_Space]]
        [self.up_shortcut, self.down_shortcut, self.left_shortcut, self.right_shortcut, self.checkbox_shortcut] = toggle_shortcuts
        
        self.gui.buttons["dec_focus_row"].clicked.connect(lambda: self.set_focus_row(-1, increase = False))
        self.up_shortcut.activated.connect(lambda: self.set_focus_row(-1, increase = False))
        self.gui.buttons["inc_focus_row"].clicked.connect(lambda: self.set_focus_row(-1, increase = True))
        self.down_shortcut.activated.connect(lambda: self.set_focus_row(-1, increase = True))

        buttons["dec_line_width"].clicked.connect(lambda: self.width_opacity_change("width", -100))
        buttons["inc_line_width"].clicked.connect(lambda: self.width_opacity_change("width", 100))
        buttons["dec_opacity"].clicked.connect(lambda: self.width_opacity_change("opacity", -1))
        buttons["inc_opacity"].clicked.connect(lambda: self.width_opacity_change("opacity", 2))
        
        buttons["x_axis"].clicked.connect(lambda: self.update_processing_flags(toggle_channelbox = "x_axis"))
        buttons["y_axis_0"].clicked.connect(lambda: self.update_processing_flags(toggle_channelbox = "y_axis_0"))
        buttons["y_axis_1"].clicked.connect(lambda: self.update_processing_flags(toggle_channelbox = "y_axis_1"))
        [x_axis_shortcut, y_axis_0_shortcut, y_axis_1_shortcut] = [QShc(QSeq(keystroke), self.gui) for keystroke in [QKey.Key_X, QKey.Key_Y, QKey.Key_Z]]
        x_axis_shortcut.activated.connect(lambda: self.update_processing_flags(toggle_channelbox = "x_axis"))
        y_axis_0_shortcut.activated.connect(lambda: self.update_processing_flags(toggle_channelbox = "y_axis_0"))
        y_axis_1_shortcut.activated.connect(lambda: self.update_processing_flags(toggle_channelbox = "y_axis_1"))

        # Connect the checkboxes
        [checkbox.toggled.connect(lambda: self.update_processing_flags(toggle_channelbox = False)) for checkbox in self.gui.checkboxes.values()]
        
        self.gui.dataDropped.connect(self.load_folder)
        
        return

    def change_view_mode(self) -> None:
        checked = self.gui.buttons["view_mode"].isChecked()
        if checked:
            self.view_mode = "bright"
            self.gui.buttons["view_mode"].setIcon(self.icons.get("bright_mode"))
            for number in range(len(self.gui.left_arrows)):
                self.gui.checkboxes[f"{number}"].setStyleSheet(f"QCheckBox {{color: {self.gui.inv_color_list[number]}; background-color: white; font-weight: bold}}")
        else:
            self.view_mode = "dark"
            self.gui.buttons["view_mode"].setIcon(self.icons.get("dark_mode"))
            for number in range(len(self.gui.left_arrows)):
                self.gui.checkboxes[f"{number}"].setStyleSheet(f"QCheckBox {{color: {self.gui.color_list[number]}; background-color: black; font-weight: bold}}")
        
        self.redraw_spectra()        
        return

    def on_select_file(self) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(None, "Open file", self.paths["data_folder"], "Dat files (*.dat)")
        if file_path: self.load_folder(file_path)
        return

    def load_folder(self, path) -> None:
        if os.path.isfile(path): folder_name = os.path.dirname(path)
        elif os.path.isdir(path): folder_name = path
        else:
            print("Error. Invalid file/folder.")
            return
        
        self.paths["data_folder"] = folder_name
        self.paths["output_folder"] = os.path.join(folder_name, self.paths["output_folder_name"])
        self.paths["metadata_file"] = os.path.join(folder_name, "metadata.yml")
        self.gui.buttons["open_folder"].setText(folder_name)



        loaded_files_dict = {}
        try:
            if os.path.exists(self.paths["metadata_file"]): # Metadata file already exists. Load metadata from file
                (loaded_files_dict, error) = self.file_functions.load_yaml(self.paths["metadata_file"])
        except:
            pass
        
        if "spectroscopy_files" in loaded_files_dict.keys() and "scan_files" in loaded_files_dict.keys(): # File loaded successfully. Roll with it
            files_dict = loaded_files_dict
            print(f"Found the scan and spectroscopy metadata in file {self.paths["metadata_file"]}")
        
        else: # No file exists, is loaded or file did not load successfully. Create from scratch by reading all the files in the folder
        
            # 1: Create an empty files dictionary
            (files_dict, error) = self.file_functions.create_empty_files_dict(folder_name)
            if error:
                print(f"Error creating the files_dict: {error}")
                return
            
            # 2: Populate it with spectroscopy headers
            (files_dict, error) = self.file_functions.populate_spectroscopy_headers(files_dict)
            if error:
                print(f"Error populating spectroscopy headers: {error}")
                return
            
            # 3: Populate it with scan headers
            (files_dict, error) = self.file_functions.populate_scan_headers(files_dict)
            if error:
                print(f"Error populating scan headers: {error}")
                return
            
            # 4: Use the scan headers and spectroscopy headers to associate spectra with scans, and update the dictionary accordingly
            (files_dict, error) = self.file_functions.populate_associated_scans(files_dict)
            if error:
                print(f"Error associating spectra and scans: {error}")
                return
            
            # 5: Save the fully populated dicts to a metadata.yml file
            error = self.file_functions.save_files_dict(files_dict, folder_name)
            if error:
                print(f"Error saving the files_dict to the metadata.yml file: {error}")
                return
            
            print(f"Loaded all scan and spectroscopy metadata and saved to file {self.paths["metadata_file"]}")



        # 6: Populate the spectroscopy dictionary with spectroscopy objects, from which the spectra can be extracted
        (files_dict, error) = self.file_functions.populate_spec_objects(files_dict)
        if error:
            print(f"Error retrieving spectroscopy objects: {error}")
            return
   
        # 7: All operations successful. Save the populated files_dict as Spectralyzer attribute. Then move on with reading the spectroscopy files/objects
        self.files_dict = files_dict
        self.read_spectroscopy_files()
        
        return

    def read_spectroscopy_files(self) -> None:
        channel_selection_comboboxes = self.gui.channel_selection_comboboxes
        plot_number_comboboxes = self.gui.plot_number_comboboxes
        checkboxes = self.gui.checkboxes
        spec_list = []
        all_channels = []

        # Extract the channels from the spec objects, then remove duplicates. Also, build a list of spec files, with names and associated scan files
        try:
            spec_dict = self.files_dict.get("spectroscopy_files")
            
            for key, single_spec_file in spec_dict.items():
                if not isinstance(single_spec_file, dict): continue
                
                spec_object = single_spec_file.get("spec_object")
                channels = single_spec_file.get("channels")
                spec_file_name = single_spec_file.get("file_name")
                associated_scan_name = single_spec_file.get("associated_scan_name")
                spec_x = single_spec_file.get("x (nm)")
                spec_y = single_spec_file.get("y (nm)")
                spec_z = single_spec_file.get("z (nm)")
                datetime = single_spec_file.get("date_time_str")
                
                [all_channels.append(str(channel)) for channel in channels]
                spec_list.append([spec_file_name, associated_scan_name, spec_object, spec_x, spec_y, spec_z, datetime])
            
            all_channels_set = set(all_channels) # Duplicate entries are automatically removed from sets
            all_channels_filt_set = {item for item in all_channels_set if not "[filt]" in item}
            all_channels_filt_set_2 = {item for item in all_channels_filt_set if not "[bwd]" in item}
            all_channels = list(all_channels_filt_set_2)
            self.spec_list = np.array(spec_list)
            [channel_selection_comboboxes[axis].renewItems(all_channels) for axis in ["x_axis", "y_axis_0", "y_axis_1"]]
            
        except:
            pass
                
        # Attempt to set the channel toggle boxes to logical starting defaults
        try:
            x_axis_targets = ["Bias (V)", "Bias calc (V)"]
            for label in x_axis_targets:
                if label in all_channels:
                    channel_selection_comboboxes["x_axis"].selectItem(label)
                    break

            y_axis_0_targets = ["LI Demod 1 X (A)", "LI Demod 1 Y (A)", "Current (A)"]
            for label in y_axis_0_targets:
                if label in all_channels:
                    channel_selection_comboboxes["y_axis_0"].selectItem(label)
                    break

            y_axis_1_targets = ["Current (A)", "Current (A)", "Current calc (A)"]
            for label in y_axis_1_targets:
                if label in all_channels:
                    channel_selection_comboboxes["y_axis_0"].selectItem(label)
                    break
        except Exception as e:
            print(f"Error while trying to set the comboboxes to default values: {e}")
        
        # If there were no scans (and channels) found, return
        if len(all_channels) < 1: return

        # Emphasize spectrum names that are associated with the scan by adding '>>'; then initialize the comboboxes
        associated_scan_indices = []
        for index, item in enumerate(self.spec_list):
            associated_scan_name = item[1]
            if associated_scan_name == self.scan_file_name:
                item[0] = f">>{item[0]}"
                associated_scan_indices.append(index)
        [plot_number_comboboxes[f"{i}"].renewItems(self.spec_list[:, 0]) for i, item in enumerate(plot_number_comboboxes)]
        
        # Initialize spectra to the indices of the spectra associated with the scan file
        index = 0        
        i_max = len(associated_scan_indices)
        if i_max < 1:
            plot_number_comboboxes[f"0"].selectIndex(index)
            self.set_consecutive(0)
        else:
            for i, index in enumerate(associated_scan_indices):
                if i > len(plot_number_comboboxes) - 1: break
                plot_number_comboboxes[f"{i}"].selectIndex(index)
                checkboxes[f"{i}"].setSilentCheck(True)
            self.set_consecutive(i)
        
        self.update_processing_flags()
        return

    def set_consecutive(self, row_number: int = 0) -> None:
        if row_number < 0 or row_number > len(self.gui.left_arrows) - 1:
            return
        
        plot_number_comboboxes = self.gui.plot_number_comboboxes
        
        start_index = plot_number_comboboxes[f"{row_number}"].currentIndex()
        index = start_index        
        for row in range(row_number + 1, len(self.gui.left_arrows)):
            if index < len(self.spec_list) - 1:
                index += 1
            else:
                index = 0
            plot_number_comboboxes[f"{row}"].selectIndex(index)
        
        self.update_processing_flags()
        return

    def update_processing_flags(self, toggle_channelbox: bool = False, increase_linewidth: bool = False) -> None:
        channel_selection_comboboxes = self.gui.channel_selection_comboboxes
        line_edits = self.gui.line_edits
        flags = self.data.spec_processing_flags
        
        # Toggle the state of the checkbox in the focus row if that is desired
        if toggle_channelbox:
            try: channel_selection_comboboxes[toggle_channelbox].toggleIndex(1)
            except: pass
                
        # Read the QComboboxes and retrieve what channels are requested
        x_channel = channel_selection_comboboxes["x_axis"].currentText()
        y_0_channel = channel_selection_comboboxes["y_axis_0"].currentText()
        y_1_channel = channel_selection_comboboxes["y_axis_1"].currentText()
        
        flags.update({
            "x_channel": x_channel,
            "y_0_channel": y_0_channel,
            "y_1_channel": y_1_channel
        })
        self.update_file_names()
        self.update_metadata_display()
        
        # Line width, opacity, offsets, smoothing window
        line_width_str = line_edits["line_width"].text()
        numbers = self.data.extract_numbers_from_str(line_width_str)
        if len(numbers) < 1: line_width = 2
        else: line_width = numbers[0]
        
        if increase_linewidth: line_width += 1
        if line_width > 10: line_width = 1
        
        opacity_str = line_edits["opacity"].text()
        numbers = self.data.extract_numbers_from_str(opacity_str)
        if len(numbers) < 1: opacity = 1
        else: opacity = numbers[0] / 100
        
        offset_0_str = line_edits["offset_0"].text()
        numbers = self.data.extract_numbers_from_str(offset_0_str)
        if len(numbers) < 1: offset_0 = 0
        else: offset_0 = numbers[0]
        
        offset_1_str = line_edits["offset_1"].text()
        numbers = self.data.extract_numbers_from_str(offset_1_str)
        if len(numbers) < 1: offset_1 = 0
        else: offset_1 = numbers[0]
        
        window_str = line_edits["window"].text()
        numbers = self.data.extract_numbers_from_str(window_str)
        if len(numbers) < 1: window = 0
        else: window = int(numbers[0])
        
        moving_average = self.gui.buttons["smooth"].isChecked()
        
        # More operations
        log_abs_0 = self.gui.buttons["log_abs_0"].isChecked()
        log_abs_1 = self.gui.buttons["log_abs_1"].isChecked()
        differentiate_0 = self.gui.buttons["differentiate_0"].isChecked()
        differentiate_1 = self.gui.buttons["differentiate_1"].isChecked()
        
        flags.update({
            "line_width": line_width,
            "opacity": opacity,
            "offset_0": offset_0,
            "offset_1": offset_1,
            "moving_average": moving_average,
            "moving_average_window": window,
            "log_abs_0": log_abs_0,
            "log_abs_1": log_abs_1,
            "differentiate_0": differentiate_0,
            "differentiate_1": differentiate_1
        })
        
        self.redraw_spectra()
        return

    def redraw_spectra(self) -> None:
        checkboxes = self.gui.checkboxes
        plot_number_comboboxes = self.gui.plot_number_comboboxes
        
        widget_0 = self.gui.plot_widgets["graph_0"]
        widget_1 = self.gui.plot_widgets["graph_1"]
        [widget.clear() for widget in [widget_0, widget_1]]
                
        graph_0 = self.gui.plot_items["graph_0"]
        graph_1 = self.gui.plot_items["graph_1"]
        [graph.clear() for graph in [graph_0, graph_1]]
        
        # Set the color scheme
        if self.view_mode == "bright": [widget.setBackground("#ffffff") for widget in [widget_0, widget_1]]
        else: [widget.setBackground("#000000") for widget in [widget_0, widget_1]]
        
        # Redraw the spectra        
        flags = self.data.spec_processing_flags
        
        # Extract the channels from the processing flags
        x_channel = flags.get("x_channel", None)
        y_0_channel = flags.get("y_0_channel", None)
        y_1_channel = flags.get("y_1_channel", None)
        if not x_channel or not y_0_channel or not y_1_channel: return
                
        # get the plot axis quantities and units and display them along the axes
        try:
            (quantity, unit, backward_bool, error) = self.file_functions.split_physical_quantity(x_channel)
            graph_0.getAxis("bottom").setLabel(f"{quantity}", units = unit)
            graph_1.getAxis("bottom").setLabel(f"{quantity}", units = unit)
            
            (quantity, unit, backward_bool, error) = self.file_functions.split_physical_quantity(y_0_channel)
            graph_0.getAxis("left").setLabel(f"{quantity}", units = unit)
            y_0_bwd_channel = f"{quantity} [bwd] ({unit})"
            
            (quantity, unit, backward_bool, error) = self.file_functions.split_physical_quantity(y_1_channel)
            graph_1.getAxis("left").setLabel(f"{quantity}", units = unit)
            y_1_bwd_channel = f"{quantity} [bwd] ({unit})"
        except:
            pass
        
        # Remove the target from the scan image
        plot = self.gui.plot_item
        for item in plot.items[:]:
            if item is not self.gui.image_item:
                plot.removeItem(item)
        
        # Set the pen and successive spectrum offset properties from processing flags
        line_width = flags.get("line_width", 1)
        opacity = flags.get("opacity", 1)
        if opacity < 0 or opacity > 1:
            opacity = 1
            flags.update({"opacity": 1})
        opacity_hex = "{:02x}".format(int(opacity * 255))        
        offset_0 = flags.get("offset_0", 0)
        offset_1 = flags.get("offset_1", 0)
       
        index = 0
        for i in range(len(plot_number_comboboxes)):            
            if not checkboxes[f"{i}"].isChecked(): continue # Only plot if the corresponding spectrum is checked
            
            index += 1
            
            try:
                if self.view_mode == "bright": color = self.gui.inv_color_list[i]
                else: color = self.gui.color_list[i]
                
                # Find the target in the spec_targets, and color and plot it accordingly in the scan image
                spec_index = plot_number_comboboxes[f"{i}"].currentIndex()
                spec_name = self.spec_list[spec_index, 0]
                
                for target in self.spec_targets:
                    target_spec_name = ">>" + target.tip_text.split("\n")[0]                    
                    if spec_name == target_spec_name:
                        pen = pg.mkPen(color = color, width = 2)
                        target.setPen(pen)
                        plot.addItem(target)
                
                # Create pen with color, width, and opacity
                color = color + opacity_hex
                pen = pg.mkPen(color = color, width = line_width)                
                pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
                
                # Retrieve the spec object
                spec_object = self.spec_list[spec_index, 2]
                spec_signal = spec_object.signals
                                
                x_data = spec_signal.get(x_channel, None)
                y_0_data = spec_signal.get(y_0_channel, None)
                y_0_bwd_data = spec_signal.get(y_0_bwd_channel, None)                
                if not isinstance(x_data, np.ndarray) or not isinstance(y_0_data, np.ndarray): continue
                
                # Build and process the spectrum dict object
                spectrum = {"x_axis": x_channel, "x_data": x_data, "y_axis": y_0_channel, "y_data": y_0_data}
                if y_0_bwd_channel: spectrum.update({"y_bwd_data": y_0_bwd_data})
                (processed_spectrum, error) = self.data.process_spectrum(spectrum, 0)

                if not error:
                    # Plot number 0
                    x_data = processed_spectrum.get("x_data")
                    y_data = processed_spectrum.get("y_data")
                    if isinstance(offset_0, float): y_data = [y_data[i] + index * offset_0 for i in range(len(y_data))]
                    graph_0.plot(x_data, y_data, pen = pen)
                    
                    if "y_bwd_data" in processed_spectrum.keys() and "x_bwd_data" in processed_spectrum.keys():
                        x_data = processed_spectrum.get("x_bwd_data")
                        y_data = processed_spectrum.get("y_bwd_data")
                        if isinstance(offset_0, float): y_data = [y_data[i] + index * offset_0 for i in range(len(y_data))]
                        graph_0.plot(x_data, y_data, pen = pen)

            except Exception as e:
                print(f"Error: {e}")
            
            try:
                x_data = spec_signal.get(x_channel, None)
                y_1_data = spec_signal.get(y_1_channel, None)
                y_1_bwd_data = spec_signal.get(y_1_bwd_channel, None)
                if not isinstance(y_1_data, np.ndarray): continue
                
                spectrum = {"x_axis": x_channel, "x_data": x_data, "y_axis": y_1_channel, "y_data": y_1_data}
                if y_1_bwd_channel: spectrum.update({"y_bwd_data": y_1_bwd_data})
                (processed_spectrum, error) = self.data.process_spectrum(spectrum, 1)

                if not error:
                    # Plot number 1
                    x_data = processed_spectrum.get("x_data")
                    y_data = processed_spectrum.get("y_data")
                    if isinstance(offset_1, float): y_data = [y_data[i] + index * offset_1 for i in range(len(y_data))]
                    graph_1.plot(x_data, y_data, pen = pen)
                    
                    if "y_bwd_data" in processed_spectrum.keys() and "x_bwd_data" in processed_spectrum.keys():
                        x_data = processed_spectrum.get("x_bwd_data")
                        y_data = processed_spectrum.get("y_bwd_data")
                        if isinstance(offset_0, float): y_data = [y_data[i] + index * offset_1 for i in range(len(y_data))]
                        graph_1.plot(x_data, y_data, pen = pen)
            
            except Exception as e:
                print(f"Error: {e}")

    def toggle_plot_number(self, plot_index: int = 0, increase: bool = True) -> None:
        if increase: self.gui.plot_number_comboboxes[f"{plot_index}"].toggleIndex(1)
        else: self.gui.plot_number_comboboxes[f"{plot_index}"].toggleIndex(-1)
        self.redraw_spectra()
        return

    def set_focus_row(self, number: int = -1, increase: bool = True) -> None:
        left_arrows = self.gui.left_arrows
        plot_number_comboboxes = self.gui.plot_number_comboboxes
        right_arrows = self.gui.right_arrows
        
        # Disconnect the key shortcuts
        try:
            self.left_shortcut.disconnect()
            self.right_shortcut.disconnect()
            self.checkbox_shortcut.disconnect()
        except Exception as e:
            print(f"Error disconnecting the key shortcuts: {e}")

        # Change the background color of the buttons
        for index in range(len(left_arrows)):
            row_buttons = [left_arrows[f"{index}"], plot_number_comboboxes[f"{index}"], right_arrows[f"{index}"]]
            [button.setStyleSheet(f"background-color: black;") for button in row_buttons]

        # Number is set
        if number > -1 and number < len(left_arrows):
            try:
                self.focus_row = number
                row_buttons = [left_arrows[f"{number}"], plot_number_comboboxes[f"{number}"], right_arrows[f"{number}"]]
                [button.setStyleSheet(f"background-color: #404000;") for button in row_buttons]
                self.gui.focus_row_combobox.selectIndex(number)
            except Exception as e:
                print(f"Error changing the focus row: {e}")

        # Number is toggled up or down
        else:
            try:
                if increase: new_row = self.focus_row + 1
                else: new_row = self.focus_row - 1

                if new_row < 0: new_row = len(left_arrows) - 1
                if new_row > len(left_arrows) - 1: new_row = 0

                self.focus_row = new_row
                row_buttons = [left_arrows[f"{new_row}"], plot_number_comboboxes[f"{new_row}"], right_arrows[f"{new_row}"]]
                [button.setStyleSheet(f"background-color: #404000;") for button in row_buttons]
                self.gui.focus_row_combobox.selectIndex(new_row)
            except Exception as e:
                print(f"Error changing the focus row: {e}")


        
        # Change the key shortcuts
        try:
            self.left_shortcut.activated.connect(lambda plot_index = self.focus_row: self.toggle_plot_number(plot_index, increase = False))
            self.right_shortcut.activated.connect(lambda plot_index = self.focus_row: self.toggle_plot_number(plot_index))
            self.checkbox_shortcut.activated.connect(self.check_checkbox)
        except Exception as e:
            print(f"Error connecting the key shortcuts: {e}")

    def toggle_axis(self, name: str = "") -> None:
        try:
            self.channel_selection_comboboxes[name].toggleIndex(1)
            self.update_processing_flags()
        except Exception as e:
            print(f"Error toggling the combobox: {e}")

        return

    def toggle_spec_direction(self) -> None:
        dir_button = self.gui.buttons["direction"]
        self.direction_index +=1
        if self.direction_index > 3: self.direction_index = 0
        
        match self.direction_index:
            case 0:
                dir_button.setIcon(self.icons.get("fwd"))
                dir_button.changeToolTip("(forward)")
                self.data.spec_processing_flags.update({"direction": "fwd"})
            case 1:
                dir_button.setIcon(self.icons.get("bwd"))
                dir_button.changeToolTip("(backward)")
                self.data.spec_processing_flags.update({"direction": "bwd"})
            case 2:
                dir_button.setIcon(self.icons.get("fwd_bwd"))
                dir_button.changeToolTip("(forward and backward)")
                self.data.spec_processing_flags.update({"direction": "fwd_bwd"})
            case 3:
                dir_button.setIcon(self.icons.get("average"))
                dir_button.changeToolTip("(forward + backward averaged)")
                self.data.spec_processing_flags.update({"direction": "average"})        
        
        self.update_processing_flags()
        return

    def width_opacity_change(self, target: str = "width", value: int = 100) -> None:
        flags = self.data.spec_processing_flags
        match target:
            case "width":
                current_width = flags.get("line_width")
                if value < 0:
                    new_width = current_width - 1
                    if new_width < 1: new_width = 10
                    
                    self.gui.line_edits["line_width"].setText(f"{round(new_width)} px")
                
                elif value > 10:
                    new_width = current_width + 1
                    if new_width > 10: new_width = 1
                    
                    self.gui.line_edits["line_width"].setText(f"{round(new_width)} px")
            
            case "opacity":
                current_opacity = flags.get("opacity")
                if value < 0:
                    new_opacity = current_opacity - 0.1
                    if new_opacity < 0: new_opacity = 1
                    
                    self.gui.line_edits["opacity"].setText(f"{round(100 * new_opacity)} %")
                
                elif value > 1:
                    new_opacity = current_opacity + 0.1
                    if new_opacity > 1: new_opacity = 0
                    
                    self.gui.line_edits["opacity"].setText(f"{round(100 * new_opacity)} %")
            case _:
                pass
        
        self.update_processing_flags()
        return

    def check_checkbox(self, all: bool = False) -> None:
        checkboxes = self.gui.checkboxes
        
        if all:
            check_list = [int(checkboxes[f"{index}"].isChecked()) for index in range(len(self.gui.left_arrows))]
            
            if sum(check_list) < len(self.gui.left_arrows):
                [checkboxes[f"{index}"].setSilentCheck(True) for index in range(len(self.gui.left_arrows))]
            else:
                [checkboxes[f"{index}"].setSilentCheck(False) for index in range(len(self.gui.left_arrows))]
        
        else: # Not 'all'; only toggle the state of the checkbox in the focus row
            checked = checkboxes[f"{self.focus_row}"].isChecked()            
            checkboxes[f"{self.focus_row}"].setSilentCheck(not checked)
        
        self.update_processing_flags()
        return

    def update_metadata_display(self) -> None:
        metadata_item = self.gui.metadata_combobox.currentText()
        
        x_old = None
        time_old = None
        
        for row_number in range(len(self.gui.left_arrows)):
            cbb = self.gui.plot_number_comboboxes[f"{row_number}"]
            l_e = self.gui.metadata_line_edits[f"{row_number}"]
            cbb_index = cbb.currentIndex()
            row_data = self.spec_list[cbb_index]
            
            date_time_str = row_data[6]
            format_string = "%Y-%m-%d %H:%M:%S"
            datetime_object = datetime.strptime(date_time_str, format_string)
            
            match metadata_item:
                case "date":
                    date_str = datetime_object.strftime("%Y-%m-%d")
                    l_e.setText(date_str)
                case "time":
                    time_str = datetime_object.strftime("%H:%M:%S")
                    l_e.setText(time_str)
                case "date_time":
                    l_e.setText(date_time_str)
                case "position":
                    [x, y, z] = [row_data[index] for index in [3, 4, 5]]
                    l_e.setText(f"({x:.1f}, {y:.1f}, {z:.1f}) nm")
                case "relative position (to previous)":
                    [x, y, z] = [row_data[index] for index in [3, 4, 5]]
                    
                    if not isinstance(x_old, float):
                        l_e.setText(f"(0, 0, 0) nm")
                    else:
                        x_rel = x - x_old
                        y_rel = y - y_old
                        z_rel = z - z_old
                        l_e.setText(f"({x_rel:.1f}, {y_rel:.1f}, {z_rel:.1f}) nm")
                    
                    x_old = x
                    y_old = y
                    z_old = z
                case "relative time (to previous)":                    
                    if not isinstance(time_old, datetime):
                        l_e.setText(f"0")
                    else:
                        delta_time = datetime_object - time_old
                        
                        seconds = delta_time.seconds
                        hours, remainder = divmod(seconds, 3600)
                        minutes, seconds = divmod(remainder, 60)
                        
                        if delta_time.days > 0:
                            l_e.setText(f"{delta_time.days} d, {hours} h: {minutes} min: {seconds} s")
                        elif hours > 0:
                            l_e.setText(f"{hours} h: {minutes} min: {seconds} s")
                        else:
                            l_e.setText(f"{minutes} min: {seconds} s")
                    
                    time_old = datetime_object
                    
                case _:
                    pass
        
        return

    def update_file_names(self) -> None:
        flags = self.data.spec_processing_flags
        
        scan_file_base = self.scan_file_name.split(".")[0]
        (x_quantity, x_unit, backward_bool, error) = self.file_functions.split_physical_quantity(flags.get("x_channel"))
        (y_0_quantity, y_0_unit, backward_bool, error) = self.file_functions.split_physical_quantity(flags.get("y_0_channel"))
        (y_1_quantity, y_1_unit, backward_bool, error) = self.file_functions.split_physical_quantity(flags.get("y_1_channel"))
        
        spec_name_0 = f"{scan_file_base}_{y_0_quantity}({x_quantity})"
        spec_name_1 = f"{scan_file_base}_{y_1_quantity}({x_quantity})"
        
        self.gui.line_edits["file_name_0"].setText(spec_name_0)
        self.gui.line_edits["file_name_1"].setText(spec_name_1)
        
        return

    def on_save_spectrum(self, plot_number: int = 0) -> None:
        try:
            export_folder = self.paths["output_folder"]
            if plot_number == 0:
                scene = self.gui.plot_widgets["graph_0"].scene()
                file_name = self.gui.line_edits["file_name_0"].text()
            else:
                scene = self.gui.plot_widgets["graph_0"].scene()
                file_name = self.gui.line_edits["file_name_1"].text()
            export_path = os.path.join(export_folder, file_name + ".svg")
            
            exporter = expts.SVGExporter(scene)
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self.gui, "Save file", export_path, "svg files (*.svg)")
            if file_path:
                exporter.export(file_path)
        
        except Exception as e:
            print(f"Error saving file: {e}")
        
        return

    def on_exit(self) -> None:
        self.gui.close()

    def open_folder(self, paths_entry: str = "") -> None:
        if paths_entry in list(self.paths.keys()):
            try: os.startfile(self.paths[paths_entry])
            except: pass        
        return



"""
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = Spectralyzer()
    sys.exit(app.exec())
"""
