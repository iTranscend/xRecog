import sys
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QDialog, QApplication, QWidget
from PyQt5.QtWidgets import QVBoxLayout, QTabWidget, QLabel
from PyQt5.QtMultimedia import *
from PyQt5.QtMultimediaWidgets import *

class TabDialog(QDialog):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Tab Widget Application")
        self.setWindowIcon(QIcon("icon.png"))

        tabwidget = QTabWidget()
        tabwidget.addTab(FirstTab(), "First Tab")
        tabwidget.addTab(TabTwo(), "Second Tab")

        vboxLayout = QVBoxLayout()
        vboxLayout.addWidget(tabwidget)

        self.setLayout(vboxLayout)

class FirstTab(QWidget):
    def __init__(self):
        super().__init__()
        tab_one_label_one = QLabel("tab_one_label_one")
        tab_one_label_two = QLabel("tab_one_label_two")
        
        first_layout = QVBoxLayout()
        first_layout.addWidget(tab_one_label_one)
        first_layout.addWidget(tab_one_label_two)
        self.setLayout(first_layout)

class TabTwo(QWidget):
    def __init__(self):
        super().__init__()
        tab_two_label_one = QLabel("tab_two_label_one")
        tab_two_label_two = QLabel("tab_two_label_two")
        
        second_layout = QVBoxLayout()
        second_layout.addWidget(tab_two_label_one)
        second_layout.addWidget(tab_two_label_two)
        self.setLayout(second_layout)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    tabdialog = TabDialog()
    tabdialog.show()
    app.exec()