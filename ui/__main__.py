import os
import sys
import random
import threading
from faker import Faker

from . import (
    QtWidgets,
    Parallelizer,
    XrecogMainWindow,
)


def mountTestInstance(main_window):
    MIN_YEAR = 2014
    MAX_YEAR = 2023

    args = sys.argv[1:]
    num_students = int(args[0]) if len(args) else 10000

    courses = [
        "Computer Science",
        "Physics",
        "Chemistry",
        "Law",
        "Sociology",
        "Political Sciences",
        "Art",
        "Philosophy",
        "Music",
        "Anthropology",
        "Psychology",
        "English",
        "Astrophysics",
        "Biology",
        "Geography",
        "Physiotheraphy",
        "Medicine",
        "French",
        "Statistics",
        "Biochemistry",
        "Cybersecurity",
        "Criminology",
        "Economics",
        "Epidemiology",
        "Statistics",
        "Mathematics"
    ]
    with main_window.logr(
            "Loading %d course%s" % (len(courses), "" if len(courses) == 1 else 's'), force=True):
        main_window.loadCourses(courses)

    max_students = max(10000, num_students)

    with main_window.logr("Generating %d student%s" % (num_students, "" if num_students == 1 else 's'), force=True):
        faker = Faker()
        students = []
        pad = len(str(num_students))
        matric_numbers = random.sample(range(0, max_students), num_students)

        def newStudent(matric_number):
            male = bool(random.getrandbits(1))
            students.append({
                "firstName": faker.first_name_male() if male else faker.first_name_female(),
                "middleName": faker.first_name_male() if male else faker.first_name_female(),
                "lastName": faker.last_name_male() if male else faker.last_name_female(),
                "entryYear": random.randint(MIN_YEAR, MAX_YEAR + 1),
                "matriculationCode": f"%0{pad}d" % matric_number,
                "courseOfStudy": random.randint(0, len(courses) - 1),
                "markPresent": False
            })
        studentJobs = Parallelizer(matric_numbers, min(
            num_students, 100 if num_students >= 80000 else 8), newStudent)
        studentJobs.start()
        studentJobs.joinAll()

    with main_window.logr(
        "Populating UI with %d student%s" % (
            len(students), "" if len(students) == 1 else 's'),
        "Populated UI with %d student%s" % (
            len(students), "" if len(students) == 1 else 's'),
        reenter=True, force=True, is_async=True
    ) as logr:
        jobs = main_window.loadStudents(students)

        def handle():
            for job in jobs:
                job.wait()
            logr.done()
        threading.Thread(target=handle).start()

    main_window.setAboutText(
        "xRecog\n\nApp Description\n\n2020 (c) Femi Bankole, Miraculous Owonubi")
    main_window.setRegistrationYearRange(MIN_YEAR, MAX_YEAR)

    def handleTestRegData(data):
        main_window.loadStudent(data)
        print("Full Name: %s%s %s" % (
            data["firstName"],
            " %s" % data["middleName"] if data["middleName"] else "",
            data["lastName"],
        ))
        print("Entry Year: %d" % data["entryYear"])
        print("Matriculation Code: %s" % data["matriculationCode"])
        print("Course of study: %s" % courses[data["courseOfStudy"]])
        print("Mark as present: %s" % ("yes" if data["markPresent"] else "no"))
        print("Captured Images:")
        for image in data["capturedImages"]:
            print(" > %s" % image)
            os.unlink(image)
        main_window.resetRegistrationForm()

    main_window.on("registrationData", handleTestRegData)

    def startAttendanceCamera(*args):
        main_window.log("<startAttendanceCamera>")
        students = main_window.getAbsentStudentsMatric()
        length = random.randint(
            0, len(students) and (int(.4 * len(students)) or len(students)))
        foundStudents = random.sample(students, k=length)
        end = "" if length == 1 else 's'
        main_window.log("<startAttendanceCamera> Found %d student%s" %
                        (length, end), force=True)
        if (length == 0):
            return
        with main_window.logr(
            "<startAttendanceCamera> Marking %s student%s" % (length, end),
            "<startAttendanceCamera> Marked %s student%s" % (length, end),
            reenter=True, force=True, is_async=True
        ) as logr:
            jobs = main_window.markStudents(foundStudents)

            def handle():
                for job in jobs:
                    job.wait()
                logr.done()
        threading.Thread(target=handle).start()

    main_window.on("startCameraButtonClicked", startAttendanceCamera)


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("xRecog")
    main_window = XrecogMainWindow()
    main_window.show()
    mountTestInstance(main_window)
    app.exec_()
