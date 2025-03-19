import sys
import os
sys.path.insert(0, os.path.abspath('.'))
from PyQt6.QtWidgets import QApplication
from src.ui.batch_summary_view import BatchSummaryView


def main():
    app = QApplication(sys.argv)
    dummy_summary = {
        "total_images": 10,
        "processed": 8,
        "failed": 2,
        "duration": "5 minutes",
        "errors": [
            ("image1.jpg", "File not found"),
            ("image2.png", "Unsupported format")
        ]
    }
    dialog = BatchSummaryView(dummy_summary)
    dialog.exec()
    sys.exit(0)


if __name__ == '__main__':
    main() 