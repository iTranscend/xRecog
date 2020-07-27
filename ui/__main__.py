import os
import sys
import random
import resources_rc
from faker import Faker
from __init__ import XrecogMainWindow, QtWidgets


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
    ]
    with main_window.logr("Loading %d courses" % len(courses)):
        main_window.loadCourses(courses)

    with main_window.logr("Generating %d students" % num_students):
        students = []
        faker = Faker()
        for index in range(0, num_students):
            students.append({
                'firstName': faker.first_name(),
                'middleName': faker.first_name(),
                'lastName': faker.last_name(),
                'entryYear': random.randint(MIN_YEAR, MAX_YEAR + 1),
                'matriculationCode': "%04d" % random.randint(0, 10000),
                'courseOfStudy': random.randint(0, len(courses) - 1),
                'markPresent': False
            })

    with main_window.logr("Populating UI with %d students" % len(students)):
        main_window.loadStudents(students)

    main_window.setAboutText(
        "xRecog\n\nApp Description\n\n2020 (c) Femi Bankole")
    main_window.setRegistrationYearRange(MIN_YEAR, MAX_YEAR)

    def handleTestRegData(data):
        main_window.addStudent(data)
        print("Full Name: %s%s %s" % (
            data["firstName"],
            " %s" % data["middleName"] if data["middleName"] else "",
            data["lastName"],
        ))
        print("Entry Year: %d" % data["entryYear"])
        print("Matriculation Code: %s" % data["matriculationCode"])
        print("Course of study: %s" % courses[data["courseOfStudy"]])
        print("Mark as present: %s" % "yes" if data["markPresent"] else "no")
        print("Captured Images:")
        for image in data["capturedImages"]:
            # os.rename(image["path"], os.path.join(dir, "%02d" % index))
            print(" > %s" % image)
            os.unlink(image)
        main_window.resetRegistrationForm()

    main_window.on('registrationData', handleTestRegData)

    def startAttendanceCamera(*args):
        print("stopCameraButtonClicked")
        students = main_window.getAbsentStudentsMatric()
        foundStudents = random.sample(
            students, k=random.randint(0, len(students)))
        print("Found %d student%s" %
              (len(foundStudents), "" if len(foundStudents) == 1 else "s"))
        if (len(foundStudents) == 0):
            return
        for student in foundStudents:
            main_window.markPresent(student)

    main_window.on('startCameraButtonClicked', startAttendanceCamera)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("xRecog")
    main_window = XrecogMainWindow()
    mountTestInstance(main_window)
    main_window.show()
    app.exec_()
