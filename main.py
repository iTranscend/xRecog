import threading
import shutil
import yaml
import sys
import os
from xrecogcore import XRecogCore
from ui import QtWidgets, XrecogMainWindow


def getStudentsFromDatabase():
    return []


def registerStudent(student):
    print("registerStudent[matric=%s]: %s%s %s" % (
        student["matriculationCode"],
        student["firstName"],
        " %s" % student["middleName"] if student["middleName"] else "",
        student["lastName"],
    ))
    STUDENTDIR = os.path.join(
        CONFIG.get("prefs", {}).get("dataset", "core/dataset"),
        student["matriculationCode"])
    os.mkdir(STUDENTDIR)
    imagePaths = []
    for (index, imagePath) in enumerate(student["capturedImages"]):
        newPath = os.path.join(STUDENTDIR, "%02d.jpg" % index)
        shutil.move(student["capturedImages"][index], newPath)
        imagePaths.append(newPath)
    xrecogCore.addStudent(student["matriculationCode"], imagePaths)
    main_window.loadStudent(student)
    main_window.resetRegistrationForm()
    # this will currently fail, since there is only (at this moment)
    # one buffered student with data, ready to be processed
    # proposed fix:
    #  • either find a means to add new labels
    #    and teach the model new faces in real time
    #  • or, recompute the labels and teach the model everytime
    threading.Thread(target=xrecogCore.quantifyFaces).start()


def lookupMatric(matric):
    return matric


def startCameraButtonClicked(*args):
    print("startCameraButtonClicked")

    def startCameraHandler():
        xrecogCore.initRecognizer(
            lookupLabel=lookupMatric,
            cameraDevice=CONFIG.get("prefs", {}).get("camera_device", 0),
            imageDisplayHandler=main_window.attendanceCaptureDialog.installDisplayHandler
        )
    main_window.attendanceCaptureDialog.init()
    threading.Thread(target=startCameraHandler).start()
    main_window.attendanceCaptureDialog.exec_()


def tabChanged(index):
    if index == 0:
        # tab changed from `register` to `attendance`
        # check if there are any new students
        # if so, spawn a thread to register them all
        pass


def mountMainInstance():
    yearObject = CONFIG.get("year", {"min": 2014, "max": 2023})
    main_window.setRegistrationYearRange(
        yearObject.get("min"),
        yearObject.get("max")
    )

    main_window.loadCourses(CONFIG.get("courses", []))
    main_window.loadStudents(getStudentsFromDatabase())
    main_window.setAboutText("APP DESCRIPTION")
    main_window.on("tabChanged", tabChanged)
    main_window.on("registrationData", registerStudent)
    main_window.on("startCameraButtonClicked", startCameraButtonClicked)


if __name__ == "__main__":
    if (not os.path.exists("core/output")):
        os.mkdir("core/output")
    app = QtWidgets.QApplication(sys.argv)
    global CONFIG, main_window, xrecogCore
    with open("config.yml") as conf:
        CONFIG = yaml.safe_load(conf)

    xrecogCore = XRecogCore(
        detector="core/face_detection_model",
        embedding_model="core/openface_nn4.small2.v1.t7",
        confidence=0.5
    )
    main_window = XrecogMainWindow()
    main_window.show()
    mountMainInstance()
    app.exec_()
    print("[INFO] Dumping model state...")
    xrecogCore.dump()
