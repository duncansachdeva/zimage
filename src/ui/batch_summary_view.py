from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QHeaderView

class BatchSummaryView(QDialog):
    def __init__(self, summary_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Batch Operation Summary")
        self.resize(600, 400)

        layout = QVBoxLayout(self)

        # Display main summary details
        summary_label = QLabel(self.format_summary(summary_data))
        summary_label.setStyleSheet('font-size: 14px;')
        layout.addWidget(summary_label)

        # If there are error details, display them in a table
        if 'errors' in summary_data and summary_data['errors']:
            table = QTableWidget()
            errors = summary_data['errors']
            table.setRowCount(len(errors))
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(["Image", "Error"])
            for row, error in enumerate(errors):
                # error expected to be a tuple (image, error message) or a dict
                if isinstance(error, (list, tuple)) and len(error) >= 2:
                    image_name = str(error[0])
                    error_msg = str(error[1])
                else:
                    image_name = "Unknown"
                    error_msg = str(error)
                img_item = QTableWidgetItem(image_name)
                err_item = QTableWidgetItem(error_msg)
                table.setItem(row, 0, img_item)
                table.setItem(row, 1, err_item)
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            layout.addWidget(table)

    def format_summary(self, summary_data):
        # Constructs a text summary from the data dictionary excluding errors
        parts = []
        for key, value in summary_data.items():
            if key != 'errors':
                parts.append(f"{key.title()}: {value}")
        return "\n".join(parts) 