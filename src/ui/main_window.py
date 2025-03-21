from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QProgressBar, QFileDialog,
                             QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit,
                             QMessageBox, QRadioButton, QButtonGroup, QScrollArea,
                             QListWidget, QCheckBox, QInputDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMimeData, QSize
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QImage
import os
import json
from loguru import logger
from PIL import Image, ImageDraw
from src.core.image_processor import ImageProcessor
from src.core.optimized_processor import OptimizedProcessor
from io import BytesIO
import shutil
import fitz

class Action:
    def __init__(self, name, params=None):
        self.name = name
        self.params = params or {}
    
    def __str__(self):
        param_str = ", ".join(f"{k}: {v}" for k, v in self.params.items())
        return f"{self.name} ({param_str})" if self.params else self.name
        
    def to_dict(self):
        """Convert action to dictionary for saving"""
        return {
            'name': self.name,
            'params': self.params
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create action from dictionary"""
        return cls(data['name'], data['params'])

class WorkerThread(QThread):
    """Worker thread for processing images"""
    progress = pyqtSignal(int)
    file_progress = pyqtSignal(str)
    action_progress = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    
    def __init__(self, processor, actions, files, output_dir, naming_option, custom_suffix):
        super().__init__()
        self.processor = processor
        self.actions = actions
        self.files = files
        self.output_dir = output_dir
        self.naming_option = naming_option
        self.custom_suffix = custom_suffix
        self._is_cancelled = False
        
    def run(self):
        """Process files with selected actions"""
        try:
            total_steps = len(self.files) * len(self.actions)
            current_step = 0
            
            # Create temporary directory for intermediate files
            temp_dir = os.path.join(self.output_dir, '.temp')
            os.makedirs(temp_dir, exist_ok=True)
            
            # Track current files being processed
            current_files = self.files.copy()
            
            for action in self.actions:
                self.action_progress.emit(f"Performing: {action.name}")
                
                # Special handling for PDF conversion with combine option
                if action.name == "Image to PDF" and action.params.get('combine_files', False):
                    # For combined PDF, create a single output file
                    base_name = "combined_output.pdf"
                    if self.naming_option == 'custom':
                        base_name = f"combined_{self.custom_suffix}.pdf"
                    elif self.naming_option == 'sequential':
                        base_name = f"combined_1.pdf"
                    
                    output_path = os.path.join(self.output_dir, base_name)
                    success = self.processor.convert_to_pdf(
                        current_files,
                        output_path,
                        **action.params
                    )
                    if not success:
                        self.error.emit(f"Failed to create combined PDF")
                        return
                    # Update current_files to point to the new PDF
                    current_files = [output_path]
                    continue
                
                # Process each file through the current action
                new_files = []
                for i, input_path in enumerate(current_files):
                    if self._is_cancelled:
                        return
                        
                    self.file_progress.emit(f"Processing file {i+1} of {len(current_files)}")
                    
                    # Generate output path
                    filename = os.path.basename(input_path)
                    name, ext = os.path.splitext(filename)
                    
                    # For PDF conversion, ensure .pdf extension
                    if action.name == "Image to PDF":
                        ext = ".pdf"
                    
                    if self.naming_option == 'custom':
                        new_name = f"{name}_{self.custom_suffix}{ext}"
                    elif self.naming_option == 'sequential':
                        new_name = f"{name}_{i+1}{ext}"
                    else:
                        new_name = filename
                        
                    # For final action, save directly to output directory
                    if action == self.actions[-1]:
                        output_path = os.path.join(self.output_dir, new_name)
                    else:
                        output_path = os.path.join(temp_dir, new_name)
                    
                    # Process the file
                    success = False
                    if action.name == "Enhance Quality":
                        success = self.processor.process_with_verification(
                            self.processor.enhance_quality,
                            input_path, output_path
                        )
                    elif action.name == "Resize Image":
                        success = self.processor.process_with_verification(
                            self.processor.resize_image,
                            input_path, output_path,
                            **action.params
                        )
                    elif action.name == "Reduce File Size":
                        success = self.processor.process_with_verification(
                            self.processor.reduce_file_size,
                            input_path, output_path,
                            **action.params
                        )
                    elif action.name == "PDF to Image":
                        # Create output directory for PDF pages
                        pdf_output_dir = os.path.join(temp_dir if action != self.actions[-1] else self.output_dir, f"{name}_pages")
                        os.makedirs(pdf_output_dir, exist_ok=True)
                        
                        # Convert PDF to images
                        success = self.processor.convert_from_pdf(
                            input_path,
                            pdf_output_dir,
                            **action.params
                        )
                        
                        if success:
                            # Add all generated images to the new files list
                            format_ext = action.params.get('format', 'jpg').lower()
                            new_files.extend([
                                os.path.join(pdf_output_dir, f)
                                for f in os.listdir(pdf_output_dir)
                                if f.lower().endswith(f'.{format_ext}')
                            ])
                            continue
                    elif action.name == "Upscale Image (Waifu2x)":
                        success = self.processor.upscale_image_waifu2x(
                            input_path, output_path,
                            **action.params
                        )
                    elif action.name == "Image to PDF":
                        success = self.processor.convert_to_pdf(
                            [input_path],
                            output_path,
                            **action.params
                        )
                    
                    if not success:
                        self.error.emit(f"Failed to process {filename}")
                        return
                        
                    new_files.append(output_path)
                    current_step += 1
                    self.progress.emit(int(current_step * 100 / total_steps))
                
                # Update current files for next action
                current_files = new_files
            
            # Clean up temp directory if it exists and is empty
            try:
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
            except Exception as e:
                logger.warning(f"Failed to clean up temp directory: {str(e)}")
            
            self.progress.emit(100)
            self.finished.emit()
            
        except Exception as e:
            self.error.emit(str(e))
            logger.error(f"Processing error: {str(e)}")
            
    def cancel(self):
        """Cancel processing"""
        self._is_cancelled = True

class BatchProcessingThread(QThread):
    progress_update = pyqtSignal(int, int)  # emits (completed, total)
    processing_finished = pyqtSignal(list)    # emits list of results
    
    def __init__(self, processor, files, actions, output_dir, naming_option, custom_suffix):
        super().__init__()
        self.processor = processor
        self.files = files
        self.actions = actions
        self.output_dir = output_dir
        self.naming_option = naming_option
        self.custom_suffix = custom_suffix

    def run(self):
        results = self.processor.process_batch_parallel(
            self.files, self.actions, self.output_dir, self.naming_option, self.custom_suffix,
            progress_callback=self.progress_update.emit
        )
        self.processing_finished.emit(results)

class MainWindow(QMainWindow):
    def __init__(self, theme_manager=None):
        super().__init__()
        self.theme_manager = theme_manager
        self.processor = ImageProcessor()
        self.default_output_dir = os.path.join(os.path.expanduser("~"), "Documents", "ZImage")
        self.queues_dir = os.path.join(self.default_output_dir, "saved_queues")
        os.makedirs(self.queues_dir, exist_ok=True)
        os.makedirs(self.default_output_dir, exist_ok=True)
        self.actions_queue = []  # List to store queued actions
        self.init_ui()
        
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle('ZImage Processor')
        self.setMinimumSize(800, 600)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Output Directory Selection
        output_dir_widget = QWidget()
        output_dir_layout = QHBoxLayout(output_dir_widget)
        output_dir_layout.setContentsMargins(0, 0, 0, 0)
        
        output_dir_label = QLabel("Output Directory:")
        self.output_dir_input = QLineEdit(self.default_output_dir)
        browse_btn = QPushButton("Browse...")
        
        output_dir_layout.addWidget(output_dir_label)
        output_dir_layout.addWidget(self.output_dir_input, stretch=1)
        output_dir_layout.addWidget(browse_btn)
        
        layout.addWidget(output_dir_widget)
        
        # Connect browse button
        browse_btn.clicked.connect(self.browse_output_dir)
        
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
        
        # Operations Section
        operations_group = QWidget()
        operations_layout = QVBoxLayout(operations_group)
        operations_layout.addWidget(QLabel("Available Actions:"))
        
        # Default actions
        self.action_checks = []
        default_actions = [
            "Enhance Quality",
            "Resize Image",
            "Reduce File Size",
            "Image to PDF",
            "PDF to Image",
            "Upscale Image (Waifu2x)"
        ]
        
        for action in default_actions:
            check = QCheckBox(action)
            self.action_checks.append(check)
            operations_layout.addWidget(check)
            # Connect checkbox state change
            check.stateChanged.connect(self.update_action_queue)
        
        left_layout.addWidget(operations_group)
        
        # Action Queue Display
        queue_group = QWidget()
        queue_layout = QVBoxLayout(queue_group)
        queue_layout.addWidget(QLabel("Action Queue:"))
        
        self.queue_list = QListWidget()
        queue_layout.addWidget(self.queue_list)
        
        # Queue Controls
        queue_controls = QHBoxLayout()
        move_up_btn = QPushButton("↑")
        move_down_btn = QPushButton("↓")
        remove_btn = QPushButton("Remove")
        save_queue_btn = QPushButton("Save Queue")
        load_queue_btn = QPushButton("Load Queue")
        
        queue_controls.addWidget(move_up_btn)
        queue_controls.addWidget(move_down_btn)
        queue_controls.addWidget(remove_btn)
        queue_controls.addWidget(save_queue_btn)
        queue_controls.addWidget(load_queue_btn)
        queue_layout.addLayout(queue_controls)
        
        left_layout.addWidget(queue_group)
        
        # Options widget for action parameters
        self.options_widget = QWidget()
        self.options_layout = QVBoxLayout(self.options_widget)
        left_layout.addWidget(self.options_widget)
        
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
        self.custom_suffix_input.setPlaceholderText("Enter custom suffix")
        self.custom_suffix_input.setEnabled(False)
        naming_layout.addWidget(self.custom_suffix_input)
        naming_layout.addWidget(self.sequential_name_radio)
        
        left_layout.addWidget(naming_group)
        
        # Add panels to main layout
        h_layout.addWidget(left_panel, 2)
        h_layout.addWidget(right_panel, 1)
        layout.addLayout(h_layout)
        
        # Connect signals
        self.process_btn.clicked.connect(self.process_files)
        self.cancel_btn.clicked.connect(self.cancel_processing)
        self.custom_name_radio.toggled.connect(
            lambda checked: self.custom_suffix_input.setEnabled(checked))
        move_up_btn.clicked.connect(self.move_action_up)
        move_down_btn.clicked.connect(self.move_action_down)
        remove_btn.clicked.connect(self.remove_action)
        save_queue_btn.clicked.connect(self.save_queue)
        load_queue_btn.clicked.connect(self.load_queue)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
        # Initialize variables
        self.files = []
        self.current_worker = None
        
        # Initial options update
        self.update_action_queue()
        
        # Add Batch Processing section
        self.batch_process_button = QPushButton("Process Batch")
        self.batch_process_button.clicked.connect(self.start_batch_processing)
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.hide()

        batch_layout = QHBoxLayout()
        batch_layout.addWidget(self.batch_process_button)
        batch_layout.addWidget(self.progress_bar)
        layout.addLayout(batch_layout)
        
        # Initialize variables
        self.files = []
        self.current_worker = None
        
        # Initial options update
        self.update_action_queue()

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
            
    def update_action_queue(self):
        # Clear any existing parameter widgets from the options layout
        while self.options_layout.count() > 0:
            item = self.options_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        
        # Clear the current queue
        self.actions_queue.clear()
        
        # Add selected actions to the queue
        for check in self.action_checks:
            if check.isChecked():
                action_name = check.text()
                params = {}
                
                # Handle special parameters for different actions
                if action_name == "Resize Image":
                    self.setup_resize_parameters()
                    params = {
                        'target_dimension': self.target_dim_spin.value(),
                        'constrain_width': self.width_radio.isChecked(),
                        'quality': self.quality_spin.value()
                    }
                elif action_name == "Upscale Image (Waifu2x)":
                    self.setup_upscale_parameters()
                    params = {
                        'scale': self.scale_spin.value(),
                        'noise_level': self.noise_spin.value()
                    }
                elif action_name == "Reduce File Size":
                    self.setup_reduce_size_parameters()
                    params = {
                        'target_size_mb': self.target_size_spin.value()
                    }
                elif action_name == "Image to PDF":
                    self.setup_pdf_parameters()
                    params = {
                        'combine_files': self.combine_pdf_check.isChecked(),
                        'orientation': self.orientation_combo.currentText(),
                        'images_per_page': int(self.images_per_page_combo.currentText()),
                        'fit_mode': self.fit_mode_combo.currentText(),
                        'quality': self.pdf_quality_combo.currentText()
                    }
                elif action_name == "PDF to Image":
                    self.setup_pdf_to_image_parameters()
                    params = {
                        'format': self.format_combo.currentText(),
                        'dpi': self.dpi_spin.value(),
                        'quality': self.pdf_quality_spin.value(),
                        'color_mode': self.color_mode_combo.currentText()
                    }
                
                # Create and add the action to the queue
                action = Action(action_name, params)
                self.actions_queue.append(action)
        
        # Update the queue display
        self.update_queue_display()
        
    def update_queue_display(self):
        """Update the queue list widget"""
        self.queue_list.clear()
        for action in self.actions_queue:
            self.queue_list.addItem(str(action))
            
    def move_action_up(self):
        """Move selected action up in the queue"""
        current_row = self.queue_list.currentRow()
        if current_row > 0:
            self.actions_queue[current_row], self.actions_queue[current_row-1] = \
                self.actions_queue[current_row-1], self.actions_queue[current_row]
            self.update_queue_display()
            self.queue_list.setCurrentRow(current_row-1)
            
    def move_action_down(self):
        """Move selected action down in the queue"""
        current_row = self.queue_list.currentRow()
        if current_row < len(self.actions_queue) - 1:
            self.actions_queue[current_row], self.actions_queue[current_row+1] = \
                self.actions_queue[current_row+1], self.actions_queue[current_row]
            self.update_queue_display()
            self.queue_list.setCurrentRow(current_row+1)
            
    def remove_action(self):
        """Remove selected action from the queue"""
        current_row = self.queue_list.currentRow()
        if current_row >= 0:
            del self.actions_queue[current_row]
            self.update_queue_display()
            
    def get_naming_option(self):
        """Get the selected naming option and custom suffix"""
        if self.custom_name_radio.isChecked():
            return 'custom', self.custom_suffix_input.text()
        elif self.sequential_name_radio.isChecked():
            return 'sequential', ''
        return 'same', ''
            
    def browse_output_dir(self):
        """Open directory browser for output directory selection"""
        dir_path = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            self.output_dir_input.text()
        )
        if dir_path:
            self.output_dir_input.setText(dir_path)
            
    def process_files(self):
        """Process the selected files"""
        if not self.files:
            QMessageBox.warning(self, "No Files", 
                              "Please select files to process first")
            return
            
        if not self.actions_queue:
            QMessageBox.warning(self, "No Actions", 
                              "Please select at least one action to perform")
            return
            
        # Get output directory from input field
        output_dir = self.output_dir_input.text()
        if not output_dir:
            QMessageBox.warning(self, "No Output Directory", 
                              "Please specify an output directory")
            return
            
        # Create output directory if it doesn't exist
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            QMessageBox.critical(self, "Error", 
                               f"Failed to create output directory: {str(e)}")
            return
            
        # Get naming option
        naming_option, custom_suffix = self.get_naming_option()
        
        # Create worker thread with action queue
        self.current_worker = WorkerThread(
            self.processor,
            self.actions_queue,
            self.files,
            output_dir,
            naming_option,
            custom_suffix
        )
        
        # Connect signals
        self.current_worker.progress.connect(self.progress_bar.setValue)
        self.current_worker.file_progress.connect(self.file_progress_label.setText)
        self.current_worker.action_progress.connect(lambda s: self.file_progress_label.setText(f"{s}"))
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
        
    def save_queue(self):
        """Save current action queue"""
        if not self.actions_queue:
            QMessageBox.warning(self, "Empty Queue", 
                              "No actions in queue to save")
            return
            
        # Get queue name from user
        name, ok = QInputDialog.getText(self, "Save Queue", 
                                      "Enter name for this queue:")
        if not ok or not name:
            return
            
        # Sanitize filename
        filename = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_'))
        filepath = os.path.join(self.queues_dir, f"{filename}.json")
        
        # Convert queue to saveable format
        queue_data = {
            'name': name,
            'actions': [action.to_dict() for action in self.actions_queue]
        }
        
        try:
            with open(filepath, 'w') as f:
                json.dump(queue_data, f, indent=2)
            QMessageBox.information(self, "Success", 
                                  f"Queue saved as '{name}'")
        except Exception as e:
            logger.error(f"Failed to save queue: {str(e)}")
            QMessageBox.critical(self, "Error", 
                               f"Failed to save queue: {str(e)}")
            
    def load_queue(self):
        """Load a saved action queue"""
        # Get list of saved queues
        try:
            queue_files = [f for f in os.listdir(self.queues_dir) 
                         if f.endswith('.json')]
        except Exception as e:
            logger.error(f"Failed to list saved queues: {str(e)}")
            QMessageBox.critical(self, "Error", 
                               f"Failed to list saved queues: {str(e)}")
            return
            
        if not queue_files:
            QMessageBox.information(self, "No Saved Queues", 
                                  "No saved queues found")
            return
            
        # Show queue selection dialog
        queue_names = []
        queue_data_map = {}
        
        for filename in queue_files:
            try:
                with open(os.path.join(self.queues_dir, filename)) as f:
                    data = json.load(f)
                    queue_names.append(data['name'])
                    queue_data_map[data['name']] = data
            except Exception as e:
                logger.error(f"Failed to read queue file {filename}: {str(e)}")
                continue
                
        if not queue_names:
            QMessageBox.critical(self, "Error", 
                               "No valid queue files found")
            return
            
        name, ok = QInputDialog.getItem(self, "Load Queue",
                                      "Select a queue to load:",
                                      queue_names, 0, False)
        if not ok or not name:
            return
            
        # Load selected queue
        try:
            data = queue_data_map[name]
            self.actions_queue = [Action.from_dict(action_data) 
                                for action_data in data['actions']]
            
            # Update UI
            self.update_queue_display()
            
            # Update checkboxes to match loaded queue
            for check in self.action_checks:
                check.setChecked(any(action.name == check.text() 
                                   for action in self.actions_queue))
                
            QMessageBox.information(self, "Success", 
                                  f"Queue '{name}' loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load queue: {str(e)}")
            QMessageBox.critical(self, "Error", 
                               f"Failed to load queue: {str(e)}")

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

    def setup_upscale_parameters(self):
        """Add parameter controls for the Upscale Image action."""
        from PyQt6.QtWidgets import QDoubleSpinBox, QHBoxLayout
        # Create a container for upscale parameters
        upscale_widget = QWidget()
        hlayout = QHBoxLayout(upscale_widget)
        scale_label = QLabel("Scale Factor:")
        self.scale_spin = QDoubleSpinBox()
        self.scale_spin.setRange(1.0, 5.0)
        self.scale_spin.setSingleStep(0.1)
        self.scale_spin.setValue(2.0)
        noise_label = QLabel("Noise Level:")
        self.noise_spin = QSpinBox()
        self.noise_spin.setRange(0, 3)
        self.noise_spin.setValue(1)
        hlayout.addWidget(scale_label)
        hlayout.addWidget(self.scale_spin)
        hlayout.addWidget(noise_label)
        hlayout.addWidget(self.noise_spin)
        self.options_layout.addWidget(upscale_widget)

    def setup_resize_parameters(self):
        """Add parameter controls for the Resize Image action."""
        # Create container for resize parameters
        resize_widget = QWidget()
        layout = QVBoxLayout(resize_widget)
        
        # Target dimension input
        dim_layout = QHBoxLayout()
        dim_label = QLabel("Target dimension (px):")
        self.target_dim_spin = QSpinBox()
        self.target_dim_spin.setRange(1, 10000)
        self.target_dim_spin.setValue(2000)
        dim_layout.addWidget(dim_label)
        dim_layout.addWidget(self.target_dim_spin)
        layout.addLayout(dim_layout)
        
        # Constraint radio buttons
        constraint_layout = QHBoxLayout()
        constraint_label = QLabel("Constrain:")
        self.width_radio = QRadioButton("Width")
        self.height_radio = QRadioButton("Height")
        self.width_radio.setChecked(True)
        constraint_layout.addWidget(constraint_label)
        constraint_layout.addWidget(self.width_radio)
        constraint_layout.addWidget(self.height_radio)
        layout.addLayout(constraint_layout)
        
        # Quality spinner
        quality_layout = QHBoxLayout()
        quality_label = QLabel("Quality:")
        self.quality_spin = QSpinBox()
        self.quality_spin.setRange(1, 100)
        self.quality_spin.setValue(100)  # Default to 100
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.quality_spin)
        layout.addLayout(quality_layout)
        
        # Preview label for dimensions
        self.resize_preview_label = QLabel()
        self.resize_preview_label.setStyleSheet("color: gray;")
        self.resize_preview_label.setWordWrap(True)  # Enable word wrap for better formatting
        layout.addWidget(self.resize_preview_label)
        
        # Connect signals to parameter update method
        self.target_dim_spin.valueChanged.connect(self.update_resize_parameters)
        self.width_radio.toggled.connect(self.update_resize_parameters)
        self.height_radio.toggled.connect(self.update_resize_parameters)
        self.quality_spin.valueChanged.connect(self.update_resize_parameters)
        
        self.options_layout.addWidget(resize_widget)
        
        # Initial preview update
        self.update_resize_parameters()

    def update_resize_parameters(self):
        """Update both action parameters and previews"""
        # Update action parameters in queue
        for action in self.actions_queue:
            if action.name == "Resize Image":
                action.params.update({
                    'target_dimension': self.target_dim_spin.value(),
                    'constrain_width': self.width_radio.isChecked(),
                    'quality': self.quality_spin.value()
                })
        
        # Update queue display
        self.update_queue_display()
        
        # Update both dimension text and image preview
        self.update_resize_preview()

    def update_resize_preview(self):
        """Update both dimension text and image preview with enhanced information"""
        if not hasattr(self, 'files') or not self.files:
            self.resize_preview_label.setText("Drop images to see dimensions")
            self.preview_label.clear()
            return
            
        try:
            # Get number of images in queue
            total_images = len(self.files)
            
            with Image.open(self.files[0]) as img:
                # Store original dimensions
                orig_width, orig_height = img.size
                target_dim = self.target_dim_spin.value()
                
                # Calculate new dimensions
                if self.width_radio.isChecked():
                    new_width = target_dim
                    new_height = int(orig_height * (target_dim / orig_width))
                else:
                    new_height = target_dim
                    new_width = int(orig_width * (target_dim / orig_height))
                
                # Create informative preview text
                preview_text = [
                    "Preview of first image:",
                    f"Original: {orig_width}px by {orig_height}px",
                    f"Output: {new_width}px by {new_height}px"
                ]
                
                # Add note about multiple images if applicable
                if total_images > 1:
                    preview_text.extend([
                        "",  # Empty line for spacing
                        f"Note: These parameters will be applied to all {total_images} images in queue.",
                        "Final dimensions may vary based on each image's aspect ratio."
                    ])
                
                self.resize_preview_label.setText("\n".join(preview_text))
                
                # Create preview image at target dimensions
                preview_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Convert PIL image to RGB mode if necessary
                if preview_img.mode != 'RGB':
                    preview_img = preview_img.convert('RGB')
                
                # Convert to QPixmap
                preview_data = preview_img.tobytes("raw", "RGB")
                qimg = QImage(preview_data, new_width, new_height, 3 * new_width, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
                
                # Scale the preview image to fit the preview area while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    self.preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # Update preview label
                self.preview_label.setPixmap(scaled_pixmap)
                
        except Exception as e:
            logger.error(f"Failed to update preview: {e}")
            self.resize_preview_label.setText("Failed to update preview")
            self.preview_label.clear()

    def setup_reduce_size_parameters(self):
        """Add parameter controls for Reduce File Size action"""
        reduce_widget = QWidget()
        layout = QVBoxLayout(reduce_widget)
        
        # Target size input
        size_layout = QHBoxLayout()
        size_label = QLabel("Target Size (MB):")
        self.target_size_spin = QDoubleSpinBox()
        self.target_size_spin.setRange(0.1, 100.0)  # 100KB to 100MB
        self.target_size_spin.setDecimals(1)
        self.target_size_spin.setSingleStep(0.1)
        self.target_size_spin.setValue(1.0)  # Default 1MB
        size_layout.addWidget(size_label)
        size_layout.addWidget(self.target_size_spin)
        layout.addLayout(size_layout)
        
        # Preview label for dimensions
        self.resize_preview_label = QLabel()
        self.resize_preview_label.setStyleSheet("color: gray;")
        self.resize_preview_label.setWordWrap(True)
        layout.addWidget(self.resize_preview_label)
        
        # Connect signal to the same preview update system
        self.target_size_spin.valueChanged.connect(self.update_reduce_size_parameters)
        
        self.options_layout.addWidget(reduce_widget)
        
        # Initial preview update
        self.update_reduce_size_parameters()

    def update_reduce_size_parameters(self):
        """Update both action parameters and previews"""
        # Update action parameters in queue
        for action in self.actions_queue:
            if action.name == "Reduce File Size":
                action.params.update({
                    'target_size_mb': self.target_size_spin.value()
                })
        
        # Update queue display
        self.update_queue_display()
        
        # Update preview
        self.update_reduce_size_preview()

    def update_reduce_size_preview(self):
        """Update the preview area with file size information"""
        if not hasattr(self, 'files') or not self.files:
            self.preview_label.clear()
            self.resize_preview_label.setText("Drop images to see file size information")
            return
            
        try:
            # Get first image file size
            file_size = os.path.getsize(self.files[0]) / (1024 * 1024)  # Convert to MB
            target_size = self.target_size_spin.value()
            
            # Calculate compression ratio and estimated quality
            ratio = target_size / file_size
            estimated_quality = int(ratio * 100)
            estimated_quality = max(1, min(100, estimated_quality))
            
            # Create preview text
            preview_text = [
                "Preview of first image:",
                f"Original size: {file_size:.1f} MB",
                f"Target size: {target_size:.1f} MB",
                f"Estimated quality: {estimated_quality}%"
            ]
            
            # Add warning if compression is high
            if ratio < 0.5:
                preview_text.append("\nNote: High compression may affect image quality")
            
            # Add note for multiple images if applicable
            if len(self.files) > 1:
                preview_text.extend([
                    "",
                    f"Note: These settings will be applied to all {len(self.files)} images.",
                    "Actual results may vary based on each image's content."
                ])
            
            # Update the same preview label used by other actions
            self.resize_preview_label.setText("\n".join(preview_text))
            
            # Show preview of image with estimated quality
            with Image.open(self.files[0]) as img:
                # Create preview with estimated quality
                preview_img = img.copy()
                if preview_img.mode in ('RGBA', 'P'):
                    preview_img = preview_img.convert('RGB')
                
                # Create a temporary buffer for the preview
                temp_buffer = BytesIO()
                preview_img.save(temp_buffer, format='JPEG', quality=estimated_quality)
                temp_buffer.seek(0)
                
                # Load the compressed preview
                preview_data = temp_buffer.getvalue()
                qimg = QImage.fromData(preview_data)
                pixmap = QPixmap.fromImage(qimg)
                
                # Scale to fit preview area while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    self.preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                
                # Update preview image
                self.preview_label.setPixmap(scaled_pixmap)
                
        except Exception as e:
            logger.error(f"Failed to update reduce size preview: {e}")
            self.resize_preview_label.setText("Failed to calculate file size")
            self.preview_label.clear()

    def start_batch_processing(self):
        # Open file dialog to select multiple images
        files, _ = QFileDialog.getOpenFileNames(self, "Select Images for Batch Processing", "", "Images (*.png *.jpg *.jpeg *.bmp)")
        if not files:
            return
        
        # Retrieve actions from the current queue (assuming self.actions_queue is updated via update_action_queue)
        if not hasattr(self, 'actions_queue') or not self.actions_queue:
            self.update_status_info("No actions selected for processing.")
            return
        actions = self.actions_queue
        
        # Prompt for output directory
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if not output_dir:
            return
        
        # Instantiate the OptimizedProcessor
        self.processor = OptimizedProcessor()
        
        # Setup progress bar and disable the button during processing
        self.progress_bar.setValue(0)
        self.progress_bar.show()
        self.batch_process_button.setEnabled(False)
        
        # Create and start the batch processing thread
        self.batch_thread = BatchProcessingThread(self.processor, files, actions, output_dir, "default", "")
        self.batch_thread.progress_update.connect(self.on_progress_update)
        self.batch_thread.processing_finished.connect(self.on_processing_finished)
        self.batch_thread.start()

    def on_progress_update(self, completed, total):
        progress = int((completed / total) * 100)
        self.progress_bar.setValue(progress)
        self.update_status_info(f"Processing: {completed}/{total}")

    def on_processing_finished(self, results):
        self.progress_bar.hide()
        self.batch_process_button.setEnabled(True)
        self.update_status_info("Batch processing completed.")
        # Optionally, show a message box with summary
        msg = QMessageBox()
        msg.setWindowTitle("Processing Complete")
        msg.setText(f"Processed {len(results)} files.")
        msg.exec() 

    def update_status_info(self, message):
        """Update status information"""
        self.file_progress_label.setText(message) 

    def setup_pdf_parameters(self):
        """Add parameter controls for the Image to PDF action."""
        # Create container for PDF parameters
        pdf_widget = QWidget()
        layout = QVBoxLayout(pdf_widget)
        
        # Save Mode
        save_mode_layout = QHBoxLayout()
        self.combine_pdf_check = QCheckBox("Combine into single PDF")
        self.combine_pdf_check.setChecked(False)
        save_mode_layout.addWidget(self.combine_pdf_check)
        layout.addLayout(save_mode_layout)
        
        # Page Orientation
        orientation_layout = QHBoxLayout()
        orientation_label = QLabel("Page Orientation:")
        self.orientation_combo = QComboBox()
        self.orientation_combo.addItems(["Auto", "Portrait", "Landscape"])
        orientation_layout.addWidget(orientation_label)
        orientation_layout.addWidget(self.orientation_combo)
        layout.addLayout(orientation_layout)
        
        # Images per Page
        images_layout = QHBoxLayout()
        images_label = QLabel("Images per Page:")
        self.images_per_page_combo = QComboBox()
        self.images_per_page_combo.addItems(["1", "2", "4", "6"])
        images_layout.addWidget(images_label)
        images_layout.addWidget(self.images_per_page_combo)
        layout.addLayout(images_layout)
        
        # Fit Mode
        fit_layout = QHBoxLayout()
        fit_label = QLabel("Fit Mode:")
        self.fit_mode_combo = QComboBox()
        self.fit_mode_combo.addItems(["Fit to page", "Stretch to fill", "Actual size"])
        fit_layout.addWidget(fit_label)
        fit_layout.addWidget(self.fit_mode_combo)
        layout.addLayout(fit_layout)
        
        # PDF Quality
        quality_layout = QHBoxLayout()
        quality_label = QLabel("PDF Quality:")
        self.pdf_quality_combo = QComboBox()
        self.pdf_quality_combo.addItems(["High", "Medium", "Low"])
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.pdf_quality_combo)
        layout.addLayout(quality_layout)
        
        # Preview label
        self.pdf_preview_label = QLabel()
        self.pdf_preview_label.setStyleSheet("color: gray;")
        self.pdf_preview_label.setWordWrap(True)
        layout.addWidget(self.pdf_preview_label)
        
        # Connect signals to update preview
        self.combine_pdf_check.stateChanged.connect(self.update_pdf_parameters)
        self.orientation_combo.currentTextChanged.connect(self.update_pdf_parameters)
        self.images_per_page_combo.currentTextChanged.connect(self.update_pdf_parameters)
        self.fit_mode_combo.currentTextChanged.connect(self.update_pdf_parameters)
        self.pdf_quality_combo.currentTextChanged.connect(self.update_pdf_parameters)
        
        self.options_layout.addWidget(pdf_widget)
        
        # Initial preview update
        self.update_pdf_parameters()

    def update_pdf_parameters(self):
        """Update both action parameters and previews for PDF conversion"""
        # Update action parameters in queue
        for action in self.actions_queue:
            if action.name == "Image to PDF":
                action.params.update({
                    'combine_files': self.combine_pdf_check.isChecked(),
                    'orientation': self.orientation_combo.currentText(),
                    'images_per_page': int(self.images_per_page_combo.currentText()),
                    'fit_mode': self.fit_mode_combo.currentText(),
                    'quality': self.pdf_quality_combo.currentText()
                })
        
        # Update queue display
        self.update_queue_display()
        
        # Update preview
        self.update_pdf_preview()

    def update_pdf_preview(self):
        """Update the PDF preview with layout information"""
        if not hasattr(self, 'files') or not self.files:
            self.pdf_preview_label.setText("Drop images to see PDF layout preview")
            return
            
        try:
            # Get number of images
            total_images = len(self.files)
            images_per_page = int(self.images_per_page_combo.currentText())
            orientation = self.orientation_combo.currentText()
            fit_mode = self.fit_mode_combo.currentText()
            
            # Calculate pages needed
            pages = (total_images + images_per_page - 1) // images_per_page
            
            # Create preview text
            preview_text = [
                f"PDF Layout Preview:",
                f"Total Images: {total_images}",
                f"Pages: {pages}",
                f"Layout: {images_per_page} image(s) per page",
                f"Orientation: {orientation}",
                f"Fit Mode: {fit_mode}"
            ]
            
            if self.combine_pdf_check.isChecked():
                preview_text.append("Output: Single combined PDF file")
            else:
                preview_text.append("Output: Individual PDF files")
            
            self.pdf_preview_label.setText("\n".join(preview_text))
            
            # Update image preview if possible
            if total_images > 0:
                self.update_pdf_image_preview(self.files[0])
                
        except Exception as e:
            logger.error(f"Failed to update PDF preview: {e}")
            self.pdf_preview_label.setText("Failed to update preview")

    def update_pdf_image_preview(self, image_path):
        """Update the image preview area with PDF layout visualization"""
        try:
            with Image.open(image_path) as img:
                # Create a visualization of the PDF layout
                preview_width = self.preview_label.width()
                preview_height = self.preview_label.height()
                
                # Create a white background image
                preview = Image.new('RGB', (preview_width, preview_height), 'white')
                draw = ImageDraw.Draw(preview)
                
                # Draw page outline
                margin = 20
                draw.rectangle([margin, margin, preview_width-margin, preview_height-margin], 
                             outline='gray', width=2)
                
                # Convert to QPixmap and display
                preview_data = preview.tobytes("raw", "RGB")
                qimg = QImage(preview_data, preview_width, preview_height, 
                            3 * preview_width, QImage.Format.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
                self.preview_label.setPixmap(pixmap)
                
        except Exception as e:
            logger.error(f"Failed to update PDF image preview: {e}")
            self.preview_label.clear() 

    def setup_pdf_to_image_parameters(self):
        """Add parameter controls for PDF to Image conversion"""
        pdf_widget = QWidget()
        layout = QVBoxLayout(pdf_widget)
        
        # Format selection
        format_layout = QHBoxLayout()
        format_label = QLabel("Output Format:")
        self.format_combo = QComboBox()
        self.format_combo.addItems(['jpg', 'png', 'tiff'])
        format_layout.addWidget(format_label)
        format_layout.addWidget(self.format_combo)
        layout.addLayout(format_layout)
        
        # DPI selection
        dpi_layout = QHBoxLayout()
        dpi_label = QLabel("DPI:")
        self.dpi_spin = QSpinBox()
        self.dpi_spin.setRange(72, 600)
        self.dpi_spin.setValue(300)  # Default 300 DPI
        self.dpi_spin.setSingleStep(72)
        dpi_layout.addWidget(dpi_label)
        dpi_layout.addWidget(self.dpi_spin)
        layout.addLayout(dpi_layout)
        
        # Quality for JPEG
        quality_layout = QHBoxLayout()
        quality_label = QLabel("JPEG Quality:")
        self.pdf_quality_spin = QSpinBox()
        self.pdf_quality_spin.setRange(1, 100)
        self.pdf_quality_spin.setValue(95)  # Default 95%
        quality_layout.addWidget(quality_label)
        quality_layout.addWidget(self.pdf_quality_spin)
        layout.addLayout(quality_layout)
        
        # Color mode selection
        color_layout = QHBoxLayout()
        color_label = QLabel("Color Mode:")
        self.color_mode_combo = QComboBox()
        self.color_mode_combo.addItems(['RGB', 'RGBA'])
        color_layout.addWidget(color_label)
        color_layout.addWidget(self.color_mode_combo)
        layout.addLayout(color_layout)
        
        # Preview label
        self.pdf_preview_label = QLabel()
        self.pdf_preview_label.setStyleSheet("color: gray;")
        self.pdf_preview_label.setWordWrap(True)
        layout.addWidget(self.pdf_preview_label)
        
        # Connect signals
        self.format_combo.currentTextChanged.connect(self.update_pdf_to_image_parameters)
        self.dpi_spin.valueChanged.connect(self.update_pdf_to_image_parameters)
        self.pdf_quality_spin.valueChanged.connect(self.update_pdf_to_image_parameters)
        self.color_mode_combo.currentTextChanged.connect(self.update_pdf_to_image_parameters)
        
        self.options_layout.addWidget(pdf_widget)
        
        # Initial preview update
        self.update_pdf_to_image_parameters()
        
    def update_pdf_to_image_parameters(self):
        """Update parameters for PDF to Image conversion"""
        # Update action parameters in queue
        for action in self.actions_queue:
            if action.name == "PDF to Image":
                action.params.update({
                    'format': self.format_combo.currentText(),
                    'dpi': self.dpi_spin.value(),
                    'quality': self.pdf_quality_spin.value(),
                    'color_mode': self.color_mode_combo.currentText()
                })
        
        # Update queue display
        self.update_queue_display()
        
        # Update preview text
        if not hasattr(self, 'files') or not self.files:
            self.pdf_preview_label.setText("Drop PDF files to see conversion details")
            return
            
        try:
            # Get first PDF file info
            doc = fitz.open(self.files[0])
            num_pages = len(doc)
            
            # Calculate estimated output size
            dpi = self.dpi_spin.value()
            format_text = self.format_combo.currentText().upper()
            quality = self.pdf_quality_spin.value()
            
            preview_text = [
                f"PDF Information:",
                f"Number of pages: {num_pages}",
                f"Output format: {format_text}",
                f"Resolution: {dpi} DPI",
                f"Color mode: {self.color_mode_combo.currentText()}"
            ]
            
            if format_text == 'JPG':
                preview_text.append(f"JPEG quality: {quality}%")
            
            # Add note for multiple files
            if len(self.files) > 1:
                preview_text.extend([
                    "",
                    f"Note: These settings will be applied to all {len(self.files)} PDF files.",
                    "Each page will be saved as a separate image."
                ])
            
            self.pdf_preview_label.setText("\n".join(preview_text))
            doc.close()
            
        except Exception as e:
            logger.error(f"Failed to update PDF preview: {e}")
            self.pdf_preview_label.setText("Failed to read PDF information")
            