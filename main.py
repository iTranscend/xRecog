import core.extract_embeddings
import core.recognize_video
import core.train_model
import sys
from ui import QtWidgets, XrecogMainWindow
from ui import resources_rc


def extractEmbeddings():
    args = {
        "dataset": "dataset",
        "embeddings": "output/embeddings.pickle",
        "detector": "face_detection_model",
        "embedding-model": "openface_nn4.small2.v1.t7"
    }
    extract_embeddings.init(args)


def trainModel():
    args = {
        "embeddings": "output/embeddings.pickle",
        "recognizer": "output/recognizer.pickle",
        "le": "output/le.pickle"
    }
    train_model.init(args)


def recognizeVideo():
    args = {
        "detector": "face_detection_model",
        "embedding-model": "openface_nn4.small2.v1.t7",
        "recognizer": "output/recognizer.pickle",
        "le": "output/le.pickle"
    }
    recognize_video.init(args)


def main():
    app = QtWidgets.QApplication(sys.argv)
    main_window = XrecogMainWindow()
    main_window.show()
    app.exec_()


if __name__ == "__main__":
    main()
