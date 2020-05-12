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
from PyQt5.QtGui import (QImage, QPixmap, QTextCursor)
from PyQt5.QtCore import (QCoreApplication, QThread,
                          QThreadPool, pyqtSignal, pyqtSlot, Qt, QTimer, QDateTime)
from PyQt5.QtWidgets import (QWidget, QMainWindow, QApplication, QLabel, QPushButton, QVBoxLayout,
                             QGridLayout, QSizePolicy, QMessageBox, QFileDialog, QSlider, QComboBox, QProgressDialog)
import sys
print(sys.version)

print('Successful import of uic')  # often reinstallation of PyQt5 is required

print('Successful import of all libraries')

qtCreatorFile = "ir_post_v2.ui"  # Enter file here.

Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile)


colorMapType = "ironblack"  # ironblack, rainbow, grayscale

warnings.filterwarnings("ignore")


toggleUnitState = 'F'

frame = 1
videoState = 'notPlay'
framerate = 1  # (1/9 frames per second), do not adjust
timerHz = 115  # ms 1/8.7 = 0.1149 sec, decrease to increase speed
fileSelected = ""
usedOnce = 1


def cktof(val):
    return round(((1.8 * cktoc(val) + 32.0)), 2)


def cktoc(val):
    return round(((val - 27315) / 100.0), 2)


def cktok(val):
    return round((val / 100.0), 2)


def get_temp_with_unit(unit, state):
    if state == 'max':
        result = maxVal
    elif state == 'min':
        result = minVal
    elif(state == 'none'):
        result = cursorVal
    else:
        display('What are you asking for?')
    result = str(calc_temp(result, unit))
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

        # a figure instance to plot on
        self.figure = Figure()

        # this is the Canvas Widget that displays the `figure`
        # it takes the `figure` instance as a parameter to __init__
        self.canvas = FigureCanvas(self.figure)

        # this is the Navigation widget
        # it takes the Canvas widget and a parent
        self.toolbar = NavigationToolbar(self.canvas, self)

        # set the layout for the main window
        self.dispLayout.addWidget(self.toolbar)
        self.dispLayout.addWidget(self.canvas)

        # buttons
        self.nextFrame.clicked.connect(self.dispNextImg)
        self.prevFrame.clicked.connect(self.dispPrevImg)
        self.selectFileBut.clicked.connect(self.getFile)
        self.playVidBut.clicked.connect(self.play)
        self.makeTiffBut.clicked.connect(self.save_tiffs)
        self.displayC.clicked.connect(self.dispCDef)
        self.displayC.clicked.connect(self.displayTempValues)
        self.displayF.clicked.connect(self.dispFDef)
        self.displayF.clicked.connect(self.displayTempValues)
        self.sl.valueChanged.connect(self.slValueChange)
        self.saveCvImageBut.clicked.connect(self.save_png)
        self.saveAsVideoSS.clicked.connect(self.save_avi)
        self.pauseVidBut.clicked.connect(self.pauseVideo)
        self.cmIronBut.clicked.connect(self.cmIronFunc)
        self.cmGrayBut.clicked.connect(self.cmGrayFunc)
        self.cmRainBut.clicked.connect(self.cmRainFunc)
        self.tempScaleBut.clicked.connect(self.colorBarDisplay)

        self.timer = QTimer(self)
        self.timer.setInterval(timerHz)
        self.timer.timeout.connect(self.playVid5)
        self.timer.start()

        if (len(sys.argv) > 1):
            self.getFile()

    def save_png(self):
        saveframe = self.f_read[('image' + str(frame))][:]
        save_as.to_png('test.png', saveframe, colorMapType)

    def save_tiffs(self):
        save_as.to_tiffs('test.csv', self.f_read, frame, editLastFrame)

    def save_avi(self):
        data = heat_data(fileSelected)
        save_as.to_avi('test.avi', data,
                       colorMapType, frame, editLastFrame)

    def cmIronFunc(self):
        global colorMapType
        colorMapType = 'ironblack'
        self.dispNextImg()
        self.dispPrevImg()
        self.history.insertPlainText('Changed Color Map\n')
        self.history.moveCursor(QTextCursor.End)

    def cmRainFunc(self):
        global colorMapType
        colorMapType = 'rainbow'
        self.dispNextImg()
        self.dispPrevImg()
        self.history.insertPlainText('Changed Color Map\n')
        self.history.moveCursor(QTextCursor.End)

    def cmGrayFunc(self):
        global colorMapType
        colorMapType = 'grayscale'
        self.dispNextImg()
        self.dispPrevImg()
        self.history.insertPlainText('Changed Color Map\n')
        self.history.moveCursor(QTextCursor.End)

    def dispCDef(self):
        global toggleUnitState
        toggleUnitState = 'C'
        self.history.insertPlainText('Display ' + str(toggleUnitState) + '\n')
        self.history.moveCursor(QTextCursor.End)

    def dispFDef(self):
        global toggleUnitState
        toggleUnitState = 'F'
        self.history.insertPlainText('Display ' + str(toggleUnitState) + '\n')
        self.history.moveCursor(QTextCursor.End)

    def slValueChange(self):
        global frame
        frame = self.sl.value()
        self.dispImg()
        self.canvas.draw()

    def setSlider(self):
        self.sl.setEnabled(True)
        self.sl.setMinimum(1)
        self.sl.setMaximum(lastFrame)
        self.sl.setValue(1)
        self.sl.setTickPosition(QSlider.TicksBelow)
        self.sl.setTickInterval(9)
        self.slStartF.setText('First Frame: 1')
        self.slMidF.setText('Mid Frame: ' + str(round(lastFrame/2)))
        self.slEndF.setText('Last Frame: ' + str(lastFrame))
        self.slStartT.setText('0 Seconds')
        self.slMidT.setText(str(round(lastFrame/(2*9), 1)) + ' Seconds')
        self.slEndT.setText(str(round(lastFrame/9, 1)) + ' Seconds')

    def grabTempValue(self):
        data = self.f_read[('image'+str(frame))][:]
        data = cv2.resize(data[:, :], (640, 480))
        return data[yMouse, xMouse]

    def on_press(self, event):
        global xMouse
        global yMouse
        global cursorVal
        xMouse = event.xdata
        yMouse = event.ydata
        cursorVal = self.grabTempValue()
        self.cursorTempLabel.setText(
            'Cursor Temp: ' + get_temp_with_unit(toggleUnitState, 'none'))

    def hover(self, event):
        global xMouse
        global yMouse
        global cursorVal
        if event.xdata != None:
            xMouse = int(round(event.xdata))
            yMouse = int(round(event.ydata))
            cursorVal = int(round(self.grabTempValue()))
            self.cursorTempLabel.setText(
                'Cursor Temp: ' + get_temp_with_unit(toggleUnitState, 'none'))
        else:
            self.cursorTempLabel.setText('Cursor Temp: MOVE CURSOR OVER IMAGE')

    def displayTempValues(self):
        if fileSelected != "":
            self.maxTempLabel.setText(
                'Current Max Temp: ' + get_temp_with_unit(toggleUnitState, 'max'))
            self.maxTempLocLabel.setText('Max Temp Loc: ' + str(maxLoc))
            self.minTempLabel.setText(
                'Current Min Temp: ' + get_temp_with_unit(toggleUnitState, 'min'))
            self.minTempLocLabel.setText('Min Temp Loc: ' + str(minLoc))

    def grabDataFrame(self):
        data = self.f_read[('image'+str(frame))][:]
        data = cv2.resize(data[:, :], (640, 480))
        img = colors.colorize(data, colorMapType)
        img2 = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        rgbImage = cv2.cvtColor(img2, cv2.COLOR_BGR2RGB)
        return(rgbImage)

    def play(self):
        global frame
        global editLastFrame
        global videoState
        self.history.insertPlainText('Play Video\n')
        self.history.moveCursor(QTextCursor.End)
        if self.startEdit.isModified():
            frame = int(self.startEdit.text())
            print('Starting at Frame: ' + self.startEdit.text())
        if self.stopEdit.isModified():
            editLastFrame = int(self.stopEdit.text())
        if fileSelected != "":
            self.timer.start()
            videoState = 'play'

    def pauseVideo(self):
        global videoState
        self.history.insertPlainText('Paused Video\n')
        self.history.moveCursor(QTextCursor.End)
        videoState = 'pause'

    def playVid5(self):
        global videoState
        global frame
        if videoState == 'play':
            if editLastFrame <= lastFrame:
                if frame <= editLastFrame:
                    self.sl.setValue(frame)
                    if frame != lastFrame:
                        frame += 1
                    #print('playing video')
                else:
                    print('You are at Stop Frame')
                    videoState = 'pause'
            else:
                print('You are at Last Frame')
                videoState = 'pause'

    def dispNextImg(self):
        global frame
        global videoState
        videoState = 'pause'
        self.history.insertPlainText('Next Frame: ' + str(frame) + '\n')
        self.history.moveCursor(QTextCursor.End)
        if fileSelected != "":
            if lastFrame > frame:
                frame += framerate
            else:
                print('You are at Last Frame')
            self.sl.setValue(frame)

    def dispPrevImg(self):
        global frame
        global videoState
        self.history.insertPlainText('Previous Frame: ' + str(frame) + '\n')
        self.history.moveCursor(QTextCursor.End)
        videoState = 'pause'
        if fileSelected != "":
            if frame > 1:
                frame -= 1
            else:
                print('You are at First Frame')
            # self.dispImg()
            # self.canvas.draw()
            self.sl.setValue(frame)

    def dispImg(self):
        global minVal
        global maxVal
        global minLoc
        global maxLoc
        global lastFrame
        self.currentFrameDisp.setText('Current Frame: ' + str(frame))
        data = self.f_read[('image'+str(frame))][:]
        data = cv2.resize(data[:, :], (640, 480))
        minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(data)
        img = colors.colorize(data, colorMapType)
        rgbImage = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        self.ax = self.figure.add_subplot(111)
        self.ax.clear()

        if frame == 1:
            self.figure.tight_layout()
        self.cax = self.ax.imshow(rgbImage)
        lastFrame = len(self.f_read)
        self.sl.setValue(frame)
        self.displayTempValues()
        self.currentTimeLabel.setText(
            'Current Time: ' + str(round(((frame-1)/9.00), 2)))
        cid = self.canvas.mpl_connect('motion_notify_event', self.hover)

    def colorBarDisplay(self):
        rgbImage = self.grabDataFrame()
        rgbImage = cv2.cvtColor(rgbImage, cv2.COLOR_BGR2RGB)
        C = colors.get_color_map(colorMapType)
        C = np.squeeze(C)
        C = C[..., ::-1]
        C2 = C/255.0
        ccm = ListedColormap(C2)
        fig = plt.figure()
        plt.title('Frame: ' + str(frame) + '   Max Temp: ' +
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

    def enableThings(self):
        self.playVidBut.setEnabled(True)
        self.pauseVidBut.setEnabled(True)
        self.nextFrame.setEnabled(True)
        self.prevFrame.setEnabled(True)
        self.startEdit.setEnabled(True)
        self.stopEdit.setEnabled(True)
        self.saveAsVideoSS.setEnabled(True)
        self.saveCvImageBut.setEnabled(True)
        self.makeTiffBut.setEnabled(True)
        self.displayC.setEnabled(True)
        self.displayF.setEnabled(True)
        self.tempScaleBut.setEnabled(True)

    def getFile(self):
        global frame
        global fileSelected
        global editLastFrame
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
                self.f_read = h5py.File(str(fileSelected), 'r')
                frame = 1
                self.dispImg()
                self.enableThings()
                self.setSlider()
                editLastFrame = lastFrame
                self.startEdit.setText(str(frame))
                self.stopEdit.setText(str(lastFrame))
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
