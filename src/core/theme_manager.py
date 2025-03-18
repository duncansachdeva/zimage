from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor


class ThemeManager:
    def __init__(self, app: QApplication, initial_theme: str = "light"):
        self.app = app
        self.theme = initial_theme
        self.apply_theme(self.theme)

    def toggle_theme(self):
        self.theme = "dark" if self.theme == "light" else "light"
        self.apply_theme(self.theme)

    def set_theme(self, theme: str):
        if theme not in ["light", "dark"]:
            raise ValueError("Theme must be 'light' or 'dark'")
        self.theme = theme
        self.apply_theme(theme)

    def apply_theme(self, theme: str):
        if theme == "light":
            self.app.setPalette(self.light_palette())
            self.app.setStyleSheet("")
        else:
            self.app.setPalette(self.dark_palette())
            self.app.setStyleSheet("")

    def dark_palette(self):
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Text, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
        return palette

    def light_palette(self):
        return self.app.style().standardPalette() 