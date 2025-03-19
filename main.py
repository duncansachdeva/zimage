import sys
from PyQt6.QtWidgets import QApplication
from src.core.theme_manager import ThemeManager
from src.ui.main_window import MainWindow

print("Starting application...")

if __name__ == '__main__':
    print("Creating QApplication...")
    app = QApplication(sys.argv)
    print("Creating ThemeManager...")
    theme_manager = ThemeManager(app)
    print("Creating MainWindow...")
    window = MainWindow(theme_manager)
    print("Showing window...")
    window.show()
    print("Starting event loop...")
    sys.exit(app.exec()) 