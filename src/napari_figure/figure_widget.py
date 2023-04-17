"""
This module is an example of a barebones QWidget plugin for napari

It implements the Widget specification.
see: https://napari.org/stable/plugins/guides.html?#widgets

Replace code below according to your needs.
"""
from typing import TYPE_CHECKING

import os
from tifffile import imread # https://pypi.org/project/tifffile/#examples
import numpy as np
import string
from pathlib import Path

from qtpy.QtWidgets import (QWidget, QPushButton, QListWidget, QDialog, QDoubleSpinBox, QSpinBox,
QGroupBox, QGridLayout, QHBoxLayout,QVBoxLayout, QLabel, QColorDialog,
QTabWidget, QLineEdit, QCheckBox, QSizePolicy, QFileDialog)
from qtpy.QtGui import QPixmap, QColor
from qtpy.QtCore import Qt

import microfilm.microplot

if TYPE_CHECKING:
    import napari


class FigureWidget(QWidget):
    # your QWidget.__init__ can optionally request the napari viewer instance
    # in one of two ways:
    # 1. use a parameter called `napari_viewer`, as done here
    # 2. use a type annotation of 'napari.viewer.Viewer' for any parameter
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer
    
        # Create a VerticalBox layout for the widget
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)
        
        ###############################  
        ## Create Tabs
        #
        # Create a tab widget AND add it to the layout
        self.tabs = QTabWidget()
        self._layout.addWidget(self.tabs)
        # File tab
        self.file = QWidget()
        self._file_layout = QVBoxLayout()
        self.file.setLayout(self._file_layout)
        self.tabs.addTab(self.file, 'File')     
         # Visual Settings tab
        self.visSet = QWidget()
        self._visSet_layout = QVBoxLayout()
        self.visSet.setLayout(self._visSet_layout)
        self.tabs.addTab(self.visSet, 'Visual settings')
        ## Add Tabs to the layout
        self._layout.addWidget(self.tabs)
        ###############################

        ###############################
        # Within the File tab, add a file browser
        self.file_selector = FileSelector(napari_viewer=self.viewer)
        self._file_layout.addWidget(self.file_selector)


    
class FileSelector(QWidget):
    def __init__(self, napari_viewer):
        super().__init__()

        self.viewer = napari_viewer

        # Create a VerticalBox layout for the widget
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)

        # Add a label to display the selected directory
        self.dir_label = QLabel( 'Please select a directory:')
        self._layout.addWidget(self.dir_label)

        # Create a QHBoxLayout for the directory selector
        self.dir_layout = QHBoxLayout()
        self._layout.addLayout(self.dir_layout)

        # Add a QLineEdit and QPushButton for selecting a directory     
        self.dir_edit = QLineEdit()
        self.dir_layout.addWidget(self.dir_edit)

        self.dir_button = QPushButton('Select Directory')
        self.dir_layout.addWidget(self.dir_button)

        # Create a QGridLayout for the image shape and channel axis
        self.channel_grid = QGridLayout(self)
        self._layout.addLayout(self.channel_grid) 

        self.shape_label = QLabel()
        self.shape_label.setText(f'Shape:')
        self.channel_grid.addWidget(self.shape_label ,  0, 0)

        self.channel_axis_label = QLabel()
        self.channel_axis_label.setText(f'Channel axis:')
        self.channel_grid.addWidget(self.channel_axis_label ,  1, 0)

        # Add a label to display the shape of the selected file
        self.shape_value = QLabel()
        self.channel_grid.addWidget(self.shape_value,  0, 1)

        # Add a drop-down menu to select the axis of the channel
        self.channel_axis_value = QSpinBox( minimum = 0, maximum = 5, singleStep = 1, value = 0)
        self.channel_grid.addWidget(self.channel_axis_value,  1, 1)

        # Create a QListWidget to display the files in the directory
        self.file_list = QListWidget()
        self._layout.addWidget(self.file_list)

        # Add a "Load Image" button
        self.load_button = QPushButton('Load Image')
        self.load_button.setEnabled(False)
        self._layout.addWidget(self.load_button)

        # Connect signals to slots
        self.dir_button.clicked.connect(self.select_directory)
        self.file_list.itemSelectionChanged.connect(self.update_selected_file)
        self.load_button.clicked.connect(self.load_selected_file)

        # Initialize the selected directory and file
        self.selected_directory = None
        self.selected_file = None
        self.selected_channel_axis = 0
        self.shape_value.setText('') 


    def select_directory(self):
        # Open a QFileDialog to select a directory
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.DirectoryOnly)
        if dialog.exec_() == QDialog.Accepted:
            self.selected_directory = dialog.selectedFiles()[0]
            self.dir_edit.setText(self.selected_directory)
            self.update_file_list()

    def update_file_list(self):
        # Clear the file list and update it with the files in the selected directory
        self.file_list.clear()
        if self.selected_directory:
            files = os.listdir(self.selected_directory)
            for file in files:
                if file.endswith('.tif') or file.endswith('.tiff'):
                    self.file_list.addItem(file)
            self.load_button.setEnabled(True)

    def update_selected_file(self):
        # Update the selected file when the item selection changes
        items = self.file_list.selectedItems()
        if items:
            self.selected_file = items[0].text()

            # read shape of selected file
            path = os.path.join(self.selected_directory, self.selected_file)
            image = imread(path)
            self.update_shape_value(image.shape)


    def load_selected_file(self):
        # Load the selected file in the current napari viewer
        if self.selected_file and self.selected_directory:
            path = os.path.join(self.selected_directory, self.selected_file)
            image = imread(path)           
            self.viewer.add_image( image, channel_axis = self.channel_axis_value.value() )

    def update_shape_value(self, shape):
        # Update the shape label text
        self.shape_value.setText(f'{shape}')   