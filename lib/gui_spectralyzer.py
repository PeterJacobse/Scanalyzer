import os
from PyQt6 import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
from . import GUIItems



class SpectralyzerGUI(QtWidgets.QMainWindow):
    dataDropped = QtCore.pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        # 1: Read icons from file.
        self.icons = self.get_icons()
        
        # 2: Create the specific GUI items using the items from the GUIItems class. Requires icons.
        self.gui_items = GUIItems()
        self.labels = self.make_labels()
        (self.buttons, self.leftarrows, self.rightarrows) = self.make_buttons()
        (self.checkboxes, self.all_checkbox) = self.make_checkboxes()
        (self.channel_selection_comboboxes, self.plot_number_comboboxes, self.focus_row_combobox) = self.make_comboboxes()
        self.line_edits = self.make_line_edits()
        self.layouts = self.make_layouts()
        self.image_widget = self.make_image_widget()
        (self.plot_widgets, self.plot_items) = self.make_plot_widgets()
        self.widgets = self.make_widgets()
                
        # 3: Populate layouts with GUI items. Requires GUI items.
        self.populate_layouts()
        
        # 4: Set up the main window layout
        self.setup_main_window()

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
    def get_icons(self):
        lib_folder = os.path.dirname(os.path.abspath(__file__))
        project_folder = os.path.dirname(lib_folder)
        icon_folder = os.path.join(project_folder, "icons")
        icon_files = os.listdir(icon_folder)
        
        icons = {}
        for icon_file in icon_files:
            [icon_name, extension] = os.path.splitext(os.path.basename(icon_file))
            try:
                if extension == ".png": icons.update({icon_name: QtGui.QIcon(os.path.join(icon_folder, icon_file))})
            except:
                pass

        self.color_list = ["#FFFFFF", "#FFFF00", "#FF90FF", "#00FFFF", "#00FF00", "#A0A0A0", "#FF4040", "#5050FF", "#FFA500", "#9050FF", "#808000", "#008080", "#900090", "#009000", "#B00000", "#0000C0"]
        return icons



    # 2: Create the specific GUI items using the items from the GUIItems class. Requires icons.
    def make_labels(self) -> dict:
        make_label = self.gui_items.make_label
        
        labels = {
            "save_0": make_label("save (plot 0)", "Save plot 0 to svg (S)"),
            "save_1": make_label("save (plot 1)", "Save plot 1 to svg (Z)"),
            "x_axis": make_label("x axis", "Toggle with (X)"),
            "y_axis_0": make_label("y axis (plot 0)", "Toggle with (Y)"),
            "y_axis_1": make_label("y axis (plot 1)", "Toggle with (Z)"),
            "offset_0": make_label("Offset", "Offset between successive spectra"),
            "offset_1": make_label("Offset", "Offset between successive spectra"),
            "line_width": make_label("Line width", "Line width"),
            "opacity": make_label("Opacity", "Opacity"),
            "empty_0": make_label(""),
            "empty_1": make_label("")
        }
        
        labels["x_axis"].setWindowIcon(self.icons.get("x_axis"))
        
        return labels
    
    def make_buttons(self) -> dict:
        make_button = self.gui_items.make_button

        buttons = {
            "x_axis": make_button("", "Toggle the x axis\n(X)", self.icons.get("x_axis")),
            "y_axis_0": make_button("", "Toggle the y axis of plot 0\n(Y)", self.icons.get("y_axis")),
            "y_axis_1": make_button("", "Toggle the y axis of plot 1\n(Y)", self.icons.get("y_axis")),
            "offset_0": make_button("", "Set the offset between successive spectra in plot 0", self.icons.get("line_offset")),
            "offset_1": make_button("", "Set the offset between successive spectra in plot 1", self.icons.get("line_offset")),
            "save_0": make_button("", "Save graph 0 to svg", self.icons.get("save_0")),
            "save_1": make_button("", "Save graph 1 to svg", self.icons.get("save_1")),
            "line_width": make_button("", "Set the line width\n(L)", self.icons.get("line_width")),
            "opacity": make_button("", "Set the line opacity\n(O)", self.icons.get("opacity")),
            "open_folder": make_button("", "Open folder", self.icons.get("folder_yellow")),
            "view_folder": make_button("", "Open folder", self.icons.get("view_folder")),
            "exit": make_button("", "Exit Spectrum Viewer\n(Q / Esc)", self.icons.get("escape")),
            "dec_focus_row": make_button("", "Decrease the focus row index\n(↑)", self.icons.get("dec_focus_row")),
            "inc_focus_row": make_button("", "Increase the focus row index\n(↓)", self.icons.get("inc_focus_row")),
        }
        
        # Named groups
        leftarrows = {}
        rightarrows = {}
        for number in range(16):
            leftarrows.update({f"{number}": make_button("", f"decrease plot number {number} (left arrow when row is highlighted)", self.icons.get("single_arrow"), rotate_icon = 180)})
            rightarrows.update({f"{number}": make_button("", f"increase plot number {number} (right arrow when row is highlighted)", self.icons.get("single_arrow"))})

        return (buttons, leftarrows, rightarrows)

    def make_checkboxes(self) -> dict:
        make_checkbox = self.gui_items.make_checkbox
        
        checkboxes = {}
        for number in range(16):
            checkboxes.update({f"{number}": make_checkbox(f"{number}", f"toggle visibility of plot {number} (space when row is in focus)")})
            checkboxes[f"{number}"].setStyleSheet(f"color: {self.color_list[number]};")
        
        all_checkbox = make_checkbox("all", f"toggle visibility of all plots")
        
        return (checkboxes, all_checkbox)
    
    def make_comboboxes(self) -> dict:
        make_combobox = self.gui_items.make_combobox
        
        channel_selection_comboboxes = {
            "x_axis": make_combobox("x_axis", "Channel to display on the x axis (X)"),
            "y_axis_0": make_combobox("y_axis_0", "Channel to display on the y axis (Y)"),
            "y_axis_1": make_combobox("y_axis_1", "Channel to display on the y axis (Z)"),
        }
        
        focus_row_combobox = make_combobox("Focus row", "Set the focus row\n(↑ / ↓)")
                        
        plot_number_comboboxes = {}
        for number in range(16):
            plot_number_comboboxes.update({f"{number}": make_combobox(f"{number}", f"data for plot {number}")})
        
        row_items = [f"Row {i} ({hex(i)[2]})" for i in range(len(plot_number_comboboxes))]
        focus_row_combobox.renewItems(row_items)
        
        # Named groups
        self.focus_row_buttons = [self.all_checkbox, self.buttons["dec_focus_row"], focus_row_combobox, self.buttons["inc_focus_row"]]
        
        return (channel_selection_comboboxes, plot_number_comboboxes, focus_row_combobox)

    def make_line_edits(self) -> dict:
        make_line_edit = self.gui_items.make_line_edit
        
        line_edits = {
            "offset_0": make_line_edit("0", "Offset between successive spectra"),
            "offset_1": make_line_edit("0", "Offset between successive spectra"),
            "line_width": make_line_edit("2", "Line width"),
            "opacity": make_line_edit("1", "Opacity")
        }
        
        # Named groups
        labels = self.labels
        buttons = self.buttons

        self.option_widgets_col0 = [buttons["y_axis_0"], buttons["offset_0"], labels["empty_0"], buttons["y_axis_1"], buttons["offset_1"], labels["empty_1"], buttons["line_width"], buttons["opacity"]]
        self.option_widgets_col1 = [self.channel_selection_comboboxes["y_axis_0"], line_edits["offset_0"], self.buttons["save_0"], self.channel_selection_comboboxes["y_axis_1"],
                                    line_edits["offset_1"], self.buttons["save_1"], line_edits["line_width"], line_edits["opacity"]]

        return line_edits

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
            "main": make_layout("g"),
            "selector": make_layout("g"),
            "x_axis": make_layout("h"),
            "plots": make_layout("v"),
            "options": make_layout("g"),
            "i/o": make_layout("h")
        }
        
        return layouts

    def make_image_widget(self) -> pg.ImageView:
        #pg.setConfigOptions(imageAxisOrder = "row-major", antialias = True)
        
        image_widget = pg.GraphicsLayoutWidget()
        
        return image_widget

    def make_plot_widgets(self) -> dict:
        plot_widgets = {
            "graph_0": pg.PlotWidget(),
            "graph_1": pg.PlotWidget()
        }
        
        plot_items = {
            "graph_0": plot_widgets["graph_0"].getPlotItem(),
            "graph_1": plot_widgets["graph_1"].getPlotItem()
        }
        
        return (plot_widgets, plot_items)

    def make_widgets(self) -> dict:
        layouts = self.layouts
        QWgt = QtWidgets.QWidget
        
        widgets = {
            "central": QWgt(),
            "selector": QWgt(),
            "plot": QWgt(),
            "options": QWgt(),
            "left_side": QWgt(),
            "x": QWgt()
        }
        
        self.setCentralWidget(widgets["central"])
        
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
            "dec_focus_row": QSeq(QKey.Key_Up),
            "inc_focus_row": QSeq(QKey.Key_Down),
            
            "folder_name": QSeq(QKey.Key_1),

            "full_data_range": QSeq(QMod.SHIFT | QKey.Key_U),
            "percentiles": QSeq(QMod.SHIFT | QKey.Key_5),
            "standard_deviation": QSeq(QMod.SHIFT | QKey.Key_D),
            "absolute_values": QSeq(QMod.SHIFT | QKey.Key_A),
            
            "spec_locations": QSeq(QKey.Key_Space),
            "spectrum_viewer": QSeq(QMod.CTRL | QKey.Key_S),

            "save_png": QSeq(QKey.Key_S),
            "save_hdf5": QSeq(QKey.Key_5),
            "output_folder": QSeq(QKey.Key_T),
        }

        return shortcuts



    # 3: Populate layouts with GUI items. Requires GUI items.
    def populate_layouts(self) -> None:
        layouts = self.layouts
        widgets = self.widgets
        buttons = self.buttons
        
        # Add items to the layouts
        ss_layout = self.layouts["selector"]
        [ss_layout.addWidget(widget, 0, i) for i, widget in enumerate(self.focus_row_buttons)]
        [ss_layout.addWidget(self.checkboxes[f"{i}"], i + 1, 0) for i in range(len(self.checkboxes))]
        [ss_layout.addWidget(self.leftarrows[f"{i}"], i + 1, 1) for i in range(len(self.leftarrows))]
        [ss_layout.addWidget(self.plot_number_comboboxes[f"{i}"], i + 1, 2) for i in range(len(self.plot_number_comboboxes))]
        [ss_layout.addWidget(self.rightarrows[f"{i}"], i + 1, 3) for i in range(len(self.rightarrows))]
        
        # Plots
        [layouts["plots"].addWidget(widget) for widget in [self.channel_selection_comboboxes["x_axis"], self.plot_widgets["graph_0"], self.plot_widgets["graph_1"]]]
        widgets["plot"].setLayout(layouts["plots"])
        self.plot_items["graph_0"].setFixedWidth(500)
        
        # Options
        [layouts["options"].addWidget(widget, index, 0) for index, widget in enumerate(self.option_widgets_col0)]
        [layouts["options"].addWidget(widget, index, 1) for index, widget in enumerate(self.option_widgets_col1)]
        widgets["options"].setLayout(layouts["options"])
        
        layouts["i/o"].addWidget(self.buttons["open_folder"], 5)
        layouts["i/o"].addWidget(self.buttons["exit"], 1)
        
        # x axis
        [layouts["x_axis"].addWidget(widget, 4 * i + 1) for i, widget in enumerate([buttons["x_axis"], self.channel_selection_comboboxes["x_axis"]])]
        layouts["x_axis"].setStretch(2, 3)
        widgets["x"].setLayout(layouts["x_axis"])
        
        #
        image_widget = self.image_widget
        self.view_box = image_widget.addViewBox()
        self.view_box.setAspectLocked(True)
        self.view_box.invertY(True)
        self.image_item = pg.ImageItem()
        self.view_box.addItem(self.image_item)
        
        # Main
        main_layout = layouts["main"]
        main_layout.addWidget(widgets["selector"], 0, 0, 2, 1) # Spectrum selector buttons
        main_layout.addWidget(widgets["x"], 0, 1) # x axis channel selection combobox
        main_layout.addWidget(widgets["plot"], 1, 1, 2, 1)
        main_layout.addLayout(layouts["i/o"], 0, 2)
        main_layout.addWidget(widgets["options"], 1, 2)
        main_layout.addWidget(self.image_widget, 2, 2)
        main_layout.setColumnMinimumWidth(1, 500)
        
        return



    # 4: Set up the main window layout
    def setup_main_window(self) -> None:
        layouts = self.layouts
        widgets = self.widgets

        # Aesthetics
        widgets["selector"].setLayout(layouts["selector"])
        
        # Set the central widget of the QMainWindow
        widgets["central"].setLayout(layouts["main"])
        widgets["central"].setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        widgets["central"].setFocus()
        
        # Finish the setup
        self.setCentralWidget(widgets["central"])
        self.setWindowTitle("Spectralyzer")
        self.setGeometry(200, 50, 1200, 800) # x, y, width, height
        self.setWindowIcon(self.icons.get("graph"))
        self.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        self.setFocus()
        self.activateWindow()
        
        return

