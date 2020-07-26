from core import extract_embeddings
from core import recognize_video
from core import train_model
import sys
from ui import QtWidgets, XrecogMainWindow
from ui import resources_rc


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


def main():
    app = QtWidgets.QApplication(sys.argv)
    main_window = XrecogMainWindow()
    main_window.show()
    app.exec_()


if __name__ == "__main__":
    extractEmbeddings()
    trainModel()
    recognizeVideo()
    # main()
