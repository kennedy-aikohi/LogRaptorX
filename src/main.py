"""
LogRaptorX - High-Performance Windows Log Parser
Developer: Kennedy Aikohi
GitHub: https://github.com/kennedy-aikohi
LinkedIn: https://www.linkedin.com/in/aikohikennedy/
Version: 1.0.0
"""

import sys
import os

# Ensure the src directory is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from ui.main_window import MainWindow


def main():
    # Enable high DPI support
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("LogRaptorX")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Kennedy Aikohi")
    app.setOrganizationDomain("github.com/kennedy-aikohi")

    # Apply global stylesheet
    from ui.theme import DARK_THEME
    app.setStyleSheet(DARK_THEME)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
