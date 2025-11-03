from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QApplication, QGridLayout, QLabel, QListView,
    QListWidget, QListWidgetItem, QPlainTextEdit, QPushButton,
    QSizePolicy, QSpacerItem, QWidget)

class VoltageUnitCalPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gridLayout = QGridLayout()
        self.setLayout(self.gridLayout)
        self.gridLayout.setObjectName(u"gridLayout")
        self.pushButton_2 = QPushButton()
        self.pushButton_2.setObjectName(u"pushButton_2")
        self.gridLayout.addWidget(self.pushButton_2, 2, 0, 1, 1)
        self.listWidget = QListWidget()
        self.listWidget.setObjectName(u"listWidget")
        self.listWidget.setMovement(QListView.Movement.Static)
        self.listWidget.setProperty(u"isWrapping", False)
        self.listWidget.setResizeMode(QListView.ResizeMode.Adjust)
        self.listWidget.setViewMode(QListView.ViewMode.IconMode)

        self.gridLayout.addWidget(self.listWidget, 5, 1, 1, 1)

        self.label = QLabel()
        self.label.setObjectName(u"label")
        self.label.setText("Voltage Unit Calibration")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 2)
        self.pushButton = QPushButton()
        self.pushButton.setObjectName(u"pushButton")
        self.gridLayout.addWidget(self.pushButton, 1, 0, 1, 1)
        self.pushButton_3 = QPushButton()
        self.pushButton_3.setObjectName(u"pushButton_3")
        self.gridLayout.addWidget(self.pushButton_3, 3, 0, 1, 1)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.gridLayout.addItem(self.verticalSpacer, 4, 0, 2, 1)

        self.plainTextEdit = QPlainTextEdit()
        self.plainTextEdit.setObjectName(u"plainTextEdit")
        self.plainTextEdit.setReadOnly(True)  # no typing / no paste
        self.plainTextEdit.setUndoRedoEnabled(False)  # no undo buffer
        self.plainTextEdit.setTextInteractionFlags(  # allow copy/select only
            Qt.TextInteractionFlag.TextSelectableByMouse)
        self.plainTextEdit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)  # don’t wrap long lines
        self.plainTextEdit.setMaximumBlockCount(10000)
        self.log()
        self.gridLayout.addWidget(self.plainTextEdit, 1, 1, 4, 1)

        self.gridLayout.setRowStretch(1, 2)
        self.gridLayout.setRowStretch(3, 1)
        self.gridLayout.setRowStretch(4, 3)
        self.gridLayout.setRowStretch(5, 1)


    def log(self):
        self.plainTextEdit.appendPlainText("""/home/tdds/PycharmProjects/HardwareGUI/.venv/bin/python /home/tdds/PycharmProjects/HardwareGUI/src/main.py 
        Bound listview to role 261
        set property as 1
        Invoked
        Requested for page id workbench
        Called for page id workbench
        current widget <src.gui.scripts.voltage_unit_cal.VoltageUnitCalPage(0x1f04c100) at 0x7610e1aea080>

        Process finished with exit code 0""")