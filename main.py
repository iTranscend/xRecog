from core import extract_embeddings
from core import recognize_video
from core import train_model
import yaml
import sys
import os
from ui import QtWidgets, XrecogMainWindow


def extractEmbeddings():
    args = {
        "dataset": "core/dataset",
        "embeddings": "core/output/embeddings.pickle",
        "detector": "core/face_detection_model",
        "embedding_model": "core/openface_nn4.small2.v1.t7",
        "confidence": 0.5
    }
    extract_embeddings.init(args)


def trainModel():
    args = {
        "embeddings": "core/output/embeddings.pickle",
        "recognizer": "core/output/recognizer.pickle",
        "le": "core/output/le.pickle"
    }
    train_model.init(args)


def recognizeVideo():
    args = {
        "detector": "core/face_detection_model",
        "embedding_model": "core/openface_nn4.small2.v1.t7",
        "recognizer": "core/output/recognizer.pickle",
        "le": "core/output/le.pickle",
        "confidence": 0.5
    }
    recognize_video.init(args)


def getStudentsFromDatabase():
    return []


def registerStudent(student):
    print("registerStudent")
    # extractEmbeddings()
    # trainModel()
    main_window.loadStudent(student)
    # create student folder
    # save images
    main_window.resetRegistrationForm()


def startCameraButtonClicked(*args):
    print("startCameraButtonClicked")
    # recognizeVideo()


def stopCameraButtonClicked(*args):
    print("stopCameraButtonClicked")


def mountMainInstance():
    with open("config.yml") as conf:
        CONFIG = yaml.safe_load(conf)

    yearObject = CONFIG.get("year", {"min": 2014, "max": 2023})
    main_window.setRegistrationYearRange(
        yearObject.get("min"),
        yearObject.get("max")
    )

    main_window.loadCourses(CONFIG.get("courses", []))
    main_window.loadStudents(getStudentsFromDatabase())
    main_window.setAboutText("APP DESCRIPTION")
    main_window.on("registrationData", registerStudent)
    main_window.on("startCameraButtonClicked", startCameraButtonClicked)
    main_window.on("stopCameraButtonClicked", stopCameraButtonClicked)


if __name__ == "__main__":
    if (not os.path.exists("core/output")):
        os.mkdir("core/output")
    app = QtWidgets.QApplication(sys.argv)
    global main_window
    main_window = XrecogMainWindow()
    main_window.show()
    mountMainInstance()
    app.exec_()
