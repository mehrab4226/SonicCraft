"""Single background job; only queued Qt signals cross into the UI."""
from PyQt6.QtCore import QThread, pyqtSignal


class Job(QThread):
    succeeded = pyqtSignal(object)
    failed = pyqtSignal(str)

    def __init__(self, function, parent=None):
        super().__init__(parent)
        self.function = function

    def run(self):
        try:
            self.succeeded.emit(self.function())
        except Exception as error:
            self.failed.emit(str(error) or type(error).__name__)
