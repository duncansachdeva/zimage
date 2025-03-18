from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QProgressBar, QFileDialog,
                             QComboBox, QSpinBox, QLineEdit, QMessageBox,
                             QRadioButton, QButtonGroup, QScrollArea)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap
import os
from loguru import logger
from ..core.image_processor import ImageProcessor

class WorkerThread(QThread):
    """Worker thread for processing images"""
    progress = pyqtSignal(int)
    file_progress = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, processor, operation, files, output_dir, naming_option='same', 
                 custom_suffix='', **kwargs):
        super().__init__()
        self.processor = processor
        self.operation = operation
        self.files = files
        self.output_dir = output_dir
        self.naming_option = naming_option
        self.custom_suffix = custom_suffix
        self.kwargs = kwargs
        self._is_cancelled = False
        
    def cancel(self):
        """Cancel the operation"""
        self._is_cancelled = True
        
    def run(self):
        try:
            total = len(self.files)
            for i, file in enumerate(self.files, 1):
                if self._is_cancelled:
                    break
                    
                # Generate output path
                output_path = self.processor.generate_output_path(
                    file, self.output_dir,
                    self.naming_option,
                    self.custom_suffix,
                    i if self.naming_option == 'sequential' else None
                )
                
                if not output_path:
                    self.error.emit(f"Failed to generate output path for {file}")
                    continue
                    
                # Process file
                self.file_progress.emit(f"Processing: {os.path.basename(file)}")
                success = self.processor.process_with_verification(
                    getattr(self.processor, self.operation),
                    file, output_path, **self.kwargs
                )
                
                if not success:
                    self.error.emit(f"Failed to process {file}")
                    
                self.progress.emit(int(i / total * 100))
                
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.processor = ImageProcessor()
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle('ZImage Processor')
        self.setMinimumSize(800, 600)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Split into left and right panels
        h_layout = QHBoxLayout()
        left_panel = QWidget()
        right_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        right_layout = QVBoxLayout(right_panel)
        
        # Left panel - Controls
        # Drag & Drop Area
        self.drop_area = QLabel("Drag and drop images here")
        self.drop_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_area.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 5px;
                padding: 20px;
                background: #f0f0f0;
            }
        """)
        self.drop_area.setMinimumHeight(200)
        left_layout.addWidget(self.drop_area)
        
        # Operations ComboBox
        self.operation_combo = QComboBox()
        self.operation_combo.addItems([
            "Enhance Quality",
            "Resize Image",
            "Reduce File Size",
            "Rotate Image",
            "Add Watermark",
            "Convert to PDF",
            "Convert from PDF"
        ])
        left_layout.addWidget(self.operation_combo)
        
        # Options widget
        self.options_widget = QWidget()
        self.options_layout = QVBoxLayout(self.options_widget)
        left_layout.addWidget(self.options_widget)
        
        # File Naming Options
        naming_group = QWidget()
        naming_layout = QVBoxLayout(naming_group)
        naming_layout.addWidget(QLabel("Output File Naming:"))
        
        self.naming_group = QButtonGroup()
        self.same_name_radio = QRadioButton("Same filename")
        self.custom_name_radio = QRadioButton("Custom suffix")
        self.sequential_name_radio = QRadioButton("Sequential numbering")
        
        self.same_name_radio.setChecked(True)
        self.naming_group.addButton(self.same_name_radio)
        self.naming_group.addButton(self.custom_name_radio)
        self.naming_group.addButton(self.sequential_name_radio)
        
        naming_layout.addWidget(self.same_name_radio)
        naming_layout.addWidget(self.custom_name_radio)
        
        # Custom suffix input
        self.custom_suffix_input = QLineEdit()
        self.custom_suffix_input.setPlaceholder("Enter custom suffix")
        self.custom_suffix_input.setEnabled(False)
        naming_layout.addWidget(self.custom_suffix_input)
        naming_layout.addWidget(self.sequential_name_radio)
        
        left_layout.addWidget(naming_group)
        
        # Progress Section
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        
        # File Progress Label
        self.file_progress_label = QLabel("")
        progress_layout.addWidget(self.file_progress_label)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.process_btn = QPushButton("Process Files")
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setEnabled(False)
        
        button_layout.addWidget(self.process_btn)
        button_layout.addWidget(self.cancel_btn)
        progress_layout.addLayout(button_layout)
        
        left_layout.addWidget(progress_widget)
        
        # Right panel - Preview
        preview_label = QLabel("Preview")
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right_layout.addWidget(preview_label)
        
        # Preview scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(300)
        
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        scroll.setWidget(self.preview_label)
        right_layout.addWidget(scroll)
        
        # Add panels to main layout
        h_layout.addWidget(left_panel, 2)
        h_layout.addWidget(right_panel, 1)
        layout.addLayout(h_layout)
        
        # Connect signals
        self.process_btn.clicked.connect(self.process_files)
        self.cancel_btn.clicked.connect(self.cancel_processing)
        self.operation_combo.currentTextChanged.connect(self.update_options)
        self.custom_name_radio.toggled.connect(
            lambda checked: self.custom_suffix_input.setEnabled(checked))
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Initialize variables
        self.files = []
        self.current_worker = None
        
        # Initial options update
        self.update_options(self.operation_combo.currentText())
        
    def update_preview(self, file_path: str):
        """Update the preview image"""
        try:
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                # Scale pixmap to fit the preview area while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    self.preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pixmap)
        except Exception as e:
            logger.error(f"Preview update failed: {str(e)}")
            
    def update_options(self, operation):
        """Update options based on selected operation"""
        # Clear previous options
        while self.options_layout.count():
            item = self.options_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if operation == "Resize Image":
            width_layout = QHBoxLayout()
            width_layout.addWidget(QLabel("Width:"))
            self.width_spin = QSpinBox()
            self.width_spin.setRange(1, 10000)
            width_layout.addWidget(self.width_spin)
            self.options_layout.addLayout(width_layout)
            
            height_layout = QHBoxLayout()
            height_layout.addWidget(QLabel("Height:"))
            self.height_spin = QSpinBox()
            self.height_spin.setRange(1, 10000)
            height_layout.addWidget(self.height_spin)
            self.options_layout.addLayout(height_layout)
            
        elif operation == "Reduce File Size":
            size_combo = QComboBox()
            size_combo.addItems(["Small", "Medium", "Large"])
            self.options_layout.addWidget(size_combo)
            
        elif operation == "Rotate Image":
            rotation_combo = QComboBox()
            rotation_combo.addItems(["90°", "180°", "270°"])
            self.options_layout.addWidget(rotation_combo)
            
        elif operation == "Add Watermark":
            text_input = QLineEdit()
            text_input.setPlaceholder("Enter watermark text")
            self.options_layout.addWidget(text_input)
            
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
        """Handle drop events"""
        files = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if self.processor.validate_image(path):
                files.append(path)
            
        if files:
            self.files = files
            self.drop_area.setText(f"{len(files)} files selected")
            # Show preview of first file
            if len(files) > 0:
                self.update_preview(files[0])
        else:
            QMessageBox.warning(self, "Invalid Files", 
                              "No valid image files were dropped")
            
    def get_naming_option(self):
        """Get the selected naming option and custom suffix"""
        if self.custom_name_radio.isChecked():
            return 'custom', self.custom_suffix_input.text()
        elif self.sequential_name_radio.isChecked():
            return 'sequential', ''
        return 'same', ''
            
    def process_files(self):
        """Process the selected files"""
        if not self.files:
            QMessageBox.warning(self, "No Files", 
                              "Please select files to process first")
            return
            
        # Get output directory
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_dir:
            return
            
        # Get naming option
        naming_option, custom_suffix = self.get_naming_option()
        
        # Create worker thread
        operation = self.operation_combo.currentText().lower().replace(" ", "_")
        self.current_worker = WorkerThread(
            self.processor,
            operation,
            self.files,
            output_dir,
            naming_option,
            custom_suffix
        )
        
        # Connect signals
        self.current_worker.progress.connect(self.progress_bar.setValue)
        self.current_worker.file_progress.connect(self.file_progress_label.setText)
        self.current_worker.finished.connect(self.processing_finished)
        self.current_worker.error.connect(self.show_error)
        
        # Update UI
        self.process_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.file_progress_label.setText("Starting...")
        
        # Start processing
        self.current_worker.start()
        
    def cancel_processing(self):
        """Cancel the current processing operation"""
        if self.current_worker and self.current_worker.isRunning():
            self.current_worker.cancel()
            self.current_worker.wait()
            self.processing_finished()
            self.file_progress_label.setText("Operation cancelled")
        
    def processing_finished(self):
        """Handle processing completion"""
        self.process_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        if self.current_worker and not self.current_worker._is_cancelled:
            QMessageBox.information(self, "Success", 
                                  "File processing completed successfully")
        
    def show_error(self, message):
        """Show error message"""
        QMessageBox.critical(self, "Error", message)
        self.process_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False) 