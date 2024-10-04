# -*- coding: utf-8 -*-
#! /home/zita1/loaenv/bin/python3.12

"""
Created on Oct 03 2024

pip install git+https://github.com/julienGautier77/visu
@author: juliengautier
modified 2024/10/03 
"""

import __init__
__version__ = __init__.__version__
__author__ = __init__.__author__
version=__version__

from PyQt6.QtWidgets import QApplication,QVBoxLayout,QHBoxLayout,QWidget,QPushButton,QDockWidget,QMenu,QLayout,QProgressBar
from PyQt6.QtWidgets import QComboBox,QSlider,QLabel,QSpinBox,QDoubleSpinBox,QGridLayout,QToolButton,QInputDialog
from PyQt6 import QtCore
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6 import QtGui 
import sys,time
import numpy as np
import pathlib,os
import pyqtgraph as pg 
import dcam
import qdarkstyle


class HAMAMATSU(QWidget):
    
    signalData = QtCore.pyqtSignal(object)
    updateBar_signal = QtCore.pyqtSignal(object) # signal for update progressbar

    def __init__(self,cam=None,confFile='conf.ini',**kwds):
        
        super(HAMAMATSU, self).__init__()

        self.progressWin = ProgressScreen(parent = self)
        self.progressWin.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.WindowStaysOnTopHint)
        self.progressWin.show()

        p = pathlib.Path(__file__)
        sepa = os.sep
        self.kwds = kwds
        self.isConnected = False

        if "confpath" in kwds:
            self.confpath = kwds["confpath"]
        else  :
            self.confpath = None
        
        if self.confpath is None:
            self.confpath = str(p.parent / confFile) # ini file with global path
        
        self.conf = QtCore.QSettings(self.confpath, QtCore.QSettings.Format.IniFormat) # ini file 
        
        
        self.kwds["confpath"] = self.confpath
        
        self.icon=str(p.parent) + sepa+'icons' +sepa
        self.configMotorPath = "./fichiersConfig/"
        self.configMotName = 'configMoteurRSAI.ini'
        self.confMotorPath = self.configMotorPath+self.configMotName
       
        self.confMot=QtCore.QSettings(str(p.parent / self.confMotorPath), QtCore.QSettings.Format.IniFormat)
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
            
        if "aff" in kwds: #  affi of Visu
            self.aff = kwds["aff"]
        else: 
            self.aff = "right"  
            
        self.icon = str(p.parent) + sepa+'icons'+sepa
        self.setWindowIcon(QIcon(self.icon+'LOA.png'))
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
        
        if cam is None: # si None on prend la première...
            self.nbcam = 'cam0'
        else:
            self.nbcam = cam

        self.ccdName = self.conf.value(self.nbcam+"/nameCDD")
        self.camID = self.conf.value(self.nbcam+"/camId")
        print('cam id to open' ,self.camID,self.nbcam)

        text = 'Connect to Camera name  : ' + self.nbcam + ' ...'
        self.updateBar_signal.emit([text,25])
        
        text = 'Set Camera Parameters  ......'
        self.updateBar_signal.emit([text,50])
        self.setup()
        text = 'widget loading  ' + self.nbcam + ' ...'
        self.initCam()
        self.updateBar_signal.emit([text,75])
        self.updateBar_signal.emit(['end',100])
        self.progressWin.close()


        self.itrig = 0
        self.actionButton()
        self.camIsRunnig = False

    def initCam(self):
        initOK = dcam.Dcamapi.init()
        if initOK  :
            idevice = 0 # device number 
            n = dcam.Dcamapi.get_devicecount()
            for i in range(0, n):
                cam = dcam.Dcam(i)
                cameraid = cam.dev_getstring(dcam.DCAM_IDSTR.CAMERAID)
                cameraid = ''.join([car for car in cameraid  if car.isdigit()]) # remove S/N
                if self.camID == cameraid:
                    idevice = i
                

            self.cam = dcam.Dcam(idevice)
            self.camOpened = self.cam.dev_open()
            if self.camOpened:
                model = self.cam.dev_getstring(dcam.DCAM_IDSTR.MODEL)
                #print('model',model)
                id = self.cam.dev_getstring(dcam.DCAM_IDSTR.CAMERAID)
                print('model',model,id)
                #print('init exposure',self.cam.prop_getvalue(dcam.DCAM_IDPROP.EXPOSURETIME))
                self.cam.prop_setvalue(dcam.DCAM_IDPROP.TRIGGER_MODE,6)
                #print('init trigger mode ',self.cam.prop_getvalue(dcam.DCAM_IDPROP.TRIGGER_MODE))
                
                
                self.cam.prop_setvalue(dcam.DCAM_IDPROP.TRIGGERACTIVE,1)  # Normal
                #print('init trigger active ',self.cam.prop_getvalue(dcam.DCAM_IDPROP.TRIGGERACTIVE))
                
                self.cam.prop_setvalue(dcam.DCAM_IDPROP.TRIGGERPOLARITY,2)  # Rising edge
                #print('init trigger polarity',self.cam.prop_getvalue(dcam.DCAM_IDPROP.TRIGGERPOLARITY,))

                self.cam.prop_setvalue(dcam.DCAM_IDPROP.TRIGGERSOURCE,1)  # Internal Camera use its own timing
                #print('init trigger source',self.cam.prop_getvalue(dcam.DCAM_IDPROP.TRIGGERSOURCE))

                self.cam.prop_setvalue(dcam.DCAM_IDPROP.EXPOSURETIME,0.001*int(self.conf.value(self.nbcam+"/shutter")) )# set cam to  ms
                #print('now exposure is ',self.cam.prop_getvalue(dcam.DCAM_IDPROP.EXPOSURETIME))

                self.itrig = 0
                self.sh = int(1000*self.cam.prop_getvalue(dcam.DCAM_IDPROP.EXPOSURETIME))
                
                min_exp_time = int(1000*self.cam.prop_getattr(dcam.DCAM_IDPROP.EXPOSURETIME).valuemin)
                max_exp_time = int(1000*self.cam.prop_getattr(dcam.DCAM_IDPROP.EXPOSURETIME).valuemax)
            
                #print("min,max exposure time in ms ",min_exp_time,max_exp_time)
                print('temp:',self.cam.prop_getvalue(dcam.DCAM_IDPROP.SENSORTEMPERATURE),self.cam.prop_getvalue(dcam.DCAM_IDPROP.SENSORTEMPERATURETARGET) )
                
                self.isConnected =  True
               
        if  self.isConnected is True:
            
            #start temperature thread : 
            self.threadTemp = ThreadTemperature(cam=self.cam)
            self.threadTemp.TEMP.connect(self.update_temp)# 
            self.threadTemp.stopTemp=False
            self.threadTemp.start()
            
            self.hSliderShutter.setMinimum(min_exp_time)
            self.shutterBox.setMinimum(min_exp_time)
            self.hSliderShutter.setMaximum(1500) # or max_exp_time but too long
            self.shutterBox.setMaximum(1500) # or max_exp_time but too long
            self.hSliderShutter.setValue(self.sh)
            self.shutterBox.setValue(self.sh)
            self.tempWidget=TEMPWIDGET(self)
            # self.settingWidget=SETTINGWIDGET(self,visualisation=self.visualisation)
            self.setWindowTitle(self.ccdName)
            
        else :
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
        #print('temp',temp)
        self.tempBox.setText('%.1f °C' % temp)
         
    def setup(self):  
        """ user interface definition: 
        """
        
        hbox1 = QHBoxLayout() # horizontal layout pour run snap stop
        self.sizebuttonMax = 40
        self.sizebuttonMin = 40
        self.runButton = QToolButton(self)
        self.runButton.setMaximumWidth(self.sizebuttonMax)
        self.runButton.setMinimumWidth(self.sizebuttonMax)
        self.runButton.setMaximumHeight(self.sizebuttonMax)
        self.runButton.setMinimumHeight(self.sizebuttonMax)
        self.runButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: transparent ;border-color: green;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"% (self.iconPlay,self.iconPlay) )
        
        self.snapButton = QToolButton(self)
        self.snapButton.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        menu = QMenu()
        #menu.addAction('acq',self.oneImage)
        menu.addAction('set nb of shot',self.nbShotAction)
        self.snapButton.setMenu(menu)
        self.snapButton.setMaximumWidth(self.sizebuttonMax)
        self.snapButton.setMinimumWidth(self.sizebuttonMax)
        self.snapButton.setMaximumHeight(self.sizebuttonMax)
        self.snapButton.setMinimumHeight(self.sizebuttonMax)
        self.snapButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: transparent ;border-color: green;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"% (self.iconSnap,self.iconSnap) )
        
        self.stopButton = QToolButton(self)
        self.stopButton.setMaximumWidth(self.sizebuttonMax)
        self.stopButton.setMinimumWidth(self.sizebuttonMax)
        self.stopButton.setMaximumHeight(self.sizebuttonMax)
        self.stopButton.setMinimumHeight(self.sizebuttonMax)
        self.stopButton.setStyleSheet("QToolButton:!pressed{border-image: url(%s);background-color: gray ;border-color: gray;}""QToolButton:pressed{image: url(%s);background-color: gray ;border-color: gray}"% (self.iconStop,self.iconStop) )
        self.stopButton.setEnabled(False)
      
        hbox1.addWidget(self.runButton)
        hbox1.addWidget(self.snapButton)
        hbox1.addWidget(self.stopButton)
        hbox1.setSizeConstraint(QLayout.SizeConstraint.SetMaximumSize)
        hbox1.setContentsMargins(0, 20, 0, 10)
        self.widgetControl = QWidget(self)
        
        self.widgetControl.setLayout(hbox1)
        self.dockControl = QDockWidget(self)
        self.dockControl.setWidget(self.widgetControl)
        self.dockControl.resize(100,100)
        self.trigg = QComboBox()
        self.trigg.setMaximumWidth(80)
        self.trigg.addItem('OFF')
        self.trigg.addItem('ON')
        self.trigg.setStyleSheet('font :bold  10pt;color: white')
        self.labelTrigger = QLabel('Trigger')
        self.labelTrigger.setMaximumWidth(70)
        self.labelTrigger.setStyleSheet('font :bold  8pt')
        self.itrig = self.trigg.currentIndex()
        
        
        hbox2 = QHBoxLayout()
        hbox2.setSizeConstraint(QLayout.SizeConstraint.SetMaximumSize)
        hbox2.setContentsMargins(5, 15, 0, 0)
        hbox2.addWidget(self.labelTrigger)
        
        hbox2.addWidget(self.trigg)
        self.widgetTrig = QWidget(self)
        
        self.widgetTrig.setLayout(hbox2)
        self.dockTrig = QDockWidget(self)
        self.dockTrig.setWidget(self.widgetTrig)
        
        self.labelExp=QLabel('Exposure (ms)')
        self.labelExp.setStyleSheet('font :bold  9pt')
        self.labelExp.setMaximumWidth(160)
        self.labelExp.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        
        self.hSliderShutter = QSlider(Qt.Orientation.Horizontal)
        self.hSliderShutter.setMaximumWidth(80)
        self.shutterBox = QSpinBox()
        self.shutterBox.setStyleSheet('font :bold  8pt')
        self.shutterBox.setMaximumWidth(120)
        
        hboxShutter = QHBoxLayout()
        hboxShutter.setContentsMargins(5, 0, 0, 0)
        hboxShutter.setSpacing(10)
        vboxShutter = QVBoxLayout()
        vboxShutter.setSpacing(0)
        vboxShutter.addWidget(self.labelExp)#,Qt.AlignLef)
        
        hboxShutter.addWidget(self.hSliderShutter)
        hboxShutter.addWidget(self.shutterBox)
        vboxShutter.addLayout(hboxShutter)
        vboxShutter.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        vboxShutter.setContentsMargins(5, 5, 0, 0)
        
        self.widgetShutter = QWidget(self)
        self.widgetShutter.setLayout(vboxShutter)
        self.dockShutter = QDockWidget(self)
        self.dockShutter.setWidget(self.widgetShutter)
        
        self.widgetTemp = QWidget(self)
        vboxTemp = QVBoxLayout()
        hboxTemp = QHBoxLayout()
        self.tempButton = QPushButton('Temp :')
        self.tempButton.setMaximumWidth(80)
        hboxTemp.addWidget(self.tempButton)
        self.tempBox = QLabel('?')
        hboxTemp.addWidget(self.tempBox)
        
        # self.settingButton=QPushButton('Settings')
        # vboxTemp.addWidget(self.settingButton)
        
        self.widgetTemp .setLayout(hboxTemp)
        self.dockTemp = QDockWidget(self)
        self.dockTemp.setWidget(self.widgetTemp)
        
        hMainLayout = QHBoxLayout()
        
        if self.light is False:
            from visu import SEE
            self.visualisation=SEE(parent=self,name=self.nbcam,**self.kwds) ## Widget for visualisation and tools  self.confVisu permet d'avoir plusieurs camera et donc plusieurs fichier ini de visualisation
        else:
            from visu import SEELIGHT
            self.visualisation = SEELIGHT(parent=self,name=self.nbcam,**self.kwds)
        
        self.dockTrig.setTitleBarWidget(QWidget())        
        self.dockControl.setTitleBarWidget(QWidget()) # to avoid tittle
        self.dockShutter.setTitleBarWidget(QWidget())
        # self.dockGain.setTitleBarWidget(QWidget())
        self.dockTemp.setTitleBarWidget(QWidget())
        if self.separate is True:
            self.dockTrig.setTitleBarWidget(QWidget())
            if self.aff == 'left':
                self.visualisation.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,self.dockControl)
                self.visualisation.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,self.dockTrig)
                self.visualisation.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,self.dockShutter)
                # self.visualisation.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,self.dockGain)
                self.visualisation.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea,self.dockTemp)
            else:
                self.visualisation.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,self.dockControl)
                self.visualisation.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,self.dockTrig)
                self.visualisation.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,self.dockShutter)
                # self.visualisation.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,self.dockGain)
                self.visualisation.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea,self.dockTemp)
        else:
        #self.dockControl.setFeatures(QDockWidget.DockWidgetMovable)
            self.visualisation.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea,self.dockControl)
            self.visualisation.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea,self.dockTrig)
            self.visualisation.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea,self.dockShutter)
            # self.visualisation.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea,self.dockGain)
            self.visualisation.addDockWidget(Qt.DockWidgetArea.TopDockWidgetArea,self.dockTemp)
            
        hMainLayout.addWidget(self.visualisation)
        self.setLayout(hMainLayout)
        self.setContentsMargins(0, 0, 0, 0)
        
        self.setLayout(hMainLayout)
    
    def shutter (self):
        '''set exposure time 
        '''
        self.sh = self.shutterBox.value() # 
        self.hSliderShutter.setValue((self.sh)) # set value of slider
        self.cam.prop_setvalue(dcam.DCAM_IDPROP.EXPOSURETIME,(self.sh)/1000)
        print('now exposure is ',self.cam.prop_getvalue(dcam.DCAM_IDPROP.EXPOSURETIME),' s')
        time.sleep(0.1)
        
        self.conf.setValue(self.nbcam+"/shutter",float(self.sh))
        self.conf.sync()
    
    def mSliderShutter(self): # for shutter slider 
        self.sh = self.hSliderShutter.value()
        self.shutterBox.setValue(self.sh)
        self.cam.prop_setvalue(dcam.DCAM_IDPROP.EXPOSURETIME,(self.sh)/1000)
        print('now exposure is ',self.cam.prop_getvalue(dcam.DCAM_IDPROP.EXPOSURETIME),' s')
        self.conf.setValue(self.nbcam+"/shutter",float(self.sh))
    
    def actionButton(self): 
        '''action when button are pressed
        '''
        self.runButton.clicked.connect(self.acquireMultiImage)
        self.snapButton.clicked.connect(self.acquireOneImage)
        self.stopButton.clicked.connect(self.stopAcq)      
        self.shutterBox.editingFinished.connect(self.shutter)    
        self.hSliderShutter.sliderReleased.connect(self.mSliderShutter)
        self.trigg.currentIndexChanged.connect(self.TrigA)
        self.tempButton.clicked.connect(lambda:self.open_widget(self.tempWidget) )
        # self.settingButton.clicked.connect(lambda:self.open_widget(self.settingWidget) )
        if self.isConnected is True :
            self.threadRunAcq = ThreadRunAcq(self)
            self.threadRunAcq.newDataRun.connect(self.Display)
            self.threadOneAcq = ThreadOneAcq(self)
            self.threadOneAcq.newDataRun.connect(self.Display)#,QtCore.Qt.DirectConnection)
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
        self.camIsRunnig=True
        
        # self.threadTemp.stopThreadTemp()
        
        self.threadRunAcq.newRun() # to set stopRunAcq=False
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
        self.camIsRunnig=True
        
        self.threadOneAcq.newRun() # to set stopRunAcq=False
        self.threadOneAcq.start()
        
        
    def nbShotAction(self):
        '''
        number of snapShot
        '''
        nbShot, ok=QInputDialog.getInt(self,'Number of SnapShot ','Enter the number of snapShot ')
        if ok:
            self.nbShot=int(nbShot)
            if self.nbShot<=0:
               self.nbShot=1
        else:
            self.nbShot=1
    
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
        
        # self.threadTemp.stopTemp=False
        # self.threadTemp.start()
        self.visualisation.frameNumber=1
        
    def TrigA(self):
    ## trig la CCD
        self.itrig = self.trigg.currentIndex()
        if self.itrig == 0:
            self.cam.prop_setvalue(dcam.DCAM_IDPROP.TRIGGERSOURCE,1) 
        if self.itrig == 1:
            self.cam.prop_setvalue(dcam.DCAM_IDPROP.TRIGGERSOURCE,2) # ETriggerSource.EXTERNAL
            print ('Trigger ON ')
        # print(self.itrig)

    def Display(self,data):
        '''Display data with Visu module
        '''
        
        self.signalData.emit(data)
        # self.visualisation.newDataReceived(self.data) # send data to visualisation widget
    
    def open_widget(self,fene):
        
        """ open new widget 
        """
        
        if fene.isWinOpen is False:
            fene.show()
            fene.isWinOpen=True
    
        else:
            fene.activateWindow()
            fene.raise_()
            fene.showNormal()
        
    def closeEvent(self,event):
        ''' closing window event (cross button)
        '''
        print(' close')
        try :
            self.threadTemp.stopThreadTemp()
        except:
            print('no camera connected')
        try :
            self.cam.dev_close()
            dcam.Dcamapi.uninit()
        except :pass
        
class ThreadOneAcq(QtCore.QThread):
    
    '''Second thread for controling one or more  acquisition independtly
    '''
    newDataRun = QtCore.pyqtSignal(object)
    newStateCam = QtCore.pyqtSignal(bool)
    endAcqState = QtCore.pyqtSignal(bool)
    
    def __init__(self, parent):
        super(ThreadOneAcq,self).__init__(parent)
        self.parent = parent
        self.cam = self.parent.cam
        self.stopRunAcq = False
       
    def newRun(self):
        self.stopRunAcq = False
        
    def run(self):
        
        self.newStateCam.emit(True)
             
        for i in range (self.parent.nbShot):
            if self.stopRunAcq is not True :
                if i<self.parent.nbShot-1:
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
                            data = np.rot90(data,-1)
                            self.newDataRun.emit(data)         
                        break
                    self.cam.buf_release()  
                except :pass
                
        self.newStateCam.emit(False)
        self.endAcqState.emit(True)
        
    def stopThreadOneAcq(self):
        self.stopRunAcq=True
        # self.cam.finish()
        
        
class ThreadRunAcq(QtCore.QThread):
    
    newDataRun = QtCore.pyqtSignal(object)
    
    def __init__(self, parent=None):
        super(ThreadRunAcq,self).__init__(parent)
        self.parent = parent
        self.cam = self.parent.cam
        self.stopRunAcq = False
        self.itrig = self.parent.itrig
    
    def newRun(self):
       
        self.stopRunAcq = False
    
    def run(self):
        print('-----> Start  multi acquisition')
        
        while True :
            if self.stopRunAcq:
                break
            self.cam.buf_alloc(1)
            self.cam.cap_snapshot()
            timeout_milisec = 1000
            while True:
                if self.cam.wait_capevent_frameready(timeout_milisec):
                    data = self.cam.buf_getlastframedata()
                    data = np.rot90(data,-1)
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

    def __init__(self, parent=None,cam=None):
        super(ThreadTemperature,self).__init__(parent)
        self.cam    = cam
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
        print ('stop thread temperature')  
        self.terminate()        


class TEMPWIDGET(QWidget):
    
    def __init__(self,parent):
        
        super(TEMPWIDGET, self).__init__()
        self.parent=parent
        self.cam=self.parent.cam
        self.isWinOpen=False
        self.setup()
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        
    def setup(self) :   
        self.setWindowIcon(QIcon('./icons/LOA.png'))
        self.setWindowTitle('Temperature')
        self.vbox=QVBoxLayout()
        labelT=QLabel('Temperature')
        self.tempVal= QDoubleSpinBox(self)
        self.tempVal.setSuffix(" %s" % '°C')
        min_temp = 0
        max_temp = 0
       
        self.tempVal.setMaximum(max_temp/100)
        self.tempVal.setMinimum( min_temp/100)
        self.tempVal.setValue(self.cam.prop_getvalue(dcam.DCAM_IDPROP.SENSORTEMPERATURE))
        self.tempSet=QPushButton('Set')
        self.hbox=QHBoxLayout()
        self.hbox.addWidget(labelT)
        self.hbox.addWidget(self.tempVal)
        self.hbox.addWidget(self.tempSet)
        self.vbox.addLayout(self.hbox)
        self.setLayout(self.vbox)
        self.tempSet.clicked.connect(self.SET)
        
        
        
    def SET(self):
        temp = float(self.tempVal.value())
        
        #self.cam.prop_setvalue(dcam.DCAM_IDPROP.SENSORTEMPERATURETARGET,temp)
        tepTarget = self.cam.prop_getvalue(dcam.DCAM_IDPROP.SENSORTEMPERATURETARGET)
        print('temp target', tepTarget)
    
    def closeEvent(self, event):
        """ when closing the window
        """
        self.isWinOpen=False
        
        time.sleep(0.1)
        event.accept() 
        
        
class SETTINGWIDGET(QWidget):
    
    def __init__(self, parent,visualisation=None):
        
        super(SETTINGWIDGET, self).__init__()
        self.parent=parent
        self.cam=self.parent.cam
        self.visualisation=visualisation
        self.isWinOpen=False
        
        self.setup()
        self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
        
        self.actionButton()
        self.roi1Is=False
        
    def setup(self) : 
        self.dimx =self.cam.sensor_size[0]
        self.dimy =self.cam.sensor_size[1]
        self.setWindowIcon(QIcon('./icons/LOA.png'))
        self.setWindowTitle('SETTINGS')
        self.vbox=QVBoxLayout()
        
        hboxShutter=QHBoxLayout()
        shutterLabel=QLabel('ShutterMode')
        self.shutterMode=QComboBox()
        self.shutterMode.setMaximumWidth(100)
        self.shutterMode.addItem('Normal')
        self.shutterMode.addItem('Always Close')
        self.shutterMode.addItem('Always Open')
        self.shutterMode.addItem('Open before trig')
        
        hboxShutter.addWidget(shutterLabel)
        hboxShutter.addWidget(self.shutterMode)
        self.vbox.addLayout(hboxShutter)
        
        hboxFrequency=QHBoxLayout()
        frequencyLabel=QLabel('Frequency')
        self.frequency=QComboBox()
        self.frequency.setMaximumWidth(100)
        self.frequency.addItem('Normal')
        self.frequency.addItem('Always Close')
        self.frequency.addItem('Always Open')
        hboxFrequency.addWidget(frequencyLabel)
        hboxFrequency.addWidget(self.frequency)
        self.vbox.addLayout(hboxFrequency)
        
        hboxROI=QHBoxLayout()
        
        hbuttonROI=QVBoxLayout()
        self.setROIButton=QPushButton('Set ROI')
        self.setROIFullButton=QPushButton('Set full Frame')
        self.setROIMouseButton=QPushButton('Mousse')
        hbuttonROI.addWidget(self.setROIButton)
        hbuttonROI.addWidget(self.setROIFullButton)
        hbuttonROI.addWidget(self.setROIMouseButton)
        hboxROI.addLayout(hbuttonROI)
        
        roiLay= QVBoxLayout()
        labelROIX=QLabel('ROI Xo')
        self.ROIX=QDoubleSpinBox(self)
        self.ROIX.setMinimum(0)
        self.ROIX.setMaximum(self.dimx)
        
        self.ROIY=QDoubleSpinBox(self)
        self.ROIY.setMinimum(1)
        self.ROIY.setMaximum(self.dimy)
        labelROIY=QLabel('ROI Yo')
        
        labelROIW=QLabel('ROI Width')
        self.ROIW=QDoubleSpinBox(self)
        self.ROIW.setMinimum(0)
        self.ROIW.setMaximum(self.dimx)     
        
        labelROIH=QLabel('ROI Height')
        self.ROIH=QDoubleSpinBox(self)
        self.ROIH.setMinimum(1)
        self.ROIH.setMaximum(self.dimy) 
        
        labelBinX=QLabel('Bin X')
        self.BINX=QDoubleSpinBox(self)
        self.BINX.setMinimum(1)
        self.BINX.setMaximum(self.dimx) 
        labelBinY=QLabel('Bin Y ')
        self.BINY=QDoubleSpinBox(self)
        self.BINY.setMinimum(1)
        self.BINY.setMaximum(self.dimy) 
        
        grid_layout = QGridLayout()
        grid_layout.addWidget(labelROIX,0,0)
        grid_layout.addWidget(self.ROIX,0,1)
        grid_layout.addWidget(labelROIY,1,0)
        grid_layout.addWidget(self.ROIY,1,1)
        grid_layout.addWidget(labelROIW,2,0)
        grid_layout.addWidget(self.ROIW,2,1)
        grid_layout.addWidget(labelROIH,3,0)
        grid_layout.addWidget(self.ROIH,3,1)
        grid_layout.addWidget(labelBinX,4,0)
        grid_layout.addWidget(self.BINX,4,1)
        grid_layout.addWidget(labelBinY,5,0)
        grid_layout.addWidget(self.BINY,5,1)
        
        roiLay.addLayout(grid_layout)
        hboxROI.addLayout(roiLay)
        self.vbox.addLayout(hboxROI)

        self.setLayout(self.vbox)
        
        self.r1=100
        self.roi1=pg.RectROI([self.dimx/2,self.dimy/2], [2*self.r1, 2*self.r1],pen='r',movable=True)
        self.roi1.setPos([self.dimx/2-self.r1,self.dimy/2-self.r1])
        
    def actionButton(self):
        self.setROIButton.clicked.connect(self.roiSet)
        self.setROIFullButton.clicked.connect(self.roiFull)
        self.frequency.currentIndexChanged.connect(self.setFrequency)
        self.shutterMode.currentIndexChanged.connect(self.setShutterMode)
        self.setROIMouseButton.clicked.connect(self.mousseROI)
        self.roi1.sigRegionChangeFinished.connect(self.moussFinished)
        
    def mousseROI(self):
        
        self.visualisation.p1.addItem(self.roi1)
        self.roi1Is=True
        
    def moussFinished(self):
        
        posRoi=self.roi1.pos()
        sizeRoi=self.roi1.size()
        self.x0=int(posRoi.x())
        self.wroi=int(sizeRoi.x())
        self.hroi=int(sizeRoi.y())
        self.y0=posRoi.y()+sizeRoi.y()
              
        self.ROIX.setValue(self.x0)
        self.ROIY.setValue(self.y0)
        self.ROIW.setValue(self.wroi)
        self.ROIH.setValue(self.hroi)
        
    def roiSet(self):
        
        self.x0=int(self.ROIX.value())
        self.y0=int(self.ROIY.value())
        self.w=int(self.ROIW.value())
        self.h=int(self.ROIH.value())
        self.BinX=int(self.BINX.value())
        self.BinY=int(self.BINY.value())
        # print('bin',self.cam.bin_x)
        self.cam.bin_x=self.BinX
        self.cam.bin_Y=self.BinY
        # self.cam.set_roi(0, 0, self.dimx,self.dimy)
        
        self.cam.set_roi(self.x0, self.dimy-self.y0, self.w, self.h) # ROI start up left pyqtgraph botton left
        
        
        if self.roi1Is==True:
            self.visualisation.p1.removeItem(self.roi1)
            self.roi1Is=False
        
    def roiFull(self):
        
        self.w = self.parent.dimx
        self.h = self.parent.dimy
        self.ROIX.setValue(0)
        self.ROIY.setValue(0)
        self.ROIW.setValue(self.w)
        self.ROIH.setValue(self.h)
        self.BINX.setValue(1)
        self.BINX.setValue(1)
        self.cam.bin_x=int(1)
        self.cam.bin_Y=int(1)
        self.cam.set_roi(0, 0,self.w,self.h) # full frame
        
        print("fullframe")
        if self.roi1Is==True:
            self.visualisation.p1.removeItem(self.roi1)
            self.roi1Is=False
        
    def setFrequency(self) :
        """
        set frequency reading in Mhz
        """          
        ifreq=self.freqency.currentIndex()
        
        # toDO
        
        # if ifreq==0:
        #      self.cam.setParameter("AdcSpeed",0.1)
        # if ifreq==0:
        #      self.cam.setParameter("AdcSpeed",1)
        # if ifreq==0:
        #      self.cam.setParameter("AdcSpeed",2)
             
        # print('adc frequency(Mhz)',self.cam.getParameter("AdcSpeed"))

    def setShutterMode(self):
        """ set shutter mode
        """
        ishut=self.shutterMode.currentIndex()
        print('shutter')
        ## todo
        # if ishut==0:
        #      self.cam.setParameter("ShutterTimingMode",0)
        # if ishut==1:
        #      self.cam.setParameter("ShutterTimingMode",1) 
        # if ishut==2:
        #      self.cam.setParameter("ShutterTimingMode",2) 
        # if ishut==3:
        #      self.cam.setParameter("ShutterTimingMode",3)
        #      print('OutputSignal',self.mte.getParameter("ShutterTimingMode"))
             
    def closeEvent(self, event):
        """ when closing the window
        """
        self.isWinOpen = False
        if self.roi1Is is True:
            self.visualisation.p1.removeItem(self.roi1)
            self.roi1Is=False
        time.sleep(0.1)
        
        event.accept() 

class ProgressScreen(QWidget):
    
    def __init__(self,parent=None):

        super().__init__()

        self.parent = parent 
        p = pathlib.Path(__file__)
        sepa = os.sep
        self.icon = str(p.parent) + sepa+'icons' + sepa
        self.setWindowIcon(QIcon(self.icon+'LOA.png'))
        self.setWindowTitle(' Loading  ...')
        self.setGeometry(600, 300, 300, 100)
        #self.setWindowFlags(Qt.WindowType.FramelessWindowHint| Qt.WindowType.WindowStaysOnTopHint)
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

    def setLabel(self,labels) :
        label = labels[0]
        val = labels[1]
        self.action.setText(str(label))
        self.progress_bar.setValue(int(val))
        QtCore.QCoreApplication.processEvents() # c'est moche mais pas de mise  jour sinon ???





if __name__ == "__main__":       
    
    appli = QApplication(sys.argv)
    # confpathVisu='C:/Users/Salle-Jaune/Desktop/Python/Princeton/confVisuFootPrint.ini'
    appli.setStyleSheet(qdarkstyle.load_stylesheet(qt_api='pyqt6'))
    e = HAMAMATSU(cam='hama')  
    e.show()
    appli.exec_()       