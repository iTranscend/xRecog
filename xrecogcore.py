from sklearn.preprocessing import LabelEncoder
from imutils.video import VideoStream
from imutils.video import FPS
from sklearn.svm import SVC
import numpy as np
import imutils
import pickle
import time
import cv2
import os
import mysql.connector
from mysql.connector import Error
from itertools import zip_longest


def loads(file=None, constructor=None):
    assert file or callable(constructor)
    if os.path.exists(file):
        with open(file, "rb") as f:
            bytes = f.read()
            if len(bytes):
                return pickle.loads(bytes)
    return constructor()


def dumps(object, file):
    with open(file, "wb") as f:
        pickle.dumps(object)


"""
xRecogCore = XRecogCore()
xRecogCore.addStudent(<matricNumber>, images=[<image>,...])
xRecogCore.addStudent(<matricNumber>, images=[<image>,...])
xRecogCore.dump() -> {<matricNumber>: <vector>,...}
"""


class XRecogCore(object):
    def __init__(self, *, detector, confidence, embedding_model):
        super().__init__()
        self.labelEncoder = loads(
            "core/output/le.pickle", lambda: LabelEncoder())
        self.svcRecognizer = loads(
            "core/output/recognizer.pickle", lambda: SVC(C=1.0, kernel="linear", probability=True))

        # load our serialized face detector from disk
        print("[INFO] loading face detector...")
        protoPath = os.path.sep.join([detector, "deploy.prototxt"])
        modelPath = os.path.sep.join(
            [detector, "res10_300x300_ssd_iter_140000.caffemodel"])
        self.detector = cv2.dnn.readNetFromCaffe(protoPath, modelPath)

        # load our serialized face embedding model from disk
        print("[INFO] loading face recognizer...")
        self.embedder = cv2.dnn.readNetFromTorch(embedding_model)

        self.confidence = confidence

        self.processQueue = []

    def dump(self):
        dumps(self.labelEncoder, "core/output/le.pickle")
        dumps(self.svcRecognizer, "core/output/recognizer.pickle")

    def addStudent(self, matricCode, images):
        for (index, imagePath) in enumerate(images):
            print("[INFO] processing image {}/{}".format(index + 1, len(images)))
            # load the image, resize it to have a width of 600 pixels (while
            # maintaining the aspect ratio), and then grab the image
            # dimensions
            image = cv2.imread(imagePath)
            image = imutils.resize(image, width=600)
            (h, w) = image.shape[:2]

            # construct a blob from the image
            imageBlob = cv2.dnn.blobFromImage(
                cv2.resize(image, (300, 300)), 1.0, (300, 300),
                (104.0, 177.0, 123.0), swapRB=False, crop=False)

            # apply OpenCV's deep learning-based face detector to localize
            # faces in the input image
            self.detector.setInput(imageBlob)
            detections = self.detector.forward()

            # ensure at least one face was found
            if len(detections) > 0:
                # we're making the assumption that each image has only ONE
                # face, so find the bounding box with the largest probability
                i = np.argmax(detections[0, 0, :, 2])
                confidence = detections[0, 0, i, 2]

                # ensure that the detection with the largest probability also
                # means our minimum probability test (thus helping filter out
                # weak detections)
                if confidence > self.confidence:
                    # compute the (x, y)-coordinates of the bounding box for
                    # the face
                    box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                    (startX, startY, endX, endY) = box.astype("int")

                    # extract the face ROI and grab the ROI dimensions
                    face = image[startY:endY, startX:endX]
                    (fH, fW) = face.shape[:2]

                    # ensure the face width and height are sufficiently large
                    if fW < 20 or fH < 20:
                        continue

                    # construct a blob for the face ROI, then pass the blob
                    # through our face embedding model to obtain the 128-d
                    # quantification of the face
                    faceBlob = cv2.dnn.blobFromImage(face, 1.0 / 255,
                                                     (96, 96), (0, 0, 0), swapRB=True, crop=False)
                    self.embedder.setInput(faceBlob)
                    vec = self.embedder.forward()

                    # add the name of the person + corresponding face
                    # embedding to their respective lists
                    # TODO: LabelEncoder fit transform & recognizer fit embeddings
                    self.processQueue.append((matricCode, vec.flatten()))

    def quantifyFaces(self):
        (names, vectors) = zip_longest(*self.processQueue)
        labelEncoder = LabelEncoder()
        labels = labelEncoder.fit_transform(names)

        svcRecognizer = SVC(C=1.0, kernel="linear", probability=True)
        svcRecognizer.fit(vectors, labels)

        self.labelEncoder, self.svcRecognizer = labelEncoder, svcRecognizer

        self.dump()

    def initRecognizer(self, endHandle, *, cameraDevice=0):
        # initialize the video stream, then allow the camera sensor to warm up
        print("[INFO] starting video stream...")
        vs = VideoStream(src=cameraDevice).start()
        time.sleep(2.0)

        # start the FPS throughput estimator
        fps = FPS().start()

        try:
            # connection = mysql.connector.connect(
            #     host='localhost', database='attendance', user='root', password='')
            # loop over frames from the video file stream
            while not endHandle.isSet():
                # grab the frame from the threaded video stream
                frame = vs.read()

                # resize the frame to have a width of 600 pixels (while
                # maintaining the aspect ratio), and then grab the image
                # dimensions
                frame = imutils.resize(frame, width=600)
                (h, w) = frame.shape[:2]

                # construct a blob from the image
                imageBlob = cv2.dnn.blobFromImage(
                    cv2.resize(frame, (300, 300)), 1.0, (300, 300),
                    (104.0, 177.0, 123.0), swapRB=False, crop=False)

                # apply OpenCV's deep learning-based face detector to localize
                # faces in the input image
                self.detector.setInput(imageBlob)
                detections = self.detector.forward()

                # loop over the detections
                for i in range(0, detections.shape[2]):
                    # extract the confidence (i.e., probability) associated with
                    # the prediction
                    confidence = detections[0, 0, i, 2]

                    # filter out weak detections
                    if confidence > self.confidence:
                        # compute the (x, y)-coordinates of the bounding box for
                        # the face
                        box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                        (startX, startY, endX, endY) = box.astype("int")

                        # extract the face ROI
                        face = frame[startY:endY, startX:endX]
                        (fH, fW) = face.shape[:2]

                        # ensure the face width and height are sufficiently large
                        if fW < 20 or fH < 20:
                            continue

                        # construct a blob for the face ROI, then pass the blob
                        # through our face embedding model to obtain the 128-d
                        # quantification of the face
                        faceBlob = cv2.dnn.blobFromImage(face, 1.0 / 255,
                                                         (96, 96), (0, 0, 0), swapRB=True, crop=False)
                        self.embedder.setInput(faceBlob)
                        vec = self.embedder.forward()

                        # perform classification to recognize the face
                        preds = self.svcRecognizer.predict_proba(vec)[0]
                        j = np.argmax(preds)
                        proba = preds[j]
                        name = self.labelEncoder.classes_[j]

                        # draw the bounding box of the face along with the
                        # associated probability
                        text = "{}: {:.2f}%".format(name, proba * 100)
                        y = startY - 10 if startY - 10 > 10 else startY + 10
                        cv2.rectangle(frame, (startX, startY), (endX, endY),
                                      (0, 0, 255), 2)
                        cv2.putText(frame, text, (startX, y),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.45, (0, 0, 255), 2)

                        # print(type(name))
                        # print(type(text))
                        # Update the database

                        # if connection.is_connected():
                        # 	db_Info = connection.get_server_info()
                        # 	print('Connected to server: ', db_Info)

                        # cursor = connection.cursor(prepared=True)
                        # cursor = connection.cursor()
                        # sql = "UPDATE attendees SET is_present = 1 WHERE matric_no LIKE %s;"
                        casted = str(name).strip()
                        val = (casted)
                        # cursor.execute(sql, (casted, ))
                        # cursor.execute(sql)

                        # connection.commit()
                        print(val)
                        # print(type(casted))

                # update the FPS counter
                fps.update()

                # show the output frame
                cv2.imshow("Frame", frame)
                key = cv2.waitKey(1) & 0xFF

                # if the `q` key was pressed, break from the loop
                if key == ord("q"):
                    break

        except Error as e:
            print("Error while connecting to MySQL", e)
        # finally:
        #     if (connection.is_connected()):
        #         cursor.close()
        #         connection.close()
        #         print("MySQL connection is closed")

        # stop the timer and display FPS information
        fps.stop()
        print("[INFO] elasped time: {:.2f}".format(fps.elapsed()))
        print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))

        # do a bit of cleanup
        cv2.destroyAllWindows()
        vs.stop()
