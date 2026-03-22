import os
import re
import secrets

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QFileDialog
)

from PySide6.QtCore import Qt


# ---------------------------------------------------------
# Safe download directory
# ---------------------------------------------------------

def safe_download_dir():

    desktop = os.path.join(os.path.expanduser("~"), "Desktop")

    folder = os.path.join(desktop, "Darkelf Temp Folder")

    os.makedirs(folder, exist_ok=True)

    return folder


# ---------------------------------------------------------
# Randomized filename generator
# ---------------------------------------------------------

def randomized_filename(suggested):

    suggested = (suggested or "download").strip()

    suggested = re.sub(r"[^A-Za-z0-9._-]+", "_", suggested)[:120]

    base, ext = os.path.splitext(suggested)

    token = secrets.token_hex(6)

    base = (base[:60] or "download")

    ext = ext[:12]

    return f"{base}_{token}{ext}"


# ---------------------------------------------------------
# Download widget
# ---------------------------------------------------------

class DownloadItem(QWidget):

    def __init__(self, download):
        super().__init__()

        self.download = download

        layout = QVBoxLayout(self)

        self.label = QLabel(download.suggestedFileName())
        self.label.setAlignment(Qt.AlignLeft)

        self.progress = QProgressBar()
        self.progress.setValue(0)

        self.open_button = QPushButton("Open Folder")
        self.open_button.setEnabled(False)

        layout.addWidget(self.label)
        layout.addWidget(self.progress)
        layout.addWidget(self.open_button)

        self.download.downloadProgress.connect(self._on_progress)
        self.download.finished.connect(self._on_finished)

        self.open_button.clicked.connect(self._open_folder)

    # -----------------------------------------------------

    def _on_progress(self, received, total):

        if total > 0:
            percent = int(received * 100 / total)
            self.progress.setValue(percent)

    # -----------------------------------------------------

    def _on_finished(self):

        self.progress.setValue(100)

        self.open_button.setEnabled(True)

    # -----------------------------------------------------

    def _open_folder(self):

        path = self.download.path()

        folder = os.path.dirname(path)

        if os.path.exists(folder):

            os.startfile(folder)


# ---------------------------------------------------------
# Download shelf
# ---------------------------------------------------------

class DownloadShelf(QWidget):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Downloads")

        self.layout = QVBoxLayout(self)

        self.items = []

    # -----------------------------------------------------

    def add_download(self, download):

        filename = randomized_filename(download.suggestedFileName())

        folder = safe_download_dir()

        path = os.path.join(folder, filename)

        download.setPath(path)

        download.accept()

        item = DownloadItem(download)

        self.layout.addWidget(item)

        self.items.append(item)

        self.show()


# ---------------------------------------------------------
# Helper for connecting profile downloads
# ---------------------------------------------------------

def install_download_handler(profile, shelf):

    profile.downloadRequested.connect(shelf.add_download)
