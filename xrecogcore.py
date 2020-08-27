from sklearn.preprocessing import LabelEncoder
from imutils.video import VideoStream
from imutils.video import FPS
from sklearn.svm import SVC
import numpy as np
import imutils
import pickle
import cv2
import os
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
        f.write(pickle.dumps(object))


"""
xRecogCore = XRecogCore()
xRecogCore.addStudent(<matricNumber>, images=[<image>,...])
xRecogCore.addStudent(<matricNumber>, images=[<image>,...])
xRecogCore.dump() -> {<matricNumber>: <vector>,...}
"""


class XRecogCore(object):
    def __init__(self, *, detector, confidence, embedding_model, prepareBaseFacialVectors):
        super().__init__()

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

        self.labelEncoder = loads(
            "core/output/le.pickle", lambda: LabelEncoder())
        self.processQueue = loads(
            "core/output/pqueue.pickle", lambda: prepareBaseFacialVectors(self._addStudent))
        self.svcRecognizer = loads(
            "core/output/recognizer.pickle", lambda: SVC(C=1.0, kernel="linear", probability=True))

    def dump(self):
        dumps(self.labelEncoder, "core/output/le.pickle")
        dumps(self.processQueue, "core/output/pqueue.pickle")
        dumps(self.svcRecognizer, "core/output/recognizer.pickle")

    def addStudent(self, matricCode, images):
        self._addStudent(matricCode, images, self.processQueue)

    def addImage(self, matricCode, image):
        print("[INFO] processing image for [{}] {}/{}".format(matricCode))
        self._addImage(matricCode, image, self.processQueue)

    def _addStudent(self, matricCode, images, pQueue):
        for (index, imagePath) in enumerate(images):
            print("[INFO] processing image {}/{}".format(index + 1, len(images)))
            self._addImage(matricCode, imagePath, pQueue)

    def _addImage(self, matricCode, imagePath, pQueue):
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
                    return

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
                pQueue \
                    .setdefault(matricCode, []) \
                    .append(vec.flatten())

    def quantifyFaces(self):
        # this is expensive, try to limit calls as much as possible
        (names, vectors) = zip_longest(
            *[
                (name, vectors)
                for name in self.processQueue
                for vectors in self.processQueue[name]
            ])
        labelEncoder = LabelEncoder()
        labels = labelEncoder.fit_transform(names)

        svcRecognizer = SVC(C=1.0, kernel="linear", probability=True)
        svcRecognizer.fit(vectors, labels)

        self.labelEncoder, self.svcRecognizer = labelEncoder, svcRecognizer

        self.dump()

    def initRecognizer(self, *, lookupLabel, markAsPresent, imageDisplayHandler=None, cameraDevice=0):
        assert callable(lookupLabel)
        assert callable(markAsPresent)
        assert callable(imageDisplayHandler)

        # initialize the video stream, then allow the camera sensor to warm up
        print("[INFO] starting video stream...")
        vs = VideoStream(src=cameraDevice).start()

        # start the FPS throughput estimator
        fps = FPS().start()

        def readFrameAndDisplay(setFrameImage):
            # grab the frame from the threaded video stream
            frame = vs.read()
            if frame is None:
                return

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
                    cv2.rectangle(frame, (startX, startY), (endX, endY),
                                  (194, 188, 200), 2)

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
                    matricCode = self.labelEncoder.classes_[j]
                    name = lookupLabel(matricCode)
                    if proba < self.confidence:
                        continue
                    if name:
                        # draw the bounding box of the face along with the
                        # associated probability
                        text = "{}: {:.2f}%".format(name, proba * 100)
                        y = startY - 10 if startY - 10 > 10 else startY + 10
                        cv2.putText(frame, text, (startX, y),
                                    cv2.FONT_HERSHEY_COMPLEX, 0.55, (0, 0, 256), 2)

                        print("DETECTED [%s] (confidence=%.2f%%)" %
                              (name, proba * 100))

                    markAsPresent(matricCode)

            # update the FPS counter
            fps.update()

            # show the output frame
            setFrameImage(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))

        # loop over frames from the video file stream
        imageDisplayHandler(readFrameAndDisplay)

        # stop the timer and display FPS information
        fps.stop()
        print("[INFO] elasped time: {:.2f}".format(fps.elapsed()))
        print("[INFO] approx. FPS: {:.2f}".format(fps.fps()))
        vs.stop()
