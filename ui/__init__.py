import os
import sys
import random
import tempfile

from PyQt5 import (
    uic,
    QtGui,
    QtCore,
    QtWidgets,
    QtMultimedia,
    QtMultimediaWidgets)


class EventEmitter(object):
    def __init__(self):
        self.handlers = {}

    def on(self, objectName, handler):
        if (objectName not in self.handlers):
            self.handlers[objectName] = []
        self.handlers[objectName].append(handler)

    def emit(self, objectName, *args):
        if (objectName not in self.handlers):
            return
        for handler in self.handlers[objectName]:
            handler(*args)


class XrecogCaptureWindow(QtWidgets.QDialog, EventEmitter):
    closed = QtCore.pyqtSignal()

    def __init__(self):
        super(XrecogCaptureWindow, self).__init__()
        uic.loadUi(translatePath('capture.ui'), self)
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
            slot.hide()
            imageSlot = slot.findChild(QtWidgets.QLabel)
            deleteButton = slot.findChild(QtWidgets.QPushButton)
            slotObject = {"object": slot, "item": None}
            deleteButton.clicked.connect(self.newDeleteHandler(slotObject))
            self.imageSlots.append(slotObject)
        self.viewfinder = QtMultimediaWidgets.QCameraViewfinder()
        self.viewFinderFrame.layout().addWidget(self.viewfinder)

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
        self.closed.emit()
        return super(QtWidgets.QDialog, self).closeEvent(event)

    def prepareHandlers(self):
        self.deviceSelectorReloadButton.clicked.connect(self.scanDevices)
        self.captureButton.clicked.connect(self.captureImage)
        self.deviceSelectorComboBox.currentIndexChanged.connect(
            self.selectCamera)
        self.closed.connect(self.hideWindow)
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
        self.selected_camera = self.available_cameras[index]
        self.camera = QtMultimedia.QCamera(self.selected_camera)
        self.camera.setViewfinder(self.viewfinder)
        self.camera.setCaptureMode(QtMultimedia.QCamera.CaptureStillImage)
        self.camera.statusChanged.connect(lambda status: self.enableCaptureButton(
        ) if status == QtMultimedia.QCamera.ActiveStatus and len(self.images) < 12 else None)
        self.camera.error.connect(
            lambda: self.alert('camera error', self.camera.errorString()))
        self.camera.start()

        self.capture = QtMultimedia.QCameraImageCapture(self.camera)
        self.capture.error.connect(
            lambda i, e, s: self.alert('capture error', s))
        self.capture.imageCaptured.connect(self.imageCaptured)

    def enableCaptureButton(self):
        self.captureButton.setDisabled(False)
        self.captureButton.setFocus(True)

    def captureImage(self):
        save_path = tempfile.mktemp(suffix='.jpg')
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


class XrecogMainWindow(QtWidgets.QMainWindow, EventEmitter):
    def __init__(self):
        super(XrecogMainWindow, self).__init__()
        uic.loadUi(translatePath('xrecog.ui'), self)
        self.capture_window = None
        self.prepareAttendance()
        self.prepareRegistration()
        self.matriculationCodeValidator = None
        self.aboutText = None
        self.query = None
        self.courses = []
        self.resetAttendance()
        self.actionAbout.triggered.connect(self.showAbout)
        self.actionResetAttendance.triggered.connect(self.resetAttendance)

    def resetAttendance(self):
        self.students = {"present": [], "absent": []}
        self.presentTable.clearContents()
        self.absentTable.clearContents()
        self.presentTable.setRowCount(0)
        self.absentTable.setRowCount(0)
        self.totalLineEdit.setText("0")
        self.presentLineEdit.setText("0")
        self.absentLineEdit.setText("0")

    def registerDispatcher(self, objectName):
        return lambda *args: self.emit(objectName, *args)

    def prepareAttendance(self):
        self.startCameraButton.clicked.connect(
            self.registerDispatcher('startCameraButtonClicked'))
        self.stopCameraButton.clicked.connect(
            self.registerDispatcher('stopCameraButtonClicked'))
        self.printButton.clicked.connect(
            self.registerDispatcher('printButtonClicked'))
        self.searchLineEdit.textChanged.connect(self.lookupText)

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

    def initRegistrationCapture(self):
        self.capture_window = self.capture_window or XrecogCaptureWindow()
        self.capture_window.init()
        self.capture_window.exec_()

    def showAbout(self):
        dialog = QtWidgets.QDialog()
        uic.loadUi(translatePath('about.ui'), dialog)
        if self.aboutText:
            dialog.aboutText.setPlainText(self.tr(self.aboutText))
        dialog.exec_()

    def setAboutText(self, text):
        self.aboutText = text

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
            self.emit('registrationData', studentData)

    def setMatricValidator(self, validator):
        self.matriculationCodeValidator = validator

    def setRegistrationYearRange(self, min, max):
        self.yearSpinBox.setMinimum(min)
        self.yearSpinBox.setMaximum(max)

    def loadCourses(self, courses):
        for course in courses:
            self.courses.append(course)
        self.courseComboBox.clear()
        self.courseComboBox.addItems(courses)
        self.courseComboBox.setCurrentIndex(-1)

    def loadStudents(self, students):
        for student in students:
            self.addStudent(student)

    def addStudent(self, student):
        student = {**student}
        markPresent = student['markPresent']
        del student['markPresent']
        if (markPresent):
            self.students['present'].append(student)
        else:
            self.students['absent'].append(student)
        self.pushRow(markPresent, student)

    def pushRow(self, isPresent, student):
        presentStudents = len(self.students['present'])
        absentStudents = len(self.students['absent'])
        self.totalLineEdit.setText("%d" % (presentStudents + absentStudents))
        self.presentLineEdit.setText("%d" % presentStudents)
        self.absentLineEdit.setText("%d" % absentStudents)

        table = self.findChild(QtWidgets.QTableWidget, '%sTable' %
                               ("present" if isPresent else "absent"))
        index = table.rowCount()
        table.insertRow(index)
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
        matricItem.setText(student["matriculationCode"])
        firstNameItem.setText(student["firstName"])
        middleNameItem.setText(student["middleName"])
        lastNameItem.setText(student["lastName"])
        yearItem.setText("%d" % student["entryYear"])
        courseItem.setText(self.courses[student["courseOfStudy"]])
        self.validateQuery(table, index, student)

    def validateQuery(self, table, index, student, query=None):
        query = query or self.query
        searchFields = [student['firstName'], student['middleName'], student['lastName'],
                        str(student['entryYear']), student['matriculationCode'], self.courses[student['courseOfStudy']]]
        if query and not all(any(
                text in part
                for value in searchFields
                for part in filter(bool, value.lower().split(' '))) for text in query):
            table.hideRow(index)
        elif table.isRowHidden(index):
            table.showRow(index)

    def lookupText(self, query):
        query = list(filter(bool, query.lower().split(' ')))
        self.query = query
        for (table, students) in (
                (self.presentTable, self.students['present']),
                (self.absentTable, self.students['absent'])):
            for (index, student) in enumerate(students):
                self.validateQuery(table, index, student, query)

    def markPresent(self, matricCode):
        try:
            (index, student) = next(
                (index, student) for (index, student) in enumerate(self.students['absent']) if student['matriculationCode'] is matricCode)
        except:
            student = None
        if student is None:
            return
        self.students['absent'].remove(student)
        self.students['present'].append(student)
        self.absentTable.removeRow(index)
        self.pushRow(True, student)
        self.emit('foundStudent', student)

    def getAbsentStudentsMatric(self):
        return [student['matriculationCode'] for student in self.students['absent']]


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
