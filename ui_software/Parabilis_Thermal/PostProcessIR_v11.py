#!/usr/bin/env python3
# Author: Karl Parks, 2018
# Python 3 and PyQt5 Implementation
import colors
import save_as
from heat_data import heat_data
import warnings
import re
import time
import h5py
import cv2
import numpy as np
import random
import matplotlib as mpl
import matplotlib.animation as animation
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
from matplotlib import image
from matplotlib.contour import ContourSet
from matplotlib import cm
from matplotlib.animation import TimedAnimation
from matplotlib.animation import FuncAnimation
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5 import QtCore, QtGui, uic
from PyQt5.QtGui import (QImage, QPixmap, QTextCursor, QIntValidator)
from PyQt5.QtCore import (QCoreApplication, QThread,
                          QThreadPool, pyqtSignal, pyqtSlot, Qt, QTimer, QDateTime)
from PyQt5.QtWidgets import (QWidget, QMainWindow, QApplication, QLabel, QPushButton, QVBoxLayout, QButtonGroup,
                             QGridLayout, QSizePolicy, QMessageBox, QFileDialog, QSlider, QComboBox, QProgressDialog)
import sys
print(sys.version)

print('Successful import of uic')  # often reinstallation of PyQt5 is required

print('Successful import of all libraries')

qtCreatorFile = "ir_post_v2.ui"  # Enter file here.

Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile)


colorMapType = "ironblack"  # ironblack, rainbow, grayscale

warnings.filterwarnings("ignore")


toggleUnitState = 'C'

current_frame = 1
videoState = 'notPlay'
framerate = 1  # (1/9 frames per second), do not adjust
timerHz = 115  # ms 1/8.7 = 0.1149 sec, decrease to increase speed
fileSelected = ""
usedOnce = 1
start_frame = 1
stop_frame = 2
last_frame = 3


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
        QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.initUI()

    def initUI(self):
        print('Starting user interface...')
        self.w = QWidget()
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)

        self.dispLayout.addWidget(self.toolbar)
        self.dispLayout.addWidget(self.canvas)

        # buttons
        self.nextFrame.clicked.connect(self.dispNextImg)
        self.prevFrame.clicked.connect(self.dispPrevImg)
        self.selectFileBut.clicked.connect(self.getFile)
        self.playVidBut.clicked.connect(self.play)
        self.makeTiffBut.clicked.connect(self.save_tiffs)

        self.sl.valueChanged.connect(self.slValueChange)
        self.saveCvImageBut.clicked.connect(self.save_png)
        self.saveAsVideoSS.clicked.connect(self.save_avi)
        self.pauseVidBut.clicked.connect(self.pauseVideo)

        self.temp_group = QButtonGroup()
        self.temp_group.addButton(self.rdoCelsius)
        self.temp_group.addButton(self.rdoKelvin)
        self.temp_group.addButton(self.rdoFahrenheit)
        self.rdoCelsius.clicked.connect(self.in_Celsius)
        self.rdoFahrenheit.clicked.connect(self.in_fahrenheit)
        self.rdoKelvin.clicked.connect(self.in_Kelvin)
        self.rdoCelsius.setChecked(True)

        self.color_group = QButtonGroup()
        self.color_group.addButton(self.rdoIronBlack)
        self.color_group.addButton(self.rdoGrayScale)
        self.color_group.addButton(self.rdoRainbow)
        self.rdoIronBlack.clicked.connect(self.to_ironblack)
        self.rdoGrayScale.clicked.connect(self.to_grayscale)
        self.rdoRainbow.clicked.connect(self.to_rainbow)
        self.rdoIronBlack.setChecked(True)

        self.tempScaleBut.clicked.connect(self.colorBarDisplay)

        validator = QIntValidator(self)
        self.startEdit.setValidator(validator)
        self.stopEdit.setValidator(validator)
        self.startEdit.textEdited.connect(self.renew_start_frame)
        self.stopEdit.textEdited.connect(self.renew_stop_frame)
        self.timer = QTimer(self)
        self.timer.setInterval(timerHz)
        self.timer.timeout.connect(self.playVid5)
        self.timer.start()

        if (len(sys.argv) > 1):
            self.getFile()

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

    def save_png(self):
        saveframe = self.h5data.frame(current_frame, 640, 480)
        save_as.to_png('test.png', saveframe, colorMapType)

    def save_tiffs(self):
        save_as.to_tiffs('test.tif', self.h5data, colorMapType,
                         start_frame, stop_frame)

    def save_avi(self):
        save_as.to_avi('test.avi', self.h5data,
                       colorMapType, start_frame, stop_frame)

    def to_ironblack(self):
        global colorMapType
        colorMapType = 'ironblack'
        self.dispNextImg()
        self.dispPrevImg()
        self.history.insertPlainText('Changed Color Map\n')
        self.history.moveCursor(QTextCursor.End)

    def to_rainbow(self):
        global colorMapType
        colorMapType = 'rainbow'
        self.dispNextImg()
        self.dispPrevImg()
        self.history.insertPlainText('Changed Color Map\n')
        self.history.moveCursor(QTextCursor.End)

    def to_grayscale(self):
        global colorMapType
        colorMapType = 'grayscale'
        self.dispNextImg()
        self.dispPrevImg()
        self.history.insertPlainText('Changed Color Map\n')
        self.history.moveCursor(QTextCursor.End)

    def in_Celsius(self):
        global toggleUnitState
        toggleUnitState = 'C'
        self.dispImg()
        self.history.insertPlainText('Display ' + str(toggleUnitState) + '\n')
        self.history.moveCursor(QTextCursor.End)

    def in_fahrenheit(self):
        global toggleUnitState
        toggleUnitState = 'F'
        self.dispImg()
        self.history.insertPlainText('Display ' + str(toggleUnitState) + '\n')
        self.history.moveCursor(QTextCursor.End)

    def in_Kelvin(self):
        global toggleUnitState
        toggleUnitState = 'K'
        self.dispImg()
        self.history.insertPlainText('Display ' + str(toggleUnitState) + '\n')
        self.history.moveCursor(QTextCursor.End)

    def slValueChange(self):
        global current_frame
        current_frame = self.sl.value()
        self.dispImg()
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

    def grabTempValue(self, xMouse, yMouse):
        data = self.h5data.frame(current_frame, 640, 480)
        return data[yMouse, xMouse]

    def hover(self, event):
        if event.xdata != None:
            xMouse = int(round(event.xdata))
            yMouse = int(round(event.ydata))
            cursorVal = int(round(self.grabTempValue(xMouse, yMouse)))
            self.cursorTempLabel.setText(
                'Cursor Temp: ' + get_temp_with_unit(cursorVal, toggleUnitState))
        else:
            self.cursorTempLabel.setText('Cursor Temp: MOVE CURSOR OVER IMAGE')

    def grabDataFrame(self):
        data = self.h5data.frame(current_frame, 640, 480)
        img = colors.colorize(data, colorMapType)
        img2 = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        rgbImage = cv2.cvtColor(img2, cv2.COLOR_BGR2RGB)
        return(rgbImage)

    def frame_setting_ng(self):
        if(1 <= start_frame and start_frame <= last_frame
            and start_frame <= stop_frame
                and stop_frame <= last_frame):
            return False
        else:
            print('Frame setting is wrong')
            self.history.insertPlainText('Frame setting is wrong\n')
            return True

    def play(self):
        if(self.frame_setting_ng()):
            return
        global current_frame
        global videoState
        self.history.insertPlainText('Play Video\n')
        self.history.moveCursor(QTextCursor.End)
        current_frame = start_frame
        print('Starting at Frame: ' + str(start_frame))
        if fileSelected != "":
            self.timer.start()
            videoState = 'play'

    def pauseVideo(self):
        self.history.insertPlainText('Paused Video\n')
        self.history.moveCursor(QTextCursor.End)
        self.set_pause()

    def playVid5(self):

        if videoState == 'play':
            self.move_frame(1)

    def dispNextImg(self):
        self.history.insertPlainText(
            'Next Frame: ' + str(current_frame) + '\n')
        self.history.moveCursor(QTextCursor.End)
        if fileSelected != "":
            self.move_frame(1)

    def set_pause(self):
        global videoState
        videoState = 'pause'

    def move_frame(self, val):
        global current_frame
        frame_to_stop = min(stop_frame, last_frame)
        if ((val < 0 and current_frame > 1)
                or(val > 0 and current_frame < frame_to_stop)):
            current_frame += val
            self.sl.setValue(current_frame)
            self.dispImg()
        else:
            self.set_pause()

    def dispPrevImg(self):
        self.history.insertPlainText(
            'Previous Frame: ' + str(current_frame) + '\n')
        self.history.moveCursor(QTextCursor.End)
        self.set_pause()
        if fileSelected != "":
            self.move_frame(-1)

    def dispImg(self):
        global last_frame
        self.currentFrameDisp.setText('Current Frame: ' + str(current_frame))
        data = self.h5data.frame(current_frame, 640, 480)

        minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(data)
        self.maxTempLabel.setText(
            'Current Max Temp: ' + get_temp_with_unit(maxVal, toggleUnitState))
        self.maxTempLocLabel.setText('Max Temp Loc: ' + str(maxLoc))
        self.minTempLabel.setText(
            'Current Min Temp: ' + get_temp_with_unit(minVal, toggleUnitState))
        self.minTempLocLabel.setText('Min Temp Loc: ' + str(minLoc))

        img = colors.colorize(data, colorMapType)
        rgbImage = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.ax = self.figure.add_subplot(111)
        self.ax.clear()

        if current_frame == 1:
            self.figure.tight_layout()
        self.cax = self.ax.imshow(rgbImage)
        last_frame = self.h5data.last_frame
        self.sl.setValue(current_frame)
        self.currentTimeLabel.setText(
            'Current Time: ' + str(round(((current_frame-1)/9.00), 2)))
        cid = self.canvas.mpl_connect('motion_notify_event', self.hover)

    def colorBarDisplay(self):
        if(fileSelected == ''):
            return
        rgbImage = self.grabDataFrame()
        rgbImage = cv2.cvtColor(rgbImage, cv2.COLOR_BGR2RGB)
        C = colors.get_color_map(colorMapType)
        C = np.squeeze(C)
        C = C[..., ::-1]
        C2 = C/255.0
        ccm = ListedColormap(C2)
        fig = plt.figure()
        plt.title('Frame: ' + str(current_frame) + '   Max Temp: ' +
                  get_temp_with_unit(toggleUnitState, 'max'))
        bounds = [0, 50, 100]
        im = plt.imshow(rgbImage, cmap=ccm, clim=(calc_temp(
            toggleUnitState, 'min'), calc_temp(toggleUnitState, 'max')))
        cbar = fig.colorbar(im)
        cbar.ax.minorticks_on()
        limits = cbar.get_clim()
        cbar.set_label(
            '     [$^\circ$' + toggleUnitState + ']', rotation=0)  # 270
        plt.show()

    def getFile(self):
        global current_frame
        global fileSelected
        global stop_frame
        global usedOnce
        if (len(sys.argv) > 1) and (usedOnce == 1):
            print("First file specified from command line")
            fileSelected = sys.argv[1]
            usedOnce = 0
        else:
            lastFileSelected = ""
            if fileSelected != "":
                lastFileSelected = fileSelected
            fileSelected = ""
            dlg = QFileDialog()
            dlg.setDefaultSuffix('.HDF5')
            fileSelected, filter = dlg.getOpenFileName(
                self, 'Open File', lastFileSelected, 'HDF5 (*.HDF5);; All Files (*)')
            print(fileSelected)
            self.dispSelectedFile.setText(fileSelected)
        if fileSelected != "":
            try:
                self.dispSelectedFile.setText(fileSelected)
                # self.h5data = h5py.File(str(fileSelected), 'r')
                self.h5data = heat_data(fileSelected)
                current_frame = 1
                self.dispImg()
                self.setSlider()
                stop_frame = last_frame
                self.startEdit.setText(str(current_frame))
                self.stopEdit.setText(str(last_frame))
                self.history.insertPlainText(
                    'Selected File and Displayed First Frame\n')
                self.history.moveCursor(QTextCursor.End)
                print('Selected File and Displayed First Frame')
                self.canvas.draw()
            except:
                self.history.insertPlainText(
                    'ERROR: Incorrect File Type Selected\n Please select .HDF5 File\n')
                self.history.moveCursor(QTextCursor.End)
                print('Incorrect File Type Selected. Please select .HDF5 File.')
        else:
            self.history.insertPlainText(
                'ERROR: Incorrect File Type Selected\n Please select .HDF5 File\n')
            self.history.moveCursor(QTextCursor.End)
            print('Incorrect File Type Selected. Please select .HDF5 File.')


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main = Window()
    main.show()
    sys.exit(app.exec_())
