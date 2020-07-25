import os
import sys
import random

from __init__ import XrecogMainWindow, QtWidgets


def mountTestInstance():
    students = [
        {
            'firstName': 'Joanna',
            'middleName': 'Emily',
            'lastName': 'Spike',
            'entryYear': 2018,
            'matriculationCode': '8472',
            'courseOfStudy': 0,
            'markPresent': False
        },
        {
            'firstName': 'Jules',
            'middleName': 'Alison',
            'lastName': 'Friday',
            'entryYear': 2019,
            'matriculationCode': '6485',
            'courseOfStudy': 4,
            'markPresent': False
        },
        {
            'firstName': 'Jimmy',
            'middleName': 'Tom',
            'lastName': 'Fellow',
            'entryYear': 2020,
            'matriculationCode': '5578',
            'courseOfStudy': 3,
            'markPresent': False
        },
        {
            'firstName': 'Janet',
            'middleName': 'Relly',
            'lastName': 'Francesca',
            'entryYear': 2019,
            'matriculationCode': '6645',
            'courseOfStudy': 1,
            'markPresent': False
        },
    ]

    courses = [
        "Computer Science",
        "Physics",
        "Chemistry",
        "Law",
        "Sociology",
        "Political Sciences",
        "Art",
    ]

    main_window.loadCourses(courses)
    main_window.loadStudents(students)

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
    main_window.setRegistrationYearRange(2014, 2023)

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
    global main_window, capture_window
    app = QtWidgets.QApplication(sys.argv)
    main_window = XrecogMainWindow()
    mountTestInstance()
    main_window.show()
    app.exec_()
