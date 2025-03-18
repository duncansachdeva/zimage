import sys
from PyQt6.QtWidgets import QApplication
from loguru import logger
import os
from src.core.theme_manager import ThemeManager
from src.ui.main_window import MainWindow

def setup_logging():
    """Setup logging configuration"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    logger.add(
        os.path.join(log_dir, "zimage.log"),
        rotation="10 MB",
        retention="1 week",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    )

def main():
    """Main application entry point"""
    # Setup logging
    setup_logging()
    logger.info("Starting ZImage application")
    
    # Create Qt application
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for consistent look
    
    # Initialize ThemeManager with default theme (light)
    theme_manager = ThemeManager(app, initial_theme="light")

    # Create and show main window
    window = MainWindow(theme_manager)
    window.show()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 