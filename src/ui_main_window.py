# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.10.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractScrollArea, QApplication, QFrame, QGridLayout,
    QHBoxLayout, QListView, QMainWindow, QPushButton,
    QSizePolicy, QSpacerItem, QStatusBar, QVBoxLayout,
    QWidget)

from gui.action_stacked_widget import ActionStackedWidget
from gui.expanding_splitter import ExpandingSplitter
from gui.hiding_listview import HidingListView
from . import icons_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1060, 851)
        MainWindow.setStyleSheet(u"")
        MainWindow.setUnifiedTitleAndToolBarOnMac(False)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.centralwidget.sizePolicy().hasHeightForWidth())
        self.centralwidget.setSizePolicy(sizePolicy)
        self.gridLayout = QGridLayout(self.centralwidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.splitter = ExpandingSplitter(self.centralwidget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setLineWidth(0)
        self.splitter.setOrientation(Qt.Orientation.Horizontal)
        self.splitter.setHandleWidth(0)
        self.sidebar = QWidget(self.splitter)
        self.sidebar.setObjectName(u"sidebar")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.sidebar.sizePolicy().hasHeightForWidth())
        self.sidebar.setSizePolicy(sizePolicy1)
        self.verticalLayout = QVBoxLayout(self.sidebar)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.verticalLayout.setStretch(0, 6)
        self.splitter.addWidget(self.sidebar)
        self.listView = HidingListView(self.splitter)
        self.listView.setObjectName(u"listView")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.listView.sizePolicy().hasHeightForWidth())
        self.listView.setSizePolicy(sizePolicy2)
        self.listView.setMinimumSize(QSize(0, 0))
        self.listView.setMaximumSize(QSize(16777215, 16777215))
        self.listView.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        self.listView.setResizeMode(QListView.ResizeMode.Adjust)
        self.splitter.addWidget(self.listView)

        self.gridLayout.addWidget(self.splitter, 1, 0, 1, 1)

        self.titleBar = QHBoxLayout()
        self.titleBar.setSpacing(0)
        self.titleBar.setObjectName(u"titleBar")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.titleBar.addItem(self.horizontalSpacer)

        self.minimizePushButton = QPushButton(self.centralwidget)
        self.minimizePushButton.setObjectName(u"minimizePushButton")
        icon = QIcon()
        icon.addFile(u":/icons/minimize.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.minimizePushButton.setIcon(icon)
        self.minimizePushButton.setIconSize(QSize(16, 16))
        self.minimizePushButton.setFlat(True)

        self.titleBar.addWidget(self.minimizePushButton)

        self.maximizePushButton = QPushButton(self.centralwidget)
        self.maximizePushButton.setObjectName(u"maximizePushButton")
        icon1 = QIcon()
        icon1.addFile(u":/icons/maximize.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.maximizePushButton.setIcon(icon1)
        self.maximizePushButton.setIconSize(QSize(16, 16))
        self.maximizePushButton.setFlat(True)

        self.titleBar.addWidget(self.maximizePushButton)

        self.closePushButton = QPushButton(self.centralwidget)
        self.closePushButton.setObjectName(u"closePushButton")
        icon2 = QIcon()
        icon2.addFile(u":/icons/close.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.closePushButton.setIcon(icon2)
        self.closePushButton.setIconSize(QSize(16, 16))
        self.closePushButton.setFlat(True)

        self.titleBar.addWidget(self.closePushButton)


        self.gridLayout.addLayout(self.titleBar, 0, 0, 1, 2)

        self.stackedWidget = ActionStackedWidget(self.centralwidget)
        self.stackedWidget.setObjectName(u"stackedWidget")
        self.stackedWidget.setFrameShape(QFrame.Shape.Box)
        self.stackedWidget.setFrameShadow(QFrame.Shadow.Plain)

        self.gridLayout.addWidget(self.stackedWidget, 1, 1, 1, 1)

        self.gridLayout.setRowStretch(0, 1)
        self.gridLayout.setRowStretch(1, 20)
        self.gridLayout.setColumnStretch(0, 1)
        self.gridLayout.setColumnStretch(1, 3)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        self.stackedWidget.setCurrentIndex(-1)


        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.minimizePushButton.setText("")
        self.maximizePushButton.setText("")
        self.closePushButton.setText("")
    # retranslateUi

