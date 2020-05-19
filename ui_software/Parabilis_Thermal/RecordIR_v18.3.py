#!/usr/bin/env python3
# Author: Karl Parks, 2018

from subprocess import call
import threading
from multiprocessing import Queue
from uvctypesParabilis_v2 import *
import psutil
import time
import h5py
import numpy as np
from tifffile import imsave
import cv2
import os.path
import sys
from PyQt5.QtWidgets import (QWidget, QMainWindow, QApplication, QLabel, QPushButton, QVBoxLayout,
                             QGridLayout, QSizePolicy, QMessageBox, QFileDialog, QSlider, QComboBox, QProgressDialog)
from PyQt5.QtGui import (QImage, QPixmap, QTextCursor)
from PyQt5.QtCore import (QCoreApplication, QThread,
                          QThreadPool, pyqtSignal, pyqtSlot, Qt, QTimer, QDateTime)
from PyQt5 import QtCore, QtGui, uic
import colors

print('Successful import of uic')  # often reinstallation of PyQt5 is required
print('Loaded Packages and Starting IR Data...')

postScriptFileName = "PostProcessIR_v11.py"

qtCreatorFile = join(dirname(__file__), "ir_v11.ui")  # Enter file here.
Ui_MainWindow, QtBaseClass = uic.loadUiType(qtCreatorFile)

BUF_SIZE = 2
q = Queue(BUF_SIZE)
colorMapType = 'ironblack'


def py_frame_callback(frame, userptr):
    array_pointer = cast(frame.contents.data, POINTER(
        c_uint16 * (frame.contents.width * frame.contents.height)))
    data = np.frombuffer(
        array_pointer.contents, dtype=np.dtype(np.uint16)).reshape(frame.contents.height, frame.contents.width)
    if frame.contents.data_bytes != (2 * frame.contents.width * frame.contents.height):
        return
    if not q.full():
        q.put(data)


PTR_PY_FRAME_CALLBACK = CFUNCTYPE(
    None, POINTER(uvc_frame), c_void_p)(py_frame_callback)


def startStream():
    global devh
    ctx = POINTER(uvc_context)()
    dev = POINTER(uvc_device)()
    devh = POINTER(uvc_device_handle)()
    ctrl = uvc_stream_ctrl()

    res = libuvc.uvc_init(byref(ctx), 0)
    if res < 0:
        print("uvc_init error")

    try:
        res = libuvc.uvc_find_device(
            ctx, byref(dev), PT_USB_VID, PT_USB_PID, 0)
        if res < 0:
            print("uvc_find_device error")
            exit(1)

        try:
            res = libuvc.uvc_open(dev, byref(devh))
            if res < 0:
                print("uvc_open error")
                exit(1)

            print("device opened!")

            print_device_info(devh)
            print_device_formats(devh)

            frame_formats = uvc_get_frame_formats_by_guid(
                devh, VS_FMT_GUID_Y16)
            if len(frame_formats) == 0:
                print("device does not support Y16")
                exit(1)

            libuvc.uvc_get_stream_ctrl_format_size(devh, byref(ctrl), UVC_FRAME_FORMAT_Y16,
                                                   frame_formats[0].wWidth, frame_formats[0].wHeight, int(
                                                       1e7 / frame_formats[0].dwDefaultFrameInterval)
                                                   )

            res = libuvc.uvc_start_streaming(
                devh, byref(ctrl), PTR_PY_FRAME_CALLBACK, None, 0)
            if res < 0:
                print("uvc_start_streaming failed: {0}".format(res))
                exit(1)

            print("done starting stream, displaying settings")
            print_shutter_info(devh)
            print("resetting settings to default")
            set_auto_ffc(devh)
            set_gain_high(devh)
            print("current settings")
            print_shutter_info(devh)

        except:
            print('Failed to Open Device')
    except:
        print('Failed to Find Device')
        exit(1)


toggleUnitState = 'F'


def ktof(val):
    return round(((1.8 * ktoc(val) + 32.0)), 2)


def ktoc(val):
    return round(((val - 27315) / 100.0), 2)


def display_temperatureK(img, val_k, loc, color):
    val = ktof(val_k)
    cv2.putText(img, "{0:.1f} degF".format(val), loc,
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
    x, y = loc
    cv2.line(img, (x - 2, y), (x + 2, y), color, 1)
    cv2.line(img, (x, y - 2), (x, y + 2), color, 1)


def display_temperatureC(img, val_k, loc, color):
    val = ktof(val_c)
    cv2.putText(img, "{0:.1f} degC".format(val), loc,
                cv2.FONT_HERSHEY_SIMPLEX, 0.75, color, 2)
    x, y = loc
    cv2.line(img, (x - 2, y), (x + 2, y), color, 1)
    cv2.line(img, (x, y - 2), (x, y + 2), color, 1)


camState = 'not_recording'
tiff_frame = 1
maxVal = 0
minVal = 0

fileNum = 1
@pyqtSlot(QImage)
def startRec():
    global camState
    if camState == 'recording':
        print('Alredy Recording')
    else:
        file_nameH = str(
            ('Lepton HDF5 Vid ' + QDateTime.currentDateTime().toString()))
        file_nameH = file_nameH.replace(" ", "_")
        file_nameH = str(file_nameH.replace(":", "-"))
    try:
        filePathAndName = str(saveFilePath + '/' + file_nameH)
        startRec.hdf5_file = h5py.File(filePathAndName, mode='w')
        camState = 'recording'
        print('Started Recording')
    except:
        print('Incorrect File Path')
        camState = 'not_recording'
        print('Did Not Begin Recording')


def getFrame():
    global tiff_frame
    global maxVal
    global minVal
    data = q.get(True, 500)
    if data is None:
        print('No Data')
    if camState == 'recording':
        startRec.hdf5_file.create_dataset(('image'+str(tiff_frame)), data=data)
        tiff_frame += 1
    minVal, maxVal, minLoc, maxLoc = cv2.minMaxLoc(data)
    img = colors.colorize(data, colorMapType)
    return img


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


def readTemp(unit, state):
    if state == 'max':
        if unit == 'F':
            return (str(ktof(maxVal)) + ' ' + unit)
        elif unit == 'C':
            return (str(ktoc(maxVal)) + ' ' + unit)
        else:
            print('What are you asking for?')
    elif state == 'min':
        if unit == 'F':
            return (str(ktof(minVal)) + ' ' + unit)
        elif unit == 'C':
            return (str(ktoc(minVal)) + ' ' + unit)
        else:
            print('What are you asking for?')
    elif state == 'none':
        if unit == 'F':
            return (str(ktof(cursorVal)) + ' ' + unit)
        elif unit == 'C':
            return (str(ktoc(cursorVal)) + ' ' + unit)
        else:
            print('What are you asking for?')
    else:
        print('What are you asking for?')


def updateMaxTempLabel():
    if toggleUnitState == 'F':
        return ktof(maxVal)
    elif toggleUnitState == 'C':
        return ktoc(maxVal)
    else:
        print('No Units Selected')


class MyThread(QThread):
    changePixmap = pyqtSignal(QImage)

    def run(self):
        print('Start Stream')
        while True:
            frame = getFrame()
            rgbImage = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            convertToQtFormat = QImage(
                rgbImage.data, rgbImage.shape[1], rgbImage.shape[0], QImage.Format_RGB888)
            p = convertToQtFormat.scaled(640, 480, Qt.KeepAspectRatio)
            self.changePixmap.emit(p)


thread = "unactive"
saveFilePath = ""
fileNamingFull = ""
bFile = ""


class App(QMainWindow, Ui_MainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        Ui_MainWindow.__init__(self)
        self.setupUi(self)
        self.initUI()
        print('Always Run This Script as ADMIN')

    @pyqtSlot(QImage)
    def setImage(self, image):
        self.displayFrame.setPixmap(QPixmap.fromImage(image))

    def initUI(self):
        global fileNamingFull
        self.startRec.clicked.connect(self.start_stop)
        self.stopRec.clicked.connect(self.stopRecAndSave)
        self.stopRec.clicked.connect(self.displayNotRec)
        self.displayC.clicked.connect(self.dispCDef)
        self.displayF.clicked.connect(self.dispFDef)
        self.runPost.clicked.connect(self.runPostScript)
        self.startStreamBut.clicked.connect(self.startThread)
        self.displayFrame.mousePressEvent = self.on_press

        self.w = QWidget()
        self.filePathBut.clicked.connect(self.getFiles)

        # time display
        self.timer = QTimer(self)
        self.timerFast = QTimer(self)
        self.timer.setInterval(1000)
        self.timerFast.setInterval(10)
        self.timer.timeout.connect(self.displayTime)
        self.timer.timeout.connect(self.displayStorage)
        self.timerFast.timeout.connect(self.displayTempValues)
        self.timer.start()
        self.timerFast.start()

        defaultName = 'IR_HDF5'
        fileNamingFull = defaultName
        self.lineEdit.setText(defaultName)
        self.lineEdit.textChanged.connect(self.fileNaming)
        self.ffcBut.clicked.connect(self.ffcFunction)
        self.comboGain.currentTextChanged.connect(self.gainFunction)
        self.comboFFCmode.currentTextChanged.connect(self.FFCmodeFunction)

        self.cmIronBut.clicked.connect(self.cmIronFunc)
        self.cmGrayBut.clicked.connect(self.cmGrayFunc)
        self.cmRainBut.clicked.connect(self.cmRainFunc)
        self.printShutterBut.clicked.connect(self.printShutterInfoFunc)

        #self.connect(self, SIGNAL('triggered()'), self.closeEvent)
    def printShutterInfoFunc(self):
        global devh
        if thread == 'active':
            print_shutter_info(devh)

    def cmIronFunc(self):
        global colorMapType
        colorMapType = "ironblack"
        self.history.insertPlainText('Changed Color Map\n')
        self.history.moveCursor(QTextCursor.End)

    def cmRainFunc(self):
        global colorMapType
        colorMapType = "rainbow"
        self.history.insertPlainText('Changed Color Map\n')
        self.history.moveCursor(QTextCursor.End)

    def cmGrayFunc(self):
        global colorMapType
        colorMapType = "grayscale"
        self.history.insertPlainText('Changed Color Map\n')
        self.history.moveCursor(QTextCursor.End)

    def gainFunction(self):
        global devh
        global thread
        if thread == 'active':
            if (self.comboGain.currentText() == 'LOW'):
                set_gain_low(devh)
            elif (self.comboGain.currentText() == 'HIGH'):
                set_gain_high(devh)
                #print('Cannot set to back to HIGH yet')
            else:
                set_gain_auto(devh)
                #print('Cannot set to AUTO')

    def FFCmodeFunction(self):
        global devh
        global thread
        if thread == 'active':
            if (self.comboFFCmode.currentText() == 'MANUAL'):
                set_manual_ffc(devh)
            elif (self.comboFFCmode.currentText() == 'EXTERNAL'):
                set_external_ffc(devh)
            else:
                set_auto_ffc(devh)
                #print('Cannot set to back to AUTO yet. Unplug USB from Raspberry Pi to reset lepton.')
        print_shutter_info(devh)

    def ffcFunction(self):
        global devh
        global thread
        if thread == 'active':
            perform_manual_ffc(devh)

    def start_stop(self):
        if camState == 'not_recording':
            self.startRec2()
            self.displayRec()
        else:  # camState == 'recording'
            self.stopRecAndSave()
            self.displayNotRec()
        return

    def startRec2(self):
        global thread
        global camState
        global saveFilePath
        global fileNamingFull
        if thread == 'active':
            if camState == 'recording':
                print('Already Recording')
            else:
                if fileNamingFull != "":
                    dateAndTime = str(QDateTime.currentDateTime().toString())
                    dateAndTime = dateAndTime.replace(" ", "_")
                    dateAndTime = dateAndTime.replace(":", "-")
                    filePathAndName = str(
                        fileNamingFull + '_' + dateAndTime + '.HDF5')
                    print(filePathAndName)
                    self.filePathDisp.setText(filePathAndName)
                    try:
                        startRec.hdf5_file = h5py.File(
                            filePathAndName, mode='w')
                        camState = 'recording'
                        print('Started Recording')
                        if saveFilePath == "":
                            self.history.insertPlainText(
                                'Saved ' + str(filePathAndName) + ' to ' + os.path.dirname(os.path.abspath(__file__)) + '\n')
                            self.history.moveCursor(QTextCursor.End)
                        else:
                            self.history.insertPlainText(
                                'Saved to ' + str(filePathAndName) + '\n')
                            self.history.moveCursor(QTextCursor.End)
                    except:
                        print('Incorrect File Path')
                        camState = 'not_recording'
                        print('Did Not Begin Recording')
                else:
                    print('No FileName Specified')
        else:
            print('Remember to Start Stream')
            self.history.insertPlainText('Remember to Start Stream\n')
            self.history.moveCursor(QTextCursor.End)

    def stopRecAndSave(self):
        global fileNum
        global tiff_frame
        global camState
        global dataCollection
        if tiff_frame > 1:
            print('Ended Recording')
            camState = 'not_recording'
            try:
                startRec.hdf5_file.close()
                print('Saved Content to File Directory')
                #fileNum += 1
            except:
                print('Save Failed')
            tiff_frame = 1
        else:
            camState = 'not_recording'
            print('Dont Forget to Start Recording')
            self.history.insertPlainText('Dont Forget to Start Recording\n')
            self.history.moveCursor(QTextCursor.End)

    def fileNaming(self):
        global fileNamingFull
        bFile = str(self.lineEdit.text())
        if saveFilePath == "":
            fileNamingFull = bFile
            self.filePathDisp.setText(
                '/' + bFile + ' ... Date & Time Will Append at Recording Start')
        elif saveFilePath != "":
            fileNamingFull = saveFilePath + '/' + bFile
            self.filePathDisp.setText(
                saveFilePath + '/' + bFile + ' ... Date & Time Will Append at Recording Start')
        else:
            print('I am Confused')

    def startThread(self):
        global thread
        try:
            if thread == "unactive":
                try:
                    startStream()
                    self.th = MyThread()
                    self.th.changePixmap.connect(self.setImage)
                    self.th.start()
                    thread = "active"
                    print('Starting Thread')
                except:
                    print('Failed!!!!')
                    exit(1)
            else:
                print('Already Started Camera')
        except:
            msgBox = QMessageBox()
            reply = msgBox.question(
                self, 'Message', "Error Starting Camera - Plug or Re-Plug Camera into Computer, Wait at Least 10 Seconds, then Click Ok and Try Again.", QMessageBox.Ok)
            print('Message Box Displayed')
            if reply == QMessageBox.Ok:
                print('Ok Clicked')
            else:
                event.ignore()

    def runPostScript(self):
        try:
            def thread_second():
                call(["python3", postScriptFileName])
            processThread = threading.Thread(
                target=thread_second)  # <- note extra ','
            processThread.start()
        except:
            print(
                'Post Processing Script Error - Most Likely Referencing Incorrect File Name')

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

    def displayTempValues(self):
        #global fileSelected
        global toggleUnitState
        # if fileSelected != "":
        self.maxTempLabel.setText(
            'Current Max Temp: ' + readTemp(toggleUnitState, 'max'))
        #self.maxTempLocLabel.setText('Max Temp Loc: ' + str(maxLoc))
        self.minTempLabel.setText(
            'Current Min Temp: ' + readTemp(toggleUnitState, 'min'))
        #self.minTempLocLabel.setText('Min Temp Loc: ' + str(minLoc))

    def displayTime(self):
        self.timeStatus.setText(QDateTime.currentDateTime().toString())

    def grabTempValue(self):
        global frame
        global lastFrame
        global fileSelected
        global xMouse
        global yMouse
        global thread
        if thread == 'active':
            data = q.get(True, 500)
            data = cv2.resize(data[:, :], (640, 480))
            return data[yMouse, xMouse]
        else:
            self.history.insertPlainText(
                'ERROR: Please Start IR Camera Feed First\n')
            self.history.moveCursor(QTextCursor.End)

    def on_press(self, event):
        global xMouse
        global yMouse
        global cursorVal
        #print('you pressed', event.button, event.xdata, event.ydata)
        try:
            xMouse = event.pos().x()
            yMouse = event.pos().y()
            cursorVal = self.grabTempValue()
            self.cursorTempLabel.setText(
                'Cursor Temp (On Mouse Click): ' + readTemp(toggleUnitState, 'none'))
        except:
            self.history.insertPlainText(
                'ERROR: Please Start IR Camera Feed First\n')
            self.history.moveCursor(QTextCursor.End)

    def displayStorage(self):
        usage = psutil.disk_usage('/')
        oneMinVid = 20000000
        timeAvail = usage.free/oneMinVid
        self.storageLabel.setText(
            'Recording Time Left: ' + str(round(timeAvail, 2)) + ' Minutes')

    def displayRec(self):
        if camState == 'recording':
            self.recLabel.setText('Recording')
        else:
            self.recLabel.setText('Not Recording')

    def displayNotRec(self):
        if camState == 'not_recording':
            self.recLabel.setText('Not Recording')
        else:
            self.recLabel.setText('Recording')

    def getFiles(self):
        global saveFilePath
        saveFilePath = QFileDialog.getExistingDirectory(
            self.w, 'Open File Directory', '/')
        self.filePathDisp.setText(saveFilePath)
        self.fileNaming()

    def closeEvent(self, event):
        print("Close Event Called")
        if camState == 'recording':
            reply = QMessageBox.question(self, 'Message',
                                         "Recording still in progress. Are you sure you want to quit?", QMessageBox.Yes, QMessageBox.No)
            print('Message Box Displayed')
            if reply == QMessageBox.Yes:
                print('Exited Application, May Have Lost Raw Data')
                event.accept()
            else:
                event.ignore()
        else:
            print('Exited Application')
            event.accept()


def main():
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
