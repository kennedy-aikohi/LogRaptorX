"""
LogRaptorX - Background Workers
Developer: Kennedy Aikohi
"""

from PyQt6.QtCore import QThread, pyqtSignal
from core.parser import ParseEngine, CSVExporter, ParseResult
from core.detections import DetectionEngine, Detection
from typing import List, Optional, Dict


class ParseWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(object)
    error    = pyqtSignal(str)

    def __init__(self, filepaths: List[str], fmt: str = "auto", filters: Optional[Dict] = None):
        super().__init__()
        self.filepaths = filepaths
        self.fmt       = fmt
        self.filters   = filters or {}
        self._engine   = ParseEngine()

    def run(self):
        try:
            result = self._engine.parse_multiple(
                self.filepaths,
                fmt=self.fmt,
                filters=self.filters,
                progress_cb=self._cb,
            )
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def _cb(self, pct, msg):
        self.progress.emit(pct, msg)

    def cancel(self):
        self._engine.cancel()


class DetectionWorker(QThread):
    progress   = pyqtSignal(int, str)
    finished   = pyqtSignal(list)   # List[Detection]
    error      = pyqtSignal(str)

    def __init__(self, entries):
        super().__init__()
        self._entries = entries
        self._engine  = DetectionEngine()

    def run(self):
        try:
            detections = self._engine.scan_all(self._entries, self._cb)
            self.finished.emit(detections)
        except Exception as e:
            self.error.emit(str(e))

    def _cb(self, pct, msg):
        self.progress.emit(pct, msg)


class ExportWorker(QThread):
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(int, str)
    error    = pyqtSignal(str)

    def __init__(self, entries, output_path: str):
        super().__init__()
        self.entries     = entries
        self.output_path = output_path

    def run(self):
        try:
            written = CSVExporter.export(
                self.entries, self.output_path, self._cb
            )
            self.finished.emit(written, self.output_path)
        except Exception as e:
            self.error.emit(str(e))

    def _cb(self, pct, msg):
        self.progress.emit(pct, msg)
