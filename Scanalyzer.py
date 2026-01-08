import os
import sys
import yaml
import numpy as np
import pint
from PyQt6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
from lib.image_functions import apply_gaussian, apply_fft, image_gradient, compute_normal, apply_laplace, complex_image_to_colors, background_subtract, get_image_statistics
from lib.file_functions import read_files, get_scan, get_spectrum
from lib.gui_functions import GUIFunctions, HoverTargetItem



class SpectrumViewer(QtWidgets.QMainWindow):
    def __init__(self, processed_scan, spec_files, associated_spectra, paths):
        super().__init__()
        self.setWindowTitle("Spectrum viewer")
        self.setGeometry(200, 200, 900, 600)
        self.spec_files = spec_files # Make the spectroscopy file list an attribute of the SpectroscopyWindow class
        self.associated_spectra = associated_spectra
        self.paths = paths

        # Spectrum colors
        self.color_list = ["#FFFFFF", "#FFFF00", "#FF90FF", "#00FFFF", "#00FF00", "#A0A0A0", "#FF4040", "#5050FF", "#FFA500", "#9050FF", "#808000", "#008080", "#900090", "#009000", "#B00000", "#0000C0"]
        
        self.parameters_init()
        self.make_gui_items()
        self.draw_layout()
        self.spec_objects, self.channels = self.read_spectroscopy_files()
        self.connect_keys()
        self.set_focus_row(0)
        self.redraw_spectra()

    def parameters_init(self) -> None:
        icon_files = os.listdir(self.paths["icon_folder"])
        self.icons = {}
        for icon_file in icon_files:
            [icon_name, extension] = os.path.splitext(os.path.basename(icon_file))
            try:
                if extension == ".png": self.icons.update({icon_name: QtGui.QIcon(os.path.join(self.paths["icon_folder"], icon_file))})
            except:
                pass
        self.setWindowIcon(self.icons.get("graph"))
        self.focus_row = 0

    def make_gui_items(self) -> None:
        gui_functions = GUIFunctions()
        make_button = lambda *args, **kwargs: gui_functions.make_button(*args, parent = self, **kwargs)
        make_label = gui_functions.make_label
        make_radio_button = gui_functions.make_radio_button
        make_checkbox = gui_functions.make_checkbox
        make_combobox = gui_functions.make_combobox
        make_line_edit = gui_functions.make_line_edit
        make_layout = gui_functions.make_layout
        make_groupbox = gui_functions.make_groupbox

        self.buttons = {
            "exit": make_button("", self.close, "Exit Spectrum Viewer (Q / Esc)", self.icons.get("escape"))
        }
        self.channel_selection_comboboxes = {
            "x_axis": make_combobox("x_axis", "Channel to display on the x axis (X)", self.redraw_spectra),
            "y_axis_0": make_combobox("y_axis_0", "Channel to display on the y axis (Y)", self.redraw_spectra),
            "y_axis_1": make_combobox("y_axis_1", "Channel to display on the y axis (Z)", self.redraw_spectra),
        }
        self.layouts = {
            "main": make_layout("g"),
            "selector": make_layout("g")
        }
        self.option_checkboxes = {
            "offset": make_checkbox("offset", "Offset successive spectra", self.icons.get("offset"))
        }
        
        self.checkboxes = {}
        self.plot_number_comboboxes = {}
        self.leftarrows = {}
        self.rightarrows = {}

        for number in range(16):
            self.checkboxes.update({f"{number}": make_checkbox(f"{number}", f"toggle visibility of plot {number} (space when row is highlighted)")})
            self.checkboxes[f"{number}"].setStyleSheet(f"color: {self.color_list[number]};")
            self.plot_number_comboboxes.update({f"{number}": make_combobox(f"{number}", f"data for plot {number}")})
            self.leftarrows.update({f"{number}": make_button("", lambda n = number: self.toggle_plot_number(n, increase = False), f"decrease plot number {number} (left arrow when row is highlighted)", self.icons.get("single_arrow"), rotate_degrees = 180)})
            self.rightarrows.update({f"{number}": make_button("", lambda n = number: self.toggle_plot_number(n, increase = True), f"increase plot number {number} (right arrow when row is highlighted)", self.icons.get("single_arrow"))})

    def draw_layout(self) -> None:
        # Set the central widget of the QMainWindow
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)

        # Spectrum selector
        spectrum_selector_widget = QtWidgets.QWidget()
        spectrum_selector_layout = self.layouts["selector"]

        [spectrum_selector_layout.addWidget(self.checkboxes[f"{i}"], i, 0) for i in range(len(self.checkboxes))]
        [spectrum_selector_layout.addWidget(self.leftarrows[f"{i}"], i, 1) for i in range(len(self.leftarrows))]
        [spectrum_selector_layout.addWidget(self.plot_number_comboboxes[f"{i}"], i, 2) for i in range(len(self.plot_number_comboboxes))]
        [spectrum_selector_layout.addWidget(self.rightarrows[f"{i}"], i, 3) for i in range(len(self.rightarrows))]
        spectrum_selector_widget.setLayout(spectrum_selector_layout)

        # Main widgets
        self.layouts["main"].addWidget(spectrum_selector_widget, 1, 0, 2, 1) # Spectrum selector buttons
        self.graph_0_widget = pg.PlotWidget()
        self.graph_1_widget = pg.PlotWidget()
        column_1_widgets = [self.channel_selection_comboboxes["x_axis"], self.graph_0_widget, self.graph_1_widget]
        column_2_widgets = [self.buttons["exit"], self.channel_selection_comboboxes["y_axis_0"], self.channel_selection_comboboxes["y_axis_1"]]
        self.graph_0 = self.graph_0_widget.getPlotItem() # Get the plotitems corresponding to the plot widgets
        self.graph_1 = self.graph_1_widget.getPlotItem()
        #self.x_channel_box.setFixedWidth(500)

        [self.layouts["main"].addWidget(widget, i, 1, alignment = QtCore.Qt.AlignmentFlag.AlignCenter) for i, widget in enumerate(column_1_widgets)]
        [self.layouts["main"].addWidget(widget, i, 2, alignment = QtCore.Qt.AlignmentFlag.AlignCenter) for i, widget in enumerate(column_2_widgets)]
        central_widget.setLayout(self.layouts["main"])

        [self.plot_number_comboboxes[f"{index}"].currentIndexChanged.connect(lambda: self.redraw_spectra(toggle_checkbox = False)) for index in range(len(self.plot_number_comboboxes))]

    def connect_keys(self) -> None:
        QKey = QtCore.Qt.Key

        exit_shortcuts = [QtGui.QShortcut(QtGui.QKeySequence(keystroke), self) for keystroke in [QKey.Key_Q, QKey.Key_Escape]]
        [exit_shortcut.activated.connect(self.close) for exit_shortcut in exit_shortcuts]

        focus_shortcuts = []
        for index, keystroke in enumerate([QKey.Key_0, QKey.Key_1, QKey.Key_2, QKey.Key_3, QKey.Key_4, QKey.Key_5, QKey.Key_6, QKey.Key_7,
                                           QKey.Key_8, QKey.Key_9, QKey.Key_A, QKey.Key_B, QKey.Key_C, QKey.Key_D, QKey.Key_E, QKey.Key_F]):
            focus_shortcut = QtGui.QShortcut(QtGui.QKeySequence(keystroke), self)
            focus_shortcut.activated.connect(lambda i = index: self.set_focus_row(i))
            focus_shortcuts.append(focus_shortcut)
        
        toggle_shortcuts = [QtGui.QShortcut(QtGui.QKeySequence(keystroke), self) for keystroke in [QKey.Key_Up, QKey.Key_Down, QKey.Key_Left, QKey.Key_Right, QKey.Key_Space]]
        [self.up_shortcut, self.down_shortcut, self.left_shortcut, self.right_shortcut, self.checkbox_shortcut] = toggle_shortcuts
        
        self.up_shortcut.activated.connect(lambda: self.set_focus_row(-1, increase = False))
        self.down_shortcut.activated.connect(lambda: self.set_focus_row(-1, increase = True))

        [x_axis_shortcut, y_axis_0_shortcut, y_axis_1_shortcut] = [QtGui.QShortcut(QtGui.QKeySequence(keystroke), self) for keystroke in [QKey.Key_X, QKey.Key_Y, QKey.Key_Z]]
        x_axis_shortcut.activated.connect(lambda: self.toggle_axis("x_axis"))
        y_axis_0_shortcut.activated.connect(lambda: self.toggle_axis("y_axis_0"))
        y_axis_1_shortcut.activated.connect(lambda: self.toggle_axis("y_axis_1"))

    def read_spectroscopy_files(self) -> tuple:
        spec_objects = [get_spectrum(spec_file[1]) for spec_file in self.spec_files] # Get a spectroscopy object for each spectroscopy file
        
        # Find all the channels recorded during all the spectroscopies and combine them into a list called all_channels
        all_channels = []
        for spec_object in spec_objects:
            all_channels.extend(list(spec_object.channels))
        all_channels = list(set(all_channels))
        all_channels = np.array([str(channel) for channel in all_channels])
        [combobox.addItems(all_channels) for combobox in [self.channel_selection_comboboxes["x_axis"], self.channel_selection_comboboxes["y_axis_0"], self.channel_selection_comboboxes["y_axis_1"]]]
        
        # Attempt to set the channel toggle boxes to logical starting defaults
        [combobox.blockSignals(True) for combobox in self.channel_selection_comboboxes.values()]
        try:
            x_axis_targets = ["Bias (V)", "Bias [bwd] V", "Bias calc (V)"]
            for label in x_axis_targets:
                if label in all_channels:
                    channel_index = np.where(all_channels == label)[0][0]
                    self.channel_selection_comboboxes["x_axis"].setCurrentIndex(channel_index)
                    break

            y_axis_0_targets = ["LI demod X1 (A)", "Current (A)"]
            for label in y_axis_0_targets:
                if label in all_channels:
                    channel_index = np.where(all_channels == label)[0][0]
                    self.channel_selection_comboboxes["y_axis_0"].setCurrentIndex(channel_index)
                    break

            y_axis_1_targets = ["Current (A)", "Current [bwd] (A)", "Current calc (A)"]
            for label in y_axis_1_targets:
                if label in all_channels:
                    channel_index = np.where(all_channels == label)[0][0]
                    self.channel_selection_comboboxes["y_axis_1"].setCurrentIndex(channel_index)
                    break
        except Exception as e:
            print(f"Error while trying to set the comboboxes to default values: {e}")
        [combobox.blockSignals(False) for combobox in self.channel_selection_comboboxes.values()]

        # Put a star on the spectrum names that are associated with the scan and initialize the comboboxes
        [combobox.blockSignals(True) for combobox in self.plot_number_comboboxes.values()]
        spec_labels = self.spec_files[:, 0]
        associated_labels = [spectrum[0] for spectrum in self.associated_spectra]
        for i in range(len(spec_labels)):
            if spec_labels[i] in associated_labels:
                [self.plot_number_comboboxes[f"{number}"].addItem("*" + spec_labels[i]) for number in range(len(self.plot_number_comboboxes))]
            else:
                [self.plot_number_comboboxes[f"{number}"].addItem(spec_labels[i]) for number in range(len(self.plot_number_comboboxes))]

        # Initialize the comboboxes to the associated spectra if possible
        spec_labels = self.spec_files[:, 0]
        for index, combobox in enumerate(self.plot_number_comboboxes.values()):
            try:
                if index < len(self.associated_spectra):
                    associated_index = np.where(spec_labels == associated_labels[index])[0][0]
                    combobox.setCurrentIndex(associated_index)
                    self.checkboxes[f"{index}"].setChecked(True)
                elif index < len(spec_labels):
                    combobox.setCurrentIndex(index)
                else:
                    pass
            except Exception as e:
                print(f"Error initializing some or all plot number comboboxes: {e}")
        [combobox.blockSignals(False) for combobox in self.plot_number_comboboxes.values()]

        # Connect the checkboxes
        [checkbox.toggled.connect(lambda: self.redraw_spectra(False)) for checkbox in self.checkboxes.values()]

        return spec_objects, all_channels

    def redraw_spectra(self, toggle_checkbox: bool = False) -> None:
        if toggle_checkbox:
            checked = self.checkboxes[f"{self.focus_row}"].isChecked()
            [checkbox.blockSignals(True) for checkbox in self.checkboxes.values()]
            self.checkboxes[f"{self.focus_row}"].setChecked(not checked)
            [checkbox.blockSignals(False) for checkbox in self.checkboxes.values()]

        # Grey out the plot rows that are not enabled (checked using the checkbox)
        for index in range(len(self.checkboxes)):
            checkbox = self.checkboxes[f"{index}"]
            checked = checkbox.isChecked()
            if checked: [button.setEnabled(True) for button in [self.leftarrows[f"{index}"], self.plot_number_comboboxes[f"{index}"], self.rightarrows[f"{index}"]]]
            else: [button.setEnabled(False) for button in [self.leftarrows[f"{index}"], self.plot_number_comboboxes[f"{index}"], self.rightarrows[f"{index}"]]]

        # Read the QComboboxes and retrieve what channels are requested
        if not hasattr(self, "channels"): return # Return if the channels have not yet been read
        x_index = self.channel_selection_comboboxes["x_axis"].currentIndex()
        y_0_index = self.channel_selection_comboboxes["y_axis_0"].currentIndex()
        y_1_index = self.channel_selection_comboboxes["y_axis_1"].currentIndex()
        [x_channel, y_0_channel, y_1_channel] = [self.channels[index] for index in [x_index, y_0_index, y_1_index]]

        x_data = np.linspace(-2, 2, 20)
        [graph.clear() for graph in [self.graph_0, self.graph_1]]

        for i in range(len(self.checkboxes) - 1, -1, -1):
            color = self.color_list[i]

            if self.checkboxes[f"{i}"].isChecked():
                spec_index = self.plot_number_comboboxes[f"{i}"].currentIndex()
                spec_object = self.spec_objects[spec_index]
                spec_signal = spec_object.signals
                
                try:
                    x_data = spec_signal[x_channel]
                    y_0_data = spec_signal[y_0_channel]
                    self.graph_0.plot(x_data, y_0_data, pen = color)
                except Exception as e:
                    print(f"Error: {e}")
                try:
                    x_data = spec_signal[x_channel]
                    y_1_data = spec_signal[y_1_channel]
                    self.graph_1.plot(x_data, y_1_data, pen = color)
                except Exception as e:
                    print(f"Error: {e}")

    def toggle_plot_number(self, plot_index: int = 0, increase: bool = True) -> None:
        try:
            current_index = self.plot_number_comboboxes[f"{plot_index}"].currentIndex()

            if increase: new_index = current_index + 1
            else: new_index = current_index - 1
            
            if new_index > len(self.spec_files) - 1: new_index = 0
            if new_index < 0: new_index = len(self.spec_files) - 1

            # Changing the index of the combobox automatically activates self.redraw_spectra() since the currentIndexChanged signal is connected to that method
            self.plot_number_comboboxes[f"{plot_index}"].setCurrentIndex(new_index)

        except Exception as e:
            print(f"Error toggling the plot: {e}")
        
        return

    def set_focus_row(self, number: int = -1, increase: bool = True) -> None:
        # Disconnect the key shortcuts
        try:
            self.left_shortcut.disconnect()
            self.right_shortcut.disconnect()
            self.checkbox_shortcut.disconnect()
        except Exception as e:
            print(f"Error disconnecting the key shortcuts: {e}")

        # Change the background color of the buttons
        for index in range(len(self.leftarrows)):
            [button.setStyleSheet(f"background-color: black;") for button in [self.leftarrows[f"{index}"], self.plot_number_comboboxes[f"{index}"], self.rightarrows[f"{index}"]]]

        # Number is set
        if number > -1 and number < len(self.leftarrows):
            try:
                self.focus_row = number
                [button.setStyleSheet(f"background-color: #404000;") for button in [self.leftarrows[f"{self.focus_row}"], self.plot_number_comboboxes[f"{self.focus_row}"], self.rightarrows[f"{self.focus_row}"]]]
            except Exception as e:
                print(f"Error changing the focus row: {e}")
        # Number is toggled up or down
        else:
            try:
                if increase: new_row = self.focus_row + 1
                else: new_row = self.focus_row - 1

                if new_row < 0: new_row = len(self.leftarrows) - 1
                if new_row > len(self.leftarrows) - 1: new_row = 0

                self.focus_row = new_row
                [button.setStyleSheet(f"background-color: #404000;") for button in [self.leftarrows[f"{self.focus_row}"], self.plot_number_comboboxes[f"{self.focus_row}"], self.rightarrows[f"{self.focus_row}"]]]
            except Exception as e:
                print(f"Error changing the focus row: {e}")
        
        # Change the key shortcuts
        try:
            self.left_shortcut.activated.connect(lambda plot_index = self.focus_row: self.toggle_plot_number(plot_index, increase = False))
            self.right_shortcut.activated.connect(lambda plot_index = self.focus_row: self.toggle_plot_number(plot_index))
            self.checkbox_shortcut.activated.connect(lambda: self.redraw_spectra(toggle_checkbox = True))
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



class AppWindow(QtWidgets.QMainWindow):
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

        # Initialize parameters and GUI items
        self.parameters_init()
        self.make_gui_items()
        self.connect_keys()

        # Set the central widget of the QMainWindow, then draw a toolbar next to it
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)        
        main_layout = QtWidgets.QHBoxLayout(central_widget)

        main_layout.addWidget(self.image_view, 3)        
        main_layout.addLayout(self.draw_toolbar(), 1)
        
        # Ensure the central widget and QMainWindow can both receive keyboard focus
        central_widget.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        central_widget.setFocus()
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
        # I/O paths
        script_path = os.path.abspath(__file__) # The full path of Scanalyzer.py, including the filename itself
        script_folder = os.path.dirname(script_path) # The parent directory of Scanalyzer.py
        sys_folder = os.path.join(script_folder, "sys") # The directory of the config file
        lib_folder = os.path.join(script_folder, "lib") # The directory of the Scanalyzer package
        icon_folder = os.path.join(script_folder, "icons") # The directory of the icon files
        config_path = os.path.join(sys_folder, "config.yml") # The path to the configuration file
        data_folder = sys_folder # Set current folder to the config file; read from the config file later to reset it to a data folder
        output_folder_name = "Extracted Files"

        self.paths = {
            "script_path": script_path,
            "script_folder": script_folder,
            "scanalyzer_folder": sys_folder,
            "lib_folder": lib_folder,
            "icon_folder": icon_folder,
            "config_path": config_path,
            "data_folder": lib_folder,
            "output_folder_name": output_folder_name,
            "output_folder": os.path.join(data_folder, output_folder_name),
            "output_file_basename": ""
        }

        icon_files = os.listdir(self.paths["icon_folder"])
        self.icons = {}
        for icon_file in icon_files:
            [icon_name, extension] = os.path.splitext(os.path.basename(icon_file))
            try:
                if extension == ".png": self.icons.update({icon_name: QtGui.QIcon(os.path.join(self.paths["icon_folder"], icon_file))})
            except:
                pass
        self.setWindowIcon(self.icons.get("scanalyzer"))
        
        self.sxm_files = np.array([[]])
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
        self.ureg = pint.UnitRegistry()
        self.spec_targets = []

        self.processing_flags = {
            "direction": "forward",
            "background_subtraction": "none",
            "sobel": False,
            "gaussian": False,
            "laplace": False,
            "fft": False,
            "normal": False,
            "min_selection": 0,
            "max_selection": 0,
            "spec_locations": False
        }

        self.gui_functions = GUIFunctions()

    def make_gui_items(self) -> None:
        make_button = lambda *args, **kwargs: self.gui_functions.make_button(*args, parent = self, **kwargs)
        make_label = self.gui_functions.make_label
        make_radio_button = self.gui_functions.make_radio_button
        make_checkbox = self.gui_functions.make_checkbox
        make_combobox = self.gui_functions.make_combobox
        make_line_edit = self.gui_functions.make_line_edit
        make_layout = self.gui_functions.make_layout
        make_groupbox = self.gui_functions.make_groupbox
        QKey = QtCore.Qt.Key

        self.buttons = {
            "previous_file": make_button("", self.on_previous_file, "Previous file (←)", self.icons.get("single_arrow"), rotate_degrees = 180, key_shortcut = QKey.Key_Left),
            "select_file": make_button("", self.on_select_file, "Load scan and corresponding folder (L)", self.icons.get("folder_yellow"), key_shortcut = QKey.Key_L),
            "next_file": make_button("", self.on_next_file, "Next file (→)", self.icons.get("single_arrow"), key_shortcut = QKey.Key_Right),

            "previous_channel": make_button("", self.on_previous_chan, "Previous channel (↑)", self.icons.get("single_arrow"), rotate_degrees = 270, key_shortcut = QKey.Key_Up),
            "next_channel": make_button("", self.on_next_chan, "Next channel (↓)", self.icons.get("single_arrow"), rotate_degrees = 90, key_shortcut = QKey.Key_Down),
            "direction": make_button("", self.on_toggle_direction, "Change scan direction (X)", self.icons.get("triple_arrow"), key_shortcut = QKey.Key_X),

            "folder_name": make_button("Open folder", self.open_data_folder, "Open the data folder (1)", self.icons.get("folder_blue"), key_shortcut = QKey.Key_1),

            "full_data_range": make_button("", self.on_full_scale, "Set the image value range to the full data range (U)", self.icons.get("100"), key_shortcut = QKey.Key_U),
            "percentiles": make_button("", self.on_percentiles, "Set the image value range by percentiles (R)", self.icons.get("percentiles"), key_shortcut = QKey.Key_R),
            "standard_deviation": make_button("", self.on_standard_deviations, "Set the image value range by standard deviations (D)", self.icons.get("deviation"), key_shortcut = QKey.Key_D),
            "absolute_values": make_button("", self.on_absolute_values, "Set the image value range by absolute values (A)", self.icons.get("numbers"), key_shortcut = QKey.Key_A),

            "spec_locations": make_button("", self.on_toggle_spec_locations, "View the spectroscopy locations (3)", self.icons.get("spec_locations"), key_shortcut = QKey.Key_3),
            "spectrum_viewer": make_button("", self.open_spectrum_viewer, "Open Spectrum Viewer (O)", self.icons.get("graph"), key_shortcut = QKey.Key_O),

            "save_png": make_button("", self.on_save_png, "Save as png file (S)", self.icons.get("floppy"), key_shortcut = QKey.Key_S),
            "save_hdf5": make_button("", self.on_save_png, "Save as hdf5 file (5)", self.icons.get("h5"), key_shortcut = QKey.Key_5),
            "output_folder": make_button("Output folder", self.open_output_folder, "Open output folder (T)", self.icons.get("folder_blue"), key_shortcut = QKey.Key_T),
            "exit": make_button("", self.on_exit, "Exit scanalyzer (Esc/X/E)", self.icons.get("escape"))
        }
        self.buttons["direction"].setCheckable(True)
        self.buttons["spec_locations"].setCheckable(True)
        exit_shortcuts = [QtGui.QShortcut(QtGui.QKeySequence(keystroke), self) for keystroke in [QKey.Key_Q, QKey.Key_E, QKey.Key_Escape]]
        [exit_shortcut.activated.connect(self.on_exit) for exit_shortcut in exit_shortcuts]
        self.labels = {
            "scan_summary": make_label("Scanalyzer by Peter H. Jacobse"),
            "statistics": make_label("Statistics"),
            "load_file": make_label("Load file:"),
            "in_folder": make_label("in folder:"),
            "number_of_files": make_label("which contains 1 sxm file"),
            "channel_selected": make_label("Channel selected:"),

            "background_subtraction": make_label("Background subtraction"),
            "width": make_label("Width (nm):"),
            "show": make_label("Show", "Select a projection or toggle with (H)"),
            "limits": make_label("Set limits", "Toggle the min and max limits with (-) and (=), respectively"),
            "matrix_operations": make_label("Matrix operations"),

            "in_output_folder": make_label("In output folder")
        }
        self.radio_buttons = {
            "bg_none": make_radio_button("", "None (0)", self.icons.get("0")),
            "bg_plane": make_radio_button("", "Plane (P)", self.icons.get("plane_subtract")),
            "bg_linewise": make_radio_button("", "Linewise (W)", self.icons.get("lines")),
            "bg_inferred": make_radio_button("", "None (0)", self.icons.get("0")),

            "min_full": make_radio_button("", "set to minimum value of scan data range; (-) to toggle"),
            "max_full": make_radio_button("", "set to maximum value of scan data range; (=) to toggle"),
            "min_percentiles": make_radio_button("", "set to minimum percentile of data range; (-) to toggle"),
            "max_percentiles": make_radio_button("", "set to maximum percentile of data range; (=) to toggle"),
            "min_deviations": make_radio_button("", "set to minimum = mean - n * standard deviation; (-) to toggle"),
            "max_deviations": make_radio_button("", "set to maximum = mean + n * standard deviation; (=) to toggle"),
            "min_absolute": make_radio_button("", "set minimum to an absolute value; (-) to toggle"),
            "max_absolute": make_radio_button("", "set maximum to an absolute value; (=) to toggle"),
        }
        self.radio_buttons["bg_none"].setChecked(True)
        self.radio_buttons["min_full"].toggled.connect(self.load_process_display)

        self.checkboxes = {
            "sobel": make_checkbox("Sobel", "Compute the complex gradient d/dx + i d/dy; (B)", self.icons.get("derivative")),
            "laplace": make_checkbox("Laplace", "Compute the Laplacian (d/dx)^2 + (d/dy)^2; (C)", self.icons.get("laplacian")),
            "fft": make_checkbox("Fft", "Compute the 2D Fourier transform; (F)", self.icons.get("fourier")),
            "normal": make_checkbox("Normal", "Compute the z component of the surface normal (N)", self.icons.get("surface_normal")),
            "gauss": make_checkbox("Gauss", "Apply a Gaussian blur (G)", self.icons.get("gaussian")),
        }
        self.line_edits = {
            "min_full": make_line_edit("", "minimum value of scan data range"),
            "max_full": make_line_edit("", "maximum value of scan data range"),
            "min_percentiles": make_line_edit("2", "minimum percentile of data range"),
            "max_percentiles": make_line_edit("98", "maximum percentile of data range"),
            "min_deviations": make_line_edit("2", "minimum = mean - n * standard deviation"),
            "max_deviations": make_line_edit("2", "maximum = mean + n * standard deviation"),
            "min_absolute": make_line_edit("0", "minimum absolute value"),
            "max_absolute": make_line_edit("1", "maximum absolute value"),

            "gaussian_width": make_line_edit("0", "Width in nm for Gaussian blur application"),
            "file_name": make_line_edit("", "Base name of the file when saved to png or hdf5")
        }
        self.line_edits["gaussian_width"].editingFinished.connect(self.load_process_display)
        self.comboboxes = {
            "channels": make_combobox("Channels", "Available scan channels", self.on_chan_change),
            "projection": make_combobox("Projection", "Select a projection or toggle with (H)", self.load_process_display, items = ["re", "im", "abs", "arg (b/w)", "arg (hue)", "complex", "abs^2", "log(abs)"]),
            "spectra": make_combobox("spectra", "Spectra associated with the current scan")
        }
        projection_toggle_shortcut = QtGui.QShortcut(QtGui.QKeySequence(QKey.Key_H), self)
        projection_toggle_shortcut.activated.connect(self.toggle_projections)

        self.layouts = {
            "toolbar": make_layout("v"),
            "scan_summary": make_layout("v"),
            "file_channel_direction": make_layout("v"),
            "file_navigation": make_layout("h"),
            "channel_navigation": make_layout("h"),
            "image_processing": make_layout("v"),
            "background_buttons": make_layout("h"),
            "matrix_processing": make_layout("g"),
            "limits": make_layout("g"),
            "spectra": make_layout("h"),
            "i/o": make_layout("g"),
            "empty": make_layout("v")
        }        
        self.groupboxes = {
            "scan_summary": make_groupbox("Scan summary", "Information about the currently selected scan"),
            "file_chan_dir": make_groupbox("File / Channel / Direction", "Select and toggle through scan files and channels"),
            "image_processing": make_groupbox("Image processing", "Select the background subtraction, matrix operations and set the image range limits"),
            "associated_spectra": make_groupbox("Associated spectra", "Spectra recorded after the acquisition of the selected scan"),
            "i/o": make_groupbox("Output", "Save or find the processed image, or exit the app")
        }
        self.expanded_groups = {
            "scan_summary": True,
            "file_chan_dir": True,
            "image_processing": True,
            "associated_spectra": True,
            "i/o": True
        }

        return
    
    def draw_toolbar(self) -> QtWidgets.QVBoxLayout:

        def draw_summary_group() -> QtWidgets.QGroupBox: # Scan summary group
            [self.layouts["scan_summary"].addWidget(widget) for widget in [self.labels["scan_summary"], self.labels["statistics"]]]
            if self.expanded_groups["scan_summary"]:
                self.groupboxes["scan_summary"].setLayout(self.layouts["scan_summary"])
            else:
                self.groupboxes["scan_summary"].setLayout(self.layouts["empty"])
            return self.groupboxes["scan_summary"]
        
        def draw_file_chan_dir_group() -> QtWidgets.QGroupBox: # File/Channel/Direction group
            self.layouts["file_channel_direction"].addWidget(self.labels["load_file"])

            [self.layouts["file_navigation"].addWidget(button, 5 * (index % 2) + 1) for index, button in enumerate([self.buttons["previous_file"], self.buttons["select_file"], self.buttons["next_file"]])]
            self.layouts["file_channel_direction"].addLayout(self.layouts["file_navigation"])

            if self.max_file_index == 0: self.labels["number_of_files"].setText("which contains 1 sxm file")
            else: self.labels["number_of_files"].setText(f"which contains {self.max_file_index + 1} sxm files")

            [self.layouts["file_channel_direction"].addWidget(widget) for widget in [self.labels["in_folder"], self.buttons["folder_name"], self.labels["number_of_files"], self.labels["channel_selected"]]]

            self.layouts["channel_navigation"].addWidget(self.buttons["previous_channel"], 1)
            self.layouts["channel_navigation"].addWidget(self.comboboxes["channels"], 4)
            self.layouts["channel_navigation"].addWidget(self.buttons["next_channel"], 1)
            self.layouts["channel_navigation"].addWidget(self.buttons["direction"], 1)
            self.layouts["file_channel_direction"].addLayout(self.layouts["channel_navigation"])

            self.groupboxes["file_chan_dir"].setLayout(self.layouts["file_channel_direction"])
            return self.groupboxes["file_chan_dir"]

        def draw_image_processing_group() -> QtWidgets.QGroupBox: # Image processing group
            self.layouts["image_processing"].addWidget(self.labels["background_subtraction"])
            
            # Background subtraction group
            self.bg_button_group = QtWidgets.QButtonGroup(self)
            background_buttons = [self.radio_buttons[button_name] for button_name in ["bg_none", "bg_plane", "bg_linewise", "bg_inferred"]]
            [self.bg_button_group.addButton(button) for button in background_buttons] # Add buttons to the QButtonGroup for exclusive selection
            [self.layouts["background_buttons"].addWidget(button) for button in background_buttons]
            self.radio_buttons["bg_none"].setChecked(True)
            self.layouts["image_processing"].addLayout(self.layouts["background_buttons"])
            self.layouts["image_processing"].addWidget(self.gui_functions.line_widget("h", 1))

            # Matrix operations
            self.layouts["image_processing"].addWidget(self.labels["matrix_operations"])
            matrix_layout = self.layouts["matrix_processing"]
            [matrix_layout.addWidget(self.checkboxes[checkbox_name], 0, index) for index, checkbox_name in enumerate(["sobel", "normal", "laplace"])]
            matrix_layout.addWidget(self.checkboxes["gauss"], 1, 0)
            matrix_layout.addWidget(self.labels["width"], 1, 1)
            matrix_layout.addWidget(self.line_edits["gaussian_width"], 1, 2)
            matrix_layout.addWidget(self.checkboxes["fft"], 2, 0)
            matrix_layout.addWidget(self.labels["show"], 2, 1)
            matrix_layout.addWidget(self.comboboxes["projection"], 2, 2)
            self.layouts["image_processing"].addLayout(matrix_layout)
            self.layouts["image_processing"].addWidget(self.gui_functions.line_widget("h", 1))

            # Limits control group
            self.layouts["image_processing"].addWidget(self.labels["limits"])
            limits_layout = self.layouts["limits"]
            min_line_edits = [self.line_edits[line_edit_name] for line_edit_name in ["min_full", "min_percentiles", "min_deviations", "min_absolute"]]
            min_radio_buttons = [self.radio_buttons[button_name] for button_name in ["min_full", "min_percentiles", "min_deviations", "min_absolute"]]
            scale_buttons = [self.buttons[button_name] for button_name in ["full_data_range", "percentiles", "standard_deviation", "absolute_values"]]            
            max_radio_buttons = [self.radio_buttons[button_name] for button_name in ["max_full", "max_percentiles", "max_deviations", "max_absolute"]]
            max_line_edits = [self.line_edits[line_edit_name] for line_edit_name in ["max_full", "max_percentiles", "max_deviations", "max_absolute"]]
            [self.line_edits[line_edit_name].setEnabled(False) for line_edit_name in ["min_full", "max_full"]]
            [self.min_button_group, self.max_button_group] = [QtWidgets.QButtonGroup(self), QtWidgets.QButtonGroup(self)]
            [self.min_button_group.addButton(button) for button in min_radio_buttons] # Min and max buttons are exclusive
            [self.max_button_group.addButton(button) for button in max_radio_buttons]
            [limits_layout.addWidget(line_edit, index, 0) for index, line_edit in enumerate(min_line_edits)]
            [limits_layout.addWidget(line_edit, index, 1) for index, line_edit in enumerate(min_radio_buttons)]
            [limits_layout.addWidget(line_edit, index, 2) for index, line_edit in enumerate(scale_buttons)]
            [limits_layout.addWidget(line_edit, index, 3) for index, line_edit in enumerate(max_radio_buttons)]
            [limits_layout.addWidget(line_edit, index, 4) for index, line_edit in enumerate(max_line_edits)]
            self.layouts["image_processing"].addLayout(limits_layout)

            # The startup default is 100%; set the buttons accordingly (without triggering the redrawing of the scan image)
            for button in [self.radio_buttons["min_full"], self.radio_buttons["max_full"]]:
                button.blockSignals(True)
                button.setChecked(True)
                button.blockSignals(False)

            self.groupboxes["image_processing"].setLayout(self.layouts["image_processing"])
            return self.groupboxes["image_processing"]
        
        def draw_associated_spectra_group() -> QtWidgets.QGroupBox: # Associated spectra dropdown menu
            self.layouts["spectra"].addWidget(self.comboboxes["spectra"], 4)
            self.layouts["spectra"].addWidget(self.buttons["spec_locations"], 1)
            self.layouts["spectra"].addWidget(self.buttons["spectrum_viewer"], 1)

            self.groupboxes["associated_spectra"].setLayout(self.layouts["spectra"])
            return self.groupboxes["associated_spectra"]

        def draw_io_group() -> QtWidgets.QGroupBox: # I/O group
            io_layout = self.layouts["i/o"]
            #io_layout.setColumnStretch(0, 1)
            #io_layout.setColumnStretch(1, 1)

            io_layout.addWidget(self.line_edits["file_name"], 0, 0)
            io_layout.addWidget(self.buttons["save_png"], 0, 1)
            io_layout.addWidget(self.buttons["save_hdf5"], 0, 2)
            io_layout.addWidget(self.labels["in_output_folder"], 1, 0)
            io_layout.addWidget(self.buttons["output_folder"], 1, 1)
            io_layout.addWidget(self.buttons["exit"], 1, 2)

            self.groupboxes["i/o"].setLayout(io_layout)
            return self.groupboxes["i/o"]

        # Make the buttons. Overal layout is a QVBoxLayout
        self.layouts["toolbar"].setContentsMargins(4, 4, 4, 4)
        [self.layouts["toolbar"].addWidget(group) for group in [draw_summary_group(), draw_file_chan_dir_group(), draw_image_processing_group(), draw_associated_spectra_group(), draw_io_group()]]
        self.layouts["toolbar"].addStretch(1) # Add a stretch at the end to push buttons up

        return self.layouts["toolbar"]

    def connect_keys(self) -> None:
        QKey = QtCore.Qt.Key

        self.radio_buttons["bg_none"].clicked.connect(lambda: self.on_bg_change("none"))
        self.radio_buttons["bg_none"].setShortcut(QKey.Key_0)
        self.radio_buttons["bg_plane"].clicked.connect(lambda: self.on_bg_change("plane"))
        self.radio_buttons["bg_plane"].setShortcut(QKey.Key_P)
        self.radio_buttons["bg_linewise"].clicked.connect(lambda: self.on_bg_change("linewise"))
        self.radio_buttons["bg_linewise"].setShortcut(QKey.Key_W)

        # Matrix operations
        [self.checkboxes[operation].clicked.connect(lambda checked, op = operation: self.toggle_matrix_processing(op)) for operation in ["sobel", "gauss", "normal", "fft", "laplace"]]
        self.checkboxes["sobel"].setShortcut(QKey.Key_B)
        self.checkboxes["normal"].setShortcut(QKey.Key_N)
        self.checkboxes["gauss"].setShortcut(QKey.Key_G)
        self.checkboxes["fft"].setShortcut(QKey.Key_F)
        self.checkboxes["laplace"].setShortcut(QKey.Key_C)

        # Limits control group
        toggle_min_shortcut = QtGui.QShortcut(QtGui.QKeySequence(QKey.Key_Minus), self)
        toggle_min_shortcut.activated.connect(lambda: self.toggle_limits("min"))
        toggle_max_shortcut = QtGui.QShortcut(QtGui.QKeySequence(QKey.Key_Equal), self)
        toggle_max_shortcut.activated.connect(lambda: self.toggle_limits("max"))

        self.radio_buttons["bg_inferred"].setEnabled(False)
        self.buttons["save_hdf5"].setEnabled(False)

        return

    def collapse_expand(self) -> None:
        self.expanded_groups["scan_summary"] = self.groupboxes["scan_summary"].isChecked()
        self.draw_toolbar()

        return

    # Button functions
    # File selection
    def on_previous_file(self) -> None:
        self.file_index -= 1
        if self.file_index < 0: self.file_index = self.max_file_index
        self.load_process_display(new_scan = True)

        return

    def on_select_file(self) -> None:
        file_name, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open file", self.paths["data_folder"], "SXM files (*.sxm);;Dat files (*.dat);;HDF5 files (*.hdf5)")
        if file_name: self.load_folder(file_name)

        return

    def on_next_file(self) -> None:
        self.file_index += 1
        if self.file_index > self.max_file_index: self.file_index = 0
        self.load_process_display(new_scan = True)

        return

    # Channel selection
    def on_previous_chan(self) -> None:
        self.channel_index -= 1
        if self.channel_index < 0: self.channel_index = self.max_channel_index
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

    # Direction toggling
    def on_toggle_direction(self) -> None:
        new_icon = self.icons["triple_arrow"]
        if self.processing_flags["direction"] == "forward":
            self.processing_flags["direction"] = "backward"
            new_icon = self.gui_functions.rotate_icon(new_icon, angle = 180)
        else:
            self.processing_flags["direction"] = "forward"

        self.buttons["direction"].blockSignals(True)
        self.buttons["direction"].setChecked(self.processing_flags["direction"] == "backward")
        self.buttons["direction"].setIcon(new_icon)
        self.buttons["direction"].blockSignals(False)

        try:
            if hasattr(self, 'image_files') and len(self.image_files) > 0:
                self.load_process_display(new_scan = True)
        except Exception as e:
            print("Error toggling the scan direction")
            pass

        return

    # Background changing
    def on_bg_change(self, mode: str = "none") -> None:
        if mode in ["none", "plane", "inferred", "linewise"]:
            self.processing_flags["background_subtraction"] = mode
            if mode == "none": self.radio_buttons["bg_none"].setChecked(True)
            elif mode == "plane": self.radio_buttons["bg_plane"].setChecked(True)
            elif mode == "inferred": self.radio_buttons["bg_inferred"].setChecked(True)
            else: self.radio_buttons["bg_linewise"].setChecked(True)
            self.load_process_display(new_scan = False)
        
        return

    # Routines for loading a new image
    def update_filename(self) -> None:
        # Apply labels to the file name reflecting the operations performed on it
        [sobel_label, fft_label, laplace_label, normal_label] = ["" for _ in range(4)]
        if self.processing_flags["sobel"]: sobel_label = "_sobel"
        if self.processing_flags["fft"]: fft_label = "_FFT"
        if self.processing_flags["laplace"]: laplace_label = "_laplace"
        if self.processing_flags["normal"]: normal_label = "_normal"
        direction_label = "_fwd"
        if self.processing_flags["direction"] == "backward": direction_label = "_bwd"
        projection_label = "_" + self.comboboxes["projection"].currentText()
        if projection_label == "_re": projection_label = ""

        # Update displayed png filename (show basename)
        self.paths["output_file_basename"] = f"{self.channel}_{self.file_index + 1:03d}{direction_label}{fft_label}{sobel_label}{laplace_label}{normal_label}{projection_label}"
        self.line_edits["file_name"].setText(os.path.basename(self.paths["output_file_basename"]))
        self.buttons["output_folder"].setText(self.paths["output_folder_name"])

        return

    def load_folder(self, file_name: str = "") -> None:
        try:
            self.paths["data_folder"] = os.path.dirname(file_name) # Set the folder to the directory of the file
            (self.sxm_files, self.spec_files) = read_files(self.paths["data_folder"]) # Read the names and datetimes of all scans (.sxm files) and spectra (.dat files)
            
            self.max_file_index = len(self.sxm_files) - 1
            self.file_index = np.where([os.path.samefile(sxm_file, file_name) for sxm_file in self.sxm_files[:, 1]])[0][0] # Find the number of the specific file that was selected
            if self.file_index > self.max_file_index: self.file_index = 0 # Roll over if the selected file index is too large
            self.paths["output_folder"] = os.path.join(self.paths["data_folder"], self.paths["output_folder_name"])
            self.sxm_file = self.sxm_files[self.file_index] # Apply the index to the list of sxm files to pick the correct sxm file
            self.file_label = self.sxm_file[0] # The file label is the file name without the directory path

            # Update folder/contents labels
            try:
                self.buttons["folder_name"].setText(self.paths["data_folder"])
                if self.max_file_index == 0: self.labels["number_of_files"].setText("which contains 1 sxm file")
                else: self.labels["number_of_files"].setText(f"which contains {self.max_file_index + 1} sxm files")
            except Exception as e:
                print(f"Error: {e}")

            if self.max_file_index > 0:
                self.load_process_display(new_scan = True)

        except Exception as e:
            print(f"Error loading files: {e}")
            self.buttons["select_file"].setText("Select file")
        
        return

    def load_scan(self) -> np.ndarray:        
        # Load the sxm file from the list of sxm files
        self.sxm_file = self.sxm_files[self.file_index]
        try:
            self.file_label = self.sxm_file[0]
        except:
            print("Error. Could not retrieve scan.")
            return
        
        self.buttons["select_file"].setText(self.file_label) # Make the select file button display the file name

        # Load the scan object using nanonispy2
        self.scan_object = get_scan(self.sxm_file[1], units = {"length": "nm", "current": "pA"})
        scan_tensor = self.scan_object.tensor
        self.channels = self.scan_object.channels # Load which channels have been recorded
        if self.channel not in self.channels: # If the requested channel does not exist in the scan, default the requested channel to be the first channel in the list of channels
            self.channel = self.channels[0]
        self.channel_index = np.where(self.channels == self.channel)[0][0]
        self.max_channel_index = len(self.channels) - 1

        # Update the channel selection box based on the available channels
        self.comboboxes["channels"].blockSignals(True)
        self.comboboxes["channels"].clear()
        self.comboboxes["channels"].addItems(self.channels)
        self.comboboxes["channels"].setCurrentIndex(self.channel_index)
        self.comboboxes["channels"].blockSignals(False)

        # Read the header and save the scan parameters
        self.bias = self.scan_object.bias
        self.bias_V = self.bias.to("V").magnitude

        self.offset = self.scan_object.offset
        self.offset_nm = [range_dim.to("nm").magnitude for range_dim in self.offset]

        self.angle = self.scan_object.angle
        self.angle_deg = self.angle.to("degree").magnitude

        self.scan_range = self.scan_object.scan_range
        self.scan_range_nm = [range_dim.to("nm").magnitude for range_dim in self.scan_range]

        self.feedback = self.scan_object.feedback # Read whether the scan was recorded in STM feedback
        self.setpoint = self.scan_object.setpoint
        self.setpoint_pA = self.setpoint.to("pA").magnitude
        self.scan_time = self.scan_object.date_time

        # Display scan data in the app
        if self.feedback:
            self.summary_text = f"STM topographic scan recorded on\n{self.scan_time.strftime('%Y/%m/%d   at   %H:%M:%S')}\n\n(V = {self.bias_V:.3f} V; I_fb = {self.setpoint_pA:.3f} pA)\nScan range: {self.scan_range_nm[0]:.3f} nm by {self.scan_range_nm[1]:.3f} nm"
        else:
            self.summary_text = f"Constant height scan recorded on\n{self.scan_time.strftime('%Y/%m/%d   at   %H:%M:%S')}\n\n(V = {self.bias_V:.3f} V)\nScan range: {self.scan_range_nm[0]:.3f} nm by {self.scan_range_nm[1]:.3f} nm"
        self.labels["scan_summary"].setText(self.summary_text)
        
        # Find the spectra associated with this scan and make them available for viewing as target items and in the combobox
        self.find_associated_spectra()

        # Channel / scan direction selection
        # Pick the correct frame out of the scan tensor based on channel and scan direction
        if self.processing_flags["direction"] == "backward": selected_scan = scan_tensor[self.channel_index, 1]
        else: selected_scan = scan_tensor[self.channel_index, 0]

        return selected_scan

    def find_associated_spectra(self):
        # From the list of spectra (spec_files), select the ones that are associated with the current scan (associated scan name is column 3 in self.spec_files and column 0 in self.sxm_files)
        try:
            associated_spectra_indices = np.where(self.spec_files[:, 3] == self.sxm_file[0])[0]
            self.associated_spectra = [self.spec_files[index] for index in associated_spectra_indices]
        except:
            self.associated_spectra = []

        # Update the spectra combobox        
        self.comboboxes["spectra"].blockSignals(True)
        self.comboboxes["spectra"].clear()
        self.comboboxes["spectra"].addItems([spectrum[0] for spectrum in self.associated_spectra])
        self.comboboxes["spectra"].blockSignals(False)

        # Remove all spectroscopy targets if there were any
        view_box = self.image_view.getView()
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

                target_item = pg.TargetItem(size = 10, pen = pg.mkPen(None), brush = pg.mkBrush('r'), movable = False)
                target_item = HoverTargetItem(pos = [x_rotated, y_rotated], size = 10, tip_text = data[0])
                target_item.setZValue(10)
                
                self.spec_targets.append(target_item)
            except Exception as e:
                print("Error populating the target items")
        
        return

    def process_scan(self, scan: np.ndarray) -> np.ndarray:
        # Background subtraction
        mode = self.processing_flags["background_subtraction"]
        processed_scan = background_subtract(scan, mode = mode)

        # Apply matrix operations
        try: gaussian_sigma = float(self.line_edits["gaussian_width"].text())
        except: gaussian_sigma = 0
        if self.processing_flags["sobel"]: processed_scan = image_gradient(processed_scan, self.scan_range)
        if self.processing_flags["normal"]: processed_scan = compute_normal(processed_scan, self.scan_range)
        if self.processing_flags["laplace"]: processed_scan = apply_laplace(processed_scan, self.scan_range)
        if self.processing_flags["gaussian"]: processed_scan = apply_gaussian(processed_scan, sigma = gaussian_sigma, scan_range = self.scan_range)
        if self.processing_flags["fft"]: processed_scan, reciprocal_range = apply_fft(processed_scan, self.scan_range)
        
        # Perform the correct projection
        match self.comboboxes["projection"].currentText():
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
        range_tot = self.statistics.get("range_total")
        mean = self.statistics.get("mean")
        standard_deviation = self.statistics.get("standard_deviation")

        unit_label = ""
        if self.channel == "X" or self.channel == "Y" or self.channel == "Z": unit_label = " nm"
        elif self.channel == "Current": unit_label = " pA"
        self.labels["statistics"].setText(f"\nValue range: {round(range_tot, 3)}{unit_label}; Mean ± std dev: {round(mean, 3)} ± {round(standard_deviation, 3)}{unit_label}")

        # Update the filename for the scan
        self.update_filename()
        
        return processed_scan

    def update_limits(self) -> None:
        self.hist_levels = list(self.hist_item.getLevels())
        [min, max] = self.hist_levels
        self.line_edits["min_full"].setText(f"{round(min, 3)}")
        self.line_edits["max_full"].setText(f"{round(max, 3)}")

        # Update the min according to which limit method is selected
        if self.radio_buttons["min_percentiles"].isChecked(): # Percentiles
            if hasattr(self, "statistics"):
                try:
                    min_percentile = float(self.line_edits["min_percentiles"].text())
                    data_sorted = self.statistics.get("data_sorted")
                    n_data = len(data_sorted)

                    min = data_sorted[int(.01 * min_percentile * n_data)]
                except Exception as e:
                    print(f"Error: {e}")
        elif self.radio_buttons["min_absolute"].isChecked(): # Absolute values
            try:
                min = float(self.line_edits["min_absolute"].text())
            except Exception as e:
                print(f"Error: {e}")
        elif self.radio_buttons["min_deviations"].isChecked(): # Standard deviation
            if hasattr(self, "statistics"):
                try:
                    value = float(self.line_edits["min_deviations"].text())
                    min = self.statistics.get("mean") - value * self.statistics.get("standard_deviation")
                except Exception as e:
                    print(f"Error: {e}")
        else:
            pass

        # Update the max according to which limit method is selected
        if self.radio_buttons["max_percentiles"].isChecked(): # Percentiles
            if hasattr(self, "statistics"):
                try:
                    max_percentile = float(self.line_edits["max_percentiles"].text())
                    data_sorted = self.statistics.get("data_sorted")
                    n_data = len(data_sorted)

                    max = data_sorted[int(.01 * max_percentile * n_data)]
                except Exception as e:
                    print(f"Error: {e}")
        elif self.radio_buttons["max_absolute"].isChecked(): # Absoulte values
            try:
                max = float(self.line_edits["max_absolute"].text())
            except Exception as e:
                print(f"Error: {e}")
        elif self.radio_buttons["max_deviations"].isChecked(): # Standard deviation
            if hasattr(self, "statistics"):
                try:
                    value = float(self.line_edits["max_deviations"].text())
                    max = self.statistics.get("mean") + value * self.statistics.get("standard_deviation")
                except Exception as e:
                    print(f"Error: {e}")
        else:
            pass

        # Set the histogram levels and reconnect the histogram widget to dynamic updating
        self.hist_item.setLevels(min, max)
        self.line_edits["min_absolute"].setText(f"{round(min, 3)}") # Update the absolute value boxes
        self.line_edits["max_absolute"].setText(f"{round(max, 3)}")
        try: self.hist_item.sigLevelChangeFinished.connect(self.histogram_scale_changed)
        except: pass

    def display(self, scan: np.ndarray) -> None:
        # Show the scan
        try: self.hist_item.sigLevelChangeFinished.disconnect()
        except: pass

        self.image_view.setImage(scan, autoRange = True) # Show the scan in the app
        image_item = self.image_view.getImageItem()
        image_item.setRect(QtCore.QRectF(-self.scan_range_nm[1] / 2, -self.scan_range_nm[1] / 2, self.scan_range_nm[1], self.scan_range_nm[0]))  # Add dimensions to the ImageView object

        if self.processing_flags["spec_locations"]:
            view_box = self.image_view.getView()        
            for target in self.spec_targets: view_box.addItem(target)

        # Reset the limits and histogram
        self.image_view.autoRange()
        self.update_limits() # The sigLevelChangeFinished method will be reconnected within self.update_limits() after the new limits are set

    def load_process_display(self, new_scan: bool = False) -> None:
        if new_scan or not hasattr(self, "current_scan"):
            self.current_scan = self.load_scan()
        processed_scan = self.process_scan(self.current_scan)
        self.display(processed_scan)
        
        return



    # Spectroscopy
    def open_spectrum_viewer(self) -> None:
        spec_shape = self.spec_files.shape
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
    def on_full_scale(self, side: str = "both") -> None:
        if side == "min" or side == "both":
            self.radio_buttons["min_full"].setChecked(True)
            self.processing_flags["min_selection"] = 0
        if side == "max" or side == "both":
            self.radio_buttons["max_full"].setChecked(True)
            self.processing_flags["max_selection"] = 0
        self.load_process_display(new_scan = False)

        return

    def on_percentiles(self, side: str = "both") -> None:
        if side == "min" or side == "both":
            self.radio_buttons["min_percentiles"].setChecked(True)
            self.processing_flags["min_selection"] = 1
        if side == "max" or side == "both":
            self.radio_buttons["max_percentiles"].setChecked(True)
            self.processing_flags["max_selection"] = 1
        self.load_process_display(new_scan = False)

        return

    def on_standard_deviations(self, side: str = "both") -> None:
        if side == "min" or side == "both":
            self.radio_buttons["min_deviations"].setChecked(True)
            self.processing_flags["min_selection"] = 2
        if side == "max" or side == "both":
            self.radio_buttons["max_deviations"].setChecked(True)
            self.processing_flags["max_selection"] = 2
        self.load_process_display(new_scan = False)

        return

    def on_absolute_values(self, side: str = "both") -> None:
        if side == "min" or side == "both":
            self.radio_buttons["min_absolute"].setChecked(True)
            self.processing_flags["max_selection"] = 3
        if side == "max" or side == "both":
            self.radio_buttons["max_absolute"].setChecked(True)
            self.processing_flags["max_selection"] = 3
        self.load_process_display(new_scan = False)

        return

    def histogram_scale_changed(self) -> None:
        (min, max) = self.hist_item.getLevels()
        if hasattr(self, "hist_levels"):
            [min_old, max_old] = self.hist_levels

            if np.abs(max - max_old) > .0000001 * (max_old - min_old): # If the top level was changed (use a tiny threshold)
                self.line_edits["max_absolute"].setText(f"{round(max, 3)}")
                self.radio_buttons["max_absolute"].setChecked(True)
                self.processing_flags["max_selection"] = 3

            if np.abs(min - min_old) > .0000001 * (max_old - min_old): # If the bottom level was changed
                self.line_edits["min_absolute"].setText(f"{round(min, 3)}")
                self.radio_buttons["min_absolute"].setChecked(True)
                self.processing_flags["min_selection"] = 3

        self.hist_levels = [min, max]

        return

    def toggle_limits(self, side: str = "min") -> None:
        if side not in ["min", "max"]:
            print("Error. No correct side chosen.")
            return
        
        if side == "min":
            self.processing_flags["min_selection"] += 1
            if self.processing_flags["min_selection"] > 3: self.processing_flags["min_selection"] = 0
            sel = self.processing_flags["min_selection"]
        else:
            self.processing_flags["max_selection"] += 1
            if self.processing_flags["max_selection"] > 3: self.processing_flags["max_selection"] = 0
            sel = self.processing_flags["max_selection"]
        
        match sel:
            case 0: self.on_full_scale(side)
            case 1: self.on_percentiles(side)
            case 2: self.on_standard_deviations(side)
            case _: self.on_absolute_values(side)
        
        return

    # Matrix processing functions
    def toggle_matrix_processing(self, operation: str = "none") -> None:
        match operation:
            case "sobel":
                checked = self.checkboxes["sobel"].isChecked()
                self.processing_flags["sobel"] = checked
            case "gauss":
                checked = self.checkboxes["gauss"].isChecked()
                self.processing_flags["gaussian"] = checked
            case "fft":
                checked = self.checkboxes["fft"].isChecked()
                self.processing_flags["fft"] = checked
            case "laplace":
                checked = self.checkboxes["laplace"].isChecked()
                self.processing_flags["laplace"] = checked
            case "normal":
                checked = self.checkboxes["normal"].isChecked()
                self.processing_flags["normal"] = checked
            case _:
                pass

        if not hasattr(self, "current_scan"):
            self.current_scan = self.load_scan()
        processed_scan = self.process_scan(self.current_scan)
        self.display(processed_scan)

        return

    def toggle_projections(self) -> None:
        try:
            number_of_items = self.comboboxes["projection"].count()
            current_index = self.comboboxes["projection"].currentIndex()
            new_index = current_index + 1
            if new_index > number_of_items - 1: new_index = 0
            self.comboboxes["projection"].setCurrentIndex(new_index)
            self.load_process_display()

        except Exception as e:
            print(f"An error occurred while applying the projection: {e}")
        
        return

    # Spectroscopy
    def on_toggle_spec_locations(self) -> None:
        self.processing_flags["spec_locations"] = not self.processing_flags["spec_locations"]
        self.buttons["spec_locations"].blockSignals(True)
        self.buttons["spec_locations"].setChecked(self.processing_flags["spec_locations"] == True)
        self.buttons["spec_locations"].blockSignals(False)

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

    def open_data_folder(self) -> None:
        if hasattr(self, "paths") and "data_folder" in list(self.paths.keys()):
            try: os.startfile(self.paths["data_folder"])
            except: pass
        
        return

    def open_output_folder(self) -> None:
        if hasattr(self, "paths") and "output_folder" in list(self.paths.keys()):
            try: os.startfile(self.paths["output_folder"])
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

    # Exit
    def closeEvent(self, a0) -> None:
        self.on_exit
    
    def on_exit(self) -> None:
        try: # Save the currently opened scan folder to the config yaml file so it opens automatically on startup next time
            with open(self.paths["config_path"], "w") as file:
                yaml.safe_dump({"last_file": str(self.sxm_file[1])}, file)
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