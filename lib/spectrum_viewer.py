import os, sys, re, yaml, pint
import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import pyqtgraph.exporters as expts
from lib import GUIFunctions, GUIItems, ScanalyzerGUI, HoverTargetItem, DataProcessing, FileFunctions



class SpectrumViewer(QtWidgets.QMainWindow):
    def __init__(self, processed_scan, spec_files, associated_spectra, paths):
        super().__init__()
        self.setWindowTitle("Spectrum viewer")
        self.setGeometry(200, 200, 1200, 800)
        self.spec_files = spec_files # Make the spectroscopy file list an attribute of the SpectroscopyWindow class
        self.associated_spectra = associated_spectra
        self.processed_scan = processed_scan
        self.paths = paths

        # Spectrum colors
        self.color_list = ["#FFFFFF", "#FFFF00", "#FF90FF", "#00FFFF", "#00FF00", "#A0A0A0", "#FF4040", "#5050FF", "#FFA500", "#9050FF", "#808000", "#008080", "#900090", "#009000", "#B00000", "#0000C0"]
        
        self.parameters_init()
        self.gui_items_init()
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
        self.data.processing_flags = {
            "line_width": 2,
            "opacity": 1
        }
        self.file_functions = FileFunctions()

    def gui_items_init(self) -> None:
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
            "save_0": make_button("", lambda: self.on_save_spectrum(0), "Save graph 0 to svg", self.icons.get("floppy")),
            "save_1": make_button("", lambda: self.on_save_spectrum(1), "Save graph 1 to svg", self.icons.get("floppy")),
            "exit": make_button("", self.close, "Exit Spectrum Viewer (Q / Esc)", self.icons.get("escape"))
        }
        self.channel_selection_comboboxes = {
            "x_axis": make_combobox("x_axis", "Channel to display on the x axis (X)", lambda: self.redraw_spectra(toggle_checkbox = False)),
            "y_axis_0": make_combobox("y_axis_0", "Channel to display on the y axis (Y)", lambda: self.redraw_spectra(toggle_checkbox = False)),
            "y_axis_1": make_combobox("y_axis_1", "Channel to display on the y axis (Z)", lambda: self.redraw_spectra(toggle_checkbox = False)),
        }
        for combobox in [self.channel_selection_comboboxes["x_axis"], self.channel_selection_comboboxes["y_axis_0"], self.channel_selection_comboboxes["y_axis_1"]]:
            combobox.currentIndexChanged.connect(lambda: self.redraw_spectra(toggle_checkbox = False))

        self.layouts = {
            "main": make_layout("g"),
            "selector": make_layout("g"),
            "x_axis": make_layout("h"),
            "plots": make_layout("v"),
            "options": make_layout("g")
        }
        self.line_edits = {
            "offset_0": make_line_edit("0", "Offset between successive spectra"),
            "offset_1": make_line_edit("0", "Offset between successive spectra"),
            "line_width": make_line_edit("2", "Line width"),
            "opacity": make_line_edit("1", "Opacity")
        }
        self.labels = {
            "save_0": make_label("save (plot 0)", "Save plot 0 to svg (S)"),
            "save_1": make_label("save (plot 1)", "Save plot 1 to svg (Z)"),
            "x_axis": make_label("x axis", "Toggle with (X)"),
            "y_axis_0": make_label("y axis (plot 0)", "Toggle with (Y)"),
            "y_axis_1": make_label("y axis (plot 1)", "Toggle with (Z)"),
            "offset_0": make_label("Offset", "Offset between successive spectra", self.icons.get("offset")),
            "offset_1": make_label("Offset", "Offset between successive spectra", self.icons.get("offset")),
            "line_width": make_label("Line width", "Line width"),
            "opacity": make_label("Opacity", "Opacity")
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

        # Plots
        plot_widget = QtWidgets.QWidget()
        self.graph_0_widget = pg.PlotWidget()
        self.graph_1_widget = pg.PlotWidget()
        [self.layouts["plots"].addWidget(widget) for widget in [self.channel_selection_comboboxes["x_axis"], self.graph_0_widget, self.graph_1_widget]]
        plot_widget.setLayout(self.layouts["plots"])
        self.graph_0 = self.graph_0_widget.getPlotItem() # Get the plotitems corresponding to the plot widgets
        self.graph_1 = self.graph_1_widget.getPlotItem()
        self.graph_0.setFixedWidth(500)

        # Options
        option_widget = QtWidgets.QWidget()
        option_widgets_col0 = [self.labels["y_axis_0"], self.labels["offset_0"], self.labels["save_0"],
                               self.labels["y_axis_1"], self.labels["offset_1"], self.labels["save_1"],
                               self.labels["line_width"], self.labels["opacity"]]
        option_widgets_col1 = [self.channel_selection_comboboxes["y_axis_0"], self.line_edits["offset_0"], self.buttons["save_0"],
                               self.channel_selection_comboboxes["y_axis_1"], self.line_edits["offset_1"], self.buttons["save_1"],
                               self.line_edits["line_width"], self.line_edits["opacity"]]
        [self.layouts["options"].addWidget(widget, index, 0) for index, widget in enumerate(option_widgets_col0)]
        [self.layouts["options"].addWidget(widget, index, 1) for index, widget in enumerate(option_widgets_col1)]
        option_widget.setLayout(self.layouts["options"])
        
        #self.layouts["options"].addWidget(self.gui_functions.line_widget("h", 1))

        # x axis
        x_widget = QtWidgets.QWidget()
        [self.layouts["x_axis"].addWidget(widget) for widget in [self.labels["x_axis"], self.channel_selection_comboboxes["x_axis"]]]
        x_widget.setLayout(self.layouts["x_axis"])

        # Scan
        self.image_widget = pg.GraphicsLayoutWidget()
        self.view_box = self.image_widget.addViewBox()
        self.view_box.setAspectLocked(True)
        self.view_box.invertY(True)
        self.image_item = pg.ImageItem()
        self.view_box.addItem(self.image_item)
        self.image_item.setImage(self.processed_scan)

        # Main widget
        self.layouts["main"].addWidget(spectrum_selector_widget, 1, 0, 2, 1) # Spectrum selector buttons
        self.layouts["main"].addWidget(x_widget, 0, 1) # x axis channel selection combobox
        self.layouts["main"].addWidget(plot_widget, 1, 1, 2, 1)
        self.layouts["main"].addWidget(self.buttons["exit"], 0, 2)
        self.layouts["main"].addWidget(option_widget, 1, 2)
        self.layouts["main"].addWidget(self.image_widget, 2, 2)
        self.layouts["main"].setColumnMinimumWidth(1, 500)

        #[self.layouts["main"].addWidget(widget, i, 1, alignment = QtCore.Qt.AlignmentFlag.AlignCenter) for i, widget in enumerate(column_1_widgets)]
        #[self.layouts["main"].addWidget(widget, i, 2, alignment = QtCore.Qt.AlignmentFlag.AlignCenter) for i, widget in enumerate(column_2_widgets)]
        central_widget.setLayout(self.layouts["main"])

    def connect_keys(self) -> None:
        # Connect the final clicky things before connecting the key-y things
        [self.plot_number_comboboxes[f"{index}"].currentIndexChanged.connect(lambda: self.redraw_spectra(toggle_checkbox = False)) for index in range(len(self.plot_number_comboboxes))]
        [edit.editingFinished.connect(self.change_pen_style) for edit in [self.line_edits["line_width"], self.line_edits["opacity"]]]
        [edit.editingFinished.connect(lambda: self.redraw_spectra(toggle_checkbox = False)) for edit in [self.line_edits["offset_0"], self.line_edits["offset_1"]]]

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
        (spec_objects, error) = [self.file_functions.get_spectrum(spec_file[1]) for spec_file in self.spec_files] # Get a spectroscopy object for each spectroscopy file
        
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

        # Set the pen
        # Set the pen properties from processing flags
        line_width = self.data.processing_flags.get("line_width", 1)
        opacity = self.data.processing_flags.get("opacity", 1)

        offset_0 = float(self.line_edits["offset_0"].text())
        offset_1 = float(self.line_edits["offset_1"].text())

        for i in range(len(self.checkboxes) - 1, -1, -1):
            color = self.color_list[i]

            if self.checkboxes[f"{i}"].isChecked():
                spec_index = self.plot_number_comboboxes[f"{i}"].currentIndex()
                spec_object = self.spec_objects[spec_index]
                spec_signal = spec_object.signals
                
                try:
                    # Create pen with color, width, and opacity
                    pen = pg.mkPen(color = color, width = line_width, alphaF = opacity)
                    pen.setCapStyle(QtCore.Qt.PenCapStyle.RoundCap)
                    pen.setJoinStyle(QtCore.Qt.PenJoinStyle.RoundJoin)

                    x_data = spec_signal[x_channel]
                    y_0_data = spec_signal[y_0_channel]
                    y_0_data_shifted = y_0_data + i * offset_0

                    self.graph_0.plot(x_data, y_0_data_shifted, pen = pen)
                except Exception as e:
                    print(f"Error: {e}")
                try:
                    x_data = spec_signal[x_channel]
                    y_1_data = spec_signal[y_1_channel]
                    y_1_data_shifted = y_1_data + i * offset_1
                
                    self.graph_1.plot(x_data, y_1_data_shifted, pen = pen)
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

    def change_pen_style(self) -> None:
        self.data.processing_flags["line_width"] = float(self.line_edits["line_width"].text())
        self.data.processing_flags["opacity"] = float(self.line_edits["opacity"].text())
        self.redraw_spectra()
        return

    def on_save_spectrum(self, plot_number: int = 0) -> None:
        try:
            export_folder = self.paths["output_folder"]
            if plot_number == 0:
                scene = self.graph_0_widget.scene()
            else:
                scene = self.graph_1_widget.scene()
            exporter = expts.SVGExporter(scene)

            file_path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save file", export_folder, "svg files (*.svg)")
            if file_path:
                exporter.export(file_path)
        
        except Exception as e:
            print("Error saving file.")
        
        return


