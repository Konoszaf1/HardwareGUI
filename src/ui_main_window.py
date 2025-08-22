# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main_window.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
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
from PySide6.QtWidgets import (QApplication, QGraphicsView, QGridLayout, QHBoxLayout,
    QListView, QMainWindow, QPushButton, QSizePolicy,
    QSpacerItem, QStatusBar, QVBoxLayout, QWidget)

from gui.expanding_sidebar import ExpandingSidebar
from gui.sidebar_button import SidebarButton
import icons_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(745, 549)
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
        self.splitter = ExpandingSidebar(self.centralwidget)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setLineWidth(0)
        self.splitter.setOrientation(Qt.Horizontal)
        self.splitter.setHandleWidth(0)
        self.widget = QWidget(self.splitter)
        self.widget.setObjectName(u"widget")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy1)
        self.verticalLayout = QVBoxLayout(self.widget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.toolButton = SidebarButton(self.widget)
        self.toolButton.setObjectName(u"toolButton")
        sizePolicy1.setHeightForWidth(self.toolButton.sizePolicy().hasHeightForWidth())
        self.toolButton.setSizePolicy(sizePolicy1)
        self.toolButton.setFocusPolicy(Qt.NoFocus)
        icon = QIcon()
        icon.addFile(u":/icons/keyboard.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.toolButton.setIcon(icon)
        self.toolButton.setCheckable(True)
        self.toolButton.setAutoExclusive(True)
        self.toolButton.setArrowType(Qt.NoArrow)

        self.verticalLayout.addWidget(self.toolButton)

        self.toolButton_3 = SidebarButton(self.widget)
        self.toolButton_3.setObjectName(u"toolButton_3")
        sizePolicy1.setHeightForWidth(self.toolButton_3.sizePolicy().hasHeightForWidth())
        self.toolButton_3.setSizePolicy(sizePolicy1)
        self.toolButton_3.setFocusPolicy(Qt.NoFocus)
        icon1 = QIcon()
        icon1.addFile(u":/icons/screen.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.toolButton_3.setIcon(icon1)
        self.toolButton_3.setCheckable(True)
        self.toolButton_3.setChecked(False)
        self.toolButton_3.setAutoExclusive(True)
        self.toolButton_3.setAutoRaise(False)

        self.verticalLayout.addWidget(self.toolButton_3)

        self.toolButton_2 = SidebarButton(self.widget)
        self.toolButton_2.setObjectName(u"toolButton_2")
        sizePolicy1.setHeightForWidth(self.toolButton_2.sizePolicy().hasHeightForWidth())
        self.toolButton_2.setSizePolicy(sizePolicy1)
        self.toolButton_2.setFocusPolicy(Qt.NoFocus)
        icon2 = QIcon()
        icon2.addFile(u":/icons/scanner-image.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.toolButton_2.setIcon(icon2)
        self.toolButton_2.setCheckable(True)
        self.toolButton_2.setAutoExclusive(True)

        self.verticalLayout.addWidget(self.toolButton_2)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.verticalLayout.setStretch(0, 1)
        self.verticalLayout.setStretch(1, 1)
        self.verticalLayout.setStretch(2, 1)
        self.verticalLayout.setStretch(3, 6)
        self.splitter.addWidget(self.widget)
        self.listView = QListView(self.splitter)
        self.listView.setObjectName(u"listView")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.listView.sizePolicy().hasHeightForWidth())
        self.listView.setSizePolicy(sizePolicy2)
        self.listView.setMinimumSize(QSize(0, 0))
        self.listView.setMaximumSize(QSize(16777215, 16777215))
        self.splitter.addWidget(self.listView)

        self.gridLayout.addWidget(self.splitter, 1, 0, 1, 1)

        self.graphicsView = QGraphicsView(self.centralwidget)
        self.graphicsView.setObjectName(u"graphicsView")
        sizePolicy3 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy3.setHorizontalStretch(0)
        sizePolicy3.setVerticalStretch(0)
        sizePolicy3.setHeightForWidth(self.graphicsView.sizePolicy().hasHeightForWidth())
        self.graphicsView.setSizePolicy(sizePolicy3)

        self.gridLayout.addWidget(self.graphicsView, 1, 1, 1, 1)

        self.titleBar = QHBoxLayout()
        self.titleBar.setSpacing(0)
        self.titleBar.setObjectName(u"titleBar")
        self.horizontalSpacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.titleBar.addItem(self.horizontalSpacer)

        self.minimizePushButton = QPushButton(self.centralwidget)
        self.minimizePushButton.setObjectName(u"minimizePushButton")
        icon3 = QIcon()
        icon3.addFile(u":/icons/minimize.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.minimizePushButton.setIcon(icon3)
        self.minimizePushButton.setIconSize(QSize(16, 16))
        self.minimizePushButton.setFlat(True)

        self.titleBar.addWidget(self.minimizePushButton)

        self.maximizePushButton = QPushButton(self.centralwidget)
        self.maximizePushButton.setObjectName(u"maximizePushButton")
        icon4 = QIcon()
        icon4.addFile(u":/icons/maximize.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.maximizePushButton.setIcon(icon4)
        self.maximizePushButton.setIconSize(QSize(16, 16))
        self.maximizePushButton.setFlat(True)

        self.titleBar.addWidget(self.maximizePushButton)

        self.closePushButton = QPushButton(self.centralwidget)
        self.closePushButton.setObjectName(u"closePushButton")
        icon5 = QIcon()
        icon5.addFile(u":/icons/close.png", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.closePushButton.setIcon(icon5)
        self.closePushButton.setIconSize(QSize(16, 16))
        self.closePushButton.setFlat(True)

        self.titleBar.addWidget(self.closePushButton)


        self.gridLayout.addLayout(self.titleBar, 0, 0, 1, 2)

        self.gridLayout.setRowStretch(0, 1)
        self.gridLayout.setRowStretch(1, 20)
        self.gridLayout.setColumnStretch(0, 1)
        self.gridLayout.setColumnStretch(1, 3)
        MainWindow.setCentralWidget(self.centralwidget)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.toolButton.setText(QCoreApplication.translate("MainWindow", u"Keyboard", None))
        self.toolButton_3.setText(QCoreApplication.translate("MainWindow", u"Screen", None))
        self.toolButton_2.setText(QCoreApplication.translate("MainWindow", u"Scanner", None))
        self.minimizePushButton.setText("")
        self.maximizePushButton.setText("")
        self.closePushButton.setText("")
    # retranslateUi

