import os, sys, re, yaml, pint
import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import pyqtgraph.exporters as expts
from . import GUIItems, HoverTargetItem, DataProcessing, FileFunctions
from .gui_spectralyzer import SpectralyzerGUI



color_list = ["#FFFFFF", "#FFFF20", "#20FFFF", "#FF80FF", "#60FF60", "#FF6060", "#8080FF", "#B0B0B0", "#FFB010", "#A050FF", "#909020", "#00A0A0", "#B030A0", "#40B040", "#B04040", "#5050E0"]



class Spectralyzer:
    def __init__(self, data_folder_path: str = "", scan_file_name: str = "", scan_image: np.ndarray = np.zeros((2, 2))):
        super().__init__()
        
        self.scan_file_name = scan_file_name
        self.parameters_init()
        self.gui = SpectralyzerGUI()
        self.gui.image_item.setImage(scan_image)
        
        self.connect_buttons()
        self.set_focus_row(0)
        
        if os.path.exists(data_folder_path): self.load_folder(data_folder_path)



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
        
        self.files_dict = {}
        self.spec_list = np.array((0, 3), dtype = object)

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
        self.file_functions = FileFunctions()
        self.data = DataProcessing()



    def connect_buttons(self) -> None:
        buttons = self.gui.buttons
        plot_number_comboboxes = self.gui.plot_number_comboboxes

        buttons["save_0"].clicked.connect(lambda: self.on_save_spectrum(0))
        buttons["save_1"].clicked.connect(lambda: self.on_save_spectrum(1))
        buttons["open_folder"].clicked.connect(self.on_select_file)
        buttons["exit"].clicked.connect(self.on_exit)        
        
        chan_sel_boxes = [self.gui.channel_selection_comboboxes[name] for name in ["x_axis", "y_axis_0", "y_axis_1"]]
        [combobox.currentIndexChanged.connect(lambda: self.update_processing_flags(toggle_checkbox = False, toggle_channelbox = False)) for combobox in chan_sel_boxes]
        [plot_number_comboboxes[f"{index}"].currentIndexChanged.connect(lambda: self.update_processing_flags(toggle_checkbox = False, toggle_channelbox = False)) for index in range(len(plot_number_comboboxes))]

        [self.gui.line_edits[name].editingFinished.connect(lambda: self.update_processing_flags(toggle_checkbox = False, toggle_channelbox = False)) for name in ["line_width", "opacity"]]
        [self.gui.line_edits[name].editingFinished.connect(lambda: self.update_processing_flags(toggle_checkbox = False, toggle_channelbox = False)) for name in ["offset_0", "offset_1"]]

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
        
        self.up_shortcut.activated.connect(lambda: self.set_focus_row(-1, increase = False))
        self.down_shortcut.activated.connect(lambda: self.set_focus_row(-1, increase = True))

        [x_axis_shortcut, y_axis_0_shortcut, y_axis_1_shortcut] = [QShc(QSeq(keystroke), self.gui) for keystroke in [QKey.Key_X, QKey.Key_Y, QKey.Key_Z]]
        x_axis_shortcut.activated.connect(lambda: self.update_processing_flags(toggle_channelbox = "x_axis"))
        y_axis_0_shortcut.activated.connect(lambda: self.update_processing_flags(toggle_channelbox = "y_axis_0"))
        y_axis_1_shortcut.activated.connect(lambda: self.update_processing_flags(toggle_channelbox = "y_axis_1"))
                
        # Connect the checkboxes
        [checkbox.toggled.connect(lambda: self.update_processing_flags(toggle_checkbox = False, toggle_channelbox = False)) for checkbox in self.gui.checkboxes.values()]
        
        self.gui.dataDropped.connect(self.load_folder)
        
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
        self.gui.buttons["open_folder"].setText(folder_name)
        
        # 0: Check if the metadata.yml file exists, and load it if it does
        metadata_file_path = os.path.join(folder_name, "metadata.yml")
        (files_dict, error) = self.file_functions.load_yaml(metadata_file_path)
        
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
        
        # 6: Populate the spectroscopy dictionary with spectroscopy objects, from which the spectra can be extracted
        (files_dict, error) = self.file_functions.populate_spec_objects(files_dict)
        if error:
            print(f"Error retrieving spectroscopy objects: {error}")
            return
        
        # 7: All operations successful. Save the populated files_dict as Spectralyzer attribute. Then move on with reading the spectroscopy files/objects
        self.files_dict = files_dict
        self.read_spectroscopy_files()
        
        return

    def read_spectroscopy_files(self) -> tuple:
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
                
                [all_channels.append(str(channel)) for channel in channels]
                spec_list.append([spec_file_name, associated_scan_name, spec_object])
            
            all_channels_set = set(all_channels) # Duplicate entries are automatically removed from sets
            all_channels = list(all_channels_set)
            self.spec_list = np.array(spec_list)
            [channel_selection_comboboxes[axis].renewItems(all_channels) for axis in ["x_axis", "y_axis_0", "y_axis_1"]]
            
        except:
            pass
        
        # Attempt to set the channel toggle boxes to logical starting defaults
        try:
            x_axis_targets = ["Bias (V)", "Bias [bwd] V", "Bias calc (V)"]
            for label in x_axis_targets:
                if label in all_channels:
                    channel_selection_comboboxes["y_axis_0"].selectItem(label)
                    break

            y_axis_0_targets = ["LI Demod 1 X (A)", "LI Demod 1 X [bwd] (A)", "LI Demod 1 X [bwd] (A)", "Current (A)"]
            for label in y_axis_0_targets:
                if label in all_channels:
                    channel_selection_comboboxes["y_axis_0"].selectItem(label)
                    break

            y_axis_1_targets = ["Current (A)", "Current [bwd] (A)", "Current calc (A)"]
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
        i_max = len(associated_scan_indices)
        for i, index in enumerate(associated_scan_indices):
            if i > len(plot_number_comboboxes) - 1: break
            plot_number_comboboxes[f"{i}"].selectIndex(index)
            checkboxes[f"{i}"].setSilentCheck(True)
        
        # Initialize the rest of the comboboxes with successive spectra after the last one associated with the scan file
        index += 1
        for i in range(i_max, len(plot_number_comboboxes)):
            if index < len(self.spec_list) - 1:
                plot_number_comboboxes[f"{i}"].selectIndex(index)
        
        self.update_processing_flags(toggle_checkbox = False, toggle_channelbox = False)
        return

    def update_processing_flags(self, toggle_checkbox: bool = False, toggle_channelbox: bool = False):
        checkboxes = self.gui.checkboxes
        leftarrows = self.gui.leftarrows
        rightarrows = self.gui.rightarrows
        plot_number_comboboxes = self.gui.plot_number_comboboxes
        channel_selection_comboboxes = self.gui.channel_selection_comboboxes
        line_edits = self.gui.line_edits
        flags = self.data.spec_processing_flags

        # Toggle the state of the checkbox in the focus row if that is desired
        if toggle_checkbox:
            checked = checkboxes[f"{self.focus_row}"].isChecked()            
            checkboxes[f"{self.focus_row}"].setSilentCheck(not checked)
        
        # Toggle the state of the checkbox in the focus row if that is desired
        if toggle_channelbox:
            try: channel_selection_comboboxes[toggle_channelbox].toggleIndex(1)
            except: pass
        
        # Grey out the plot rows that are not enabled (checked using the checkbox)
        for index in range(len(checkboxes)):
            row_enabled = checkboxes[f"{index}"].isChecked()
            if row_enabled: [button.setEnabled(True) for button in [leftarrows[f"{index}"], plot_number_comboboxes[f"{index}"], rightarrows[f"{index}"]]]
            else: [button.setEnabled(False) for button in [leftarrows[f"{index}"], plot_number_comboboxes[f"{index}"], rightarrows[f"{index}"]]]
        
        # Read the QComboboxes and retrieve what channels are requested
        x_channel = channel_selection_comboboxes["x_axis"].currentText()
        y_0_channel = channel_selection_comboboxes["y_axis_0"].currentText()
        y_1_channel = channel_selection_comboboxes["y_axis_1"].currentText()
        
        flags.update({
            "x_channel": x_channel,
            "y_0_channel": y_0_channel,
            "y_1_channel": y_1_channel
        })
        
        # Add the offsets
        offset_0 = float(line_edits["offset_0"].text())
        offset_1 = float(line_edits["offset_1"].text())
        
        flags.update({
            "offset_0": offset_0,
            "offset_1": offset_1
        })
        
        self.redraw_spectra()
        return

    def redraw_spectra(self) -> None:
        plot_items = self.gui.plot_items
        line_edits = self.gui.line_edits
        checkboxes = self.gui.checkboxes
        leftarrows = self.gui.leftarrows
        rightarrows = self.gui.rightarrows
        plot_number_comboboxes = self.gui.plot_number_comboboxes
        graph_0 = self.gui.plot_items["graph_0"]
        graph_1 = self.gui.plot_items["graph_1"]
        flags = self.data.spec_processing_flags
        
        # Extract the channels from the processing flags
        x_channel = flags.get("x_channel", None)
        y_0_channel = flags.get("y_0_channel", None)
        y_1_channel = flags.get("y_1_channel", None)
        if not x_channel or not y_0_channel or not y_1_channel: return
        
        # Set the pen and successive spectrum offset properties from processing flags
        line_width = flags.get("line_width", 1)
        opacity = flags.get("opacity", 1)
        offset_0 = flags.get("offset_0", 0)
        offset_1 = flags.get("offset_1", 0)
        
        # Redraw the spectra
        [graph.clear() for graph in [graph_0, graph_1]]
        for i in range(len(checkboxes)):
            color = color_list[i]

            if not checkboxes[f"{i}"].isChecked(): continue
            
            try:
                # Create pen with color, width, and opacity
                pen = pg.mkPen(color = color, width = line_width, alphaF = opacity)
                pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
                pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)
                
                # Retrieve the spec object
                spec_index = plot_number_comboboxes[f"{i}"].currentIndex()
                spec_object = self.spec_list[spec_index, 2]
                spec_signal = spec_object.signals
                
                x_data = spec_signal.get(x_channel, None)
                y_0_data = spec_signal.get(y_0_channel, None)
                if not isinstance(x_data, np.ndarray) or not isinstance(y_0_data, np.ndarray): continue

                # Plot number 0
                y_0_data_shifted = y_0_data + i * offset_0
                graph_0.plot(x_data, y_0_data_shifted, pen = pen)
                
            except Exception as e:
                print(f"Error: {e}")
            
            try:
                y_1_data = spec_signal.get(y_1_channel, None)
                if not isinstance(y_1_data, np.ndarray): continue
                
                # Plot number 1
                y_1_data_shifted = y_1_data + i * offset_1
                graph_1.plot(x_data, y_1_data_shifted, pen = pen)
            
            except Exception as e:
                print(f"Error: {e}")

    def toggle_plot_number(self, plot_index: int = 0, increase: bool = True) -> None:
        if increase: self.gui.plot_number_comboboxes[f"{plot_index}"].toggleIndex(1)
        else: self.gui.plot_number_comboboxes[f"{plot_index}"].toggleIndex(-1)
        self.redraw_spectra()
        return

    def set_focus_row(self, number: int = -1, increase: bool = True) -> None:
        leftarrows = self.gui.leftarrows
        plot_number_comboboxes = self.gui.plot_number_comboboxes
        rightarrows = self.gui.rightarrows
        
        # Disconnect the key shortcuts
        try:
            self.left_shortcut.disconnect()
            self.right_shortcut.disconnect()
            self.checkbox_shortcut.disconnect()
        except Exception as e:
            print(f"Error disconnecting the key shortcuts: {e}")

        # Change the background color of the buttons
        for index in range(len(leftarrows)):
            row_buttons = [leftarrows[f"{index}"], plot_number_comboboxes[f"{index}"], rightarrows[f"{index}"]]
            [button.setStyleSheet(f"background-color: black;") for button in row_buttons]

        # Number is set
        if number > -1 and number < len(leftarrows):
            try:
                self.focus_row = number
                row_buttons = [leftarrows[f"{number}"], plot_number_comboboxes[f"{number}"], rightarrows[f"{number}"]]
                [button.setStyleSheet(f"background-color: #404000;") for button in row_buttons]
            except Exception as e:
                print(f"Error changing the focus row: {e}")

        # Number is toggled up or down
        else:
            try:
                if increase: new_row = self.focus_row + 1
                else: new_row = self.focus_row - 1

                if new_row < 0: new_row = len(leftarrows) - 1
                if new_row > len(leftarrows) - 1: new_row = 0

                self.focus_row = new_row
                row_buttons = [leftarrows[f"{new_row}"], plot_number_comboboxes[f"{new_row}"], rightarrows[f"{new_row}"]]
                [button.setStyleSheet(f"background-color: #404000;") for button in row_buttons]
            except Exception as e:
                print(f"Error changing the focus row: {e}")
        
        # Change the key shortcuts
        try:
            self.left_shortcut.activated.connect(lambda plot_index = self.focus_row: self.toggle_plot_number(plot_index, increase = False))
            self.right_shortcut.activated.connect(lambda plot_index = self.focus_row: self.toggle_plot_number(plot_index))
            self.checkbox_shortcut.activated.connect(lambda: self.update_processing_flags(toggle_checkbox = True))
        except Exception as e:
            print(f"Error connecting the key shortcuts: {e}")

    def toggle_axis(self, name: str = "") -> None:
        try:
            index = self.channel_selection_comboboxes[name].currentIndex()
            index += 1
            if index > len(self.channels) - 1: index = 0
            self.channel_selection_comboboxes[name].blockSignals(True)
            self.channel_selection_comboboxes[name].setCurrentIndex(index)
            self.channel_selection_comboboxes[name].blockSignals(False)
            self.redraw_spectra(False)
        except Exception as e:
            print(f"Error toggling the combobox: {e}")

        return

    def on_save_spectrum(self, plot_number: int = 0) -> None:
        try:
            export_folder = self.paths["output_folder"]
            if plot_number == 0:
                scene = self.gui.plot_widgets["graph_0"].scene()
            else:
                scene = self.gui.plot_widgets["graph_0"].scene()
            
            exporter = expts.SVGExporter(scene)
            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save file", export_folder, "svg files (*.svg)")
            if file_path:
                exporter.export(file_path)
        
        except Exception as e:
            print("Error saving file.")
        
        return

    def on_exit(self) -> None:
        self.gui.close()


"""
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = Spectralyzer()
    sys.exit(app.exec())
"""
