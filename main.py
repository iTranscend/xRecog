import threading
import shutil
import mysql
import yaml
import sys
import os
from xrecogcore import XRecogCore
from ui import QtWidgets, XrecogMainWindow
from mysql import connector


def getCoursesFromDatabase():
    try:
        cursor = connection.cursor(prepared=True)
        cursor.execute("SELECT * FROM courses;")
        return [name for (_, name) in cursor.fetchall()]
    finally:
        cursor.close()


def getStudentsFromDatabase():
    try:
        cursor = connection.cursor(prepared=True)
        cursor.execute("SELECT * FROM attendees;")
        return [
            {
                "firstName": firstName,
                "middleName": middleName,
                "lastName": lastName,
                "entryYear": entryYear,
                "matriculationCode": matriculationCode,
                "courseOfStudy": courseOfStudy,
                "markPresent": markPresent
            }
            for (
                firstName,
                middleName,
                lastName,
                entryYear,
                matriculationCode,
                courseOfStudy,
                markPresent) in cursor.fetchall()
            if matriculationCode != '0000'
        ]
    finally:
        cursor.close()


def sqlErrorHandler(err):
    print("Error while connecting to MySQL", err.__repr__())


def attendanceErrorHandler(err):
    if isinstance(err, connector.Error):
        sqlErrorHandler(err)
    else:
        print(
            "[ERROR] An unknown error occurred with the attendance capture dialog:", err.__repr__())


def resetAttendance():
    cursor = connection.cursor(prepared=True)
    cursor.execute(
        "UPDATE attendees SET isPresent = 0 WHERE isPresent = 1;")
    connection.commit()
    cursor.close()
    # hacky workaround, find a better way
    main_window.loadStudents(getStudentsFromDatabase())


def verifyAsPresent(matricCode):
    if matricCode != "0000":
        main_window.markStudent(matricCode)
        cursor = connection.cursor(prepared=True)
        cursor.execute(
            f"UPDATE attendees SET isPresent = 1 WHERE matricCode LIKE \"{matricCode}\";")
        connection.commit()
        cursor.close()


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
    main_window.loadStudent(student)

    def processStudent(logTick):
        logTick("Preparing student stage...", 8)
        os.mkdir(STUDENTDIR)
        nImages = len(student["capturedImages"])
        imagePaths = []
        for (index, imagePath) in enumerate(student["capturedImages"]):
            logTick("Saving student image [%02d/%02d]..." %
                    (index, nImages), tick=(42 / nImages))
            newPath = os.path.join(STUDENTDIR, "%02d.jpg" % index)
            shutil.move(student["capturedImages"][index], newPath)
            xrecogCore.addImage(student["matriculationCode"], newPath)
        logTick("Registering student, please wait...", 80)
        cursor = connection.cursor(prepared=True)
        cursor.execute(
            f"""
            INSERT INTO `attendees`
            (firstName, middleName, lastName, entryYear, matricCode, courseOfStudy, isPresent)
            VALUES
            (
                '{student["firstName"]}',
                '{student["middleName"]}',
                '{student["lastName"]}',
                '{student["entryYear"]}',
                '{student["matriculationCode"]}',
                '{student["courseOfStudy"]}',
                '{int(student["markPresent"])}'
            )
            """
        )
        connection.commit()
        cursor.close()
        logTick("Analyzing student's face...", 100)
        xrecogCore.quantifyFaces()
        logTick("Finalizing student registration...")

    main_window._dispatch(
        processStudent,
        max=100,
        tickValue=1,
        timeout=1,
        title="Registering"
    )
    main_window.resetRegistrationForm()


def lookupMatric(matric):
    if matric != "0000":
        student = main_window.students.get(matric, {})
        firstName = student.get("firstName", None)
        lastName = student.get("lastName", None)
        return ("%s %s" % (firstName, lastName)) if firstName and lastName else firstName or matric


def startCameraButtonClicked(*args):
    print("startCameraButtonClicked")

    def startCameraHandler():
        xrecogCore.initRecognizer(
            lookupLabel=lookupMatric,
            cameraDevice=CONFIG.get("prefs", {}).get("camera_device", 0),
            imageDisplayHandler=main_window.attendanceCaptureDialog.installDisplayHandler,
            markAsPresent=verifyAsPresent
        )
    main_window.attendanceCaptureDialog.init()
    threading.Thread(target=startCameraHandler).start()
    main_window.attendanceCaptureDialog.exec_()


def tabChanged(index):
    if index == 0:
        # NOTE:
        #   tab changed from `register` to `attendance`.
        #   this was originally inteneded to serve as a signal
        #   to register students to save multiple call might just
        #   be a trivial issue but might lag if performance is
        #   a priority. if that ever happens, heres a hint for a fix
        #    * check if any new students were registered since we
        #    * entered the `register` tab
        #    * if so, spawn a thread to register them all
        #    * it might help to use main_window._dispatch() to
        #    * launch a progress window like in registerStudent()
        pass


def mountMainInstance():
    yearObject = CONFIG.setdefault("year", {})
    main_window.setRegistrationYearRange(
        yearObject.setdefault("min", 2014),
        yearObject.setdefault("max", 2023)
    )

    main_window.loadCourses(getCoursesFromDatabase())
    main_window.loadStudents(getStudentsFromDatabase())
    main_window.setAboutText(
        "xRecog\n\nApp Description\n\n2020 (c) Femi Bankole, Miraculous Owonubi")
    main_window.on("tabChanged", tabChanged)
    main_window.on("resetAttendance", resetAttendance)
    main_window.on("registrationData", registerStudent)
    main_window.on("startCameraButtonClicked", startCameraButtonClicked)
    main_window.attendanceCaptureDialog.on("error", attendanceErrorHandler)


def prepareBaseFacialVectors(addStudent):
    from imutils import paths
    print("[INFO] preparing base image store...")
    pQueue = {}
    addStudent(
        "0000",
        list(paths.list_images(os.path.join(
            CONFIG
            .get("prefs", {})
            .get("dataset", "core/dataset"),
            "0000"
        ))),
        pQueue
    )
    return pQueue


if __name__ == "__main__":
    if (not os.path.exists("core/output")):
        os.mkdir("core/output")
    app = QtWidgets.QApplication(sys.argv)
    global CONFIG, main_window, xrecogCore, connection
    if os.path.exists("config.yml"):
        with open("config.yml") as conf:
            CONFIG = yaml.safe_load(conf)
            if not CONFIG:
                print(
                    "[INFO] configuration file \"config.yml\" wasn't successfully loaded, falling back to defaults")
                CONFIG = {}
    else:
        print("[WARN] configuration file \"config.yml\" does not exist, using defaults")
        CONFIG = {}

    xrecogCore = XRecogCore(
        detector="core/face_detection_model",
        embedding_model="core/openface_nn4.small2.v1.t7",
        confidence=float(CONFIG.get("model", {}).get("confidence", 0.5)),
        prepareBaseFacialVectors=prepareBaseFacialVectors
    )
    try:
        print("[INFO] initializing MySQL Connection...")
        database_opts = CONFIG.get("database", {})
        connection_opts = database_opts.get("connection", {})
        auth_opts = database_opts.get("auth", {})
        connection = connector.connect(
            host=str(connection_opts.get("host", "localhost")),
            port=int(connection_opts.get("port", 3306)),
            database=str(database_opts.get("name", "xrecog")),
            user=str(auth_opts.get("user", "root")),
            password=str(auth_opts.get("pass", "")))
        main_window = XrecogMainWindow()
        main_window.show()
        mountMainInstance()
        app.exec_()
        print("[INFO] closing MySQL Connection...")
        if (connection.is_connected()):
            connection.close()
            print("[INFO] closed MySQL connection")
        print("[INFO] dumping model state...")
        xrecogCore.dump()
    except connector.Error as err:
        sqlErrorHandler(err)
