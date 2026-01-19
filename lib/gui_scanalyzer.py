import os
from PyQt6 import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
from . import GUIItems



class ScanalyzerGUI(QtWidgets.QMainWindow):
    def __init__(self, icons_path):
        super().__init__()
        
        # 1: Read icons from file.
        self.icons_path = icons_path
        self.get_icons()
        
        # 2: Create the specific GUI items using the items from the GUIItems class. Requires icons.
        self.gui_items = GUIItems()
        self.labels = self.make_labels()
        self.buttons = self.make_buttons()
        self.checkboxes = self.make_checkboxes()
        self.comboboxes = self.make_comboboxes()
        self.line_edits = self.make_line_edits()
        self.radio_buttons = self.make_radio_buttons()
        self.lines = self.make_lines()
        self.layouts = self.make_layouts()
        self.image_view = self.make_image_view()
        self.widgets = self.make_widgets()
        self.consoles = self.make_consoles()
        self.shortcuts = self.make_shortcuts()
                
        # 3: Populate layouts with GUI items. Requires GUI items.
        self.populate_layouts()
        
        # 4: Make groupboxes and set their layouts. Requires populated layouts.
        self.groupboxes = self.make_groupboxes()
        
        # 5: Set up the main window layout
        #self.setup_main_window()



    # 1: Read icons from file.
    def get_icons(self):
        icons_path = self.icons_path
        icon_files = os.listdir(icons_path)
        
        self.icons = {}
        for icon_file in icon_files:
            [icon_name, extension] = os.path.splitext(os.path.basename(icon_file))
            try:
                if extension == ".png": self.icons.update({icon_name: QtGui.QIcon(os.path.join(icons_path, icon_file))})
            except:
                pass



    # 2: Create the specific GUI items using the items from the GUIItems class. Requires icons.
    def make_labels(self) -> dict:
        make_label = self.gui_items.make_label
        
        labels = {
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
        
        # Named groups
        
        return labels
    
    def make_buttons(self) -> dict:
        make_button = self.gui_items.make_button
        make_toggle_button = self.gui_items.make_toggle_button
        icons = self.icons
        labels = self.labels
        arrow = icons.get("single_arrow")
        sivr = "Set the image value range "

        buttons = {
            "previous_file": make_button("", "Previous file\n(←)", self.icons.get("single_arrow"), rotate_icon = 180),
            "select_file": make_button("", "Load scan and corresponding folder\n(L)", self.icons.get("folder_yellow")),
            "next_file": make_button("", "Next file\n(→)", self.icons.get("single_arrow")),

            "previous_channel": make_button("", "Previous channel\n(↑)", icon = arrow, rotate_icon = 270),
            "next_channel": make_button("","Next channel\n(↓)", icon = arrow, rotate_icon = 90),
            "direction": make_toggle_button("", "Change scan direction\n(X)", self.icons.get("triple_arrow"), flip_icon = True),

            "folder_name": make_button("Open folder", "Open the data folder\n(1)", self.icons.get("folder_blue")),

            "full_data_range": make_button("", sivr + "to the full data range\n(Shift + U)", self.icons.get("100")),
            "percentiles": make_button("", sivr + "by percentiles\n(Shift + R)", self.icons.get("percentiles")),
            "standard_deviation": make_button("", sivr + "by standard deviations\n(Shift + D)", self.icons.get("deviation")),
            "absolute_values": make_button("", sivr + "by absolute values\n(Shift + A)", self.icons.get("numbers")),

            "spec_info": make_button("", "Spectrum information", self.icons.get("question")),
            "spec_locations": make_toggle_button("", "View the spectroscopy locations\n(3)", self.icons.get("spec_locations"), flip_icon = True),
            "spectrum_viewer": make_button("", "Open Spectrum Viewer\n(O)", self.icons.get("graph")),

            "save_png": make_button("", "Save as png file\n(S)", self.icons.get("floppy")),
            "save_hdf5": make_button("", "Save as hdf5 file\n(5)", self.icons.get("h5")),
            "output_folder": make_button("Output folder", "Open output folder\n(T)", self.icons.get("folder_blue")),
            "exit": make_button("", "Exit scanalyzer\n(Esc / X / E)", self.icons.get("escape")),
            "info": make_button("", "Info", self.icons.get("i"))
        }
        
        # Named groups
        self.file_selection_buttons = [buttons[name] for name in ["previous_file", "select_file", "next_file"]]
        self.scale_buttons = [buttons[name] for name in ["full_data_range", "percentiles", "standard_deviation", "absolute_values"]]
        self.fcd_widgets = [labels["in_folder"], buttons["folder_name"], labels["number_of_files"], labels["channel_selected"]]

        return buttons

    def make_checkboxes(self) -> dict:
        make_checkbox = self.gui_items.make_checkbox
        
        checkboxes = {
            "sobel": make_checkbox("Sobel", "Compute the complex gradient d/dx + i d/dy\n(Shift + S)", self.icons.get("derivative")),
            "laplace": make_checkbox("Laplace", "Compute the Laplacian (d/dx)^2 + (d/dy)^2\n(Shift + L)", self.icons.get("laplacian")),
            "fft": make_checkbox("Fft", "Compute the 2D Fourier transform\n(Shift + F)", self.icons.get("fourier")),
            "normal": make_checkbox("Normal", "Compute the z component of the surface normal\n(Shift + N)", self.icons.get("surface_normal")),
            "gaussian": make_checkbox("Gauss", "Gaussian blur applied\n(Provide a width to toggle)", self.icons.get("gaussian")),
        }

        return checkboxes

    def make_comboboxes(self) -> dict:
        make_combobox = self.gui_items.make_combobox
        buttons = self.buttons
        
        comboboxes = {
            "channels": make_combobox("Channels", "Available scan channels\ntoggle with (↑ / ↓)"),
            "projection": make_combobox("Projection", "Select a projection\ntoggle with (Shift + ↑ / ↓)", items = ["re", "im", "abs", "arg (b/w)", "arg (hue)", "complex", "abs^2", "log(abs)"]),
            "spectra": make_combobox("spectra", "Spectra associated with the current scan")
        }
        
        # Named groups
        self.chan_nav_widgets = [buttons["previous_channel"], comboboxes["channels"], buttons["next_channel"], buttons["direction"]]
        
        return comboboxes

    def make_line_edits(self) -> dict:
        make_line_edit = self.gui_items.make_line_edit
        
        line_edits = {
            "min_full": make_line_edit("", "minimum value of scan data range"),
            "max_full": make_line_edit("", "maximum value of scan data range"),
            "min_percentiles": make_line_edit("2", "minimum percentile of data range"),
            "max_percentiles": make_line_edit("98", "maximum percentile of data range"),
            "min_deviations": make_line_edit("2", "minimum = mean - n * standard deviation"),
            "max_deviations": make_line_edit("2", "maximum = mean + n * standard deviation"),
            "min_absolute": make_line_edit("0", "minimum absolute value"),
            "max_absolute": make_line_edit("1", "maximum absolute value"),

            "gaussian_width": make_line_edit("0 nm", "Width in nm for Gaussian blur application", unit = "nm"),
            "file_name": make_line_edit("", "Base name of the file when saved to png or hdf5")
        }
        
        # Named groups
        
        return line_edits

    def make_radio_buttons(self) -> dict:
        make_radio_button = self.gui_items.make_radio_button
        QGroup = QtWidgets.QButtonGroup
        
        radio_buttons = {
            "bg_none": make_radio_button("", "None\n(Shift + 0)", self.icons.get("0")),
            "bg_plane": make_radio_button("", "Plane\n(Shift + P)", self.icons.get("plane_subtract")),
            "bg_linewise": make_radio_button("", "Linewise\n(Shift + L)", self.icons.get("lines")),
            "bg_inferred": make_radio_button("", "None\n(Shift + 0)", self.icons.get("0")),

            "min_full": make_radio_button("", "set to minimum value of scan data range\n(-) to toggle"),
            "max_full": make_radio_button("", "set to maximum value of scan data range\n(=) to toggle"),
            "min_percentiles": make_radio_button("", "set to minimum percentile of data range\n(-) to toggle"),
            "max_percentiles": make_radio_button("", "set to maximum percentile of data range\n(=) to toggle"),
            "min_deviations": make_radio_button("", "set to minimum = mean - n * standard deviation\n(-) to toggle"),
            "max_deviations": make_radio_button("", "set to maximum = mean + n * standard deviation\n(=) to toggle"),
            "min_absolute": make_radio_button("", "set minimum to an absolute value\n(-) to toggle"),
            "max_absolute": make_radio_button("", "set maximum to an absolute value\n(=) to toggle"),
        }
        
        # Named groups
        self.background_buttons = [radio_buttons[name] for name in ["bg_none", "bg_plane", "bg_linewise", "bg_inferred"]]
        self.min_radio_buttons = [radio_buttons[name] for name in ["min_full", "min_percentiles", "min_deviations", "min_absolute"]]
        self.max_radio_buttons = [radio_buttons[name] for name in ["max_full", "max_percentiles", "max_deviations", "max_absolute"]]
                
        # Add buttons to QButtonGroups for exclusive selection and check the defaults
        self.background_button_group = QGroup()
        [self.background_button_group.addButton(button) for button in self.background_buttons]
        
        self.min_button_group = QGroup()
        self.max_button_group = QGroup()
        [self.min_button_group.addButton(button) for button in self.min_radio_buttons]
        [self.max_button_group.addButton(button) for button in self.max_radio_buttons]
        
        # Initialize
        checked_buttons = [radio_buttons[name] for name in ["min_full", "max_full", "bg_none"]]
        [button.setChecked(True) for button in checked_buttons]
        
        return radio_buttons

    def make_lines(self) -> dict:
        make_line = self.gui_items.line_widget
        
        lines = {
            "scan_control": make_line("h"),
            "background": make_line("h"),
            "matrix_operations": make_line("h")
        }
        
        return lines

    def make_layouts(self) -> dict:
        make_layout = self.gui_items.make_layout
        
        layouts = {
            "main": make_layout("h"),
            "toolbar": make_layout("v"),
            "scan_summary": make_layout("v"),
            "file_chan_dir": make_layout("v"),
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
        
        return layouts

    def make_image_view(self) -> pg.ImageView:
        pg.setConfigOptions(imageAxisOrder = "row-major", antialias = True)
        
        self.im_view = pg.ImageView(view = pg.PlotItem())
        
        return self.im_view

    def make_widgets(self) -> dict:
        layouts = self.layouts
        QWgt = QtWidgets.QWidget
        
        widgets = {
            "central": QWgt(),
            "left_side": QWgt(),
            "coarse_actions": QWgt(),
            "arrows": QWgt()
        }
        
        self.coarse_control_widgets = [widgets[name] for name in ["coarse_actions", "arrows"]]     
        
        widgets["central"].setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        widgets["central"].setFocus()
        
        return widgets

    def make_consoles(self) -> dict:
        make_console = self.gui_items.make_console
        
        consoles = {
            "output": make_console("", "Output console"),
            "input": make_console("", "Input console")
        }
        
        consoles["output"].setReadOnly(True)
        consoles["input"].setReadOnly(False)
        consoles["input"].setMaximumHeight(30)
        [consoles[name].setStyleSheet("QTextEdit{ background-color: #101010; }") for name in ["output", "input"]]
        
        # Add the handles to the tooltips
        [consoles[name].changeToolTip(f"gui.consoles[\"{name}\"]", line = 10) for name in consoles.keys()]
        
        return consoles

    def make_shortcuts(self) -> dict:
        QKey = QtCore.Qt.Key
        QMod = QtCore.Qt.Modifier
        QSeq = QtGui.QKeySequence
        
        shortcuts = {
            "previous_file": QSeq(QKey.Key_Left),
            "select_file": QSeq(QKey.Key_L),
            "next_file": QSeq(QKey.Key_Right),
            
            "previous_channel": QSeq(QKey.Key_Up),
            "next_channel": QSeq(QKey.Key_Down),
            "direction": QSeq(QKey.Key_X),
            
            "folder_name": QSeq(QKey.Key_1),
            "full_data_range": QSeq(QMod.SHIFT | QKey.Key_U),
            
            "direction": QSeq(QKey.Key_X),
            "full_data_range": QSeq(QMod.SHIFT | QKey.Key_U),
            "percentiles": QSeq(QMod.SHIFT | QKey.Key_R),
            "standard_deviation": QSeq(QMod.SHIFT | QKey.Key_D),
            "absolute_values": QSeq(QMod.SHIFT | QKey.Key_A),
            
            "spec_locations": QSeq(QKey.Key_3),
            "spectrum_viewer": QSeq(QKey.Key_O),

            "save_png": QSeq(QKey.Key_S),
            "save_hdf5": QSeq(QKey.Key_5),
            "output_folder": QSeq(QKey.Key_T),
        }

        return shortcuts



    # 3: Populate layouts with GUI items. Requires GUI items.
    def populate_layouts(self) -> None:
        layouts = self.layouts
        
        # Add items to the layouts
        [layouts["scan_summary"].addWidget(self.labels[name]) for name in ["scan_summary", "statistics"]]
        
        [layouts["file_navigation"].addWidget(widget, 5 * (index % 2) + 1) for index, widget in enumerate(self.file_selection_buttons)]
        [layouts["channel_navigation"].addWidget(widget) for widget in self.chan_nav_widgets]
        layouts["channel_navigation"].setStretchFactor(self.comboboxes["channels"], 4)
                
        fcd_layout = layouts["file_chan_dir"]
        fcd_layout.addWidget(self.labels["load_file"])
        fcd_layout.addLayout(layouts["file_navigation"])
        [fcd_layout.addWidget(widget) for widget in self.fcd_widgets]
        fcd_layout.addLayout(layouts["channel_navigation"])
        
        
        """
        ca_layout = layouts["coarse_actions"]
        [ca_layout.addWidget(checkbox, i, 0) for i, checkbox in enumerate(self.action_checkboxes)]
        [ca_layout.addWidget(button, i + int(i / 2), 1) for i, button in enumerate(self.action_buttons)]
        [ca_layout.addWidget(line_edit, i + 1, 2) for i, line_edit in enumerate(self.action_line_edits)]
        [ca_layout.addWidget(label, i + 1, 3) for i, label in enumerate(self.steps_labels)]
        
        [layouts["arrows"].addWidget(button, int(i / 3), i % 3) for i, button in enumerate(self.arrow_buttons)]
        [layouts["scan_parameter_sets"].addWidget(button) for button in self.scan_parameter_sets]
        [layouts["parameters"].addWidget(box, 0, i) for i, box in enumerate(self.parameter_line_0)]
        layouts["parameters"].addLayout(layouts["scan_parameter_sets"], 1, 0, 1, 3)        
        [layouts["parameters"].addWidget(box, 1, i + 3) for i, box in enumerate(self.parameter_line_1)]
        
        [layouts["experiment_controls"].addWidget(widget) for widget in self.experiment_controls]
        e_layout = layouts["experiment"]
        [e_layout.addWidget(self.comboboxes[name], 0, i) for i, name in enumerate(["experiment", "direction"])]
        e_layout.addLayout(layouts["experiment_controls"], 1, 0, 2, 1)
        
        layouts["scan_control"].addWidget(self.comboboxes["channels"], 5)
        layouts["scan_control"].addWidget(self.buttons["direction"], 1)
        [layouts["background_buttons"].addWidget(button) for button in self.background_buttons]
        p_layout = layouts["matrix_processing"]
        [p_layout.addWidget(self.checkboxes[name], 0, i) for i, name in enumerate(["sobel", "normal", "laplace"])]
        [p_layout.addWidget(self.checkboxes[name], i + 1, 0) for i, name in enumerate(["gauss", "fft"])]
        [p_layout.addWidget(self.labels[name], i + 1, 1) for i, name in enumerate(["width", "show"])]
        p_layout.addWidget(self.line_edits["gaussian_width"], 1, 2)
        p_layout.addWidget(self.comboboxes["projection"], 2, 2)        
        
        l_layout = layouts["limits"]
        [l_layout.addWidget(item, i, 0) for i, item in enumerate(self.min_line_edits)]
        [l_layout.addWidget(item, i, 1) for i, item in enumerate(self.min_radio_buttons)]
        [l_layout.addWidget(item, i, 2) for i, item in enumerate(self.scale_buttons)]
        [l_layout.addWidget(item, i, 3) for i, item in enumerate(self.max_radio_buttons)]
        [l_layout.addWidget(item, i, 4) for i, item in enumerate(self.max_line_edits)]
        
        ip_layout = layouts["image_processing"]
        ip_layout.addWidget(self.labels["scan_control"])
        ip_layout.addLayout(layouts["scan_control"])
        ip_layout.addWidget(self.lines["scan_control"])
        ip_layout.addWidget(self.labels["background_subtraction"])
        ip_layout.addLayout(layouts["background_buttons"])
        ip_layout.addWidget(self.lines["background"])
        ip_layout.addWidget(self.labels["matrix_operations"])
        ip_layout.addLayout(layouts["matrix_processing"])
        ip_layout.addWidget(self.lines["matrix_operations"])
        ip_layout.addWidget(self.labels["limits"])            
        ip_layout.addLayout(layouts["limits"])
        
        layouts["coarse_control"].addLayout(ca_layout)
        layouts["coarse_control"].addLayout(layouts["arrows"])
        
        #layouts["input"].addWidget(self.buttons["input"], 1)
        layouts["input"].addWidget(self.consoles["input"])
        """
        
        return



    # 4: Make widgets and groupboxes and set their layouts. Requires layouts.
    def make_groupboxes(self) -> dict:
        make_groupbox = self.gui_items.make_groupbox
        layouts = self.layouts
        
        groupboxes = {
            "scan_summary": make_groupbox("Scan summary", "Information about the currently selected scan"),
            "file_chan_dir": make_groupbox("File / Channel / Direction", "Select and toggle through scan files and channels"),
            "image_processing": make_groupbox("Image processing", "Select the background subtraction, matrix operations and set the image range limits"),
            "spectra": make_groupbox("Spectra", "Associated spectra (those recorded after the acquisition of the selected scan) are shown with an asterisk"),
            "i/o": make_groupbox("Output", "Save or find the processed image, or exit the app")
        }

        # Set layouts for the groupboxes
        #[groupboxes[name].setLayout(layouts[name]) for name in ["connections", "coarse_control", "parameters", "experiment", "image_processing"]]
        
        # Draw experiments group: to be absorbed in gui_scantelligent.py        
        #[self.layouts["toolbar"].addWidget(groupboxes[name]) for name in ["connections", "coarse_control", "parameters", "experiment", "image_processing"]]
        
        return groupboxes



    # 5: Set up the main window layout
    def setup_main_window(self) -> None:
        layouts = self.layouts
        widgets = self.widgets

        # Aesthetics
        
        """
        layouts["left_side"].setContentsMargins(0, 0, 0, 0)
        layouts["toolbar"].setContentsMargins(4, 4, 4, 4)
        layouts["toolbar"].addStretch(1)
        
        # Compose the image_view plus consoles layout
        layouts["left_side"].addWidget(self.image_view, stretch = 4)
        layouts["left_side"].addWidget(self.consoles["output"], stretch = 1)
        layouts["left_side"].addWidget(self.line_edits["input"])
        self.widgets["left_side"].setLayout(layouts["left_side"])
        
        # Attach the toolbar        
        layouts["main"].addWidget(self.widgets["left_side"], stretch = 4)
        layouts["main"].addLayout(layouts["toolbar"], 1)
        
        # Set the central widget of the QMainWindow
        widgets["central"].setLayout(layouts["main"])
        widgets["central"].setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        widgets["central"].setFocus()
        
        # Finish the setup
        self.setCentralWidget(widgets["central"])
        self.setWindowTitle("Scantelligent by Peter H. Jacobse")
        self.setGeometry(100, 50, 1400, 800) # x, y, width, height
        self.setWindowIcon(self.icons.get("scanalyzer"))
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setFocus()
        self.activateWindow()
        """
        
        return

