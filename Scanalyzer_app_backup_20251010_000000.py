import os
import sys
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QToolButton, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QFileDialog, QButtonGroup, QComboBox, QRadioButton, QGroupBox
from PyQt6.QtGui import QPixmap, QIcon, QImage
from PyQt6.QtCore import Qt, QSize
from pathlib import Path
import pyqtgraph as pg
from scanalyzer.image_functions import get_scan
from PIL import Image



class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Scanalyzer") # Make the app window
        self.setGeometry(100, 100, 900, 600) # x, y, width, height

        # Initialize default parameters
        self.script_path = os.path.abspath(__file__) # The default folder is the directory of the app
        self.folder = os.path.dirname(self.script_path)
        self.scanalyzer_folder = self.folder + "\\scanalyzer"
        self.file_label = "Select file"
        self.image_files = [""]
        self.file_index = 0
        self.max_file_index = 0
        self.selected_file = ""
        self.scan_tensor = []
        self.selected_scan = self.load_dummy_image()
        self.channel = ""
        self.channels = []
        self.channel_index = 0
        self.max_channel_index = 0
        self.scan_direction = "forward"
        self.background_subtraction = "plane"

        # Set the central widget of the QMainWindow
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Add ImageView
        self.image_view = pg.ImageView(view = pg.PlotItem())
        


        # Buttons
        # Make file toggling/selecting buttons
        self.previous_file_button, self.file_select_button, self.next_file_button = (QToolButton(), QPushButton(self.file_label), QToolButton())
        self.previous_file_button.setArrowType(Qt.ArrowType.LeftArrow)
        self.previous_file_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.previous_file_button.clicked.connect(self.on_previous_file)
        self.file_select_button.clicked.connect(self.on_file_select)
        self.next_file_button.setArrowType(Qt.ArrowType.RightArrow)
        self.next_file_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.next_file_button.clicked.connect(self.on_next_file)

        # Make channel toggling/selecting buttons
        self.previous_chan_button, self.channel_box, self.next_chan_button = (QToolButton(), QComboBox(), QToolButton())
        self.previous_chan_button.setArrowType(Qt.ArrowType.DownArrow)
        self.previous_chan_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.previous_chan_button.clicked.connect(self.on_previous_chan)
        self.channel_box.addItems(["Channels"])
        self.channel_box.currentIndexChanged.connect(self.on_chan_change)
        self.next_chan_button.setArrowType(Qt.ArrowType.UpArrow)
        self.next_chan_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self.next_chan_button.clicked.connect(self.on_next_chan)

        # Direction toggle button (above the other buttons)
        self.direction_button = QPushButton(f"Direction: {self.scan_direction}")
        self.direction_button.setCheckable(True)
        self.direction_button.setChecked(self.scan_direction == "backward")
        self.direction_button.clicked.connect(self.on_toggle_direction)

        # Background subtraction radio buttons (none, plane, inferred)
        self.bg_none_radio = QRadioButton("none")
        self.bg_plane_radio = QRadioButton("plane")
        self.bg_inferred_radio = QRadioButton("inferred")

        # Group them for exclusive selection
        self.bg_button_group = QButtonGroup(self)
        self.bg_button_group.addButton(self.bg_none_radio)
        self.bg_button_group.addButton(self.bg_plane_radio)
        self.bg_button_group.addButton(self.bg_inferred_radio)
        
        # Set default according to self.background_subtraction
        if self.background_subtraction == "plane":
            self.bg_plane_radio.setChecked(True)
        elif self.background_subtraction == "inferred":
            self.bg_inferred_radio.setChecked(True)
        else:
            self.bg_none_radio.setChecked(True)
        
        # Connect toggle signals
        self.bg_none_radio.toggled.connect(lambda checked: self.on_bg_change("none") if checked else None)
        self.bg_plane_radio.toggled.connect(lambda checked: self.on_bg_change("plane") if checked else None)
        self.bg_inferred_radio.toggled.connect(lambda checked: self.on_bg_change("inferred") if checked else None)

        # Make I/O buttons
        self.save_button, self.exit_button = (QPushButton("Save image"), QPushButton("Exit app"))
        self.save_button.clicked.connect(self.on_save)
        self.exit_button.clicked.connect(self.on_exit)

        # Add all the buttons to the layout
        button_layout = QGridLayout()

        # Prepare a QGroupBox titled 'Background subtraction' to hold the three radio buttons horizontally
        bg_group = QGroupBox("Background subtraction")
        bg_hbox = QHBoxLayout()
        bg_hbox.setContentsMargins(6, 6, 6, 6)
        bg_hbox.addWidget(self.bg_none_radio)
        bg_hbox.addWidget(self.bg_plane_radio)
        bg_hbox.addWidget(self.bg_inferred_radio)
        bg_group.setLayout(bg_hbox)

        # Place buttons in grid; insert bg_widget at row 2, then direction, save, exit below
        button_widgets = [
            [self.previous_file_button, 0, 0], [self.file_select_button, 0, 1], [self.next_file_button, 0, 2],
            [self.previous_chan_button, 1, 0], [self.channel_box, 1, 1], [self.next_chan_button, 1, 2],
            [self.direction_button, 2, 1],
                [bg_group, 3, 0, 1, 3],
            [self.save_button, 4, 1], [self.exit_button, 5, 1],
        ]

        for item in button_widgets:
            if len(item) == 3:
                button_layout.addWidget(item[0], item[1], item[2])
            else:
                # widget with rowSpan/colSpan
                button_layout.addWidget(item[0], item[1], item[2], item[3], item[4])
        


        # Right column: metadata + buttons
        right_column = QVBoxLayout()
        self.metadata_label = QLabel("")
        self.metadata_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        right_column.addWidget(self.metadata_label)
        right_column.addLayout(button_layout)



        # Combine nested layouts: image view and left column
        main_layout.addWidget(self.image_view, 3)
        main_layout.addLayout(right_column, 1)
        
        # Ensure the central widget can receive keyboard focus
        central_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        central_widget.setFocus()

        # Ensure the main window also accepts focus and is active
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()
        self.activateWindow()

        # Display some initial dummy data
        self.image_view.setImage(self.selected_scan)

        self.channel_box.dropEvent



    # The dummy image is the Scanalyzer background picture
    def load_dummy_image(self):
        data = np.random.rand(200, 200) * 255 # Random data to display if the dummy image file cannot be found
        dummy_image_path = self.scanalyzer_folder + "\\Scanalyzer_drawing.png"
        if os.path.exists(dummy_image_path):
            try:
                img = Image.open(dummy_image_path)
                data = np.transpose(np.array(img)[:, :, 0])
            except Exception as e:
                print(f"An error occurred while attempting to load an image: {e}")
        return data

    # Key event handler
    def keyPressEvent(self, event):
        key = event.key()
        modifiers = event.modifiers()

        if key == Qt.Key.Key_Left: self.on_previous_file()
        if key == Qt.Key.Key_F: self.on_file_select()
        if key == Qt.Key.Key_Right: self.on_next_file()
        if key == Qt.Key.Key_Down: self.on_previous_chan()
        if key == Qt.Key.Key_Up: self.on_next_chan()
        if key == Qt.Key.Key_S: self.on_save()
        if key == Qt.Key.Key_D: self.on_toggle_direction()
        # Background subtraction shortcuts: P -> plane, I -> inferred, N -> none
        if key == Qt.Key.Key_P: self.on_bg_change("plane")
        if key == Qt.Key.Key_I: self.on_bg_change("inferred")
        if key == Qt.Key.Key_N: self.on_bg_change("none")
        if key == Qt.Key.Key_Q or key == Qt.Key.Key_X or key == Qt.Key.Key_E or key == Qt.Key.Key_Escape: self.on_exit()
        super().keyPressEvent(event)



    # Button functions
    def on_previous_file(self):
        self.file_index -= 1
        if self.file_index < 0: self.file_index = self.max_file_index
        self.load_image()

    def on_file_select(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Open file", "", "SXM files (*.sxm)")

        if file_name: # Check if a file was selected
            self.folder = os.path.dirname(file_name)
            print(f"Selected folder: {self.folder}")
            self.image_files = np.array([str(file) for file in Path(self.folder).glob("*.sxm")])
            print(Path(file_name))
            print(np.where(self.image_files == file_name))
            self.max_file_index = len(self.image_files) - 1
            
            if self.file_index > self.max_file_index: self.file_index = 0
            self.selected_file = self.image_files[self.file_index]
            self.file_label = os.path.basename(self.selected_file)
        if self.max_file_index < 1: # No scans detected; revert button text to 'Select file'
            self.file_label = "Select file"
            self.file_select_button.setText(self.file_label)
        else: self.load_image()

    def on_toggle_direction(self):
        # Toggle between 'forward' and 'backward'
        self.scan_direction = "backward" if self.scan_direction == "forward" else "forward"
        # Reload the image if one is currently selected
        try:
            if hasattr(self, 'image_files') and not (len(self.image_files) == 0 or (len(self.image_files) == 1 and self.image_files[0] == "")):
                self.load_image()
        except Exception as e:
            print(f"Error reloading image after toggling direction: {e}")

    def on_bg_change(self, mode: str):
        """Handler for background subtraction radio buttons."""
        self.background_subtraction = mode
        # Sync UI
        self.update_metadata_display()
        # Optionally reload the image to apply background subtraction
        try:
            if hasattr(self, 'image_files') and not (len(self.image_files) == 0 or (len(self.image_files) == 1 and self.image_files[0] == "")):
                # reload current image to reflect background change
                self.load_image()
        except Exception as e:
            print(f"Error reloading image after background change: {e}")

    def update_metadata_display(self):
        """Update the metadata_label and sync radios/direction text."""
        try:
            has_files = hasattr(self, 'image_files') and not (len(self.image_files) == 0 or (len(self.image_files) == 1 and self.image_files[0] == ""))
        except Exception:
            has_files = False

        if has_files:
            count = len(self.image_files)
            folder = getattr(self, 'folder', '')
            channel = getattr(self, 'channel', '')
            text = f"Folder: {folder}\nFound {count} .sxm files\nDirection: {self.scan_direction}\nBackground: {self.background_subtraction}\nChannel: {channel}"
        else:
            text = f"No folder selected.\nDirection: {self.scan_direction}\nBackground: {self.background_subtraction}"

        self.metadata_label.setText(text)
        # Sync controls
        if hasattr(self, 'direction_button'):
            self.direction_button.setText(f"Direction: {self.scan_direction}")
            self.direction_button.setChecked(self.scan_direction == "backward")
        # Sync radios
        if hasattr(self, 'bg_none_radio'):
            if self.background_subtraction == 'plane':
                self.bg_plane_radio.setChecked(True)
            elif self.background_subtraction == 'inferred':
                self.bg_inferred_radio.setChecked(True)
            else:
                self.bg_none_radio.setChecked(True)

    def on_next_file(self):
        self.file_index += 1
        if self.file_index > self.max_file_index: self.file_index = 0
        self.load_image()



    # Channel buttons
    def on_previous_chan(self):
        self.channel_index -= 1
        if self.channel_index < 0: self.channel_index = self.max_channel_index
        self.channel = self.channels[self.channel_index]
        self.load_image()

    def on_chan_change(self, index):
        self.channel_index = index
        self.channel = self.channels[index]
        self.load_image()

    def on_next_chan(self):
        self.channel_index += 1
        if self.channel_index > self.max_channel_index: self.channel_index = 0
        self.channel = self.channels[self.channel_index]
        self.load_image()



    # Routine for loading a new image
    def load_image(self):
        self.selected_file = self.image_files[self.file_index]
        self.file_label = os.path.basename(self.selected_file)
        self.file_select_button.setText(self.file_label) # Make the select file button display the file name

        scan_object = get_scan(self.selected_file) # Load the scan data
        self.channels = scan_object.channels # Load which channels have been recorded
        if self.channel not in self.channels: # If the requested channel does not exist in the scan, default the requested channel to be the first channel in the list of channels
            self.channel = self.channels[0]
        self.channel_index = np.where(self.channels == self.channel)[0][0]
        self.max_channel_index = len(self.channels) - 1
    
        # Pick the correct frame out of the scan tensor based on channel and scan direction
        if self.scan_direction == "backward": self.selected_scan = scan_object.scan_tensor[self.channel_index, 1]
        else: self.selected_scan = scan_object.scan_tensor[self.channel_index, 0]
        self.image_view.setImage(self.selected_scan) # Show the scan in the app

        # Update the channel selection box based on the available channels
        self.channel_box.blockSignals(True)
        self.channel_box.clear()
        self.channel_box.addItems(self.channels)
        self.channel_box.setCurrentIndex(self.channel_index)
        self.channel_box.blockSignals(False)

        # Read the header and save the scan parameters
        self.bias = scan_object.bias
        self.scan_range = scan_object.scan_range_nm
        self.feedback = scan_object.feedback
        self.setpoint = scan_object.setpoint_pA

        if self.feedback:
            self.metadata_label.setText(f"STM topographic scan\nV = {self.bias} V\nI_fb = {self.setpoint} pA\nScan range: {self.scan_range} nm\nChannel: {self.channel}\nScan direction: {self.scan_direction}")
        else:
            self.metadata_label.setText(f"Constant height scan\nV = {self.bias} V\nScan range: {self.scan_range}\nChannel: {self.channel} nm\nScan direction: {self.scan_direction}")

    # Save button
    def on_save(self):
        # Save the currently displayed scan as a PNG image, applying HistogramLUTItem levels if present
        try:
            if not hasattr(self, 'selected_scan') or self.selected_scan is None:
                self.metadata_label.setText("No image loaded to save.")
                return

            # Ask user for save location
            filename, _ = QFileDialog.getSaveFileName(self, "Save image as", "", "PNG Image (*.png)")
            if not filename:
                return

            # Convert numeric array to 8-bit grayscale image
            img = self.selected_scan
            import numpy as _np

            # Ensure numpy array
            if not isinstance(img, _np.ndarray):
                img = _np.array(img)

            # Try to obtain histogram LUT levels from the ImageView so saved image matches contrast
            hist_levels = None
            try:
                # common path: ImageView.ui.histogram.item
                ui = getattr(self.image_view, 'ui', None)
                if ui is not None and hasattr(ui, 'histogram') and hasattr(ui.histogram, 'item'):
                    hist_levels = ui.histogram.item.getLevels()
                else:
                    # fallback: getHistogramWidget() if available
                    get_hw = getattr(self.image_view, 'getHistogramWidget', None)
                    if callable(get_hw):
                        hw = get_hw()
                        if hasattr(hw, 'item'):
                            hist_levels = hw.item.getLevels()
            except Exception:
                hist_levels = None

            # Determine normalization bounds
            if hist_levels and hist_levels[0] is not None and hist_levels[1] is not None:
                imin, imax = float(hist_levels[0]), float(hist_levels[1])
            else:
                imin = float(_np.nanmin(img))
                imax = float(_np.nanmax(img))

            # Normalize to 0-255 using chosen bounds
            if imax - imin == 0:
                scaled = _np.clip(img - imin, 0, 255).astype(_np.uint8)
            else:
                scaled = ((_np.clip(img, imin, imax) - imin) / (imax - imin) * 255.0).astype(_np.uint8)

            # Create QImage (grayscale) from numpy array (width x height)
            if scaled.ndim != 2:
                # if multi-channel or unexpected shape, try to select first 2D frame
                scaled = _np.squeeze(scaled)
                if scaled.ndim != 2:
                    # fallback: take first channel/frame
                    scaled = scaled[..., 0]

            h, w = scaled.shape
            from PyQt6.QtGui import QImage
            # Ensure contiguous C-order
            scaled_c = _np.ascontiguousarray(scaled)
            qimg = QImage(scaled_c.data.tobytes(), w, h, w, QImage.Format.Format_Grayscale8)
            # Write to file
            ok = qimg.save(filename, "PNG")
            if ok:
                self.metadata_label.setText(f"Saved image: {filename}")
            else:
                self.metadata_label.setText(f"Failed to save image to: {filename}")
        except Exception as e:
            self.metadata_label.setText(f"Error saving image: {e}")

    # Exit button
    def on_exit(self):
        print("Thank you for using Scanalyzer!")
        QApplication.instance().quit()



if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AppWindow()
    window.show()
    sys.exit(app.exec())
# Backup copy created by tool on 2025-10-10 00:00:00
# This is a snapshot of Scanalyzer_app.py with changes applied.

# ...existing content preserved...

import os
import sys
import numpy as np
from PyQt6.QtWidgets import QApplication, QMainWindow, QLabel, QPushButton, QToolButton, QVBoxLayout, QHBoxLayout, QGridLayout, QWidget, QFileDialog, QButtonGroup, QComboBox, QRadioButton, QGroupBox
from PyQt6.QtGui import QPixmap, QIcon, QImage
from PyQt6.QtCore import Qt, QSize
from pathlib import Path
import pyqtgraph as pg
from scanalyzer.image_functions import get_scan
from PIL import Image



class AppWindow(QMainWindow):
    pass

# Note: full file contents are available in the working file `Scanalyzer_app.py`.
