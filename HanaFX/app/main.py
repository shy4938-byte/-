import sys
from pathlib import Path
from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QApplication
from .dashboard import Window


def main():
    app=QApplication(sys.argv);app.setOrganizationName('HanaFX');app.setApplicationName('HanaFX')
    location=Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation));location.mkdir(parents=True,exist_ok=True)
    window=Window(location/'hanafx.sqlite3');window.show();return app.exec()
