import os
import sys
import time
import queue
import random
import tempfile
import functools
import markdown2
import threading
from datetime import datetime
from collections import deque

from PyQt5 import (
    uic,
    QtGui,
    QtCore,
    QtWidgets,
    QtMultimedia,
    QtPrintSupport,
    QtMultimediaWidgets)

from . import resources_rc
from .eventemitter import EventEmitter
from .parallelizer import Parallelizer


class XrecogCaptureWindow(QtWidgets.QDialog):
    def __init__(self):
        super(XrecogCaptureWindow, self).__init__()
        uic.loadUi(translatePath("capture.ui"), self)
        self.images = []
        self.imageSlots = []
        self.selected_camera = None
        self.camera = None
        self.capture = None
        self.hasInit = False
        slots = [self.imageGrid.findChildren(QtWidgets.QWidget, QtCore.QRegExp(
            "imageSlot%02d" % index))[0] for index in range(1, 13)]
        for slot in slots:
            newSizePolicy = slot.sizePolicy()
            newSizePolicy.setRetainSizeWhenHidden(True)
            slot.setSizePolicy(newSizePolicy)
            slot.setAttribute(QtCore.Qt.WA_Hover)
            slot.installEventFilter(self)
            slot.hide()
            imageSlot = slot.findChild(QtWidgets.QLabel)
            deleteButton = slot.findChild(QtWidgets.QToolButton)
            deleteButton.hide()
            slotObject = {"object": slot, "item": None}
            deleteButton.clicked.connect(self.newDeleteHandler(slotObject))
            self.imageSlots.append(slotObject)
        self.viewfinder = QtMultimediaWidgets.QCameraViewfinder()
        self.viewFinderFrame.layout().addWidget(self.viewfinder)
        self.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self and event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Escape:
                self.close()
                return True
        if type(obj) is QtWidgets.QWidget:
            if event.type() == QtCore.QEvent.HoverEnter:
                obj.findChild(QtWidgets.QToolButton).show()
                return True
            elif event.type() == QtCore.QEvent.HoverLeave:
                obj.findChild(QtWidgets.QToolButton).hide()
                return True
        return super(QtWidgets.QDialog, self).eventFilter(obj, event)

    def init(self):
        self.captureButton.setDisabled(True)
        self.scanDevices()
        if (not self.hasInit):
            self.hasInit = True
            self.prepareHandlers()

    def newDeleteHandler(self, slotObject):
        def deleteHandler():
            if (slotObject["item"] is None):
                return
            item = next(
                image for image in self.images if image["image"] is slotObject["item"])
            self.images.remove(item)
            if (os.path.exists(item["path"])):
                os.unlink(item["path"])
            self.progressBar.setValue(len(self.images))
            slotObject["item"] = None

        slotObject["deleteHandler"] = deleteHandler
        return lambda: (deleteHandler(), self.displayImages())

    def deleteAll(self):
        self.cleanup()
        self.displayImages()

    def closeEvent(self, event):
        self.hideWindow()
        return super(QtWidgets.QDialog, self).closeEvent(event)

    def prepareHandlers(self):
        self.deviceSelectorReloadButton.clicked.connect(self.scanDevices)
        self.captureButton.clicked.connect(self.captureImage)
        self.deviceSelectorComboBox.currentIndexChanged.connect(
            self.selectCamera)
        self.deleteAllButton.clicked.connect(self.deleteAll)

    def hideWindow(self):
        self.releaseCamera()
        self.hide()

    def scanDevices(self):
        self.available_cameras = QtMultimedia.QCameraInfo.availableCameras()
        self.deviceSelectorComboBox.blockSignals(True)
        self.deviceSelectorComboBox.clear()
        self.deviceSelectorComboBox.addItems(
            [c.description() for c in self.available_cameras])
        index = self.index(self.available_cameras, self.selected_camera)
        if index is not None:
            self.deviceSelectorComboBox.setCurrentIndex(index)
        elif len(self.available_cameras):
            index = self.index(
                self.available_cameras, QtMultimedia.QCameraInfo.defaultCamera())
            if index is not None:
                self.selectCamera(index)
                self.deviceSelectorComboBox.setCurrentIndex(index)
        self.deviceSelectorComboBox.blockSignals(False)

    def index(self, iter, item):
        try:
            return iter.index(item)
        except:
            return None

    def alert(self, *args):
        print("ALERT", *args)

    def selectCamera(self, index):
        pre_index = self.index(self.available_cameras, self.selected_camera)
        if pre_index is index:
            return
        if pre_index is not None:
            self.releaseCamera()
        self.selected_camera = self.available_cameras[index]
        self.camera = QtMultimedia.QCamera(self.selected_camera)
        self.camera.setViewfinder(self.viewfinder)
        self.camera.setCaptureMode(QtMultimedia.QCamera.CaptureStillImage)
        self.camera.statusChanged.connect(lambda status: self.enableCaptureButton(
        ) if status == QtMultimedia.QCamera.ActiveStatus and len(self.images) < 12 else None)
        self.camera.error.connect(
            lambda: self.alert("camera error", self.camera.errorString()))
        self.camera.start()

        self.capture = QtMultimedia.QCameraImageCapture(self.camera)
        self.capture.error.connect(
            lambda i, e, s: self.alert("capture error", s))
        self.capture.imageCaptured.connect(self.imageCaptured)

    def enableCaptureButton(self):
        self.captureButton.setDisabled(False)
        self.captureButton.setFocus(True)

    def captureImage(self):
        save_path = tempfile.mktemp(suffix=".jpg")
        id = self.capture.capture(save_path)
        self.images.append({"path": save_path})
        self.captureButton.setDisabled(True)

    def imageCaptured(self, id, image):
        stack = self.images[-1]
        stack["image"] = image
        self.progressBar.setValue(len(self.images))
        self.displayImages(True)

    def displayImages(self, force=False):
        lastIndex = -1
        if (len(self.images) < 12):
            self.enableCaptureButton()
        for (index, imageObject) in enumerate(self.images):
            lastIndex = index
            slot = self.imageSlots[index]
            if (slot["item"] == imageObject["image"]):
                continue
            if ("image" not in imageObject):
                break
            slot["item"] = imageObject["image"]
            label = slot["object"].findChild(QtWidgets.QLabel)
            label.setPixmap(
                QtGui.QPixmap.fromImage(imageObject["image"])
                .scaled(label.size(),
                        QtCore.Qt.KeepAspectRatioByExpanding,
                        QtCore.Qt.SmoothTransformation,
                        ))
            slot["object"].show()
        for slot in self.imageSlots[lastIndex + 1:]:
            slot["item"] = None
            slot["object"].hide()

    def releaseCamera(self):
        if (not (self.capture and self.camera)):
            return
        self.selected_camera = None
        self.capture.cancelCapture()
        self.camera.stop()

    def cleanup(self):
        for slot in self.imageSlots:
            slot["deleteHandler"]()

    def stop(self):
        self.releaseCamera()
        self.destroy()

    def getImages(self):
        return [image["path"] for image in self.images]


class XrecogProgressDialog(QtWidgets.QDialog):
    def __init__(self, title=None, max=None):
        super(XrecogProgressDialog, self).__init__()
        uic.loadUi(translatePath("progress_dialog.ui"), self)
        self.setWindowFlags(QtCore.Qt.WindowMaximizeButtonHint)
        self.installEventFilter(self)
        if max:
            self.progressBar.setMaximum(max)
            self.progressBar.setValue(0)
        if title:
            self.setWindowTitle(title)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.KeyPress:
            if event.key() == QtCore.Qt.Key_Escape:
                return True
        return super(QtWidgets.QDialog, self).eventFilter(obj, event)


class XrecogPreviewWindow(QtWidgets.QDialog, EventEmitter):
    def __init__(self):
        super(XrecogPreviewWindow, self).__init__()
        uic.loadUi(translatePath("reportpreview.ui"), self)
        self.isPreviewing = False
        self.previewText = None
        self.formatComboBox.currentIndexChanged.connect(
            lambda index: self.load(self.comboSlots[index]))
        self.loadPreviewButton.clicked.connect(self.handleLoadPreview)
        self.printButton.setDisabled(True)
        self.printButton.clicked.connect(
            lambda: self.emit("print", self.previewTextBrowser))
        self.actionPrintPreview.triggered.connect(
            lambda: self.emit("printPreview", self.previewTextBrowser))
        self.saveButton.clicked.connect(self.save)

    def handleLoadPreview(self):
        self.printButton.setDisabled(False)
        self.loadPreviewButton.hide()
        self.setPreview(forcePreview=True)

    def setPreview(self, content=None, forcePreview=False):
        self.previewText = self.previewText or content
        self.isPreviewing = self.isPreviewing or forcePreview
        if self.isPreviewing:
            self.previewTextBrowser.setHtml(self.previewText)

    comboSlots = []
    loaderMap = {}

    def setLoader(self, type, title, loader):
        if (type not in self.loaderMap):
            self.loaderMap[type] = {}
        self.loaderMap[type]["data"] = None
        self.loaderMap[type]["title"] = title
        self.loaderMap[type]["loader"] = loader
        self.comboSlots.append(type)
        self.formatComboBox.blockSignals(True)
        self.formatComboBox.addItem(title)
        self.formatComboBox.blockSignals(False)

    def save(self):
        key = self.comboSlots[self.formatComboBox.currentIndex()]
        self.emit("saveFile", key, self.loaderMap[key]["data"])

    def load(self, type):
        self.formatComboBox.blockSignals(True)
        self.formatComboBox.setCurrentIndex(self.comboSlots.index(type))
        self.formatComboBox.blockSignals(False)
        typeStack = self.loaderMap[type]
        if typeStack["data"] is None:
            typeStack["data"] = typeStack["loader"]()
        self.rawGroupBox.setTitle(self.tr(typeStack["title"]))
        self.rawTextEdit.setPlainText(typeStack["data"])


class XrecogMainWindow(QtWidgets.QMainWindow, EventEmitter):
    def __init__(self):
        super(XrecogMainWindow, self).__init__()
        uic.loadUi(translatePath("xrecog.ui"), self)
        self.query = set()
        self.courses = []
        self.aboutText = None
        self.capture_window = None
        self.matriculationCodeValidator = None
        self.prepareAttendance()
        self.prepareRegistration()
        self.preparePrint()
        self.actionAbout.triggered.connect(self.showAbout)
        self.actionResetAttendance.triggered.connect(self.resetAttendance)
        self.recordLock = threading.Lock()
        self.studentsLock = threading.Lock()

    def closeEvent(self, event):
        self.emit("windowClose")
        return super(QtWidgets.QMainWindow, self).closeEvent(event)

    def showAbout(self):
        dialog = QtWidgets.QDialog()
        uic.loadUi(translatePath("about.ui"), dialog)
        if self.aboutText:
            dialog.aboutText.setPlainText(self.tr(self.aboutText))
        dialog.exec_()

    def setAboutText(self, text):
        self.aboutText = text

    def registerDispatcher(self, objectName):
        return lambda *args: self.emit(objectName, *args)

    statUpdateSignal = QtCore.pyqtSignal()

    @QtCore.pyqtSlot()
    def updateStats(self):
        absentStudents = len(self.matric_records["absent"])
        presentStudents = len(self.matric_records["present"])
        self.totalLineEdit.setText(
            "%d" % (presentStudents + absentStudents))
        self.presentLineEdit.setText("%d" % presentStudents)
        self.absentLineEdit.setText("%d" % absentStudents)

    def initStudentsLoader(self):
        self.studentLoaderQueue = queue.Queue()
        self.studentLoaderJobs = Parallelizer(
            self.studentLoaderQueue.get, 4, self._addStudent)
        self.studentLoaderJobs.start()

        def clearStudentLoaderJobs():
            self.studentLoaderJobs.pause()
            [dq, self.studentLoaderQueue.queue] = [
                self.studentLoaderQueue.queue, deque()]
            self.studentLoaderJobs.resume()
            dq.append(None)
            for studentStack in iter(dq.popleft, None):
                studentStack["event"].set()
        self._clearStudentLoaderJobs = clearStudentLoaderJobs

        def cancelStudentLoaderJobs():
            self.studentLoaderJobs.cancel()
            clearStudentLoaderJobs()
            self.studentLoaderQueue.put(None)
        self.on("windowClose", cancelStudentLoaderJobs)

    def _addStudent(self, studentStack):
        student = {
            **studentStack["student"],
            "isPresent": threading.Event(),
            "handleLock": threading.Lock(),
        }
        with student["handleLock"]:
            if bool(student["markPresent"]):
                student["isPresent"].set()
            del student["markPresent"]
            with self.studentsLock:
                if student["matriculationCode"] in self.students:
                    studentStack["event"].set()
                    return
                self.students[student["matriculationCode"]] = student
            self._pushRow(student)
            studentStack["event"].set()

    xRowSignal = QtCore.pyqtSignal(str, str, int, threading.Event)

    @QtCore.pyqtSlot(str, str, int, threading.Event)
    def _xRowHandler(self, type, key, index, event):
        if type not in ("add", "rm"):
            raise ValueError("Unexpected rowHandler type [%s]" % type)
        table = self.presentTable if key == "present" else self.absentTable
        (table.insertRow if type == "add" else table.removeRow)(index)
        event.set()

    def initStudentsMarker(self):
        self.studentMarkerQueue = queue.Queue()
        self.studentMarkerJobs = Parallelizer(
            self.studentMarkerQueue.get, 2, self._markStudent)
        self.studentMarkerJobs.start()

        def cancelStudentMarkerJobs():
            self.studentMarkerJobs.cancel()
            [dq, self.studentMarkerQueue.queue] = [
                self.studentMarkerQueue.queue, deque()]
            self.studentMarkerQueue.put(None)
            dq.append(None)
            for student in iter(dq.popleft, None):
                student["isPresent"].set()
        self.on("windowClose", cancelStudentMarkerJobs)

    def _markStudent(self, student):
        matricCode = student["matriculationCode"]
        with student["handleLock"]:
            if student["isPresent"].isSet():
                return
            with self.recordLock:
                with self.logr("<markPresent> Matric lookup in records [%s]" % matricCode):
                    index = self.matric_records["absent"].index(matricCode)
                with self.logr("<markPresent> Matric remove from records [%s]" % matricCode):
                    del self.matric_records["absent"][index]
                self.xRowSignal.emit("rm", "absent", index, threading.Event())
            with self.logr(
                "<markPresent> Push student into present table [%s]" % matricCode,
                "<markPresent> Pushed student into present table [%s]" % matricCode,
                reenter=True
            ):
                student["isPresent"].set()
                self._pushRow(student)
        self.log("<markPresent> Marked student as present [%s]" % matricCode)
        self.emit("foundStudent", student)

    def initQueryValidator(self):
        self.lookupLock = threading.Lock()
        self.stop_lookup = threading.Event()
        self.validatorQueue = queue.Queue()
        self.validatorJobs = Parallelizer(
            self.validatorQueue.get, 2, self._validateQuery)
        self.validatorJobs.start()

        def cancelValidatorJobs():
            self.validatorJobs.cancel()
            self.validatorQueue.queue.clear()
            self.validatorQueue.put(None)
        self.on("windowClose", cancelValidatorJobs)

    def _validateQuery(self, studentObject, doCancel):
        student = studentObject["student"]
        searchFields = [student["firstName"], student["middleName"], student["lastName"],
                        str(student["entryYear"]), student["matriculationCode"], self.courses[student["courseOfStudy"]]]
        table = self.presentTable \
            if student["isPresent"].isSet() \
            else self.absentTable
        if self.query and not all(any(
            text in part
            for value in searchFields
            if not doCancel()
            for part in filter(bool, value.lower().split(' '))
            if not doCancel()
        ) for text in self.query if not doCancel()):
            table.hideRow(studentObject["index"])
        elif not doCancel() and table.isRowHidden(studentObject["index"]):
            table.showRow(studentObject["index"])

    def _pushRow(self, student):
        self.log("<_pushRow> Creating student row on table")

        with self.recordLock:
            (table, key) = (self.presentTable, "present") \
                if student["isPresent"].isSet() \
                else (self.absentTable, "absent")
            record = self.matric_records[key]
            index = len(record)
            record.append(student["matriculationCode"])
            self.statUpdateSignal.emit()
            addedRowEvent = threading.Event()
            self.xRowSignal.emit("add", key, index, addedRowEvent)
        addedRowEvent.wait()
        with self.logr("<_pushRow> Insert row slots"):
            matricItem = QtWidgets.QTableWidgetItem()
            firstNameItem = QtWidgets.QTableWidgetItem()
            middleNameItem = QtWidgets.QTableWidgetItem()
            lastNameItem = QtWidgets.QTableWidgetItem()
            yearItem = QtWidgets.QTableWidgetItem()
            courseItem = QtWidgets.QTableWidgetItem()
            table.setItem(index, 0, matricItem)
            table.setItem(index, 1, firstNameItem)
            table.setItem(index, 2, middleNameItem)
            table.setItem(index, 3, lastNameItem)
            table.setItem(index, 4, yearItem)
            table.setItem(index, 5, courseItem)
        with self.logr("<_pushRow> Set row cell text"):
            matricItem.setText(student["matriculationCode"])
            firstNameItem.setText(student["firstName"])
            middleNameItem.setText(student["middleName"])
            lastNameItem.setText(student["lastName"])
            yearItem.setText("%d" % student["entryYear"])
            courseItem.setText(self.courses[student["courseOfStudy"]])
        self.validatorQueue.put({"index": index, "student": student})

    def resetAttendance(self):
        self.students = {}
        self.matric_records = {"present": deque(), "absent": deque()}
        if hasattr(self, "_clearStudentLoaderJobs"):
            self._clearStudentLoaderJobs()
        self.presentTable.clearContents()
        self.absentTable.clearContents()
        self.presentTable.setRowCount(0)
        self.absentTable.setRowCount(0)
        self.totalLineEdit.setText('0')
        self.presentLineEdit.setText('0')
        self.absentLineEdit.setText('0')

    def prepareAttendance(self):
        self.resetAttendance()
        self.initQueryValidator()
        self.initStudentsLoader()
        self.initStudentsMarker()
        self.absentTable.setColumnWidth(0, 90)
        self.presentTable.setColumnWidth(0, 90)
        self.absentTable.setColumnWidth(4, 49)
        self.presentTable.setColumnWidth(4, 49)
        self.xRowSignal.connect(self._xRowHandler)
        self.statUpdateSignal.connect(self.updateStats)
        self.startCameraButton.clicked.connect(
            self.registerDispatcher("startCameraButtonClicked"))
        self.stopCameraButton.clicked.connect(
            self.registerDispatcher("stopCameraButtonClicked"))
        self.searchLineEdit.textChanged.connect(self.lookupText)

    def setRegistrationYearRange(self, min, max):
        self.yearSpinBox.setMinimum(min)
        self.yearSpinBox.setMaximum(max)

    def initRegistrationCapture(self):
        self.capture_window = self.capture_window or XrecogCaptureWindow()
        self.capture_window.init()
        self.capture_window.exec_()

    def clearRegistrationForm(self):
        self.firstNameLineEdit.clear()
        self.middleNameLineEdit.clear()
        self.lastNameLineEdit.clear()
        self.yearSpinBox.setValue(self.yearSpinBox.minimum())
        self.matricNumberLineEdit.clear()
        self.courseComboBox.clearEditText()
        if (self.capture_window):
            self.capture_window.cleanup()

    def resetRegistrationForm(self):
        self.clearRegistrationForm()
        if (self.capture_window):
            self.capture_window.stop()
        self.capture_window = XrecogCaptureWindow()

    def setMatricValidator(self, validator):
        self.matriculationCodeValidator = validator

    def collateRegistrationData(self):
        firstName = ensureValid(self.firstNameLineEdit,
                                self.firstNameLineEdit.text())
        middleName = ensureValid(self.middleNameLineEdit,
                                 self.middleNameLineEdit.text(), lambda data: True)
        lastName = ensureValid(self.lastNameLineEdit,
                               self.lastNameLineEdit.text())
        entryYear = ensureValid(self.yearSpinBox,
                                self.yearSpinBox.text(), int)
        matriculationCode = ensureValid(self.matricNumberLineEdit,
                                        self.matricNumberLineEdit.text(), self.matriculationCodeValidator)
        courseOfStudy = ensureValid(self.courseComboBox,
                                    self.courseComboBox.currentIndex(), lambda index: index >= 0)
        capturedImages = ensureValid(self.captureButton,
                                     self.capture_window and self.capture_window.getImages(), lambda images: len(images) == 12)
        if (all(x is not None for x in [firstName, middleName, lastName, entryYear,
                                        matriculationCode, courseOfStudy, capturedImages])):
            studentData = {
                "firstName": firstName,
                "middleName": middleName,
                "lastName": lastName,
                "entryYear": int(entryYear),
                "matriculationCode": matriculationCode,
                "courseOfStudy": courseOfStudy,
                "markPresent": False,
                "capturedImages": capturedImages
            }
            self.emit("registrationData", studentData)

    def prepareRegistration(self):
        self.clearRegistrationForm()
        self.captureButton.clicked.connect(self.initRegistrationCapture)
        self.resetButton.clicked.connect(self.resetRegistrationForm)
        self.registerButton.clicked.connect(self.collateRegistrationData)
        hookupStripBGHandler(self.firstNameLineEdit,
                             self.firstNameLineEdit.textChanged)
        hookupStripBGHandler(self.middleNameLineEdit,
                             self.middleNameLineEdit.textChanged)
        hookupStripBGHandler(self.lastNameLineEdit,
                             self.lastNameLineEdit.textChanged)
        hookupStripBGHandler(self.yearSpinBox,
                             self.yearSpinBox.valueChanged)
        hookupStripBGHandler(self.matricNumberLineEdit,
                             self.matricNumberLineEdit.textChanged)
        hookupStripBGHandler(self.courseComboBox,
                             self.courseComboBox.currentTextChanged)
        hookupStripBGHandler(self.captureButton,
                             self.captureButton.clicked)

    def preparePrint(self):
        self.printToolButton.clicked.connect(self.print)
        self.actionPrintPreview.triggered.connect(self.printPreview)
        self.actionReportPreview.triggered.connect(self.showReportPreview)
        self.actionExportCSV.triggered.connect(lambda: self.export("csv"))
        self.actionExportHTML.triggered.connect(lambda: self.export("html"))
        self.actionExportMarkdown.triggered.connect(
            lambda: self.export("markdown"))

    lookupTimer = None

    def lookupText(self, query):
        with self.lookupLock:
            if self.lookupTimer and not self.lookupTimer.finished.isSet():
                self.lookupTimer.cancel()
                self.stop_lookup.set()
                self.lookupTimer.join()
                self.stop_lookup.clear()

            def doQueueLookups(query):
                with self.logr("Looking up query [%s]" % query):
                    query = set(filter(bool, query.lower().split(' ')))
                    if self.query.symmetric_difference(query):
                        self.query = query

                        with self.studentsLock:
                            for student in self.students.values():
                                if self.stop_lookup.isSet():
                                    break
                                (table, key) = (self.presentTable, "present") \
                                    if student["isPresent"].isSet() \
                                    else (self.absentTable, "absent")
                                with self.recordLock:
                                    index = self.matric_records[key].index(
                                        student["matriculationCode"])
                                self.validatorQueue.put(
                                    {"index": index, "student": student})
            self.lookupTimer = threading.Timer(1, doQueueLookups, (query,))
        self.lookupTimer.start()

    def loadCourses(self, courses):
        for course in courses:
            self.courses.append(course)
        self.courseComboBox.clear()
        self.courseComboBox.addItems(courses)
        self.courseComboBox.setCurrentIndex(-1)

    def loadStudents(self, students):
        return [self.loadStudent(student) for student in students]

    def loadStudent(self, student):
        addedEvent = threading.Event()
        self.studentLoaderQueue.put({"student": student, "event": addedEvent})
        return addedEvent

    def markStudents(self, matricCodes):
        return [self.markStudent(matricCode) for matricCode in matricCodes]

    def markStudent(self, matricCode):
        student = self.students[matricCode]
        self.studentMarkerQueue.put(student)
        return student["isPresent"]

    def getAbsentStudentsMatric(self, n=None):
        return [*self.matric_records["absent"]][:n]

    def _dispatch(self, executor, timeout=None, args=(), kwargs=None, *, title=None, message=None, max=None, tickValue=None):
        finished = threading.Event()
        dialog = XrecogProgressDialog(title=title, max=max)

        def logTick(msg=None, progress=None, *, tick=False):
            if type(msg) == int:
                (msg, progress) = (None, msg)
            if progress:
                dialog.progressBar.setValue(progress)
            elif tick and tickValue:
                dialog.progressBar.setValue(
                    dialog.progressBar.value() + tickValue)
            return dialog.label.setText("%s" % (msg or message or "Loading..."))

        def execTarget(*args):
            executor(logTick, *args, **(kwargs or {}))
            dialog.progressBar.setValue(100)
            finished.set()
            dialog.close()

        thread = threading.Thread(target=execTarget, args=args)
        thread.start()

        if timeout:
            time.sleep(timeout)
        if finished.isSet():
            return
        logTick()
        dialog.exec_()

    def log(self, *args, **kwargs):
        force = False
        if "force" in kwargs:
            force = kwargs["force"]
            del kwargs["force"]
        ActingLogger(force=force).print(*args, **kwargs)

    def logr(self, *args, **kwargs):
        return ActingLogger(*args, **kwargs)

    def buildReport(self):
        self.log("<buildReport> Building Report")

        def buildTable(tableName):
            with self.logr("<buildReport> Building [%s] table" % tableName):
                table = [
                    "| Matric Code | First Name | Middle Name | Last Name | Year | Course of Study |",
                    "|-------------|------------|-------------|-----------|------|-----------------|",
                    "|             |            |             |           |      |                 |"
                ]
                if len(self.matric_records[tableName]):
                    table.pop()
                for matric in self.matric_records[tableName]:
                    student = self.students[matric]
                    row = "| %s | %s | %s | %s | %d | %s |" % (
                        student["matriculationCode"],
                        student["firstName"],
                        student["middleName"],
                        student["lastName"],
                        student["entryYear"],
                        self.courses[student["courseOfStudy"]],
                    )
                    table.append(row)
            return table

        presentStudents = len(self.matric_records["present"])
        absentStudents = len(self.matric_records["absent"])

        presentTable = buildTable("present")
        absentTable = buildTable("absent")

        with self.logr("<buildReport> Compiling report"):
            styling = "".join(map(str.strip, [
                "<style>",
                "  body {",
                "    font-family:'Noto Sans';",
                "    font-size:10pt;",
                "    font-weight:400;",
                "    font-style:normal;",
                "  }",
                "  h1 {",
                "    font-size:xx-large;",
                "    font-weight:600;",
                "  }",
                "  table, th, td {",
                "    font-size:10pt;",
                "    border: 1px solid black;",
                "  }",
                "</style>"]))
            markdown = [
                styling,
                "# xRecog Report at %s" % datetime.now().strftime("%I:%M %p on %d-%m-%Y"),
                "",
                "|    Statistics    | Count |",
                "|------------------|-------|",
                "| Total Students   | %s    |" % "%d " % (
                    presentStudents + absentStudents),
                "| [Present Students](#present-students) | %s    |" % "%d " % presentStudents,
                "| [Absent Students](#absent-students)  | %s    |" % "%d " % absentStudents,
                "",
                "## Present Students",
                "",
                *presentTable,
                "",
                "## Absent Students",
                "",
                *absentTable,
                "",
                "<sub style='color: grey'>Attendance report autogenerated by xRecog</sub>"
            ]
        with self.logr("<buildReport> Merging markdown lines"):
            markdown = '\n'.join(markdown)
        self.log("<buildReport> Done building report")
        return markdown

    def buildReportDocument(self):
        self.log("<buildReportDocument>")
        report = self.buildHTMLReport()
        document = QtGui.QTextDocument()
        with self.logr("<buildReportDocument> Creating document"):
            document.setHtml(report)
        return document

    def showReportPreview(self):
        self.log("<showReportPreview> Opening Report Preview Dialog")
        dialog = XrecogPreviewWindow()
        report = self.buildReport()
        html = self.buildHTMLReportFrom(report)
        with self.logr("<showReportPreview> Setting HTML Preview"):
            dialog.setPreview(html)
        dialog.setLoader("csv", "CSV", self.buildCSV)
        dialog.setLoader("html", "HTML", lambda: html)
        dialog.setLoader("markdown", "Markdown", lambda: report)
        dialog.on("print", self.printFor)
        dialog.on("saveFile", self.export)
        dialog.on("printPreview", self.printPreviewFor)
        with self.logr("<showReportPreview> Loading markdown preview"):
            dialog.load("markdown")
        with self.logr("<showReportPreview> Launching report window"):
            dialog.show()
        dialog.exec_()

    def buildCSV(self):
        self.log("<buildCSV> Building CSV")
        document = "matric_code,first_name,middle_name,last_name,is_present,year,course_of_study\n"
        with self.logr("<buildCSV> Compiling CSV records"):
            document += '\n'.join([
                ','.join([
                    student["matriculationCode"],
                    student["firstName"],
                    student["middleName"],
                    student["lastName"],
                    '1' if student["isPresent"].isSet() else '0',
                    str(student["entryYear"]),
                    self.courses[student["courseOfStudy"]]
                ])
                for student in self.students.values()])
        self.log(
            "<buildCSV> Successfully built CSV Report")
        return document

    def buildHTMLReportFrom(self, report):
        self.log("<buildHTMLReportFrom> Building HTML Report from markdown report")
        with self.logr("<buildHTMLReport> Preparing HTML document"):
            document = markdown2.markdown(
                report, extras=["tables", "header-ids"])
        self.log(
            "<buildHTMLReportFrom> Successfully built HTML Report from markdown report")
        return document

    def buildHTMLReport(self):
        self.log("<buildHTMLReport> Building HTML Report")
        document = self.buildHTMLReportFrom(self.buildReport())
        self.log("<buildHTMLReport> Successfully built HTML Report")
        return document

    file_maps = {
        "csv": {
            "title": "CSV",
            "handler": buildCSV,
            "last_file": None,
            "save_filters": "CSV File (*.csv)",
        },
        "html": {
            "title": "HTML",
            "handler": buildHTMLReport,
            "last_file": None,
            "save_filters": "HTML File (*.html)",
        },
        "markdown": {
            "title": "Markdown",
            "handler": buildReport,
            "last_file": None,
            "save_filters": "Markdown File (*.md)",
        },
    }

    def export(self, type, document=None):
        stack = self.file_maps[type]
        self.log("<export> Exporting %s" % stack["title"])
        document = document or stack["handler"](self)
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save %s File" % stack["title"], stack["last_file"] or os.getcwd(), stack["save_filters"])
        if filename:
            stack["last_file"] = filename
            with self.logr(
                    "<export> Saving requested %s report to %s" % (stack["title"], filename)):
                with open(filename, 'w') as file:
                    file.write(document)
        else:
            self.log("<export> Save %s cancelled by user" % stack["title"])

    def printDocument(self, document):
        self.log("<printDocument> Printing document")
        with self.logr("<printDocument> Starting Print"):
            dialog = QtPrintSupport.QPrintDialog()
            if dialog.exec_() == QtWidgets.QDialog.Accepted:
                document.print_(dialog.printer())

    def printDocumentPreview(self, document):
        with self.logr("<printDocumentPreview> Rendering to print preview"):
            dialog = QtPrintSupport.QPrintPreviewDialog()
            dialog.paintRequested.connect(
                lambda printer: document.print_(printer))
            dialog.exec_()

    def print(self):
        self.log("<print> Printing document")
        self.printDocument(self.buildReportDocument())
        self.log("<print> Successfully Printed document")

    def printFor(self, report):
        self.log("<printFor> Printing document for HTML document report")
        self.printDocument(report)
        self.log("<printFor> Successfully Printed document for HTML document report")

    def printPreview(self):
        self.log("<printPreview> Printing Preview")
        self.printDocumentPreview(self.buildReportDocument())
        self.log("<printPreview> Successfully Printed Preview")

    def printPreviewFor(self, report):
        self.log("<printPreviewFor> Printing Preview for HTML document report")
        self.printDocumentPreview(report)
        self.log(
            "<printPreviewFor> Successfully Printed Preview for HTML document report")


class ActingLogger:
    entry_time = exit_time = None

    def __init__(self, entry=None, exit=None, reenter=False, is_async=False, end="", force=False, entry_kwargs=None, exit_kwargs=None):
        self.entry_tuple = () if entry is None else (
            entry,) if type(entry) is not tuple else entry
        self.entry_kwargs = entry_kwargs or {}
        self.exit_tuple = ("done",) if exit is None else (
            exit,) if type(exit) is not tuple else exit
        self.exit_kwargs = exit_kwargs or {}
        self.reenter = reenter
        self.is_async = is_async
        self.end_str = end
        self.do_print = force or os.environ.get("DEBUG_UI") == '1'

    def print(self, *args, **kwargs):
        if not self.do_print:
            return
        self.entry_time = datetime.now()
        print("[%s]" % self.entry_time, *args, **kwargs)

    def __enter__(self):
        kwargs = {"end": self.end_str or "...",
                  "flush": True} if not self.reenter else {}
        self.print(*self.entry_tuple, **kwargs, **self.entry_kwargs)
        return self

    def __exit__(self, *args):
        if not self.is_async:
            self.done()

    def done(self):
        if not self.do_print:
            return
        self.exit_time = datetime.now()

        delta = (self.exit_time - self.entry_time).total_seconds()
        delta = "(%ss)" % ("%d" %
                           delta if delta.is_integer() else "%.4f" % delta)
        print(*self.exit_tuple, delta, flush=True, **self.exit_kwargs) \
            if not self.reenter else \
            print("[%s]" % self.exit_time, *self.exit_tuple, "%s" %
                  delta, flush=True, **self.exit_kwargs)


CSS_BG_RED = "background-color: rgb(223, 36, 15);"


def hookupStripBGHandler(object: QtWidgets.QLineEdit, event):
    event.connect(lambda: object.setStyleSheet(
        object.styleSheet().replace(CSS_BG_RED, "")))


def ensureValid(object, value, validifier=None):
    try:
        valid = bool(validifier(value) if validifier else value)
    except:
        valid = False
    if (not valid):
        object.setStyleSheet(CSS_BG_RED)
        return None
    return value


def translatePath(file):
    return os.path.join(os.path.dirname(os.path.realpath(__file__)), file)
