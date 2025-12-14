import os
import sys
import yaml
import numpy as np
from PyQt6 import QtGui, QtWidgets
from PyQt6.QtCore import Qt
from datetime import datetime
from typing import Callable, Dict, List, Tuple



class GUIFunctions:
    def __init__(self):
        pass

    def make_button(self, name: str, func: Callable, description: str = "", icon = None, key_shortcut = None, rotate_degrees: float = 0) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton(name)
        button.setObjectName(name)
        button.clicked.connect(lambda checked, f = func: f())
        button.setToolTip(description)
        
        if isinstance(key_shortcut, Qt.Key):
            shortcut = QtGui.QShortcut(QtGui.QKeySequence(key_shortcut), self)
            shortcut.activated.connect(lambda checked, f = func: f())

        if isinstance(icon, QtGui.QIcon):
            if type(rotate_degrees) == float or type(rotate_degrees) == int and rotate_degrees != 0:
                try: icon = self.rotate_icon(icon, rotate_degrees)
                except: pass
            try: button.setIcon(icon)
            except: pass
        return button
    
    def make_label(self, name: str, description: str = "", icon_path = None) -> QtWidgets.QLabel:
        label = QtWidgets.QLabel(name)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setObjectName(name)
        label.setToolTip(description)
        if isinstance(icon_path, str):
            try:
                icon = QtGui.QIcon(icon_path)
                label.setIcon(icon)
            except:
                pass
        return label

    def rotate_icon(icon, angle) -> QtGui.QIcon:
        try:
            pixmap = icon.pixmap()
            transform = QtGui.QTransform()
            transform.rotate(angle)

            rotated_pixmap = pixmap.transformed(transform)

            return QtGui.QIcon(rotated_pixmap)
        except:
            return False