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
from PIL import Image
from src.core.image_processor import ImageProcessor
from src.core.optimized_processor import OptimizedProcessor

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
    
    def __init__(self, processor, actions, files, output_dir, naming_option='same', 
                 custom_suffix=''):
        super().__init__()
        self.processor = processor
        self.actions = actions  # List of Action objects
        self.files = files
        self.output_dir = output_dir
        self.naming_option = naming_option
        self.custom_suffix = custom_suffix
        self._is_cancelled = False
        
    def cancel(self):
        """Cancel the operation"""
        self._is_cancelled = True
        
    def run(self):
        try:
            total_files = len(self.files)
            for file_idx, file in enumerate(self.files, 1):
                if self._is_cancelled:
                    break
                
                # Generate final output path
                output_path = self.processor.generate_output_path(
                    file, self.output_dir,
                    self.naming_option,
                    self.custom_suffix,
                    file_idx if self.naming_option == 'sequential' else None
                )
                
                if not output_path:
                    self.error.emit(f"Failed to generate output path for {file}")
                    continue
                
                # Process file through action chain
                current_file = file
                temp_file = None
                
                # Get the original file extension
                original_ext = os.path.splitext(file)[1].lower()
                
                for action_idx, action in enumerate(self.actions, 1):
                    if self._is_cancelled:
                        break
                        
                    self.action_progress.emit(f"Action {action_idx}/{len(self.actions)}: {action}")
                    
                    # For intermediate steps, use a temp file with proper extension
                    if action_idx < len(self.actions):
                        temp_file = f"{output_path}.temp{action_idx}{original_ext}"
                    else:
                        temp_file = output_path
                    
                    # Convert action name to method name
                    method_name = action.name.lower().replace(" ", "_")
                    success = self.processor.process_with_verification(
                        getattr(self.processor, method_name),
                        current_file, temp_file,
                        **action.params
                    )
                    
                    if not success:
                        self.error.emit(f"Failed to process {file} with action: {action}")
                        break
                    
                    # Update current file for next action
                    if action_idx < len(self.actions):
                        current_file = temp_file
                
                # Clean up temporary files
                for i in range(1, len(self.actions)):
                    temp = f"{output_path}.temp{i}{original_ext}"
                    if os.path.exists(temp):
                        try:
                            os.remove(temp)
                        except:
                            pass
                
                self.file_progress.emit(f"Processing: {os.path.basename(file)}")
                self.progress.emit(int(file_idx / total_files * 100))
                
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

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
            "Rotate Image",
            "Add Watermark",
            "Convert to PDF",
            "Convert from PDF",
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
        self.quality_spin.setValue(100)
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
