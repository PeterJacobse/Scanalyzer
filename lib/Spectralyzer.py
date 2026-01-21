import os, sys, re, yaml, pint
import numpy as np
from PyQt6 import QtCore, QtGui, QtWidgets
import pyqtgraph as pg
import pyqtgraph.exporters as expts
from . import GUIItems, HoverTargetItem, DataProcessing, FileFunctions, ScanalyzerGUI, SpectralyzerGUI



class Spectralyzer:
    def __init__(self, spec_files: list = [], associated_spectra: list = [], scan_image: np.ndarray = np.zeros((2, 2))):
        super().__init__()
        
        self.spec_files = spec_files
        self.associated_spectra = associated_spectra

        # Spectrum colors
        self.color_list = ["#FFFFFF", "#FFFF00", "#FF90FF", "#00FFFF", "#00FF00", "#A0A0A0", "#FF4040", "#5050FF", "#FFA500", "#9050FF", "#808000", "#008080", "#900090", "#009000", "#B00000", "#0000C0"]
        
        self.parameters_init()
        self.gui = SpectralyzerGUI()
        self.gui.image_item.setImage(scan_image)
        self.spec_objects, self.channels = self.read_spectroscopy_files()
        self.connect_keys()
        self.set_focus_row(0)
        self.redraw_spectra()
        self.gui.show()



    def parameters_init(self) -> None:
        lib_folder = os.path.dirname(os.path.abspath(__file__))
        project_folder = os.path.dirname(lib_folder)
        icon_folder = os.path.join(project_folder, "icons")
        
        icon_files = os.listdir(icon_folder)
        self.icons = {}
        for icon_file in icon_files:
            [icon_name, extension] = os.path.splitext(os.path.basename(icon_file))
            try:
                if extension == ".png": self.icons.update({icon_name: QtGui.QIcon(os.path.join(icon_folder, icon_file))})
            except:
                pass

        self.focus_row = 0
        self.processing_flags = {
            "line_width": 2,
            "opacity": 1
        }
        self.file_functions = FileFunctions()
        self.data = DataProcessing()



    def connect_keys(self) -> None:
        buttons = self.gui.buttons
        plot_number_comboboxes = self.gui.plot_number_comboboxes

        buttons["save_0"].clicked.connect(lambda: self.on_save_spectrum(0))
        buttons["save_1"].clicked.connect(lambda: self.on_save_spectrum(1))
        buttons["exit"].clicked.connect(self.on_exit)        
        
        chan_sel_boxes = [self.gui.channel_selection_comboboxes[name] for name in ["x_axis", "y_axis_0", "y_axis_1"]]
        [combobox.currentIndexChanged.connect(lambda: self.redraw_spectra(toggle_checkbox = False)) for combobox in chan_sel_boxes]
        [plot_number_comboboxes[f"{index}"].currentIndexChanged.connect(lambda: self.redraw_spectra(toggle_checkbox = False)) for index in range(len(plot_number_comboboxes))]

        [self.gui.line_edits[name].editingFinished.connect(self.change_pen_style) for name in ["line_width", "opacity"]]
        [self.gui.line_edits[name].editingFinished.connect(lambda: self.redraw_spectra(toggle_checkbox = False)) for name in ["offset_0", "offset_1"]]

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
        x_axis_shortcut.activated.connect(lambda: self.toggle_axis("x_axis"))
        y_axis_0_shortcut.activated.connect(lambda: self.toggle_axis("y_axis_0"))
        y_axis_1_shortcut.activated.connect(lambda: self.toggle_axis("y_axis_1"))



    def read_spectroscopy_files(self) -> tuple:
        channel_selection_comboboxes = self.gui.channel_selection_comboboxes
        plot_number_comboboxes = self.gui.plot_number_comboboxes
        
        #(spec_objects, error) = [self.file_functions.get_spectrum(spec_file[1]) for spec_file in self.spec_files] # Get a spectroscopy object for each spectroscopy file
        spec_objects = {}
        
        # Find all the channels recorded during all the spectroscopies and combine them into a list called all_channels
        all_channels = []
        for spec_object in spec_objects:
            all_channels.extend(list(spec_object.channels))
        all_channels = list(set(all_channels))
        all_channels = np.array([str(channel) for channel in all_channels])
        
        [channel_selection_comboboxes[axis].addItems(all_channels) for axis in ["x_axis", "y_axis_0", "y_axis_1"]]
        
        # Attempt to set the channel toggle boxes to logical starting defaults
        [combobox.blockSignals(True) for combobox in channel_selection_comboboxes.values()]
        try:
            x_axis_targets = ["Bias (V)", "Bias [bwd] V", "Bias calc (V)"]
            for label in x_axis_targets:
                if label in all_channels:
                    channel_index = np.where(all_channels == label)[0][0]
                    channel_selection_comboboxes["x_axis"].setCurrentIndex(channel_index)
                    break

            y_axis_0_targets = ["LI demod X1 (A)", "Current (A)"]
            for label in y_axis_0_targets:
                if label in all_channels:
                    channel_index = np.where(all_channels == label)[0][0]
                    channel_selection_comboboxes["y_axis_0"].setCurrentIndex(channel_index)
                    break

            y_axis_1_targets = ["Current (A)", "Current [bwd] (A)", "Current calc (A)"]
            for label in y_axis_1_targets:
                if label in all_channels:
                    channel_index = np.where(all_channels == label)[0][0]
                    channel_selection_comboboxes["y_axis_1"].setCurrentIndex(channel_index)
                    break
        except Exception as e:
            print(f"Error while trying to set the comboboxes to default values: {e}")
        [combobox.blockSignals(False) for combobox in channel_selection_comboboxes.values()]

        # Put a star on the spectrum names that are associated with the scan and initialize the comboboxes
        [combobox.blockSignals(True) for combobox in plot_number_comboboxes.values()]
        #spec_labels = self.spec_files[:, 0]
        """
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
        """
        
        # Connect the checkboxes
        [checkbox.toggled.connect(lambda: self.redraw_spectra(False)) for checkbox in self.gui.checkboxes.values()]

        return spec_objects, all_channels

    def redraw_spectra(self, toggle_checkbox: bool = False) -> None:
        plot_items = self.gui.plot_items
        line_edits = self.gui.line_edits
        checkboxes = self.gui.checkboxes
        leftarrows = self.gui.leftarrows
        rightarrows = self.gui.rightarrows
        plot_number_comboboxes = self.gui.plot_number_comboboxes
        graph_0 = self.gui.plot_items["graph_0"]
        graph_1 = self.gui.plot_items["graph_1"]
        
        if toggle_checkbox:
            checked = checkboxes[f"{self.focus_row}"].isChecked()
            [checkbox.blockSignals(True) for checkbox in checkboxes.values()]
            checkboxes[f"{self.focus_row}"].setChecked(not checked)
            [checkbox.blockSignals(False) for checkbox in checkboxes.values()]

        # Grey out the plot rows that are not enabled (checked using the checkbox)
        for index in range(len(checkboxes)):
            checkbox = checkboxes[f"{index}"]
            checked = checkbox.isChecked()
            if checked: [button.setEnabled(True) for button in [leftarrows[f"{index}"], plot_number_comboboxes[f"{index}"], rightarrows[f"{index}"]]]
            else: [button.setEnabled(False) for button in [leftarrows[f"{index}"], plot_number_comboboxes[f"{index}"], rightarrows[f"{index}"]]]

        # Read the QComboboxes and retrieve what channels are requested
        if not hasattr(self, "channels"): return # Return if the channels have not yet been read
        #x_index = self.channel_selection_comboboxes["x_axis"].currentIndex()
        #y_0_index = self.channel_selection_comboboxes["y_axis_0"].currentIndex()
        #y_1_index = self.channel_selection_comboboxes["y_axis_1"].currentIndex()
        #[x_channel, y_0_channel, y_1_channel] = [self.channels[index] for index in [x_index, y_0_index, y_1_index]]

        x_data = np.linspace(-2, 2, 20)
        [graph.clear() for graph in [graph_0, graph_1]]

        # Set the pen
        # Set the pen properties from processing flags
        line_width = self.data.processing_flags.get("line_width", 1)
        opacity = self.data.processing_flags.get("opacity", 1)

        offset_0 = float(line_edits["offset_0"].text())
        offset_1 = float(line_edits["offset_1"].text())

        for i in range(len(checkboxes) - 1, -1, -1):
            color = self.color_list[i]

            if checkboxes[f"{i}"].isChecked():
                spec_index = plot_number_comboboxes[f"{i}"].currentIndex()
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

                    graph_0.plot(x_data, y_0_data_shifted, pen = pen)
                except Exception as e:
                    print(f"Error: {e}")
                try:
                    x_data = spec_signal[x_channel]
                    y_1_data = spec_signal[y_1_channel]
                    y_1_data_shifted = y_1_data + i * offset_1
                
                    graph_1.plot(x_data, y_1_data_shifted, pen = pen)
                except Exception as e:
                    print(f"Error: {e}")

    def toggle_plot_number(self, plot_index: int = 0, increase: bool = True) -> None:
        try:
            current_index = self.gui.plot_number_comboboxes[f"{plot_index}"].currentIndex()

            if increase: new_index = current_index + 1
            else: new_index = current_index - 1
            
            if new_index > len(self.spec_files) - 1: new_index = 0
            if new_index < 0: new_index = len(self.spec_files) - 1

            # Changing the index of the combobox automatically activates self.redraw_spectra() since the currentIndexChanged signal is connected to that method
            self.gui.plot_number_comboboxes[f"{plot_index}"].setCurrentIndex(new_index)

        except Exception as e:
            print(f"Error toggling the plot: {e}")
        
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
        QtWidgets.QApplication.instance().quit()



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = Spectralyzer()
    sys.exit(app.exec())
