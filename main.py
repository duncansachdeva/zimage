import sys
from PyQt6.QtWidgets import QApplication
from src.core.theme_manager import ThemeManager
from src.ui.main_window import MainWindow


if __name__ == '__main__':
    app = QApplication(sys.argv)
    theme_manager = ThemeManager(app)  # Instantiate ThemeManager
    window = MainWindow(theme_manager)  # Pass theme_manager to MainWindow
    window.show()
    sys.exit(app.exec()) 