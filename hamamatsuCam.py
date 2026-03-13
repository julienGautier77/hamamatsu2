# -*- coding: utf-8 -*-
#! /home/zita1/loaenv/bin/python3.12

"""
Created on Oct 03 2024

pip install git+https://github.com/julienGautier77/visu
@author: juliengautier
modified 2025/03/21 
"""

import __init__
from PyQt6.QtWidgets import QApplication, QVBoxLayout, QHBoxLayout, QWidget
from PyQt6.QtWidgets import QPushButton, QDockWidget, QMenu, QLayout
from PyQt6.QtWidgets import QComboBox, QSlider, QLabel, QSpinBox, QProgressBar
from PyQt6.QtWidgets import QDoubleSpinBox, QGridLayout, QToolButton
from PyQt6.QtWidgets import QMessageBox
from PyQt6.QtWidgets import QInputDialog
from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
import sys
import time
import numpy as np
import pathlib
import os
import pyqtgraph as pg
import dcam
import qdarkstyle

__version__ = __init__.__version__
__author__ = __init__.__author__
version = __version__


class HAMAMATSU(QWidget):
    
    signalData = QtCore.pyqtSignal(object)  # signal emited when receive image
    updateBar_signal = QtCore.pyqtSignal(object)  # signal for update progressbar

    def __init__(self, cam=None, confFile='conf.ini', **kwds):
        
        super(HAMAMATSU, self).__init__()

        self.progressWin = ProgressScreen(parent=self)
        self.progressWin.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.WindowStaysOnTopHint)
        self.progressWin.show()
        
        p = pathlib.Path(__file__)
        sepa = os.sep
        self.kwds = kwds
        self.isConnected = False
        self.icon = str(p.parent) + sepa + 'icons'+ sepa

        if "confpath" in kwds:
            self.confpath = kwds["confpath"]
        else:
            self.confpath = None
        
        if self.confpath is None:
            self.confpath = str(p.parent / confFile)  # ini file with global path
        
        self.conf = QtCore.QSettings(self.confpath, QtCore.QSettings.Format.IniFormat)  # ini file 
        self.kwds["confpath"] = self.confpath
        
        self.configMotorPath = "./fichiersConfig/"
        self.configMotName = 'configMoteurRSAI.ini'
        self.confMotorPath = self.configMotorPath+self.configMotName
       
        self.confMot = QtCore.QSettings(str(p.parent / self.confMotorPath), QtCore.QSettings.Format.IniFormat)
        self.kwds["conf"] = self.conf
        # self.kwds["confMot"]=self.confMot # add motor rsai position in visu
        
        if "affLight" in kwds:
            self.light = kwds["affLight"]
        else:
            self.light = False
        if "multi" in kwds:
            self.multi = kwds["multi"]
        else:
            self.multi = False
        
        if "separate" in kwds:
            self.separate = kwds["separate"]
        else: 
            self.separate = False
            
        if "aff" in kwds:  # affi of Visu
            self.aff = kwds["aff"]
        else: 
            self.aff = "right"
            
        self.setWindowIcon(QIcon(self.icon+'LOA.png'))
        self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6')) # qdarkstyle :  black windows style
        self.iconPlay = self.icon+'Play.png'
        self.iconSnap = self.icon+'Snap.png'
        self.iconStop = self.icon+'Stop.png'
        self.iconPlay = pathlib.Path(self.iconPlay)
        self.iconPlay = pathlib.PurePosixPath(self.iconPlay)
        self.iconStop = pathlib.Path(self.iconStop)
        self.iconStop = pathlib.PurePosixPath(self.iconStop)
        self.iconSnap = pathlib.Path(self.iconSnap)
        self.iconSnap = pathlib.PurePosixPath(self.iconSnap)
        self.nbShot = 1
        
        if cam is None:  # si None on prend la première...
            self.nbcam = 'camDefault'
        else:
            self.nbcam = cam

        self.ccdName = self.conf.value(self.nbcam+"/nameCDD")
        self.camID = self.conf.value(self.nbcam+"/camId")
        print('cam id to open', self.camID, self.nbcam)

        text = 'Connect to Camera name  : ' + self.nbcam + ' ...'
        self.updateBar_signal.emit([text, 25])
        
        text = 'Set Camera Parameters  ......'
        self.updateBar_signal.emit([text, 50])
        self.setup()
        text = 'widget loading  ' + self.nbcam + ' ...'
        self.updateBar_signal.emit([text, 60])
        self.initCam()
        
        text = 'Initializing camera...'
        self.updateBar_signal.emit([text, 70])
        
        
        self.itrig = 0
        self.actionButton()
        self.camIsRunnig = False
        self.updateBar_signal.emit(['Ready!', 100])
        QtCore.QTimer.singleShot(300, self.progressWin.close)
    
    def initCam(self):

        initOK = dcam.Dcamapi.init()
        if initOK:
            idevice = 0  # device number
            n = dcam.Dcamapi.get_devicecount()
            for i in range(0, n):
                cam = dcam.Dcam(i)
                cameraid = cam.dev_getstring(dcam.DCAM_IDSTR.CAMERAID)
                cameraid = ''.join([car for car in cameraid if car.isdigit()])  # remove S/N
                if self.camID == cameraid:
                    idevice = i
            
            self.cam = dcam.Dcam(idevice)
            self.camOpened = self.cam.dev_open()
            if self.camOpened:
                self.model = self.cam.dev_getstring(dcam.DCAM_IDSTR.MODEL)
                id = self.cam.dev_getstring(dcam.DCAM_IDSTR.CAMERAID)
                # print('model', self.model, id)
                if self.cam.prop_getvalue(dcam.DCAM_IDPROP.SUBARRAYMODE) != 1: # full frame
                    self.cam.prop_setvalue(dcam.DCAM_IDPROP.SUBARRAYMODE, 1)

                self.cam.prop_setvalue(dcam.DCAM_IDPROP.TRIGGER_MODE, 1)
                self.cam.prop_setvalue(dcam.DCAM_IDPROP.TRIGGERACTIVE, 1)  # Normal
                self.cam.prop_setvalue(dcam.DCAM_IDPROP.TRIGGERPOLARITY, 2)  # Rising edge
                self.cam.prop_setvalue(dcam.DCAM_IDPROP.TRIGGERSOURCE, 1) # Internal Camera use its own timing
                self.cam.prop_setvalue(dcam.DCAM_IDPROP.EXPOSURETIME, 0.001*int(self.conf.value(self.nbcam+"/shutter")) )# set cam to  ms
                print(f'trig gobalbexp value {self.cam.prop_getvalue(dcam.DCAM_IDPROP.TRIGGER_GLOBALEXPOSURE)}')
                self.cam.prop_setvalue(dcam.DCAM_IDPROP.TRIGGER_GLOBALEXPOSURE,5)
                print(f'trig gobalbexp value {self.cam.prop_getvalue(dcam.DCAM_IDPROP.TRIGGER_GLOBALEXPOSURE)}')
                self.itrig = 0
                self.sh = int(1000*self.cam.prop_getvalue(dcam.DCAM_IDPROP.EXPOSURETIME))
                min_exp_time = int(1000*self.cam.prop_getattr(dcam.DCAM_IDPROP.EXPOSURETIME).valuemin)
                max_exp_time = int(1000*self.cam.prop_getattr(dcam.DCAM_IDPROP.EXPOSURETIME).valuemax)
            
                self.isConnected = True
               
        if self.isConnected is True:
            
            # start temperature thread : 
            self.threadTemp = ThreadTemperature(cam=self.cam)
            self.threadTemp.TEMP.connect(self.update_temp)
            self.threadTemp.stopTemp = False
            self.threadTemp.start()
            
            self.hSliderShutter.setMinimum(min_exp_time)
            self.shutterBox.setMinimum(min_exp_time)
            self.hSliderShutter.setMaximum(1500)  # or max_exp_time but too long
            self.shutterBox.setMaximum(1500)  # or max_exp_time but too long
            self.hSliderShutter.setValue(self.sh)
            self.shutterBox.setValue(self.sh)
            self.tempWidget = TEMPWIDGET(self)
            
            self.settingWidget = SETTINGWIDGET(cam=self.cam, conf=self.conf,
                                               nbcam=self.nbcam,
                                               visualisation=self.visualisation)
            
            
            
            self.setWindowTitle(self.ccdName + ' v. ' + str(version)+'  ' +
                                self.model + ' Visu v.'+
                                self.visualisation.version)
            
        else:
            self.runButton.setEnabled(False)
            self.runButton.setStyleSheet("QPushButton:!pressed{border-image: url(%s);background-color: gray ;border-color: rgb(0, 0, 0,0);}""QPushButton:pressed{image: url(%s);background-color: gray ;border-color: rgb(0, 0, 0)}"%(self.iconPlay,self.iconPlay))
            self.stopButton.setEnabled(False)
            self.stopButton.setStyleSheet("QPushButton:!pressed{border-image: url(%s);background-color: gray ;border-color: rgb(0, 0, 0,0);}""QPushButton:pressed{image: url(%s);background-color: gray ;border-color: rgb(0, 0, 0)}"%(self.iconStop,self.iconStop) )
            self.trigg.setEnabled(False)
            self.hSliderShutter.setEnabled(False)
            self.shutterBox.setEnabled(False)  
            self.setWindowTitle('No camera Connected')
            
    def update_temp(self, temp=None):
        if temp is None:
            temp = self.cam.prop_getvalue(dcam.DCAM_IDPROP.SENSORTEMPERATURE)
        # print('temp',temp)
        self.tempBox.setText('%.1f °C' % temp)
         
    def setup(self):
        """ user interface definition: 
        """
        vbox1 = QVBoxLayout() # 
        hbox1 = QHBoxLayout() # horizontal layout pour run snap stop
        self.sizebuttonMax = 30
        self.sizebuttonMin = 30

        self.runButton = QToolButton(self)
        self.runButton.setMaximumWidth(self.sizebuttonMax)
        self.runButton.setMinimumWidth(self.sizebuttonMax)
        self.runButton.setMaximumHeight(self.sizebuttonMax)
        self.runButton.setMinimumHeight(self.sizebuttonMax)
        self.runButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: transparent ;border-color: green;}""QToolButton:pressed{border-image: url(%s);background-color: gray ;border-color: gray}"% (self.iconPlay,self.iconPlay) )
        
        self.snapButton = QToolButton(self)
        self.snapButton.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        menu = QMenu()
        menu.addAction('set nb of shot', self.nbShotAction)
        self.snapButton.setMenu(menu)
        self.snapButton.setMaximumWidth(self.sizebuttonMax)
        self.snapButton.setMinimumWidth(self.sizebuttonMax)
        self.snapButton.setMaximumHeight(self.sizebuttonMax)
        self.snapButton.setMinimumHeight(self.sizebuttonMax)
        self.snapButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: transparent ;border-color: green;}""QToolButton:pressed{border-image: url(%s);background-color: gray ;border-color: gray}"% (self.iconSnap,self.iconSnap) )
        
        self.stopButton = QToolButton(self)
        self.stopButton.setMaximumWidth(self.sizebuttonMax)
        self.stopButton.setMinimumWidth(self.sizebuttonMax)
        self.stopButton.setMaximumHeight(self.sizebuttonMax)
        self.stopButton.setMinimumHeight(self.sizebuttonMax)
        self.stopButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: gray ;border-color: gray;}""QToolButton:pressed{border-image: url(%s);background-color: gray ;border-color: gray}"% (self.iconStop,self.iconStop) )
        self.stopButton.setEnabled(False)
        
        hbox1.addWidget(self.runButton)
        hbox1.addWidget(self.snapButton)
        hbox1.addWidget(self.stopButton)
        
        hbox1.setSizeConstraint(QLayout.SizeConstraint.SetMaximumSize)  # setFixedSize)#
        hbox1.setContentsMargins(0, 0, 0, 0)
        hbox1.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        vbox1.addLayout(hbox1)
        vbox1.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        vbox1.setContentsMargins(0, 20, 10, 10)
        
        self.widgetControl = QWidget(self)
        self.widgetControl.setLayout(vbox1)
        self.dockControl = QDockWidget(self)
        self.dockControl.setWidget(self.widgetControl)
        
        self.trigg = QComboBox()
        self.trigg.setMaximumWidth(90)
        self.trigg.addItem('OFF')
        self.trigg.addItem('ON')
        self.trigg.setStyleSheet('font :bold 10pt;color: white')
        self.labelTrigger = QLabel('Trig')
        self.labelTrigger.setMaximumWidth(50)
        # self.labelTrigger.setMinimumHeight(50)
        self.labelTrigger.setStyleSheet('font :bold  10pt')
        self.itrig = self.trigg.currentIndex()
        hbox2 = QHBoxLayout()
        hbox2.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        hbox2.setContentsMargins(0, 20, 10, 10)
        hbox2.addWidget(self.labelTrigger)
        hbox2.addWidget(self.trigg)
        self.widgetTrig = QWidget(self)
        self.widgetTrig.setLayout(hbox2)
        self.dockTrig = QDockWidget(self)
        self.dockTrig.setWidget(self.widgetTrig)
        
        self.labelExp = QLabel('Exposure (ms)')
        self.labelExp.setStyleSheet('font :bold  10pt')
        self.labelExp.setMaximumWidth(140)
        self.labelExp.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.hSliderShutter = QSlider(Qt.Orientation.Horizontal)
        self.hSliderShutter.setMaximumWidth(60)
        self.shutterBox = QSpinBox()
        self.shutterBox.setStyleSheet('font :bold  8pt')
        self.shutterBox.setMaximumWidth(120)
        
        self.shutterBox.setMaximum(1500)
        self.hSliderShutter.setMaximum(1500)
        
        hboxShutter = QHBoxLayout()
        hboxShutter.setContentsMargins(0, 0, 0, 5)
        hboxShutter.setSpacing(10)
        vboxShutter = QVBoxLayout()
        vboxShutter.setSpacing(0)
        vboxShutter.addWidget(self.labelExp)  #
        
        hboxShutter.addWidget(self.hSliderShutter)
        hboxShutter.addWidget(self.shutterBox)

        vboxShutter.addLayout(hboxShutter)
        vboxShutter.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        vboxShutter.setContentsMargins(0, 0, 10, 0)
        vboxShutter.setSpacing(2)
        
        self.widgetShutter = QWidget(self)
        self.widgetShutter.setLayout(vboxShutter)
        self.dockShutter = QDockWidget(self)
        self.dockShutter.setWidget(self.widgetShutter)
        
        hMainLayout = QHBoxLayout()
        
        if self.light is False:  # light option : not all the option af visu 
            from visu import SEE
            self.visualisation = SEE(parent=self, name=self.nbcam, **self.kwds)  ## Widget for visualisation and tools  self.confVisu permet d'avoir plusieurs camera et donc plusieurs fichier ini de visualisation
        else:
            from visu import SEELIGHT
            self.visualisation = SEELIGHT(parent=self, name=self.nbcam, **self.kwds)

        self.dockTrig.setTitleBarWidget(QWidget())     
        self.dockControl.setTitleBarWidget(QWidget())  # to avoid tittle
        self.dockShutter.setTitleBarWidget(QWidget())
        
        if self.separate is True: # control camera button is not on the menu but in a widget at the left or right of the display screen
            self.dockTrig.setTitleBarWidget(QWidget())
            if self.aff == 'left':
                self.visualisation.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,self.dockControl)
                self.visualisation.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,self.dockTrig)
                self.visualisation.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,self.dockShutter)
                
            else:
                self.visualisation.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,self.dockControl)
                self.visualisation.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,self.dockTrig)
                self.visualisation.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,self.dockShutter)  
        else:
            self.visualisation.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea,self.dockControl)
            self.visualisation.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea,self.dockTrig)
            self.visualisation.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea,self.dockShutter)
            
        hMainLayout.addWidget(self.visualisation)       

        self.settingButton = QToolButton(self)
        self.settingButton.setMaximumWidth(self.sizebuttonMax+50)
        self.settingButton.setMinimumWidth(self.sizebuttonMax+50)
        self.settingButton.setMaximumHeight(self.sizebuttonMax)
        self.settingButton.setMinimumHeight(self.sizebuttonMax)
        self.settingButton.setText('Settings')
        hbox1.addWidget(self.settingButton)

        self.tempButton = QToolButton(self)
        self.tempButton.setMaximumWidth(self.sizebuttonMax+40)
        self.tempButton.setMinimumWidth(self.sizebuttonMax+40)
        self.tempButton.setMaximumHeight(self.sizebuttonMax)
        self.tempButton.setMinimumHeight(self.sizebuttonMax)
        self.tempButton.setText('Temp')
        hbox1.addWidget(self.tempButton)
        self.tempBox = QLabel('?')
        hbox1.addWidget(self.tempBox)
        
        self.setLayout(hMainLayout)
        self.setContentsMargins(0, 0, 0, 0)
        print('fin setup')
    def shutter(self):
        '''set exposure time
        '''
        self.sh = self.shutterBox.value()
        self.hSliderShutter.setValue((self.sh))  # set value of slider
        self.cam.prop_setvalue(dcam.DCAM_IDPROP.EXPOSURETIME,(self.sh)/1000)
        print('now exposure is ', self.cam.prop_getvalue(dcam.DCAM_IDPROP.EXPOSURETIME), ' s')
        time.sleep(0.1)
        
        self.conf.setValue(self.nbcam+"/shutter", float(self.sh))
        self.conf.sync()
    
    def mSliderShutter(self): # for shutter slider 
        self.sh = self.hSliderShutter.value()
        self.shutterBox.setValue(self.sh)
        self.cam.prop_setvalue(dcam.DCAM_IDPROP.EXPOSURETIME,(self.sh)/1000)
        print('now exposure is ', self.cam.prop_getvalue(dcam.DCAM_IDPROP.EXPOSURETIME),' s')
        self.conf.setValue(self.nbcam+"/shutter", float(self.sh))
    
    def actionButton(self):
        '''action when button are pressed
        '''
        self.runButton.clicked.connect(self.acquireMultiImage)
        self.snapButton.clicked.connect(self.acquireOneImage)
        self.stopButton.clicked.connect(self.stopAcq)
        self.shutterBox.editingFinished.connect(self.shutter)    
        self.hSliderShutter.sliderReleased.connect(self.mSliderShutter)
        self.trigg.currentIndexChanged.connect(self.TrigA)
        self.tempButton.clicked.connect(lambda: self.open_widget(self.tempWidget))
        self.settingButton.clicked.connect(lambda: self.open_widget(self.settingWidget))
        if self.isConnected is True:
            self.threadRunAcq = ThreadRunAcq(self)
            self.threadRunAcq.newDataRun.connect(self.Display)
            self.threadOneAcq = ThreadOneAcq(self)
            self.threadOneAcq.newDataRun.connect(self.Display)
            self.threadOneAcq.endAcqState.connect(self.stopAcq)
         
    def acquireMultiImage(self):    
        ''' start the acquisition thread
        '''
        self.runButton.setEnabled(False)
        self.runButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: gray ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconPlay,self.iconPlay))
        self.snapButton.setEnabled(False)
        self.snapButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: gray ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconSnap,self.iconSnap))
        self.stopButton.setEnabled(True)
        self.stopButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: transparent ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconStop,self.iconStop) )
        self.trigg.setEnabled(False)
        self.camIsRunnig = True
        
        # self.threadTemp.stopThreadTemp()
        for child in self.settingWidget.findChildren(QPushButton):
            child.setEnabled(False)
        for child in self.settingWidget.findChildren(QComboBox):
            child.setEnabled(False)
        self.threadRunAcq.newRun()  # to set stopRunAcq=False
        self.threadRunAcq.start()
       
    def acquireOneImage(self):
        
        self.runButton.setEnabled(False)
        self.runButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: gray ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconPlay,self.iconPlay))
        self.snapButton.setEnabled(False)
        self.snapButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: gray ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconSnap,self.iconSnap))
        self.stopButton.setEnabled(True)
        self.stopButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: transparent ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconStop,self.iconStop) )
        self.trigg.setEnabled(False)
        
        # self.threadTemp.stopThreadTemp()
        self.camIsRunnig = True
        for child in self.settingWidget.findChildren(QPushButton):
            child.setEnabled(False)
        for child in self.settingWidget.findChildren(QComboBox):
            child.setEnabled(False)

        self.threadOneAcq.newRun()  # to set stopRunAcq=False
        self.threadOneAcq.start()
        
    def nbShotAction(self):
        '''
        number of snapShot
        '''
        nbShot, ok = QInputDialog.getInt(self, 'Number of SnapShot ', 'Enter the number of snapShot ')
        if ok:
            self.nbShot = int(nbShot)
            if self.nbShot <= 0:
                self.nbShot = 1
        else:
            self.nbShot = 1
    
    def stopAcq(self):
        
        self.threadRunAcq.stopThreadRunAcq()
        self.threadOneAcq.stopThreadOneAcq()
        
        self.runButton.setEnabled(True)
        self.runButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: transparent ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconPlay,self.iconPlay))
        self.snapButton.setEnabled(True)
        self.snapButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: transparent ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconSnap,self.iconSnap))
        self.stopButton.setEnabled(False)
        self.stopButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: gray ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"%(self.iconStop,self.iconStop) )
        self.trigg.setEnabled(True)
        for child in self.settingWidget.findChildren(QPushButton):
            child.setEnabled(True)
        for child in self.settingWidget.findChildren(QComboBox):
            child.setEnabled(True)
        
        # self.threadTemp.stopTemp=False
        # self.threadTemp.start()
        self.visualisation.frameNumber = 1
        
    def TrigA(self):
    # trig la CCD
        self.itrig = self.trigg.currentIndex()
        if self.itrig == 0:
            self.cam.prop_setvalue(dcam.DCAM_IDPROP.TRIGGERSOURCE,1)
        if self.itrig == 1:
            self.cam.prop_setvalue(dcam.DCAM_IDPROP.TRIGGERSOURCE,2)  # ETriggerSource.EXTERNAL
            print('Trigger ON ')
        # print(self.itrig)

    def Display(self, data):
        '''Display data with Visu module
        '''
        
        self.signalData.emit(data)
        # self.visualisation.newDataReceived(self.data) # send data to visualisation widget
    
    def open_widget(self, fene):
        
        """ open new widget
        """
        print(fene.isWinOpen)
        if fene.isWinOpen is False:
            fene.show()
            fene.isWinOpen = True
    
        else:
            fene.activateWindow()
            fene.raise_()
            fene.showNormal()
        
    def closeEvent(self, event):
        ''' closing window event (cross button)
        '''
        print(' close')
        try:
            self.threadTemp.stopThreadTemp()
        except:
            print('no camera connected')
        try:
            self.cam.dev_close()
            dcam.Dcamapi.uninit()
        except: pass


class ThreadOneAcq(QtCore.QThread):
    '''Second thread for controling one or more  acquisition independtly
    '''
    newDataRun = QtCore.pyqtSignal(object)
    newStateCam = QtCore.pyqtSignal(bool)
    endAcqState = QtCore.pyqtSignal(bool)
    
    def __init__(self, parent):
        super(ThreadOneAcq, self).__init__(parent)
        self.parent = parent
        self.cam = self.parent.cam
        self.stopRunAcq = False
       
    def newRun(self):
        self.stopRunAcq = False
        
    def run(self):
        
        self.newStateCam.emit(True)
             
        for i in range(self.parent.nbShot):
            if self.stopRunAcq is not True:
                if i < self.parent.nbShot-1:
                    self.newStateCam.emit(True)
                    time.sleep(0.01)
                else:
                    self.newStateCam.emit(False)
                try:
                    self.cam.buf_alloc(1)
                    self.cam.cap_snapshot()
                    timeout_milisec = 1000
                    while True:
                        if self.cam.wait_capevent_frameready(timeout_milisec):
                            data = self.cam.buf_getlastframedata()
                            data = np.rot90(data, -1)
                            self.newDataRun.emit(data)
                        break
                    self.cam.buf_release()
                except: pass
                
        self.newStateCam.emit(False)
        self.endAcqState.emit(True)
        
    def stopThreadOneAcq(self):
        self.stopRunAcq = True
        # self.cam.finish()


class ThreadRunAcq(QtCore.QThread):
    
    newDataRun = QtCore.pyqtSignal(object)
    
    def __init__(self, parent=None):
        super(ThreadRunAcq, self).__init__(parent)
        self.parent = parent
        self.cam = self.parent.cam
        self.stopRunAcq = False
        self.itrig = self.parent.itrig
    
    def newRun(self):
       
        self.stopRunAcq = False
    
    def run(self):
        print('-----> Start  multi acquisition')
        
        while True:
            if self.stopRunAcq:
                break
            self.cam.buf_alloc(1)
            self.cam.cap_snapshot()
            timeout_milisec = 1000
            while True:
                if self.cam.wait_capevent_frameready(timeout_milisec):
                    data = self.cam.buf_getlastframedata()
                    data = np.rot90(data, -1)
                    self.newDataRun.emit(data)
                    break
            self.cam.buf_release()
                
    def stopThreadRunAcq(self):
        self.stopRunAcq = True


class ThreadTemperature(QtCore.QThread):
    """
    Thread pour la lecture de la temperature toute les 2 secondes
    """
    TEMP = QtCore.pyqtSignal(float) # signal pour afichage temperature

    def __init__(self, parent=None, cam=None):
        super(ThreadTemperature, self).__init__(parent)
        self.cam = cam
        self.stopTemp = False
        
    def run(self):
        while self.cam is not None:
            temp = self.cam.prop_getvalue(dcam.DCAM_IDPROP.SENSORTEMPERATURE)
            time.sleep(2)
            self.TEMP.emit(temp)
            if self.stopTemp:
                break

    def stopThreadTemp(self):
        self.stopTemp = True
        print('stop thread temperature')
        self.terminate()


class TEMPWIDGET(QWidget):
    
    def __init__(self, parent):
        
        super(TEMPWIDGET, self).__init__()
        self.parent = parent
        self.cam = self.parent.cam
        self.isWinOpen = False
        self.setup()
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        
    def setup(self):
        self.setWindowIcon(QIcon('./icons/LOA.png'))
        self.setWindowTitle('Temperature')
        self.vbox = QVBoxLayout()
        labelT = QLabel('Temperature')
        self.tempVal = QDoubleSpinBox(self)
        self.tempVal.setSuffix(" %s" % '°C')
        min_temp = 0
        max_temp = 0
       
        self.tempVal.setMaximum(max_temp/100)
        self.tempVal.setMinimum(min_temp/100)
        self.tempVal.setValue(self.cam.prop_getvalue(dcam.DCAM_IDPROP.SENSORTEMPERATURE))
        self.tempSet = QPushButton('Set')
        self.tempSet.setEnabled(False)
        self.hbox = QHBoxLayout()
        self.hbox.addWidget(labelT)
        self.hbox.addWidget(self.tempVal)
        self.hbox.addWidget(self.tempSet)
        self.vbox.addLayout(self.hbox)
        self.setLayout(self.vbox)
        self.tempSet.clicked.connect(self.SET)
          
    def SET(self):
        temp = float(self.tempVal.value())
        a = self.cam.prop_setvalue(dcam.DCAM_IDPROP.SENSORTEMPERATURETARGET,temp)
        
        tepTarget = self.cam.prop_getvalue(dcam.DCAM_IDPROP.SENSORTEMPERATURETARGET)
        print('temp target', tepTarget, a)
    
    def closeEvent(self, event):
        """ when closing the window
        """
        self.isWinOpen = False
        time.sleep(0.1)
        event.accept()
        
        
class SETTINGWIDGET(QWidget):
    
    def __init__(self, cam=None, conf=None, parent=None, nbcam=None, visualisation=None):
        super(SETTINGWIDGET, self).__init__(parent)
        self.isWinOpen = False
        p = pathlib.Path(__file__)
        sepa = os.sep
        self.icon = str(p.parent) + sepa+'icons'+sepa
        self.parent = parent
        self.conf = conf
        self.cam = cam
        self.nbcam = nbcam
        self.roi1Is = False
        self.visualisation = visualisation
        self.setup()
        self.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
        self.actionButton()

    def setup(self):
      
        self.dimx = 2000  # self.cam.prop_getvalue(dcam.DCAM_IDPROP.IMAGE_WIDTH)
        self.dimy = 2000  # self.cam.prop_getvalue(dcam.DCAM_IDPROP.IMAGE_HEIGHT)
        self.setWindowIcon(QIcon('./icons/LOA.png'))
        self.setWindowTitle('SETTINGS')
        self.vbox = QVBoxLayout()
        # hboxShutter = QHBoxLayout()
        # shutterLabel = QLabel('ShutterMode')
        # self.shutterMode = QComboBox()
        # self.shutterMode.setMaximumWidth(100)
        # self.shutterMode.addItem('Normal')
        # self.shutterMode.addItem('Always Close')
        # self.shutterMode.addItem('Always Open')
        # self.shutterMode.addItem('Open before trig')
        # hboxShutter.addWidget(shutterLabel)
        # hboxShutter.addWidget(self.shutterMode)
        # self.vbox.addLayout(hboxShutter)
        
        hboxROI = QHBoxLayout()
        hbuttonROI = QVBoxLayout()
        self.setROIButton = QPushButton('Set ROI')
        self.setROIFullButton = QPushButton('Set full Frame')
        self.setROIMouseButton = QPushButton('Mouse')
        hbuttonROI.addWidget(self.setROIButton)
        hbuttonROI.addWidget(self.setROIFullButton)
        hbuttonROI.addWidget(self.setROIMouseButton)
        hboxROI.addLayout(hbuttonROI)
        
        roiLay = QVBoxLayout()
        labelROIX = QLabel('ROI X0')
        self.ROIX = QSpinBox(self)
        self.ROIX.setMinimum(0)
        self.ROIX.setMaximum(int(self.dimx))
        self.ROIX.setValue(int(self.conf.value(self.nbcam + "/x0")))
        
        self.ROIY = QSpinBox(self)
        self.ROIY.setMinimum(0)
        self.ROIY.setMaximum(int(self.dimy))
        self.ROIY.setValue(int(self.conf.value(self.nbcam + "/y0")))
        labelROIY = QLabel('ROI Y0')
        
        labelROIW = QLabel('ROI Width')
        self.ROIW = QSpinBox(self)
        self.ROIW.setMinimum(100)
        self.ROIW.setMaximum(int(self.dimx))
        self.ROIW.setValue(int(self.conf.value(self.nbcam + "/wroi")))
        
        labelROIH = QLabel('ROI Height')
        self.ROIH = QSpinBox(self)
        self.ROIH.setMinimum(100)
        self.ROIH.setMaximum(int((self.dimy)))
        self.ROIH.setValue(int(self.conf.value(self.nbcam + "/hroi")))
        
        labelBinX = QLabel('Binning')
        self.BINX = QComboBox()
        self.BINX.setStyleSheet('font :bold 10pt;color: white')
        self.BINX.addItem('1x1')
        self.BINX.addItem('2x2')
        self.BINX.addItem('4x4')
        self.BINX.addItem('8x8')
        #  self.BINX.addItem('16x16')
        #  self.BINX.addItem('1x2')
        #  self.BINX.addItem('2x4')

        grid_layout = QGridLayout()
        grid_layout.addWidget(labelROIX, 0, 0)
        grid_layout.addWidget(self.ROIX, 0, 1)
        grid_layout.addWidget(labelROIY, 1, 0)
        grid_layout.addWidget(self.ROIY, 1, 1)
        grid_layout.addWidget(labelROIW, 2, 0)
        grid_layout.addWidget(self.ROIW, 2, 1)
        grid_layout.addWidget(labelROIH, 3, 0)
        grid_layout.addWidget(self.ROIH, 3, 1)
        grid_layout.addWidget(labelBinX, 4, 0)
        grid_layout.addWidget(self.BINX, 4, 1)
        
        roiLay.addLayout(grid_layout)
        hboxROI.addLayout(roiLay)
        self.vbox.addLayout(hboxROI)

        self.setLayout(self.vbox)
        self.r1 = 100
        self.roi1 = pg.RectROI([self.dimx/2, self.dimy/2], [2*self.r1, 2*self.r1], pen='r', movable=True)
        self.roi1.setPos([self.dimx/2-self.r1, self.dimy/2-self.r1])
        
    def actionButton(self):
        self.setROIButton.clicked.connect(self.roiSet)
        self.setROIFullButton.clicked.connect(self.roiFull)
        #self.shutterMode.currentIndexChanged.connect(self.setShutterMode)
        self.setROIMouseButton.clicked.connect(self.mouseROI)
        self.roi1.sigRegionChangeFinished.connect(self.mousFinished)
        self.ROIX.editingFinished.connect(self.roiChange)
        self.ROIY.editingFinished.connect(self.roiChange)
        self.ROIW.editingFinished.connect(self.roiChange)
        self.ROIH.editingFinished.connect(self.roiChange)

    def mouseROI(self):
        self.visualisation.p1.addItem(self.roi1)
        self.roi1Is = True
    
    def roiChange(self):
        self.ROIX.setValue(round(self.ROIX.value()/100)*100)
        self.ROIY.setValue(round(self.ROIY.value()/100)*100)
        self.ROIW.setValue(round(self.ROIW.value()/100)*100)
        self.ROIH.setValue(round(self.ROIH.value()/100)*100)

    def mousFinished(self):
        
        posRoi = self.roi1.pos()
        sizeRoi = self.roi1.size()
        self.x0 = int(posRoi.x())
        self.wroi = int(sizeRoi.x())
        self.hroi = int(sizeRoi.y())
        self.y0 = int(posRoi.y())  # +sizeRoi.y())
        
        self.ROIX.setValue(round(self.x0/100)*100)
        self.ROIY.setValue(round(self.y0/100)*100)
        self.ROIW.setValue(round(self.wroi/100)*100)
        self.ROIH.setValue(round(self.hroi/100)*100)

    def roiSet(self):
        
        self.x0 = int(self.ROIX.value())
        self.y0 = int(self.ROIY.value())
        self.w = int(self.ROIW.value())
        self.h = int(self.ROIH.value())
        self.binX = int(self.BINX.currentIndex())
        
        self.y0 = int(abs(self.dimy - (self.y0 + self.h)))

        self.yo = round(self.y0/100)*100
        self.x0 = round(self.x0/100)*100
        self.w = round(self.w/100)*100
        self.h = round(self.h/100)*100

        if self.x0 <= 0:
            self.x0 = int(0)
        if self.y0 <= 0:

            self.y0 = int(0)
        if self.h >= self.dimy:
            self.h = int(self.dimy)
        if self.w >= self.dimx:
            self.w = int(self.dimx)

        self.conf.setValue(self.nbcam + "/x0", self.x0)
        self.conf.setValue(self.nbcam + "/y0", self.y0)
        self.conf.setValue(self.nbcam + "/wroi", self.w)
        self.conf.setValue(self.nbcam + "/hroi", self.h)

        if self.roi1Is is True:
            self.visualisation.p1.removeItem(self.roi1)
            self.roi1Is = False

        #self.cam.prop_setvalue(dcam.DCAM_IDPROP.SUBARRAYMODE, 1)
        #self.cam.prop_setvalue(dcam.DCAM_IDPROP.BINNING, 1)
        
        self.cam.prop_setvalue(dcam.DCAM_IDPROP.SUBARRAYHSIZE, float(self.w))
        self.cam.prop_setvalue(dcam.DCAM_IDPROP.SUBARRAYVSIZE, float(self.h))
        self.cam.prop_setvalue(dcam.DCAM_IDPROP.SUBARRAYHPOS, self.x0)
        self.cam.prop_setvalue(dcam.DCAM_IDPROP.SUBARRAYVPOS, self.y0)

        if self.binX == 0:
            self.bin = 1
        if self.binX == 1:
            self.bin = 2
        if self.binX == 2:
            self.bin = 4
        if self.binX == 3:
            self.bin == 8
        if self.binX == 4:
            self.bin = 16
        if self.binX == 5:
            self.bin == 102
        if self.binX == 7:
            self.bin = 204
        
        ret = self.cam.prop_setvalue(dcam.DCAM_IDPROP.BINNING, self.bin)
        if ret is False:
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Icon.Warning)
            msg.setWindowTitle('Warnning Binnig is not possible ')
            msg.setText("Change ROI width and height and value must be multiple of 100")
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.setWindowIcon(QIcon(self.icon+'LOA.png'))
            tt = msg.exec()
        
        if self.cam.prop_getvalue(dcam.DCAM_IDPROP.SUBARRAYMODE):

            self.cam.prop_setvalue(dcam.DCAM_IDPROP.SUBARRAYMODE, 2)  # mode on

    def roiFull(self):

        if self.cam.prop_getvalue(dcam.DCAM_IDPROP.SUBARRAYMODE) != 1:  # full frame
            self.cam.prop_setvalue(dcam.DCAM_IDPROP.SUBARRAYMODE, 1)

        print("full frame")
        self.ROIX.setValue(0)
        self.ROIY.setValue(0)
        self.ROIW.setValue(self.dimx)
        self.ROIH.setValue(self.dimx)

        if self.roi1Is is True:
            self.visualisation.p1.removeItem(self.roi1)
            self.roi1Is = False
        
    def setShutterMode(self):
        """ set shutter mode
        """
        ishut = self.shutterMode.currentIndex()
        
        if ishut == 0:
             self.cam.setParameter("PicamParameter_ShutterTimingMode",0)
        if ishut == 1:
             self.cam.setParameter("PicamParameter_ShutterTimingMode",1) 
        if ishut == 2:
             self.cam.setParameter("PicamParameter_ShutterTimingMode",2) 
        if ishut == 3:
             self.cam.setParameter("PicamParameter_ShutterTimingMode",3)
             print('OutputSignal',self.cam.getParameter("ShutterTimingMode"))
             
    def closeEvent(self, event):
        """ when closing the window
        """
        self.isWinOpen = False
        if self.roi1Is is True:
            self.visualisation.p1.removeItem(self.roi1)
            self.roi1Is = False
        time.sleep(0.1)
        event.accept() 


class ProgressScreen(QWidget):
    
    def __init__(self, parent=None):

        super().__init__()

        self.parent = parent
        p = pathlib.Path(__file__)
        sepa = os.sep
        self.icon = str(p.parent) + sepa+'icons' + sepa
        self.setWindowIcon(QIcon(self.icon+'LOA.png'))
        self.setWindowTitle(' Loading  ...')
        self.setGeometry(600, 300, 300, 100)
        # self.setWindowFlags(Qt.WindowType.FramelessWindowHint| Qt.WindowType.WindowStaysOnTopHint)
        layout = QVBoxLayout()

        self.label = QLabel('Loading Camera V'+str(__version__))
        self.label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.label2 = QLabel("Laboratoire d'Optique Appliquée")
        self.label2.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.label2.setStyleSheet('font :bold 20pt;color: white')
        self.action = QLabel('Load visu')
        layout.addWidget(self.label2)
        layout.addWidget(self.label)
        layout.addWidget(self.action)
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)
        if self.parent is not None:
            self.parent.updateBar_signal.connect(self.setLabel)

    def setLabel(self, labels):
        label = labels[0]
        val = labels[1]
        self.action.setText(str(label))
        self.progress_bar.setValue(int(val))
        QtCore.QCoreApplication.processEvents()  # c'est moche mais pas de mise  jour sinon ???


if __name__ == "__main__":
    appli = QApplication(sys.argv)
    # confpathVisu='C:/Users/Salle-Jaune/Desktop/Python/Princeton/confVisuFootPrint.ini'
    appli.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
    try :
        a= HAMAMATSU()
        a.show()
    except Exception as e :
        print ("error with visu and  RSAI ?",e)
        w = HAMAMATSU(cam='Spectro',RSAI=False)
        w.show()
    appli.exec()
