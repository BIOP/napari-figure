"""
This module is an example of a barebones QWidget plugin for napari

It implements the Widget specification.
see: https://napari.org/stable/plugins/guides.html?#widgets

Replace code below according to your needs.
"""
from typing import TYPE_CHECKING

import os
from tifffile import imread # https://pypi.org/project/tifffile/#examples
from skimage import io
import numpy as np
import string
from pathlib import Path

from qtpy.QtWidgets import (QWidget, QPushButton, QListWidget, QDialog, QDoubleSpinBox, QSpinBox,
QGroupBox, QGridLayout, QHBoxLayout,QVBoxLayout, QLabel, QColorDialog, QLayout,
QTabWidget, QLineEdit, QCheckBox, QSizePolicy, QFileDialog)
from qtpy.QtGui import QPixmap, QColor
from qtpy.QtCore import Qt

from microfilm.microplot import Micropanel
from microfilm.microplot import microshow

import napari
from napari.utils.notifications import show_info

import vispy.color # to make own colormaps
from matplotlib.colors import ListedColormap # to make own colormaps


class FigureWidget(QWidget):
    # your QWidget.__init__ can optionally request the napari viewer instance
    # in one of two ways:
    # 1. use a parameter called `napari_viewer`, as done here
    # 2. use a type annotation of 'napari.viewer.Viewer' for any parameter
    def __init__(self, napari_viewer):
        super().__init__()
        self.viewer = napari_viewer   
        self.params = Params()
        #self.colormaps = ColorMaps()  

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
        self.tabs.addTab(self.file, 'File & Display')     
         # Montage tab
        self.montage = QWidget()
        self._montage_layout = QVBoxLayout()
        self.montage.setLayout(self._montage_layout)
        self.tabs.addTab(self.montage, 'Montage')
        ## Add Tabs to the layout
        self._layout.addWidget(self.tabs)
        ###############################

        ##############################################################
        # Within the File tab, 
        # make a QGrid
        self.file_grid = QGridLayout()
        self._file_layout.addLayout(self.file_grid)

        ###############create a file selector
        self.file_selector = FileSelector(napari_viewer=self.viewer, params= self.params)
        # make a groupbox for the file selector    
        self.file_groupbox = QGroupBox('Select a file')
        self.file_groupbox_layout = QVBoxLayout()       
        self.file_groupbox_layout.addWidget(self.file_selector ) 
        self.file_groupbox.setLayout(self.file_groupbox_layout )
        # add the groupbox to the grid
        self.file_grid.addWidget(self.file_groupbox,0,0)
        
        # Add a "remove existing layers" checkbox
        self.remove_existing_layers = QCheckBox('Remove existing layers')
        self.remove_existing_layers.setChecked(True)
        self.file_grid.addWidget(self.remove_existing_layers , 1,0)

        # Add a "Load Image" button
        self.load_button = QPushButton('Load Image')
        self.load_button.setEnabled(  True ) #TODO: make this dependent on the file selector
        self.file_grid.addWidget(self.load_button , 2 ,0)

        ###############create a settings selector
        self.visual_settings_selector = SettingsSelector(napari_viewer=self.viewer, params= self.params)
        self.visual_settings_groupbox = QGroupBox('Visual settings')
        self.visual_settings_groupbox_layout = QVBoxLayout() 
        self.visual_settings_groupbox_layout.addWidget(self.visual_settings_selector )
        self.visual_settings_groupbox.setLayout(self.visual_settings_groupbox_layout )
        self.file_grid.addWidget(self.visual_settings_groupbox,3,0)
        ###############################

        # Connect signals to slots
        self.load_button.clicked.connect(self.load_selected_file)
        ##############################################################

        ##############################################################
        # Within the Montage tab
        self.montage_creator = MontageSettingsSelector(napari_viewer=self.viewer, params= self.params)
        self._montage_layout.addWidget( self.montage_creator )

        self.montage_button = QPushButton('Create Montage')
        self.montage_button.setEnabled(  True )
        self._montage_layout.addWidget(self.montage_button)

        # Connect signals to slots
        self.montage_button.clicked.connect(self.create_montage_image)
        ##############################################################

        self.initialize()

    def initialize(self):
        # This method is called when the widget is added to the viewer dock widget
        # You can do things like connect to events here
        self.params.selected_directory = 'data/'
        self.params.selected_file = '6chs_loading.tif'
        self.params.channel_axis_value = 0
        self.params.channels_LUTs = "biop_azure,biop_amber,biop_brightpink,biop_chartreuse,biop_electricindigo,biop_springgreen"
        self.params.channels_names = "ch1,ch2,ch3,ch4,ch5,ch6"
        self.params.channels_mins = "0,0,0,0,0,0"
        self.params.channels_maxs = "255,255,255,255,255,255"
        self.load_selected_file() 


    def create_montage_image(self):
        layers_data = []
        for layer in self.viewer.layers:
            layers_data.append(layer.data)

        colormaps = self.params.channels_LUTs.split(",")
        while (  len( colormaps) != len(self.viewer.layers) ): colormaps.append("gray")
        
        N=256
        for idx in range(len(colormaps)):
            if colormaps[idx] == "biop_amber":
                colormaps[idx] = self.MakeMltCmap(N, N  , N/2,0)
            elif colormaps[idx] == "biop_azure":
                colormaps[idx] = self.MakeMltCmap(N, 0  , N/2,N)
            elif colormaps[idx] == "biop_brightpink":
                colormaps[idx] = self.MakeMltCmap(N, N  , 0  ,N/2)
            elif colormaps[idx] == "biop_chartreuse":
                colormaps[idx] = self.MakeMltCmap(N, N/2, N  ,0)
            elif colormaps[idx] == "biop_electricindigo":
                colormaps[idx] = self.MakeMltCmap(N, N/2, 0  ,N)
            elif colormaps[idx] == "biop_springgreen":
                colormaps[idx] = self.MakeMltCmap(N, 0  , N  ,N/2)

        panels = []

        panels.append( microshow( images=layers_data[0:3] , cmaps=colormaps[0:3] ) )
                      
        for idx in range(len(self.viewer.layers)):
            layer = layers_data[idx]
            colormap = colormaps[idx]
            panels.append( microshow( images=layer , cmaps=colormap ) )

        micropanel = Micropanel( rows = self.params.montage_rows, 
                                 cols = self.params.montage_columns
                                )
        
        #TODO make sure it works with r and c 
        i=0
        for r in range(self.params.montage_rows):
            for c in range(self.params.montage_columns):
                micropanel.add_element( pos=[r,c] , microim=panels[i] )
                i+=1


        # Save the montage image
        montage_path = os.path.join(self.params.selected_directory, "montage.png")
        micropanel.savefig(str(montage_path), bbox_inches = 'tight', pad_inches = 0, dpi=600)
       
        #TODO replace this with a QPixMap
        montage_image = io.imread(str(montage_path))
        montage_viewer = napari.Viewer()
        montage_viewer.add_image(montage_image, name="montage")

    #TODO move this to a separate file
    def MakeMltCmap(self, N, red_lim,g_lim,blue_lim):
        array = np.ones((N, 4))
        array[:, 0] = np.linspace(0, red_lim /N, N)
        array[:, 1] = np.linspace(0, g_lim   /N, N)
        array[:, 2] = np.linspace(0, blue_lim/N, N)
        return ListedColormap(array)
    

    def load_selected_file(self):
        # Remove existing layers
        if self.remove_existing_layers.isChecked():
            self.viewer.layers.clear()

        # Load the selected file in the current napari viewer
        if self.params.selected_file and self.params.selected_directory:
            path = os.path.join(self.params.selected_directory, self.params.selected_file)
                        
            image_basename = os.path.basename(self.params.selected_file)         

            image =  io.imread(path)
            
            #TODO check channel axis value, if it's too big pop up a warning
            ch_axis = self.params.channel_axis_value

            # Get the channel names
            names = self.params.channels_names.split(",")    
            while (  len( names) < image.shape[ch_axis] ): names.append("null")    
            layer_names = np.char.add( [image_basename+"_"]*len(names) , names)

            colormaps = self.params.channels_LUTs.split(",")
            while (  len( colormaps) < image.shape[ch_axis]  & len( colormaps) <10  ): colormaps.append("gray")
            
            for idx in range(len(colormaps)):
                if colormaps[idx] == "biop_amber":
                    colormaps[idx] =  ( "biop_amber", vispy.color.Colormap([[0.0, 0.0, 0.0], [1.0, 0.5, 0.0]]) )
                elif colormaps[idx] == "biop_azure":
                    colormaps[idx] =  ( "biop_azure", vispy.color.Colormap([[0.0, 0.0, 0.0], [0.0, 0.5, 1.0]]) ) 
                elif colormaps[idx] == "biop_brightpink":
                    colormaps[idx] = ("biop_brightpink", vispy.color.Colormap([[0.0, 0.0, 0.0], [1.0, 0.0, 0.5]]))
                elif colormaps[idx] == "biop_chartreuse":
                    colormaps[idx] = ("biop_chartreuse", vispy.color.Colormap([[0.0, 0.0, 0.0], [0.5, 1.0, 0.0]]))
                elif colormaps[idx] == "biop_electricindigo":
                    colormaps[idx] = ("biop_electricindigo", vispy.color.Colormap([[0.0, 0.0, 0.0], [0.5, 0.0, 1.0]]))
                elif colormaps[idx] == "biop_springgreen":
                    colormaps[idx] = ("biop_springgreen", vispy.color.Colormap([[0.0, 0.0, 0.0], [0, 1.0, 0.5]]))

                #TODO continue with other colors

            print( colormaps )

            contrast_mins = [int(x) for x in self.params.channels_mins.split(",")]
            contrast_maxs = [int(x) for x in self.params.channels_maxs.split(",")]
            while (  len( contrast_mins) < image.shape[ch_axis] ): contrast_mins.append(0)
            while (  len( contrast_maxs) < image.shape[ch_axis] ): contrast_maxs.append(255)
            contrast_limits=[]
            for x in range( 0 , len(contrast_mins) ): contrast_limits.append( [ contrast_mins[x] , contrast_maxs[x] ] )


            self.viewer.add_image( image, 
                                   channel_axis = ch_axis,
                                   name = layer_names,
                                   colormap = colormaps,
                                   contrast_limits = contrast_limits
                                   )
            
            show_info( str(path)+" done!" )




class Params():
    def __init__(self):
        # File settings
        self.selected_file = None
        self.selected_directory = None
        self.load_button_status = True
        self.channel_axis_value = None
        # Visual settings
        self.channels_names = 'DAPI,A488,A555'
        self.channels_LUTs = 'cyan,biop_amber,biop_pink'
        self.channels_mins = '0,0,0'
        self.channels_maxs = '255,255,255'
        self.remove_existing_layers = True
        # Montage settings
        self.montage_rows = 2
        self.montage_columns = 4
        self.montage_spacing = 3


class MontageSettingsSelector(QWidget , Params):
    def __init__(self, napari_viewer, params):
        super().__init__()    

        self.viewer = napari_viewer
        self.params = params    



class SettingsSelector(QWidget , Params):
    def __init__(self, napari_viewer, params):
        super().__init__()

        self.viewer = napari_viewer
        self.params = params    

        # Create a VerticalBox layout for the widget
        self._layout = QVBoxLayout()
        self.setLayout(self._layout)    

        # Create  'Basic' and 'Advanced' tabs
        # create Tabs widget
        self.tabs = QTabWidget()
        self._layout.addWidget(self.tabs)

        # Basic tab
        self.basic = QWidget()
        self._basic_layout = QVBoxLayout()
        self.basic.setLayout(self._basic_layout)
        self.tabs.addTab(self.basic, 'Basic')

        # Advanced tab, with a QGrid
        self.advanced = QWidget()
        self._advanced_layout = QGridLayout()
        self.advanced.setLayout(self._advanced_layout)
        self.tabs.addTab(self.advanced, 'Advanced')

        #### Basic tab ####
        self.main_label_basic = QLabel('Please modify layers settings \nand click the "Update from viewer" button.')
        self._basic_layout.addWidget(self.main_label_basic)
        
        self.settings_from_viewer = QPushButton('Update from viewer')
        self._basic_layout.addWidget(self.settings_from_viewer)

        #### Advanced tab ####
        #TODO find a way to add a label that spans multiple columns
        #self.main_label_advanced = QLabel('Please use the "," separated values\n to define the settings below')
        #self._advanced_layout.addWidget( self.main_label_advanced , columnSpan=2)

        self.channels_names = QLabel('Names')
        self.channels_names_edit = QLineEdit() # create a text box
        self.channels_names_edit.setText(self.params.channels_names)  # default value
        self.params.channels_names = self.channels_names_edit.text()  # update the params
        self._advanced_layout.addWidget( self.channels_names , 1 ,0) # add the text box to the layout
        self._advanced_layout.addWidget( self.channels_names_edit ,1 ,1 ) # add the text box to the layout

        self.channels_LUTs = QLabel('Colormaps')
        self.channels_LUTs_edit = QLineEdit()
        self.channels_LUTs_edit.setText(self.params.channels_LUTs)
        self.params.channels_LUTs = self.channels_LUTs_edit.text()
        self._advanced_layout.addWidget( self.channels_LUTs , 2,0)
        self._advanced_layout.addWidget( self.channels_LUTs_edit,2,1 )

        self.channels_mins = QLabel('mins')
        self.channels_mins_edit = QLineEdit()
        self.channels_mins_edit.setText(self.params.channels_mins)
        self.params.channels_mins = self.channels_mins_edit.text()
        self._advanced_layout.addWidget( self.channels_mins , 3,0)
        self._advanced_layout.addWidget( self.channels_mins_edit ,3,1 )

        self.channels_maxs = QLabel('maxs')
        self.channels_maxs_edit = QLineEdit()
        self.channels_maxs_edit.setText(self.params.channels_maxs)
        self.params.channels_maxs = self.channels_maxs_edit.text()
        self._advanced_layout.addWidget( self.channels_maxs , 4,0)
        self._advanced_layout.addWidget( self.channels_maxs_edit , 4,1  )

        # create connect when text is changed
        self.channels_names_edit.textChanged.connect(self.update_channels_names)
        self.channels_LUTs_edit.textChanged.connect(self.update_channels_LUTs)
        self.channels_mins_edit.textChanged.connect(self.update_channels_mins)
        self.channels_maxs_edit.textChanged.connect(self.update_channels_maxs)

        # create connect to update the text boxes when button is clicked
        self.settings_from_viewer.clicked.connect(self.update_boxes_from_viewer)

    def update_boxes_from_viewer(self, event):
        colormaps = self.params.channels_LUTs.split(",")
        contrast_mins = self.params.channels_mins.split(",")
        contrast_maxs = self.params.channels_maxs.split(",")
        
        for layer in self.viewer.layers :
            layer_index = self.viewer.layers.index(layer)
            new_color_map = layer.colormap.name
            colormaps[layer_index] = new_color_map

            new_contrast_min = int( layer.contrast_limits[0] )
            contrast_mins[layer_index] = str( new_contrast_min)

            new_contrast_max = int( layer.contrast_limits[1] )
            contrast_maxs[layer_index] = str( new_contrast_max  )

        
        # then update the text box and the params
        self.channels_LUTs_edit.setText( ",".join(colormaps) )
        self.params.channels_LUTs = self.channels_LUTs_edit.text()

        self.channels_mins_edit.setText( ",".join(contrast_mins) )
        self.params.channels_mins = self.channels_mins_edit.text()
        self.channels_maxs_edit.setText( ",".join(contrast_maxs) )
        self.params.channels_maxs = self.channels_maxs_edit.text()

        
    def update_channels_names(self):
        self.params.channels_names = self.channels_names_edit.text()
        
    def update_channels_LUTs(self):
        self.params.channels_LUTs = self.channels_LUTs_edit.text()
        
    def update_channels_mins(self):
        self.params.channels_mins = self.channels_mins_edit.text()

    def update_channels_maxs(self):
        self.params.channels_maxs = self.channels_maxs_edit.text()




class FileSelector(QWidget , Params):
    def __init__(self, napari_viewer, params):
        super().__init__()
        
        self.viewer = napari_viewer
        self.params = params

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
        self.params.channel_axis_value = QSpinBox( minimum = 0, maximum = 5 , singleStep = 1, value = 0)
        self.channel_grid.addWidget(self.params.channel_axis_value,  1, 1)

        # Create a QListWidget to display the files in the directory
        self.file_list = QListWidget()
        self._layout.addWidget(self.file_list)

        # Connect signals to slots
        self.dir_button.clicked.connect(self.select_directory )
        self.file_list.itemSelectionChanged.connect( self.update_selected_file )

        # Initialize the selected directory and file
        self.selected_directory = params.selected_directory
        self.selected_file = params.selected_file
        self.selected_channel_axis = params.channel_axis_value
        self.shape_value.setText('') 


    def select_directory(self):
        # Open a QFileDialog to select a directory
        dialog = QFileDialog()
        dialog.setFileMode(QFileDialog.DirectoryOnly)
        if dialog.exec_() == QDialog.Accepted:
            self.params.selected_directory = dialog.selectedFiles()[0]
            self.dir_edit.setText(self.params.selected_directory)
            self.update_file_list()

    def update_file_list(self):
        # Clear the file list and update it with the files in the selected directory
        self.file_list.clear()
        if self.params.selected_directory:
            files = os.listdir(self.params.selected_directory)
            for file in files:
                if file.endswith('.tif') or file.endswith('.tiff'):
                    self.file_list.addItem(file)
            self.params.load_button_status = True

    def update_selected_file(self):
        # Update the selected file when the item selection changes
        items = self.file_list.selectedItems()
        if items:
            self.params.selected_file = items[0].text()

            # read shape of selected file
            path = os.path.join( self.params.selected_directory, self.params.selected_file )
            image = imread(path)
            self.update_shape_value( image.shape )
            self.params.load_button_status = True

    def update_shape_value(self, shape):
        # Update the shape label text
        self.shape_value.setText(f'{shape}')   