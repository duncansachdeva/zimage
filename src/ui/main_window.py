from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QPushButton, QLabel, QProgressBar, QFileDialog,
                             QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit,
                             QMessageBox, QRadioButton, QButtonGroup, QScrollArea,
                             QListWidget, QCheckBox, QInputDialog, QGroupBox,
                             QFormLayout, QSlider, QTabWidget)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMimeData, QSize, QTimer
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
from pdf2image import convert_from_path
import logging

CONFIG_FILE = 'zimage_config.json'

def load_config():
    """Load configuration from file"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return get_default_config()
    return get_default_config()

def save_config(config):
    """Save configuration to file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save config: {e}")

def get_default_config():
    """Get default configuration"""
    return {
        'output_dir': os.path.join(os.path.expanduser("~"), "Documents", "ZImage"),
        'last_actions': []  # Store last selected actions
    }

class Action:
    def __init__(self, name, params=None):
        self.name = name if name else ""
        self.params = params if params is not None else {}
    
    def __str__(self):
        try:
            if not self.name:
                return "Unnamed Action"
            
            if not self.params:
                return self.name
            
            param_str = ", ".join(f"{k}: {v}" for k, v in self.params.items() if v is not None)
            return f"{self.name} ({param_str})" if param_str else self.name
            
        except Exception as e:
            logger.error(f"Error converting action to string: {e}")
            return self.name if self.name else "Unnamed Action"
        
    def to_dict(self):
        """Convert action to dictionary for saving"""
        return {
            'name': self.name,
            'params': self.params
        }
    
    @classmethod
    def from_dict(cls, data):
        """Create action from dictionary"""
        return cls(data.get('name', ''), data.get('params', {}))

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
                
                if action.name == "Image to PDF" and action.params.get('combine_files', False):
                    # For combined PDF, create a single output file using proper naming
                    base_name = os.path.join(self.output_dir, "combined")
                    if self.naming_option == 'custom' and self.custom_suffix:
                        base_name = os.path.join(self.output_dir, f"combined_{self.custom_suffix}")
                    elif self.naming_option == 'sequential':
                        base_name = os.path.join(self.output_dir, f"combined_1")
                    
                    output_path = f"{base_name}.pdf"
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
                    
                    # Let the processor handle the naming
                    if action == self.actions[-1]:
                        output_path = os.path.join(self.output_dir, filename)
                    else:
                        output_path = os.path.join(temp_dir, filename)
                    
                    # Process the file
                    try:
                        success = False
                        if action.name == "Enhance Quality":
                            success = self.processor.process_with_verification(
                                self.processor.enhance_quality,
                                input_path, output_path,
                                naming_option=self.naming_option,
                                custom_suffix=self.custom_suffix,
                                file_index=i+1,
                                **action.params
                            )
                        elif action.name == "Resize Image":
                            success = self.processor.process_with_verification(
                                self.processor.resize_image,
                                input_path, output_path,
                                naming_option=self.naming_option,
                                custom_suffix=self.custom_suffix,
                                file_index=i+1,
                                **action.params
                            )
                        elif action.name == "Reduce File Size":
                            success = self.processor.process_with_verification(
                                self.processor.reduce_file_size,
                                input_path, output_path,
                                naming_option=self.naming_option,
                                custom_suffix=self.custom_suffix,
                                file_index=i+1,
                                **action.params
                            )
                        elif action.name == "PDF to Image":
                            # Create output directory for PDF pages
                            pdf_output_dir = os.path.join(temp_dir if action != self.actions[-1] else self.output_dir, f"{name}_pages")
                            os.makedirs(pdf_output_dir, exist_ok=True)
                            
                            # Convert PDF to images with naming options
                            success = self.processor.pdf_to_image(
                                input_path,
                                pdf_output_dir,
                                naming_option=self.naming_option,
                                custom_suffix=self.custom_suffix,
                                file_index=i + 1,
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
                            success = self.processor.process_with_verification(
                                self.processor.upscale_image_waifu2x,
                                input_path, output_path,
                                naming_option=self.naming_option,
                                custom_suffix=self.custom_suffix,
                                file_index=i+1,
                                **action.params
                            )
                        elif action.name == "Image to PDF":
                            # Handle individual PDF conversion with naming options
                            logger.debug(f"Worker thread Image to PDF: naming_option={self.naming_option}, custom_suffix={self.custom_suffix}, file_index={i+1}")
                            
                            # Combine action params with naming options
                            pdf_params = {
                                'naming_option': self.naming_option,
                                'custom_suffix': self.custom_suffix,
                                'file_index': i+1
                            }
                            
                            success = self.processor.process_with_verification(
                                lambda x, y: self.processor.convert_to_pdf([x], y, **action.params, **pdf_params),
                                input_path, output_path
                            )
                        
                        if not success:
                            self.error.emit(f"Failed to process {filename}")
                            return
                        
                        new_files.append(output_path)
                        current_step += 1
                        self.progress.emit(int(current_step * 100 / total_steps))
                    except Exception as e:
                        self.error.emit(f"Error processing {filename}: {e}")
                        return
                
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

class MainWindow(QMainWindow):
    """Main window of the application."""

    def __init__(self, theme_manager=None):
        """Initialize the main window."""
        super().__init__()
        
        # Initialize logger
        self.logger = logging.getLogger(__name__)
        
        # Set theme manager
        self.theme_manager = theme_manager
        
        # Initialize image processor
        self.image_processor = ImageProcessor()
        
        # Load configuration
        self.config = self.load_config()
        
        # Set output directory
        self.output_dir = self.config['output_dir']
        
        # Initialize variables
        self.files = []
        self.actions_queue = []
        self.action_checks = []
        self.current_widgets = {}
        self.current_worker = None
        
        # Initialize UI components
        self.init_ui()
        
        # Restore last actions if available
        if 'last_actions' in self.config:
            self.restore_last_actions(self.config['last_actions'])
        
    def load_config(self):
        """Load configuration from file or create default."""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
            else:
                config = self.get_default_config()
                self.show_first_time_setup(config)
                self.save_config(config)
            
            # Ensure output directory exists
            os.makedirs(config['output_dir'], exist_ok=True)
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load config: {str(e)}")
            config = self.get_default_config()
            os.makedirs(config['output_dir'], exist_ok=True)
            return config
    
    def get_default_config(self):
        """Get default configuration."""
        return {
            'output_dir': os.path.join(os.path.expanduser('~'), 'Documents', 'ZImage'),
            'last_actions': []
        }
    
    def save_config(self, config=None):
        """Save configuration to file."""
        try:
            if config is None:
                config = {
                    'output_dir': self.output_dir_input.text(),
                    'last_actions': self.get_selected_actions()
                }
            
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
                
        except Exception as e:
            self.logger.error(f"Failed to save config: {str(e)}")
    
    def show_first_time_setup(self, config):
        """Show first-time setup dialog."""
        try:
            msg = QMessageBox()
            msg.setWindowTitle("Welcome to ZImage")
            msg.setText("Please select a default output directory for your processed files.")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg.exec()
            
            dir_path = QFileDialog.getExistingDirectory(
                self,
                "Select Output Directory",
                os.path.expanduser("~"),
                QFileDialog.Option.ShowDirsOnly
            )
            
            if dir_path:
                config['output_dir'] = dir_path
                
        except Exception as e:
            self.logger.error(f"Failed to show first-time setup: {str(e)}")
    
    def get_selected_actions(self):
        """Get list of currently selected actions."""
        return [check.text() for check in self.action_checks if check.isChecked()]
    
    def restore_last_actions(self, actions):
        """Restore last selected actions."""
        try:
            for check in self.action_checks:
                check.setChecked(check.text() in actions)
            self.update_action_queue()
        except Exception as e:
            self.logger.error(f"Failed to restore last actions: {str(e)}")

    def update_files_display(self):
        """Update the drag & drop area to show loaded files"""
        if not self.files:
            self.drop_area.setText("Drag and drop images here")
            return
            
        file_count = len(self.files)
        file_list = ", ".join(os.path.basename(f) for f in self.files)
        self.drop_area.setText(f"Loaded Files ({file_count}):\n{file_list}")

    def clear_files(self):
        """Clear all loaded files"""
        self.files.clear()
        self.update_files_display()
        self.preview_label.clear()
        self.preview_label.setText("Preview")
        logger.info("Cleared all files")

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
        self.output_dir_input = QLineEdit(self.config['output_dir'])
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
            # Connect checkbox state change - only connect to setup_parameters
            # update_action_queue will be called after parameter setup
            check.stateChanged.connect(self.setup_parameters)
        
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
        right_layout.addWidget(self.drop_area)
        
        # Add Clear Files button below drop area
        clear_files_btn = QPushButton("Clear Files")
        clear_files_btn.clicked.connect(self.clear_files)
        right_layout.addWidget(clear_files_btn)
        
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
        
        # Initial options update
        self.update_action_queue()
        
    def update_preview(self, file_path: str):
        """Update the preview image"""
        try:
            # Handle PDF files
            if file_path.lower().endswith('.pdf'):
                # If PDF to Image action is selected, use the PDF preview widget
                if any(check.text() == "PDF to Image" and check.isChecked() 
                      for check in self.action_checks):
                    if hasattr(self, 'pdf_preview'):
                        self.pdf_preview.load_pdf(file_path)
                    return
                    
                try:
                    # Otherwise, show first page preview
                    doc = fitz.open(file_path)
                    if doc.page_count > 0:
                        page = doc[0]
                        pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
                        img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
                        pixmap = QPixmap.fromImage(img)
                        
                        # Scale pixmap to fit preview area
                        scaled_pixmap = pixmap.scaled(
                            self.preview_label.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        self.preview_label.setPixmap(scaled_pixmap)
                    doc.close()
                except Exception as pdf_error:
                    logger.error(f"PDF preview failed: {pdf_error}")
                    self.preview_label.setText("Unable to preview PDF. The file may be corrupted or password-protected.")
                return
            
            # Handle image files
            pixmap = QPixmap(file_path)
            if not pixmap.isNull():
                # Scale pixmap to fit preview area while maintaining aspect ratio
                scaled_pixmap = pixmap.scaled(
                    self.preview_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.preview_label.setPixmap(scaled_pixmap)
            else:
                self.preview_label.setText("Unable to load image. The file may be corrupted or in an unsupported format.")
        except Exception as e:
            logger.error(f"Preview update failed: {str(e)}")
            self.preview_label.setText("Preview not available")
            QMessageBox.warning(self, "Preview Error", f"Failed to generate preview: {str(e)}")
            
    def update_action_queue(self):
        """Update the actions queue based on selected actions"""
        try:
            # Store existing action parameters
            existing_params = {action.name: action.params for action in self.actions_queue}
            
            self.actions_queue = []  # Clear existing queue
            
            # Check for incompatible actions
            has_pdf_files = any(f.lower().endswith('.pdf') for f in self.files) if self.files else False
            has_image_files = any(not f.lower().endswith('.pdf') for f in self.files) if self.files else False
            
            for check in self.action_checks:
                if not check.isChecked():
                    continue
                    
                action_name = check.text()
                
                # Initialize action with default parameters
                action = Action(action_name)
                
                # If we have existing parameters for this action, use them
                if action_name in existing_params:
                    action.params = existing_params[action_name]
                else:
                    # Set default parameters based on action type
                    if action_name == "Enhance Quality":
                        action.params = {'level': self.enhance_level_combo.currentText().split()[0] if hasattr(self, 'enhance_level_combo') else 'High'}
                    elif action_name == "Resize Image":
                        action.params = {
                            'width': self.width_spin.value() if hasattr(self, 'width_spin') else 2500,
                            'height': self.height_spin.value() if hasattr(self, 'height_spin') else 0,
                            'maintain_aspect': self.maintain_aspect_check.isChecked() if hasattr(self, 'maintain_aspect_check') else True
                        }
                    elif action_name == "Reduce File Size":
                        action.params = {
                            'target_size_mb': self.target_size_spin.value() if hasattr(self, 'target_size_spin') else 0.5
                        }
                    elif action_name == "Image to PDF":
                        action.params = {
                            'combine_files': self.combine_pdf_check.isChecked() if hasattr(self, 'combine_pdf_check') else True,
                            'orientation': self.orientation_combo.currentText() if hasattr(self, 'orientation_combo') else 'Auto',
                            'images_per_page': int(self.images_per_page_combo.currentText()) if hasattr(self, 'images_per_page_combo') else 1,
                            'fit_mode': self.fit_mode_combo.currentText() if hasattr(self, 'fit_mode_combo') else 'Fit to page',
                            'quality': self.pdf_quality_combo.currentText() if hasattr(self, 'pdf_quality_combo') else 'High'
                        }
                    elif action_name == "PDF to Image":
                        action.params = {
                            'format': self.format_combo.currentText().lower() if hasattr(self, 'format_combo') else 'png',
                            'dpi': self.dpi_spin.value() if hasattr(self, 'dpi_spin') else 300,
                            'quality': self.quality_spin.value() if hasattr(self, 'quality_spin') else 95,
                            'color_mode': self.color_combo.currentText() if hasattr(self, 'color_combo') else 'RGB'
                        }
                    elif action_name == "Upscale Image (Waifu2x)":
                        action.params = {
                            'scale_factor': int(self.scale_factor_combo.currentText().replace('x', '')) if hasattr(self, 'scale_factor_combo') else 2,
                            'noise_level': int(self.noise_level_combo.currentText().split('Level ')[1].split(')')[0]) if hasattr(self, 'noise_level_combo') else 1,
                            'model_type': self.model_type_combo.currentText().lower() if hasattr(self, 'model_type_combo') else 'auto'
                        }
                
                # Add action to queue
                self.actions_queue.append(action)
            
            # Update the queue display
            self.update_queue_display()
            
        except Exception as e:
            logger.error(f"Error updating action queue: {e}")
            self.update_queue_display()  # Ensure queue display is updated even if there's an error

    def update_queue_display(self):
        """Update the queue list widget"""
        try:
            self.queue_list.clear()
            for action in self.actions_queue:
                try:
                    display_text = str(action)
                    self.queue_list.addItem(display_text)
                except Exception as e:
                    logger.error(f"Error displaying action: {e}")
                    # Fallback to just displaying the action name
                    self.queue_list.addItem(action.name)
        except Exception as e:
            logger.error(f"Error updating queue display: {e}")
            self.queue_list.clear()  # Ensure the list is cleared even if there's an error

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
            self.output_dir = dir_path  # Update the output_dir attribute
            self.config['output_dir'] = dir_path
            self.save_config()
            
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
            
        # Get output directory from input field and update the attribute
        output_dir = self.output_dir_input.text()
        if not output_dir:
            QMessageBox.warning(self, "No Output Directory", 
                              "Please specify an output directory")
            return
            
        # Update the output_dir attribute
        self.output_dir = output_dir
            
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
            self.image_processor,
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
        """Handle dropped files"""
        try:
            urls = event.mimeData().urls()
            if urls:
                # Clear existing files if switching file types
                first_file = urls[0].toLocalFile().lower()
                is_pdf = first_file.endswith('.pdf')
                
                if self.files:
                    existing_is_pdf = self.files[0].lower().endswith('.pdf')
                    if is_pdf != existing_is_pdf:
                        # Ask user before clearing different file types
                        msg = QMessageBox()
                        msg.setIcon(QMessageBox.Icon.Question)
                        msg.setWindowTitle("Different File Type")
                        msg.setText("You are dropping a different type of file. Would you like to clear existing files?")
                        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                        if msg.exec() == QMessageBox.StandardButton.Yes:
                            self.files.clear()
                        else:
                            event.ignore()
                            return
                
                # Add dropped files to the list
                for url in urls:
                    file_path = url.toLocalFile()
                    if self.image_processor.validate_file(file_path):
                        self.files.append(file_path)
                
                # Update the files display
                self.update_files_display()
                
                # Update preview with first file
                if self.files:
                    self.update_preview(self.files[0])
                    
                event.accept()
                
        except Exception as e:
            logger.error(f"Drop event failed: {e}")
            QMessageBox.warning(self, "Error", f"Failed to load files: {str(e)}")
            event.ignore()

    def setup_parameters(self):
        """Set up parameter widgets based on selected actions"""
        try:
            # Block signals during widget cleanup and setup
            for i in range(self.options_layout.count()):
                widget = self.options_layout.itemAt(i).widget()
                if widget:
                    widget.blockSignals(True)
            
            # Clear existing widgets safely
            while self.options_layout.count():
                item = self.options_layout.takeAt(0)
                if item.widget():
                    widget = item.widget()
                    widget.setParent(None)
                    widget.deleteLater()

            # Create tab widget for parameters if there are selected actions
            selected_actions = [check for check in self.action_checks if check.isChecked()]
            if not selected_actions:
                # If no actions selected, still update the queue to clear it
                self.update_action_queue()
                return

            self.tab_widget = QTabWidget()
            self.tab_widget.setDocumentMode(True)  # Makes tabs look cleaner
            self.options_layout.addWidget(self.tab_widget)

            # Store existing parameters before recreating widgets
            existing_params = {action.name: action.params for action in self.actions_queue}

            # Add parameters for selected actions
            for check in selected_actions:
                # Create a tab for each action
                tab = QWidget()
                layout = QFormLayout(tab)
                layout.setContentsMargins(10, 10, 10, 10)  # Add some padding
                layout.setSpacing(10)  # Space between form elements

                action_name = check.text()
                current_params = existing_params.get(action_name, {})

                if action_name == "Enhance Quality":
                    self.enhance_level_combo = QComboBox()
                    self.enhance_level_combo.addItems([
                        "High (100)", 
                        "Medium (92)", 
                        "Low (85)"
                    ])
                    # Set current value from existing parameters
                    level = current_params.get('level', 'High')
                    self.enhance_level_combo.setCurrentText(f"{level} (100)" if level == "High" else 
                                                          f"{level} (92)" if level == "Medium" else 
                                                          f"{level} (85)")
                    self.enhance_level_combo.currentTextChanged.connect(lambda: self.on_parameter_changed("Enhance Quality"))
                    layout.addRow("Quality Level:", self.enhance_level_combo)
                    self.tab_widget.addTab(tab, "Enhance Quality")
                
                elif action_name == "PDF to Image":
                    # Format selection
                    self.format_combo = QComboBox()
                    self.format_combo.setObjectName("format_combo")
                    self.format_combo.addItems(["PNG", "JPG", "TIFF"])
                    self.format_combo.setCurrentText(current_params.get('format', 'PNG').upper())
                    layout.addRow("Format:", self.format_combo)
                    self.format_combo.currentTextChanged.connect(lambda: self.on_parameter_changed("PDF to Image"))

                    # DPI selection
                    self.dpi_spin = QSpinBox()
                    self.dpi_spin.setObjectName("dpi_spin")
                    self.dpi_spin.setRange(72, 600)
                    self.dpi_spin.setValue(current_params.get('dpi', 300))
                    layout.addRow("DPI:", self.dpi_spin)
                    self.dpi_spin.valueChanged.connect(lambda: self.on_parameter_changed("PDF to Image"))

                    # Quality selection (for JPG)
                    self.quality_spin = QSpinBox()
                    self.quality_spin.setObjectName("quality_spin")
                    self.quality_spin.setRange(1, 100)
                    self.quality_spin.setValue(current_params.get('quality', 95))
                    layout.addRow("JPEG Quality:", self.quality_spin)
                    self.quality_spin.valueChanged.connect(lambda: self.on_parameter_changed("PDF to Image"))

                    # Color mode selection
                    self.color_combo = QComboBox()
                    self.color_combo.setObjectName("color_combo")
                    self.color_combo.addItems(["RGB", "RGBA"])
                    self.color_combo.setCurrentText(current_params.get('color_mode', 'RGB'))
                    layout.addRow("Color Mode:", self.color_combo)
                    self.color_combo.currentTextChanged.connect(lambda: self.on_parameter_changed("PDF to Image"))

                    # Enable/disable quality spin based on format
                    self.format_combo.currentTextChanged.connect(
                        lambda fmt: self.quality_spin.setEnabled(fmt.upper() == 'JPG')
                    )
                    self.quality_spin.setEnabled(self.format_combo.currentText().upper() == 'JPG')
                    self.tab_widget.addTab(tab, "PDF to Image")

                elif action_name == "Image to PDF":
                    # Combine files option
                    self.combine_pdf_check = QCheckBox("Combine all images into one PDF")
                    self.combine_pdf_check.setObjectName("combine_pdf_check")
                    self.combine_pdf_check.setChecked(current_params.get('combine_files', True))
                    layout.addRow(self.combine_pdf_check)
                    self.combine_pdf_check.stateChanged.connect(lambda: self.on_parameter_changed("Image to PDF"))

                    # Orientation selection
                    self.orientation_combo = QComboBox()
                    self.orientation_combo.setObjectName("orientation_combo")
                    self.orientation_combo.addItems(["Auto", "Portrait", "Landscape"])
                    self.orientation_combo.setCurrentText(current_params.get('orientation', 'Auto'))
                    layout.addRow("Orientation:", self.orientation_combo)
                    self.orientation_combo.currentTextChanged.connect(lambda: self.on_parameter_changed("Image to PDF"))

                    # Images per page selection
                    self.images_per_page_combo = QComboBox()
                    self.images_per_page_combo.setObjectName("images_per_page_combo")
                    self.images_per_page_combo.addItems(["1", "2", "4", "6"])
                    self.images_per_page_combo.setCurrentText(str(current_params.get('images_per_page', 1)))
                    layout.addRow("Images per Page:", self.images_per_page_combo)
                    self.images_per_page_combo.currentTextChanged.connect(lambda: self.on_parameter_changed("Image to PDF"))

                    # Fit mode selection
                    self.fit_mode_combo = QComboBox()
                    self.fit_mode_combo.setObjectName("fit_mode_combo")
                    self.fit_mode_combo.addItems(["Fit to page", "Stretch to fill", "Actual size"])
                    self.fit_mode_combo.setCurrentText(current_params.get('fit_mode', 'Fit to page'))
                    layout.addRow("Fit Mode:", self.fit_mode_combo)
                    self.fit_mode_combo.currentTextChanged.connect(lambda: self.on_parameter_changed("Image to PDF"))

                    # PDF Quality selection
                    self.pdf_quality_combo = QComboBox()
                    self.pdf_quality_combo.setObjectName("pdf_quality_combo")
                    self.pdf_quality_combo.addItems(["High", "Medium", "Low"])
                    self.pdf_quality_combo.setCurrentText(current_params.get('quality', 'High'))
                    layout.addRow("Quality:", self.pdf_quality_combo)
                    self.pdf_quality_combo.currentTextChanged.connect(lambda: self.on_parameter_changed("Image to PDF"))
                    self.tab_widget.addTab(tab, "Image to PDF")

                elif action_name == "Resize Image":
                    # Width input
                    self.width_spin = QSpinBox()
                    self.width_spin.setRange(1, 10000)
                    self.width_spin.setValue(current_params.get('width', 2500))
                    layout.addRow("Width:", self.width_spin)
                    self.width_spin.valueChanged.connect(lambda: self.on_parameter_changed("Resize Image"))

                    # Height input
                    self.height_spin = QSpinBox()
                    self.height_spin.setRange(0, 10000)
                    self.height_spin.setValue(current_params.get('height', 0))
                    layout.addRow("Height (0 for auto):", self.height_spin)
                    self.height_spin.valueChanged.connect(lambda: self.on_parameter_changed("Resize Image"))

                    # Maintain aspect ratio
                    self.maintain_aspect_check = QCheckBox("Maintain aspect ratio")
                    self.maintain_aspect_check.setChecked(current_params.get('maintain_aspect', True))
                    layout.addRow(self.maintain_aspect_check)
                    self.maintain_aspect_check.stateChanged.connect(lambda: self.on_parameter_changed("Resize Image"))
                    self.tab_widget.addTab(tab, "Resize Image")

                elif action_name == "Reduce File Size":
                    self.target_size_spin = QDoubleSpinBox()
                    self.target_size_spin.setRange(0.1, 100.0)
                    self.target_size_spin.setValue(current_params.get('target_size_mb', 0.5))
                    self.target_size_spin.setSuffix(" MB")
                    layout.addRow("Target Size:", self.target_size_spin)
                    self.target_size_spin.valueChanged.connect(lambda: self.on_parameter_changed("Reduce File Size"))
                    self.tab_widget.addTab(tab, "Reduce Size")

                elif action_name == "Upscale Image (Waifu2x)":
                    # Scale factor selection
                    self.scale_factor_combo = QComboBox()
                    self.scale_factor_combo.addItems(['1x', '2x', '4x'])
                    self.scale_factor_combo.setCurrentText(f"{current_params.get('scale_factor', 2)}x")
                    self.scale_factor_combo.currentTextChanged.connect(lambda: self.on_parameter_changed("Upscale Image (Waifu2x)"))
                    layout.addRow("Scale Factor:", self.scale_factor_combo)
                    
                    # Noise reduction level
                    self.noise_level_combo = QComboBox()
                    self.noise_level_combo.addItems(['None (Level 0)', 'Light (Level 1)', 'Medium (Level 2)', 'High (Level 3)'])
                    noise_level = current_params.get('noise_level', 1)
                    noise_text = {0: 'None (Level 0)', 1: 'Light (Level 1)', 2: 'Medium (Level 2)', 3: 'High (Level 3)'}.get(noise_level, 'Light (Level 1)')
                    self.noise_level_combo.setCurrentText(noise_text)
                    self.noise_level_combo.currentTextChanged.connect(lambda: self.on_parameter_changed("Upscale Image (Waifu2x)"))
                    layout.addRow("Noise Reduction:", self.noise_level_combo)
                    
                    # Model type selection
                    self.model_type_combo = QComboBox()
                    self.model_type_combo.addItems(['Auto', 'Photo', 'Anime'])
                    self.model_type_combo.setCurrentText(current_params.get('model_type', 'Auto').capitalize())
                    self.model_type_combo.currentTextChanged.connect(lambda: self.on_parameter_changed("Upscale Image (Waifu2x)"))
                    layout.addRow("Model Type:", self.model_type_combo)
                    self.tab_widget.addTab(tab, "Waifu2x")

            # Save current actions to config and update queue immediately
            self.save_config()
            self.update_action_queue()

        except Exception as e:
            logger.error(f"Error in setup_parameters: {e}")
            # Ensure queue is updated even if there's an error
            self.update_action_queue()

    def on_parameter_changed(self, action_name):
        """Handle parameter changes for any action"""
        try:
            # Find the action in the queue
            for action in self.actions_queue:
                if action.name == action_name:
                    # Update parameters based on action type
                    if action_name == "Enhance Quality":
                        action.params = {
                            'level': self.enhance_level_combo.currentText().split()[0]
                        }
                    elif action_name == "PDF to Image":
                        action.params = {
                            'format': self.format_combo.currentText().lower(),
                            'dpi': self.dpi_spin.value(),
                            'quality': self.quality_spin.value(),
                            'color_mode': self.color_combo.currentText()
                        }
                    elif action_name == "Image to PDF":
                        action.params = {
                            'combine_files': self.combine_pdf_check.isChecked(),
                            'orientation': self.orientation_combo.currentText(),
                            'images_per_page': int(self.images_per_page_combo.currentText()),
                            'fit_mode': self.fit_mode_combo.currentText(),
                            'quality': self.pdf_quality_combo.currentText()
                        }
                    elif action_name == "Resize Image":
                        action.params = {
                            'width': self.width_spin.value(),
                            'height': self.height_spin.value(),
                            'maintain_aspect': self.maintain_aspect_check.isChecked()
                        }
                    elif action_name == "Reduce File Size":
                        action.params = {
                            'target_size_mb': self.target_size_spin.value()
                        }
                    elif action_name == "Upscale Image (Waifu2x)":
                        action.params = {
                            'scale_factor': int(self.scale_factor_combo.currentText().replace('x', '')),
                            'noise_level': int(self.noise_level_combo.currentText().split('Level ')[1].split(')')[0]),
                            'model_type': self.model_type_combo.currentText().lower()
                        }
                    break

            # Update the queue display
            self.update_queue_display()
            
        except Exception as e:
            logger.error(f"Error updating parameters for {action_name}: {e}")

class PDFPreviewWidget(QWidget):
    """Widget for PDF preview with navigation"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_page = 0
        self.total_pages = 0
        self.current_pdf = None
        self.pdf_info = None
        self.processor = None
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Preview area
        self.preview_label = QLabel()
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(300, 400)
        
        # Navigation controls
        nav_layout = QHBoxLayout()
        self.prev_button = QPushButton("←")
        self.next_button = QPushButton("→")
        self.page_label = QLabel("Page 0 of 0")
        self.page_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.page_label)
        nav_layout.addWidget(self.next_button)
        
        # PDF information
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("QLabel { color: #666; }")
        
        # Add widgets to layout
        layout.addWidget(self.preview_label)
        layout.addLayout(nav_layout)
        layout.addWidget(self.info_label)
        
        # Connect signals
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)
        
        # Initial state
        self.update_navigation()
        
    def set_processor(self, processor):
        """Set the image processor instance"""
        self.processor = processor
        
    def load_pdf(self, pdf_path):
        """Load a PDF file and display its first page"""
        try:
            # Close previous PDF if open
            if self.current_pdf:
                self.current_pdf.close()
            
            # Open new PDF
            self.current_pdf = fitz.open(pdf_path)
            self.total_pages = self.current_pdf.page_count
            self.current_page = 0
            
            # Get PDF information
            self.pdf_info = {
                'pages': self.total_pages,
                'dimensions': []
            }
            
            # Get dimensions for each page
            for page in self.current_pdf:
                rect = page.rect
                self.pdf_info['dimensions'].append((rect.width, rect.height))
            
            # Update display
            self.update_page_display()
            self.update_navigation()
            self.update_info()
            
        except Exception as e:
            logger.error(f"Failed to load PDF: {e}")
            self.info_label.setText("Failed to load PDF")
            
    def update_page_display(self):
        """Update the display with current page"""
        if not self.current_pdf:
            return
            
        try:
            page = self.current_pdf[self.current_page]
            pix = page.get_pixmap(matrix=fitz.Matrix(1, 1))
            
            # Convert pixmap to QImage
            img = QImage(pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(img)
            
            # Scale pixmap to fit preview area
            scaled_pixmap = pixmap.scaled(
                self.preview_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            
            self.preview_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            logger.error(f"Failed to update page display: {e}")
            self.preview_label.clear()
            
    def update_navigation(self):
        """Update navigation buttons and page label"""
        self.prev_button.setEnabled(self.current_page > 0)
        self.next_button.setEnabled(self.current_pdf and self.current_page < self.total_pages - 1)
        self.page_label.setText(f"Page {self.current_page + 1} of {self.total_pages}")
        
    def update_info(self):
        """Update PDF information display"""
        if not self.pdf_info:
            return
            
        try:
            # Get current page dimensions
            width, height = self.pdf_info['dimensions'][self.current_page]
            
            # Create info text
            info_text = [
                f"Dimensions: {width:.1f} x {height:.1f} points",
                f"Total Pages: {self.pdf_info['pages']}"
            ]
            
            # Add size estimate if processor is available
            if self.processor:
                estimated_size = self.processor.estimate_output_size(
                    (width, height),
                    300,  # Default DPI
                    'png',  # Default format
                    95  # Default quality
                )
                info_text.append(f"Estimated size per page: {estimated_size:.1f} MB")
            
            self.info_label.setText("\n".join(info_text))
            
        except Exception as e:
            logger.error(f"Failed to update PDF info: {e}")
            self.info_label.setText("Failed to get PDF information")
            
    def prev_page(self):
        """Show previous page"""
        if self.current_page > 0:
            self.current_page -= 1
            self.update_page_display()
            self.update_navigation()
            self.update_info()
            
    def next_page(self):
        """Show next page"""
        if self.current_pdf and self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_page_display()
            self.update_navigation()
            self.update_info()
            
    def resizeEvent(self, event):
        """Handle resize events to update preview scaling"""
        super().resizeEvent(event)
        self.update_page_display()
            