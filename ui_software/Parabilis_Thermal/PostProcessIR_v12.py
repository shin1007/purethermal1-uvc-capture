#!/usr/bin/env python3
# Author: Karl Parks, 2018
# Python 3 and PyQt5 Implementation
from PyQt5.QtWidgets import (QWidget, QMainWindow, QApplication, QLabel, QPushButton, QVBoxLayout, QButtonGroup,
                             QGridLayout, QSizePolicy, QMessageBox, QFileDialog, QSlider, QComboBox, QProgressDialog)
from PyQt5.QtCore import (QCoreApplication, QThread,
                          QThreadPool, pyqtSignal, pyqtSlot, Qt, QTimer, QDateTime)
from PyQt5.QtGui import (QImage, QPixmap, QTextCursor, QIntValidator)
from PyQt5 import QtCore, QtGui, uic
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.animation import FuncAnimation
from matplotlib.animation import TimedAnimation
from matplotlib import cm
from matplotlib.contour import ContourSet
from matplotlib import image
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib as mpl
import random
import numpy as np
from os.path import (join, dirname)
import cv2
import h5py
import time
import re
import glob
import warnings
import os
import colors
import save_as
from heat_data import heat_data
import sys
from pathlib import Path
print(sys.version)

print('Successful import of uic')  # often reinstallation of PyQt5 is required
print('Successful import of all libraries')
warnings.filterwarnings("ignore")

colorMapType = "ironblack"  # ironblack, rainbow, grayscale
toggleUnitState = 'C'
current_frame = 1
framerate = 1  # (1/9 frames per second), do not adjust
timerHz = 115  # ms 1/8.7 = 0.1149 sec, decrease to increase speed
usedOnce = True
start_frame = 1
stop_frame = 2
last_frame = 3


qtCreatorFile = join(dirname(__file__), "ir_post_v2.ui")  # Enter file here.
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile)


def cktof(val):
    return round(((1.8 * cktoc(val) + 32.0)), 2)


def cktoc(val):
    return round(((val - 27315) / 100.0), 2)


def cktok(val):
    return round((val / 100.0), 2)


def get_temp_with_unit(val, unit):
    result = str(calc_temp(val, unit))
    return result + ' ' + unit


def calc_temp(val, unit):
    if unit == 'K':
        return (cktok(val))
    elif unit == 'C':
        return (cktoc(val))
    elif unit == 'F':
        return (cktof(val))
    else:
        return 0


class Window(QMainWindow, Ui_MainWindow):
    def __init__(self):
        Ui_MainWindow.__init__(self)
        QMainWindow.__init__(self)
        self.h5data = ""
        self.setupUi(self)
        self.initUI()

    def initUI(self):
        print('Starting user interface...')
        self.widget = QWidget()
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.dispLayout.addWidget(self.toolbar)
        self.dispLayout.addWidget(self.canvas)

        # BUTTONS
        self.btnFileSelect.clicked.connect(self.dialog_file_select)
        self.btnFolder.clicked.connect(self.open_folder)
        self.btnPrev.clicked.connect(self.prev_file)
        self.btnNext.clicked.connect(self.next_file)
        self.btnTempScale.clicked.connect(self.figure_with_temp_scale)

        # BUTTONS - player controls
        self.btnNextFrame.clicked.connect(self.to_next_frame)
        self.btnPrevFrame.clicked.connect(self.to_previous_frame)
        self.btnPlay.clicked.connect(self.play)
        self.btnPause.clicked.connect(self.pauseVideo)

        # BUTTONS - saving files
        self.btnMultiConvert.clicked.connect(self.save_multi_frames)
        self.btnSingleConvert.clicked.connect(self.save_single_frame)

        # RADIO BUTTONS - temperature
        self.temp_group = QButtonGroup()
        self.temp_group.addButton(self.rdoCelsius)
        self.temp_group.addButton(self.rdoKelvin)
        self.temp_group.addButton(self.rdoFahrenheit)
        self.rdoCelsius.clicked.connect(self.in_Celsius)
        self.rdoFahrenheit.clicked.connect(self.in_fahrenheit)
        self.rdoKelvin.clicked.connect(self.in_Kelvin)
        self.rdoCelsius.setChecked(True)

        # RADIO BUTTONS - colormap
        self.color_group = QButtonGroup()
        self.color_group.addButton(self.rdoIronBlack)
        self.color_group.addButton(self.rdoGrayScale)
        self.color_group.addButton(self.rdoRainbow)
        self.rdoIronBlack.clicked.connect(self.to_ironblack)
        self.rdoGrayScale.clicked.connect(self.to_grayscale)
        self.rdoRainbow.clicked.connect(self.to_rainbow)
        self.rdoIronBlack.setChecked(True)

        # EDIT TEXT - start and stop frames
        validator = QIntValidator(self)
        self.startEdit.setValidator(validator)
        self.stopEdit.setValidator(validator)
        self.startEdit.textEdited.connect(self.renew_start_frame)
        self.stopEdit.textEdited.connect(self.renew_stop_frame)

        # SLIDER
        self.sl.valueChanged.connect(self.slValueChange)

        # TIMER - used when playing video
        self.timer = QTimer(self)
        self.timer.setInterval(timerHz)
        self.timer.timeout.connect(self.playVid5)

        if (len(sys.argv) > 1) and (usedOnce == True):
            self.command_line_file_select()

    def enable_buttons(self, bl):
        self.btnTempScale.setEnabled(bl)

        # BUTTONS - player controls
        self.btnNextFrame.setEnabled(bl)
        self.btnPrevFrame.setEnabled(bl)
        self.btnPlay.setEnabled(bl)
        self.btnPause.setEnabled(bl)

        # BUTTONS - saving files
        self.btnSingleConvert.setEnabled(bl)
        self.btnMultiConvert.setEnabled(bl)

        # BUTTONS - open another file
        self.btnPrev.setEnabled(bl)
        self.btnNext.setEnabled(bl)

        # RADIO BUTTONS - temperature
        self.rdoCelsius.setEnabled(bl)
        self.rdoFahrenheit.setEnabled(bl)
        self.rdoKelvin.setEnabled(bl)
        self.rdoCelsius.setChecked(bl)

        # RADIO BUTTONS - colormap
        self.rdoIronBlack.setEnabled(bl)
        self.rdoGrayScale.setEnabled(bl)
        self.rdoRainbow.setEnabled(bl)

        # EDIT TEXT - start and stop frames
        self.startEdit.setEnabled(bl)
        self.stopEdit.setEnabled(bl)

        # SLIDER
        self.sl.setEnabled(bl)

        return

    def logger(self, text: str):
        self.history.insertPlainText(text + '\n')
        self.history.moveCursor(QTextCursor.End)
        print(text)

    def renew_start_frame(self):
        global start_frame
        try:
            start_frame = int(self.startEdit.text())
        except:
            pass

    def renew_stop_frame(self):
        global stop_frame
        try:
            stop_frame = int(self.stopEdit.text())
        except:
            pass

    # saving multiple frames
    def open_folder(self):
        path = QFileDialog.getExistingDirectory(
            self.widget, 'Open File Directory', '/')
        self.folder = path
        self.files = glob.glob(path + "/*.HDF5")
        self.filenum = 0
        if(len(self.files) == 0):
            print('no HDF5 file in selected folder')
            return
        self.enable_buttons
        self.open_file(self.files[0])

    def prev_file(self):
        try:
            self.filenum -= 1
            self.open_file(self.files[self.filenum])
        except:
            pass

    def next_file(self):
        try:
            self.filenum += 1
            self.open_file(self.files[self.filenum])
        except:
            pass

    def save_multi_frames(self):
        if(self.chkCSVs.checkState()):
            # ディレクトリがなければ作成
            if not(os.path.exists(self.folder + './csv')):
                os.mkdir(self.folder + './csv')
            savestem = self.folder + '\\csv\\' + self.h5data.basename
            save_as.to_csvs(savestem, self.h5data, start_frame, stop_frame)
        if(self.chkTIFFs.checkState()):
            savepath = self.h5data.fullpath + '.tiff'
            save_as.to_tiffs(savepath, self.h5data,
                             colorMapType, start_frame, stop_frame)
        if(self.chkPNGs.checkState()):
            # ディレクトリがなければ作成
            if not(os.path.exists(self.folder + './png')):
                os.mkdir(self.folder + './png')
            savestem = self.folder + '\\png\\' + self.h5data.basename
            save_as.to_pngs(savestem, self.h5data,
                            colorMapType, start_frame, stop_frame)
        if(self.chkAVI.checkState()):
            savepath = self.h5data.fullpath + '.avi'
            save_as.to_avi(savepath, self.h5data,
                           colorMapType, start_frame, stop_frame)
        return

    def save_single_frame(self):
        saveframe = self.h5data.frame(current_frame, 640, 480)
        savestem = self.folder + '\\' + self.h5data.basename + '_f' + current_frame
        if(self.chkCSV.checkState()):
            save_as.to_csv(savestem + '.csv', saveframe)
        if(self.chkTIFF.checkState()):
            save_as.to_tiff(savestem + '.tif', saveframe, colorMapType)
        if(self.chkPNG.checkState()):
            save_as.to_png(savestem + '.png', saveframe, colorMapType)
        return

    # color functions (on radiobutton click)

    def to_ironblack(self):
        global colorMapType
        colorMapType = 'ironblack'
        self.renew_image()
        self.logger('Changed Color Map')

    def to_rainbow(self):
        global colorMapType
        colorMapType = 'rainbow'
        self.renew_image()
        self.logger('Changed Color Map')

    def to_grayscale(self):
        global colorMapType
        colorMapType = 'grayscale'
        self.renew_image()
        self.logger('Changed Color Map')

    # temperature functions (on radiobutton click)
    def in_Celsius(self):
        global toggleUnitState
        toggleUnitState = 'C'
        self.renew_image()
        self.logger('Display ' + str(toggleUnitState))

    def in_fahrenheit(self):
        global toggleUnitState
        toggleUnitState = 'F'
        self.renew_image()
        self.logger('Display ' + str(toggleUnitState))

    def in_Kelvin(self):
        global toggleUnitState
        toggleUnitState = 'K'
        self.renew_image()
        self.logger('Display ' + str(toggleUnitState))

    # slider functions
    def slValueChange(self):
        global current_frame
        current_frame = self.sl.value()
        self.renew_image()
        self.canvas.draw()

    def setSlider(self):
        self.sl.setMinimum(1)
        self.sl.setMaximum(last_frame)
        self.sl.setValue(1)
        self.sl.setTickPosition(QSlider.TicksBelow)
        self.sl.setTickInterval(9)
        self.slStartF.setText('First Frame: 1')
        self.slMidF.setText('Mid Frame: ' + str(round(last_frame/2)))
        self.slEndF.setText('Last Frame: ' + str(last_frame))
        self.slStartT.setText('0 Seconds')
        self.slMidT.setText(str(round(last_frame/(2*9), 1)) + ' Seconds')
        self.slEndT.setText(str(round(last_frame/9, 1)) + ' Seconds')

    # on hovering on the picture
    def grabTempValue(self, xMouse, yMouse):
        frame = self.h5data.frame(current_frame, 640, 480)
        return frame[yMouse, xMouse]

    def hover(self, event):
        if event.xdata == None:
            self.cursorTempLabel.setText('Cursor Temp: MOVE CURSOR OVER IMAGE')
        else:
            xMouse = int(round(event.xdata))
            yMouse = int(round(event.ydata))
            cursorVal = int(round(self.grabTempValue(xMouse, yMouse)))
            self.cursorTempLabel.setText(
                'Cursor Temp: ' + get_temp_with_unit(cursorVal, toggleUnitState))

    # video playing functions
    def frame_setting_ng(self):
        if(1 <= start_frame and start_frame <= last_frame
            and start_frame <= stop_frame
                and stop_frame <= last_frame):
            return False
        else:
            self.logger('Frame setting is wrong')
            return True

    def play(self):
        if(self.frame_setting_ng()):
            return

        global current_frame
        current_frame = start_frame

        self.logger('Playing video from Frame: ' + str(start_frame))
        self.timer.start()

    def playVid5(self):
        self.move_frame(1)

    def pauseVideo(self):
        self.timer.stop()
        self.logger('Paused Video')

    def move_frame(self, val):
        global current_frame
        frame_to_stop = min(stop_frame, last_frame)
        if ((val < 0 and current_frame > 1)
                or(val > 0 and current_frame < frame_to_stop)):
            current_frame += val
            self.sl.setValue(current_frame)
            self.renew_image()
            if current_frame == frame_to_stop:
                self.pauseVideo()
        else:
            pass

    def to_previous_frame(self):
        self.move_frame(-1)
        self.logger('Previous Frame: ' + str(current_frame))

    def to_next_frame(self):
        self.move_frame(1)
        self.logger('Next Frame: ' + str(current_frame))

    # drawing images
    def renew_image(self):
        try:
            if current_frame == 1:
                self.figure.tight_layout()

            self.currentFrameDisp.setText(
                'Current Frame: ' + str(current_frame))

            frame = self.h5data.frame(current_frame, 640, 480)
            minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(frame)
            self.maxTempLabel.setText(
                'Current Max Temp: ' + get_temp_with_unit(maxVal, toggleUnitState))
            self.maxTempLocLabel.setText('Max Temp Loc: ' + str(maxLoc))
            self.minTempLabel.setText(
                'Current Min Temp: ' + get_temp_with_unit(minVal, toggleUnitState))
            self.minTempLocLabel.setText('Min Temp Loc: ' + str(minLoc))

            img = colors.colorize(frame, colorMapType)
            rgbImage = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

            self.ax = self.figure.add_subplot(111)
            self.ax.clear()
            self.cax = self.ax.imshow(rgbImage)

            self.sl.setValue(current_frame)
            self.currentTimeLabel.setText(
                'Current Time: ' + str(round(((current_frame-1)/9.00), 2)))
            cid = self.canvas.mpl_connect('motion_notify_event', self.hover)
        except:
            pass

    def maxtemp(self):
        return self.maxTempLabel.text()[18:]

    def mintemp(self):
        return self.minTempLabel.text()[18:]

    def figure_with_temp_scale(self):
        data = self.h5data.frame(current_frame, 640, 480)
        img = colors.colorize(data, colorMapType)
        rgbImage = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # colormap of the bar
        C = colors.get_color_map(colorMapType)
        C = np.squeeze(C)
        C = C[..., ::-1]
        C2 = C/255.0
        ccm = ListedColormap(C2)

        fig = plt.figure()
        plt.title('Frame: ' + str(current_frame) + '   Max Temp: ' +
                  self.maxtemp())
        bounds = [0, 50, 100]
        im = plt.imshow(rgbImage, cmap=ccm,
                        clim=(self.maxtemp()[:-2], self.mintemp()[:-2]))
        cbar = fig.colorbar(im)
        cbar.ax.minorticks_on()
        limits = cbar.get_clim()
        cbar.set_label(
            '     [$^\circ$' + toggleUnitState + ']', rotation=0)  # 270
        plt.show()

    # opening hdf5 file
    def command_line_file_select(self):
        global usedOnce
        print("First file specified from command line")
        path = sys.argv[1]
        usedOnce = False
        self.open_file(path)

    def dialog_file_select(self):
        dlg = QFileDialog()
        dlg.setDefaultSuffix('.HDF5')
        path, filter = dlg.getOpenFileName(
            self, 'Open File', "", 'HDF5 (*.HDF5);; All Files (*)')
        print(path)
        self.dispSelectedFile.setText(path)
        self.open_file(path)

    def open_file(self, path):
        global current_frame
        global last_frame
        global stop_frame
        if path == "":
            self.logger('Please select .HDF5 File')
            return
        else:
            try:
                self.enable_buttons(True)
                self.dispSelectedFile.setText(path)
                self.h5data = heat_data(path)
                current_frame = 1
                last_frame = self.h5data.last_frame
                stop_frame = last_frame
                self.renew_image()
                self.setSlider()
                self.startEdit.setText(str(current_frame))
                self.stopEdit.setText(str(last_frame))
                self.logger('Selected File and Displayed First Frame')
                self.canvas.draw()
            except:
                self.logger('Please select .HDF5 File')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = Window()
    main.show()
    sys.exit(app.exec_())
