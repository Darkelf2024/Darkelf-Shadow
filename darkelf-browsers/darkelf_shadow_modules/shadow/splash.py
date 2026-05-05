# shadow/splash.py

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QProgressBar
from PySide6.QtGui import QFont


class BootSplash(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setFixedSize(420, 200)

        layout = QVBoxLayout(self)

        self.title = QLabel("Darkelf Shadow")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setFont(QFont("Arial", 18, QFont.Bold))

        self.status = QLabel("Initializing...")
        self.status.setAlignment(Qt.AlignCenter)

        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setFormat("%p%")

        layout.addStretch()
        layout.addWidget(self.title)
        layout.addWidget(self.status)
        layout.addWidget(self.bar)
        layout.addStretch()

        self.setStyleSheet("""
            QWidget {
                background-color: #0d0f12;
                color: #A855F7;
            }
            QProgressBar {
                border: 1px solid #222;
                height: 18px;
                text-align: center;
                background: #111;
                color: black;
            }
            QProgressBar::chunk {
                background-color: #A855F7;
            }
        """)
