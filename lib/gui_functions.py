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

    def make_groupbox(self, name: str, description: str = "") -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox(name)
        box.setToolTip(description)
        box.setCheckable(True)
        return box

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
    
    def make_radio_button(self, name: str, func: Callable, description: str = "", icon = None, key_shortcut = None, rotate_degrees: float = 0) -> QtWidgets.QRadioButton:
        button = QtWidgets.QRadioButton(name)
        button.setObjectName(name)
        button.toggled.connect(lambda checked, f = func: f() if checked else None)
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
    
    def make_checkbox(self, name: str, func: Callable, description: str = "", icon = None, key_shortcut = None, rotate_degrees: float = 0) -> QtWidgets.QCheckBox:
        box = QtWidgets.QCheckBox(name)
        box.setObjectName(name)
        box.clicked.connect(lambda checked, f = func: f() if checked else None)
        box.setToolTip(description)
        
        if isinstance(key_shortcut, Qt.Key):
            shortcut = QtGui.QShortcut(QtGui.QKeySequence(key_shortcut), self)
            shortcut.activated.connect(lambda checked, f = func: f())

        if isinstance(icon, QtGui.QIcon):
            if type(rotate_degrees) == float or type(rotate_degrees) == int and rotate_degrees != 0:
                try: icon = self.rotate_icon(icon, rotate_degrees)
                except: pass
            try: box.setIcon(icon)
            except: pass
        return box
    
    def make_combobox(self, name: str, func: Callable, description: str = "") -> QtWidgets.QComboBox:
        box = QtWidgets.QComboBox()
        box.setObjectName(name)
        box.currentIndexChanged.connect(lambda checked, f = func: f() if checked else None)
        box.setToolTip(description)
        return box
    
    def make_line_edit(self, name: str, description: str = "", icon = None, key_shortcut = None, rotate_degrees: float = 0) -> QtWidgets.QLineEdit:
        button = QtWidgets.QLineEdit()
        button.setObjectName(name)
        button.setToolTip(description)

        if isinstance(icon, QtGui.QIcon):
            if type(rotate_degrees) == float or type(rotate_degrees) == int and rotate_degrees != 0:
                try: icon = self.rotate_icon(icon, rotate_degrees)
                except: pass
            try: button.setIcon(icon)
            except: pass
        return button 
    
    def make_layout(self, orientation: str = "h") -> QtWidgets.QLayout:
        match orientation:
            case "h":
                layout = QtWidgets.QHBoxLayout()
            case "v":
                layout = QtWidgets.QVBoxLayout()
            case _:
                layout = QtWidgets.QGridLayout()
        
        layout.setSpacing(1)
        return layout
    
    def line_widget(self, orientation: str = "v", thickness: int = 1) -> QtWidgets.QFrame:
        line = QtWidgets.QFrame()
        match orientation:
            case "h":
                line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
            case _:
                line.setFrameShape(QtWidgets.QFrame.Shape.VLine)
        line.setLineWidth(thickness)
        return line

    def rotate_icon(icon, angle) -> QtGui.QIcon:
        try:
            pixmap = icon.pixmap()
            transform = QtGui.QTransform()
            transform.rotate(angle)

            rotated_pixmap = pixmap.transformed(transform)

            return QtGui.QIcon(rotated_pixmap)
        except:
            return False