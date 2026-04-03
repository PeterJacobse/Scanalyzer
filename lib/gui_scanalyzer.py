import os
from PyQt6 import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
from . import STWidgets, rotate_icon, make_layout, make_line



class ScanalyzerGUI(QtWidgets.QMainWindow):
    dataDropped = QtCore.pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        # 1: Read icons from file.
        self.icons = self.get_icons()
        
        # 2: Create the specific GUI items using the items from the GUIItems class. Requires icons.
        self.labels = self.make_labels()
        self.buttons = self.make_buttons()
        self.comboboxes = self.make_comboboxes()
        self.line_edits = self.make_line_edits()
        self.radio_buttons = self.make_radio_buttons()
        self.layouts = self.make_layouts()
        (self.image_view, self.plot_item) = self.make_image_view()
        self.widgets = self.make_widgets()
        self.consoles = self.make_consoles()
        self.shortcuts = self.make_shortcuts()
        (self.info_box, self.message_box) = self.make_boxes()
        self.splash_screen = self.make_splash_screen()
        self.dialog = self.make_file_dialog()
        self.make_target_item = STWidgets.TargetItem
                
        # 3: Populate layouts with GUI items. Requires GUI items.
        self.populate_layouts()
        
        # 4: Make groupboxes and set their layouts. Requires populated layouts.
        self.groupboxes = self.make_groupboxes()
        
        # 5: Set up the main window layout
        self.setup_main_window()
        
        # 3: Define interconnected behavior
        self.interconnect()



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
            self.dataDropped.emit(file_name)



    # 1: Read icons from file.
    def get_icons(self) -> dict:
        lib_folder = os.path.dirname(os.path.abspath(__file__))
        project_folder = os.path.dirname(lib_folder)
        sys_folder = os.path.join(project_folder, "sys")
        splash_screen_path = os.path.join(sys_folder, "splash_screen.png")
        icon_folder = os.path.join(project_folder, "icons")
        icon_files = os.listdir(icon_folder)
        
        self.paths = {
            "scanalyzer_folder": project_folder,
            "lib_folder": lib_folder,
            "sys_folder": sys_folder,
            "icon_folder": icon_folder,
            "splash_screen": splash_screen_path
        }
        
        icons = {}
        for icon_file in icon_files:
            [icon_name, extension] = os.path.splitext(os.path.basename(icon_file))
            try:
                if extension == ".png": icons.update({icon_name: QtGui.QIcon(os.path.join(icon_folder, icon_file))})
            except:
                pass
        
        return icons



    # 2: Create the specific GUI items using the items from the GUIItems class. Requires icons.
    def make_labels(self) -> dict:
        STL = STWidgets.Label

        labels = {
            "scan_summary": STL(text = "Scanalyzer by Peter H. Jacobse"),
            "statistics": STL(text = "Statistics"),
            "load_file": STL(text = "Load file:"),
            "in_folder": STL(text = "in folder:"),
            "number_of_files": STL(text = "which contains 1 sxm file"),
            "channel_selected": STL(text = "Channel selected:"),

            "background_subtraction": STL(text = "Background / frame subtraction"),
            "width": STL(text = "Width (nm):"),
            "show": STL(text = "Show", tooltip = "Select a projection or toggle with (H)"),
            "limits": STL(text = "Set limits", tooltip = "Toggle the min and max limits with (-) and (=), respectively"),
            "matrix_operations": STL(text = "Matrix operations"),

            "in_output_folder": STL(text = "In output folder")
        }
        
        return labels

    def make_buttons(self) -> dict:
        MSB = STWidgets.MultiStateButton
        icons = self.icons
        labels = self.labels
        arrow = icons.get("single_arrow")
        sivr = "Set the image value range "

        buttons = {
            "previous_file": MSB(tooltip = "Previous file\n(←)", icon = rotate_icon(self.icons.get("single_arrow"), 180)),
            "select_file": MSB(tooltip = "Load scan and corresponding folder\n(Ctrl + L)", icon = self.icons.get("folder_yellow")),
            "next_file": MSB(tooltip = "Next file\n(→)", icon = self.icons.get("single_arrow")),

            "previous_channel": MSB(tooltip = "Previous channel\n(↑)", icon = rotate_icon(arrow, 270)),
            "next_channel": MSB(tooltip = "Next channel\n(↓)", icon = rotate_icon(arrow, 90)),
            "direction": MSB(states = [{"tooltip": "Scan direction: forward\n(X)", "icon": self.icons.get("triple_arrow"), "color": "#101010"},
                                      {"tooltip": "Scan direction: backward\n(X)", "icon": rotate_icon(self.icons.get("triple_arrow"), 180), "color": "#2020C0"}]),

            "folder_name": MSB(name = "Open folder", tooltip = "Open the data folder\n(1)", icon = self.icons.get("view_folder")),

            "full_data_range": MSB(tooltip = sivr + "to the full data range\n(Shift + U)", icon = self.icons.get("100")),
            "percentiles": MSB(tooltip = sivr + "by percentiles\n(Shift + P)", icon = self.icons.get("percentiles")),
            "standard_deviation": MSB(tooltip = sivr + "by standard deviations\n(Shift + D)", icon = self.icons.get("deviation")),
            "absolute_values": MSB(tooltip = sivr + "by absolute values\n(Shift + A)", icon = self.icons.get("numbers")),
            
            "bg_none": MSB(states = [{"tooltip": "None\n(0)", "icon": self.icons.get("0_2"), "color": "#101010"},
                                    {"color": "#2020C0"}]),
            "bg_plane": MSB(states = [{"tooltip": "Plane\n(0)", "icon": self.icons.get("plane_subtract"), "color": "#101010"},
                                    {"color": "#2020C0"}]),
            "bg_linewise": MSB(states = [{"tooltip": "Linewise\n(0)", "icon": self.icons.get("lines"), "color": "#101010"},
                                    {"color": "#2020C0"}]),
            "bg_inferred": MSB(states = [{"tooltip": "None\n(0)", "icon": self.icons.get("0_2"), "color": "#101010"},
                                    {"color": "#2020C0"}]),
            
            "sobel": MSB(text = "Sobel", tooltip = "Compute the complex gradient d/dx + i d/dy\n(Shift + S)", icon = self.icons.get("sobel"),
                         states = [{"color": "#101010"}, {"color": "#2020C0"}]),
            "laplace": MSB(text = "Laplace", tooltip = "Compute the Laplacian (d/dx)^2 + (d/dy)^2\n(Shift + L)", icon = self.icons.get("laplacian"),
                           states = [{"color": "#101010"}, {"color": "#2020C0"}]),
            "fft": MSB(text = "Fft", tooltip = "Compute the 2D Fourier transform\n(Shift + F)", icon = self.icons.get("fourier"),
                       states = [{"color": "#101010"}, {"color": "#2020C0"}]),
            "normal": MSB(text = "Normal", tooltip = "Compute the z component of the surface normal\n(Shift + N)", icon = self.icons.get("surface_normal"),
                          states = [{"color": "#101010"}, {"color": "#2020C0"}]),
            "gaussian": MSB(text = "Gauss", tooltip = "Gaussian blur applied\n(Shift + G) or provide a width to toggle", icon = self.icons.get("gaussian"),
                            states = [{"color": "#101010"}, {"color": "#2020C0"}]),
            "rot_trans": MSB(tooltip = "Show the scan in the scan window coordinates\nwith rotation and translation\n(R)", icon = self.icons.get("rot_trans"),
                             states = [{"color": "#101010"}, {"color": "#2020C0"}]),
            
            "spec_info": MSB(tooltip = "Spectrum information", icon = self.icons.get("question")),
            "spec_locations": MSB(states = [{"tooltip": "Spectroscopy locations: not visible\n(Space)", "icon": self.icons.get("spec_locations"), "color": "#101010"},
                                           {"tooltip": "Spectroscopy locations: visible\n(Space)", "color": "#2020C0"}]),
            "spectralyzer": MSB(tooltip = "Open Spectralyzer\n(S)", icon = self.icons.get("graph")),

            "save_png": MSB(states = [{"tooltip": "Save as png file\n(Ctrl + S)", "icon": self.icons.get("save_png"), "color": "#101010"},
                                     {"tooltip": "File already exists\n(Ctrl + S)", "color": "#2020C0"}]),
            "save_svg": MSB(states = [{"tooltip": "Save image and markers to svg", "icon": self.icons.get("svg"), "color": "#101010"},
                                     {"tooltip": "File already exists", "color": "#2020C0"}]),
            "reset": MSB(tooltip = "Reset file name", icon = self.icons.get("reset")),
            "use_dialog": MSB(states = [{"tooltip": "Save directly", "icon": self.icons.get("dialog"), "color": "#101010"},
                                       {"tooltip": "Use save dialog if file exists", "color": "#20A020"},
                                       {"tooltip": "Save using dialog", "color": "#2020C0"}]),
            "save_hdf5": MSB(tooltip = "Save as hdf5 file\n(Ctrl + 5)", icon = self.icons.get("h5")),
            
            "output_folder": MSB(name = "Extracted Files", tooltip = "Open output folder\n(O)", icon = self.icons.get("view_folder")),
            "exit": MSB(tooltip = "Exit scanalyzer\n(Esc / X / E)", icon = self.icons.get("escape")),
            "info": MSB(tooltip = "Info", icon = self.icons.get("i"))
        }
        
        # Named groups
        self.file_selection_buttons = [buttons[name] for name in ["previous_file", "select_file", "next_file"]]
        self.limits_names = ["full_data_range", "percentiles", "standard_deviation", "absolute_values"]
        self.scale_buttons = [buttons[name] for name in self.limits_names]
        self.fcd_widgets = [labels["in_folder"], buttons["folder_name"], labels["number_of_files"], labels["channel_selected"]]
        self.background_buttons = [buttons[name] for name in ["bg_none", "bg_plane", "bg_linewise"]]

        # Initialize
        buttons["bg_none"].setState(1)

        return buttons

    def make_comboboxes(self) -> dict:
        CB = STWidgets.ComboBox
        buttons = self.buttons

        comboboxes = {
            "channels": CB(name = "Channels", tooltip = "Available scan channels\n(↑ / ↓)"),
            "projection": CB(name = "Projection", tooltip = "Select a projection\n(Shift + ↑ / ↓)",
                                     items = ["re", "im", "abs", "arg (b/w)", "arg (hue)", "complex", "abs^2", "log(abs)"]),
            "spectra": CB(name = "spectra", tooltip = "Spectra\n(\">>\" indicates spectra associated with current scan)")
        }
        
        # Named groups
        self.chan_nav_widgets = [buttons["previous_channel"], comboboxes["channels"], buttons["next_channel"], buttons["direction"]]
        self.spectra_widgets = [buttons["spec_info"], comboboxes["spectra"], buttons["spec_locations"], buttons["spectralyzer"]]
        
        return comboboxes

    def make_line_edits(self) -> dict:
        LE = STWidgets.PhysicsLineEdit
        
        line_edits = {
            "min_full": LE(tooltip = "minimum value of scan data range", digits = 3),
            "max_full": LE(tooltip = "maximum value of scan data range", digits = 3),
            "min_percentiles": LE(value = 1.0, tooltip = "minimum percentile of data range", unit = "%", digits = 1),
            "max_percentiles": LE(value = 99.0, tooltip = "maximum percentile of data range", unit = "%", digits = 1),
            "min_deviations": LE(value = 2.0, tooltip = "minimum = mean - n * standard deviation", unit = "\u03C3", digits = 1),
            "max_deviations": LE(value = 2.0, tooltip = "maximum = mean + n * standard deviation", unit = "\u03C3", digits = 1),
            "min_absolute": LE(value = 0, tooltip = "minimum absolute value", digits = 3),
            "max_absolute": LE(value = 1, tooltip = "maximum absolute value", digits = 3),

            "gaussian_width": LE(value = 0.000, tooltip = "Width for Gaussian blur application", unit = "nm", digits = 3),
            "file_name": QtWidgets.QLineEdit("Base name of the file when saved to png or hdf5")
        }
        line_edits["file_name"].setStyleSheet("QLineEdit{ background-color: #101010 }")
        
        [line_edits[name].setEnabled(False) for name in ["min_full", "max_full"]]
        
        # Named groups
        self.min_names = ["min_full", "min_percentiles", "min_deviations", "min_absolute"]
        self.max_names = ["max_full", "max_percentiles", "max_deviations", "max_absolute"]
        self.min_line_edits = [line_edits[name] for name in self.min_names]
        self.max_line_edits = [line_edits[name] for name in self.max_names]
        
        self.io_widgets = [self.buttons[name] for name in ["output_folder", "info", "exit"]]
        
        return line_edits

    def make_radio_buttons(self) -> dict:
        RBN = STWidgets.RadioButton
        QGroup = QtWidgets.QButtonGroup
        
        radio_buttons = {
            "min_full": RBN(tooltip = "set to minimum value of scan data range\n(-) to toggle"),
            "max_full": RBN(tooltip = "set to maximum value of scan data range\n(=) to toggle"),
            "min_percentiles": RBN(tooltip = "set to minimum percentile of data range\n(-) to toggle"),
            "max_percentiles": RBN(tooltip = "set to maximum percentile of data range\n(=) to toggle"),
            "min_deviations": RBN(tooltip = "set to minimum = mean - n * standard deviation\n(-) to toggle"),
            "max_deviations": RBN(tooltip = "set to maximum = mean + n * standard deviation\n(=) to toggle"),
            "min_absolute": RBN(tooltip = "set minimum to an absolute value\n(-) to toggle"),
            "max_absolute": RBN(tooltip = "set maximum to an absolute value\n(=) to toggle"),
        }
        
        # Named groups
        self.min_radio_buttons = [radio_buttons[name] for name in self.min_names]
        self.max_radio_buttons = [radio_buttons[name] for name in self.max_names]
                
        # Add buttons to QButtonGroups for exclusive selection and check the defaults        
        self.min_button_group = QGroup()
        self.max_button_group = QGroup()
        [self.min_button_group.addButton(button) for button in self.min_radio_buttons]
        [self.max_button_group.addButton(button) for button in self.max_radio_buttons]
        
        # Initialize
        checked_buttons = [radio_buttons[name] for name in ["min_full", "max_full"]]
        [button.setChecked(True) for button in checked_buttons]

        return radio_buttons

    def make_layouts(self) -> dict:        
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
            "i/o_widgets": make_layout("h"),
            "empty": make_layout("v")
        }
        
        return layouts

    def make_image_view(self) -> tuple[pg.ImageView, pg.PlotItem]:
        pg.setConfigOptions(imageAxisOrder = "row-major", antialias = True)
        
        plot_item = pg.PlotItem()        
        im_view = pg.ImageView(view = plot_item)
        im_view.view.invertY(False)
        
        return (im_view, plot_item)

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

        layouts.update({"main": QtWidgets.QHBoxLayout(widgets["central"])})
        
        self.phase_slider = STWidgets.PhaseSlider(tooltip = "Set complex phase phi\n(= multiplication by exp(i * pi * phi rad / (180 deg)))", unit = "deg", phase_0_icon = self.icons.get("0"), phase_180_icon = self.icons.get("180"))
        
        return widgets

    def make_consoles(self) -> dict:
        STC = STWidgets.Console

        consoles = {
            "output": STC("", "Output console"),
            "input": STC("", "Input console")
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
            "select_file": QSeq(QMod.CTRL | QKey.Key_L),
            "next_file": QSeq(QKey.Key_Right),
            
            "previous_channel": QSeq(QKey.Key_Up),
            "next_channel": QSeq(QKey.Key_Down),
            
            "folder_name": QSeq(QKey.Key_1),
            
            "bg_none": QSeq(QKey.Key_0),
            "bg_plane": QSeq(QKey.Key_P),
            "bg_linewise": QSeq(QKey.Key_L),
            
            "sobel": QSeq(QMod.SHIFT | QKey.Key_S),
            "normal": QSeq(QMod.SHIFT | QKey.Key_N),
            "gaussian": QSeq(QMod.SHIFT | QKey.Key_G),
            "fft": QSeq(QMod.SHIFT | QKey.Key_F),
            "laplace": QSeq(QMod.SHIFT | QKey.Key_L),
            "rot_trans": QSeq(QKey.Key_R),

            "full_data_range": QSeq(QMod.SHIFT | QKey.Key_U),
            "percentiles": QSeq(QMod.SHIFT | QKey.Key_P),
            "standard_deviation": QSeq(QMod.SHIFT | QKey.Key_D),
            "absolute_values": QSeq(QMod.SHIFT | QKey.Key_A),
            
            "spec_locations": QSeq(QKey.Key_Space),
            "spectralyzer": QSeq(QKey.Key_S),

            "save_png": QSeq(QMod.CTRL | QKey.Key_S),
            "save_hdf5": QSeq(QMod.CTRL | QKey.Key_5),
            "output_folder": QSeq(QKey.Key_O),
        }

        return shortcuts

    def make_boxes(self) -> tuple[QtWidgets.QMessageBox, QtWidgets.QMessageBox]:
        info_box = QtWidgets.QMessageBox(self)
        info_box.setWindowTitle("Info")
        info_box.setText("Scanalyzer (2026)\nby Peter H. Jacobse\nRice University; Lawrence Berkeley National Lab")
        info_box.setStandardButtons(QtWidgets.QMessageBox.StandardButton.Ok)
        info_box.setWindowIcon(self.icons.get("i"))
        
        message_box = QtWidgets.QMessageBox(self)
        message_box.setWindowTitle("Success")
        message_box.setText("png file saved")
        return (info_box, message_box)

    def make_splash_screen(self) -> QtWidgets.QSplashScreen:
        pixmap = QtGui.QPixmap()
        pixmap.load(self.paths["splash_screen"])
        splash_screen = QtWidgets.QSplashScreen(pixmap, QtCore.Qt.WindowType.WindowStaysOnTopHint)
        return splash_screen

    def make_file_dialog(self) -> QtWidgets.QFileDialog:
        dialog = QtWidgets.QFileDialog()        
        return dialog



    # 3: Populate layouts with GUI items. Requires GUI items.
    def populate_layouts(self) -> None:
        layouts = self.layouts
        buttons = self.buttons
        comboboxes = self.comboboxes
        line_edits = self.line_edits
        labels = self.labels
        
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
        
        [layouts["background_buttons"].addWidget(button) for button in self.background_buttons]
        layouts["background_buttons"].addWidget(buttons["rot_trans"])
        p_layout = layouts["matrix_processing"]
        [p_layout.addWidget(buttons[name], 0, index) for index, name in enumerate(["sobel", "normal", "laplace"])]
        p_layout.addWidget(buttons["gaussian"], 1, 1)
        p_layout.addWidget(line_edits["gaussian_width"], 1, 2)
        p_layout.addWidget(buttons["fft"], 1, 0)
        p_layout.addWidget(comboboxes["projection"], 2, 0)
        p_layout.addWidget(self.phase_slider, 2, 1, 1, 2)
        
        l_layout = layouts["limits"]
        self.limits_columns = [self.min_line_edits, self.min_radio_buttons, self.scale_buttons, self.max_radio_buttons, self.max_line_edits]
        for j, group in enumerate(self.limits_columns): [l_layout.addWidget(item, i, j) for i, item in enumerate(group)]

        ip_layout = layouts["image_processing"]
        ip_layout.addWidget(labels["background_subtraction"])
        ip_layout.addLayout(layouts["background_buttons"])
        ip_layout.addWidget(make_line("h", 1))
        ip_layout.addWidget(labels["matrix_operations"])
        ip_layout.addLayout(p_layout)
        ip_layout.addWidget(make_line("h", 1))
        ip_layout.addWidget(labels["limits"])         
        ip_layout.addLayout(l_layout)
        
        [layouts["spectra"].addWidget(widget) for widget in self.spectra_widgets]
        layouts["spectra"].setStretchFactor(comboboxes["spectra"], 4)
        
        io_layout = layouts["i/o"]
        io_layout.addWidget(buttons["reset"], 0, 0)
        io_layout.addWidget(line_edits["file_name"], 0, 1)
        [io_layout.addWidget(buttons[name], 0, i + 2) for i, name in enumerate(["save_png", "save_svg", "use_dialog"])]
        [layouts["i/o_widgets"].addWidget(widget) for widget in self.io_widgets]
        io_layout.addLayout(layouts["i/o_widgets"], 1, 0, 1, 5)
                
        return



    # 4: Make widgets and groupboxes and set their layouts. Requires layouts.
    def make_groupboxes(self) -> dict:
        SGB = STWidgets.GroupBox
        layouts = self.layouts
        
        groupboxes = {
            "scan_summary": SGB("Scan summary", tooltip = "Information about the currently selected scan"),
            "file_chan_dir": SGB("File / Channel / Direction", tooltip = "Select and toggle through scan files and channels"),
            "image_processing": SGB("Image processing", tooltip = "Select the background subtraction, matrix operations and set the image range limits"),
            "spectra": SGB("Spectra", tooltip = "Associated spectra (those recorded after the acquisition of the selected scan) are shown with an asterisk"),
            "i/o": SGB("Output", tooltip = "Save or find the processed image, or exit the app")
        }

        # Set layouts for the groupboxes
        group_names = ["scan_summary", "file_chan_dir", "image_processing", "spectra", "i/o"]
        [groupboxes[name].setLayout(layouts[name]) for name in group_names]
        
        [self.layouts["toolbar"].addWidget(groupboxes[name]) for name in group_names]        
        
        return groupboxes



    # 5: Set up the main window layout
    def setup_main_window(self) -> None:
        layouts = self.layouts
        widgets = self.widgets

        # Aesthetics
        layouts["toolbar"].setContentsMargins(4, 4, 4, 4)
        layouts["toolbar"].addStretch(1)
        
        # Set the layout as the image_view plus toolbar
        layouts["main"].addWidget(self.image_view, 3)
        layouts["main"].addLayout(layouts["toolbar"], 1)
        
        # Set the central widget of the QMainWindow
        widgets["central"].setLayout(layouts["main"])
        widgets["central"].setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        widgets["central"].setFocus()
        
        # Finish the setup
        self.setCentralWidget(widgets["central"])
        self.setWindowTitle("Scanalyzer")
        self.setGeometry(100, 50, 1400, 800) # x, y, width, height
        self.setWindowIcon(self.icons.get("scanalyzer"))
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setFocus()
        #self.activateWindow()
        
        return



    # 6: Interconnected behavior
    def interconnect(self) -> None:
        self.buttons["bg_none"].clicked.connect(lambda: self.background_mutex("none"))
        self.buttons["bg_plane"].clicked.connect(lambda: self.background_mutex("plane"))
        self.buttons["bg_linewise"].clicked.connect(lambda: self.background_mutex("linewise"))
        return
        
    def background_mutex(self, method: str = "none") -> None:
        [none, plane, linewise] = [self.buttons[name] for name in ["bg_none", "bg_plane", "bg_linewise"]]
        match method:
            case "none":
                [button.setState(0) for button in [plane, linewise]]
                none.setState(1)
            case "plane":
                [button.setState(0) for button in [none, linewise]]
                plane.setState(1)
            case _:
                [button.setState(0) for button in [none, plane]]
                linewise.setState(1)
        return
