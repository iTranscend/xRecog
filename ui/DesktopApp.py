# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'DesktopApp.ui'
#
# Created by: PyQt5 UI code generator 5.14.2
#
# WARNING! All changes made in this file will be lost!


from PyQt5 import QtCore, QtGui, QtWidgets, QtMultimedia, QtMultimediaWidgets
import os
import sys
import time

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(526, 300)
        self.QTabWidget = QtWidgets.QTabWidget(Dialog)
        self.QTabWidget.setGeometry(QtCore.QRect(-10, 0, 541, 311))
        self.QTabWidget.setTabShape(QtWidgets.QTabWidget.Triangular)
        self.QTabWidget.setUsesScrollButtons(True)
        self.QTabWidget.setTabsClosable(True)
        self.QTabWidget.setMovable(True)
        self.QTabWidget.setTabBarAutoHide(True)
        self.QTabWidget.setObjectName("QTabWidget")
        self.RegisterStudents = QtWidgets.QWidget()
        self.RegisterStudents.setObjectName("RegisterStudents")
        self.lineEdit = QtWidgets.QLineEdit(self.RegisterStudents)
        self.lineEdit.setGeometry(QtCore.QRect(160, 10, 311, 26))
        self.lineEdit.setObjectName("lineEdit")
        self.label = QtWidgets.QLabel(self.RegisterStudents)
        self.label.setGeometry(QtCore.QRect(50, 20, 74, 18))
        self.label.setObjectName("label")
        self.label_2 = QtWidgets.QLabel(self.RegisterStudents)
        self.label_2.setGeometry(QtCore.QRect(50, 70, 121, 161))
        self.label_2.setAlignment(QtCore.Qt.AlignLeading|QtCore.Qt.AlignLeft|QtCore.Qt.AlignTop)
        self.label_2.setWordWrap(True)
        self.label_2.setObjectName("label_2")
        self.QTabWidget.addTab(self.RegisterStudents, "")
        self.TakeAttendance = QtWidgets.QWidget()
        self.TakeAttendance.setObjectName("TakeAttendance")
        self.QTabWidget.addTab(self.TakeAttendance, "")

        self.retranslateUi(Dialog)
        self.QTabWidget.setCurrentIndex(0)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.QTabWidget.setToolTip(_translate("Dialog", "<html><head/><body><p>Register Students</p><p><br/></p></body></html>"))
        self.QTabWidget.setWhatsThis(_translate("Dialog", "<html><head/><body><p>Register Students</p></body></html>"))
        self.label.setText(_translate("Dialog", "Name:"))
        self.label_2.setText(_translate("Dialog", "Facial Images (Upload btwn. 10-20 facial images under various lighting conditions)"))
        self.QTabWidget.setTabText(self.QTabWidget.indexOf(self.RegisterStudents), _translate("Dialog", "Register Students"))
        self.QTabWidget.setTabText(self.QTabWidget.indexOf(self.TakeAttendance), _translate("Dialog", "Take Attendance"))

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setApplicationName("RealTimeAttendance")
    window = MainWindow()
    app.exec_()