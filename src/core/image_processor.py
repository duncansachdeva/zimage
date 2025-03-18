from PIL import Image
import os
import shutil
from loguru import logger
from typing import Tuple, Optional, Union
import img2pdf
from pdf2image import convert_from_path

class ImageProcessor:
    """
    Core image processing class that handles all image manipulation operations
    """
    
    def __init__(self):
        logger.info("Initializing ImageProcessor")
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        
    def verify_disk_space(self, input_path: str, output_path: str, factor: float = 1.5) -> bool:
        """Verify if there's enough disk space for the operation"""
        try:
            input_size = os.path.getsize(input_path)
            required_space = input_size * factor  # Estimate required space
            
            # Get free space in output directory
            output_dir = os.path.dirname(output_path)
            free_space = shutil.disk_usage(output_dir).free
            
            if free_space < required_space:
                logger.error(f"Insufficient disk space. Required: {required_space}, Available: {free_space}")
                return False
            return True
        except Exception as e:
            logger.error(f"Disk space verification failed: {str(e)}")
            return False

    def generate_output_path(self, input_path: str, output_dir: str, 
                           naming_option: str = 'same', 
                           custom_suffix: str = '',
                           sequence_number: int = None) -> str:
        """Generate output path based on naming options"""
        try:
            # Get just the filename from the input path
            filename = os.path.basename(input_path)
            name, ext = os.path.splitext(filename)
            
            # Generate new filename based on naming option
            if naming_option == 'same':
                new_name = filename
            elif naming_option == 'custom':
                new_name = f"{name}_{custom_suffix}{ext}"
            elif naming_option == 'sequential':
                new_name = f"{name}_{sequence_number}{ext}"
            else:
                new_name = filename
                
            # Simply join the output directory with the new filename
            output_path = os.path.join(output_dir, new_name)
            
            # Create output directory if it doesn't exist
            os.makedirs(output_dir, exist_ok=True)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Output path generation failed: {str(e)}")
            return None

    def validate_image(self, image_path: str) -> bool:
        """Validate if file is an image and exists"""
        try:
            if not os.path.exists(image_path):
                logger.error(f"File not found: {image_path}")
                return False
            
            ext = os.path.splitext(image_path)[1].lower()
            if ext not in self.supported_formats:
                logger.error(f"Unsupported format: {ext}")
                return False
                
            # Try opening the image to verify it's valid
            with Image.open(image_path) as img:
                img.verify()
            return True
        except Exception as e:
            logger.error(f"Image validation failed: {str(e)}")
            return False
            
    def enhance_quality(self, image_path: str, output_path: str) -> bool:
        """Enhance image quality to 100%"""
        try:
            with Image.open(image_path) as img:
                img.save(output_path, quality=100, optimize=True)
            logger.info(f"Enhanced quality for: {image_path}")
            return True
        except Exception as e:
            logger.error(f"Quality enhancement failed: {str(e)}")
            return False
            
    def resize_image(self, image_path: str, output_path: str, 
                    target_size: Optional[Tuple[int, int]] = None,
                    scale_factor: Optional[float] = None) -> bool:
        """Resize image maintaining aspect ratio"""
        try:
            with Image.open(image_path) as img:
                if target_size:
                    target_width, target_height = target_size
                    # Get the longer side
                    if img.width >= img.height:
                        # Width is longer, set it to target width
                        ratio = target_width / img.width
                        new_size = (target_width, int(img.height * ratio))
                    else:
                        # Height is longer, set it to target width
                        ratio = target_width / img.height
                        new_size = (int(img.width * ratio), target_width)
                    
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                elif scale_factor:
                    new_size = (int(img.width * scale_factor), 
                              int(img.height * scale_factor))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                
                # Save with high quality and optimization
                img.save(output_path, quality=95, optimize=True)
                logger.info(f"Resized image: {image_path} to {new_size}")
                return True
        except Exception as e:
            logger.error(f"Resize failed: {str(e)}")
            return False
            
    def reduce_file_size(self, image_path: str, output_path: str, 
                        target_size: str) -> bool:
        """Reduce file size to target size (small, medium, large)"""
        size_map = {
            'small': 300 * 1024,  # 300KB
            'medium': 800 * 1024,  # 800KB
            'large': 2 * 1024 * 1024  # 2MB
        }
        
        try:
            target_bytes = size_map.get(target_size.lower())
            if not target_bytes:
                raise ValueError(f"Invalid target size: {target_size}")
                
            quality = 95
            with Image.open(image_path) as img:
                while True:
                    img.save(output_path, quality=quality, optimize=True)
                    if os.path.getsize(output_path) <= target_bytes or quality <= 5:
                        break
                    quality -= 5
                    
            logger.info(f"Reduced file size for: {image_path}")
            return True
        except Exception as e:
            logger.error(f"File size reduction failed: {str(e)}")
            return False
            
    def rotate_image(self, image_path: str, output_path: str, 
                    degrees: int) -> bool:
        """Rotate image by specified degrees"""
        try:
            with Image.open(image_path) as img:
                rotated = img.rotate(degrees, expand=True)
                rotated.save(output_path, quality=95, optimize=True)
            logger.info(f"Rotated image: {image_path}")
            return True
        except Exception as e:
            logger.error(f"Rotation failed: {str(e)}")
            return False
            
    def add_watermark(self, image_path: str, output_path: str,
                     watermark: Union[str, Image.Image],
                     position: Tuple[int, int] = None) -> bool:
        """Add watermark (text or image) to image"""
        try:
            with Image.open(image_path) as base_img:
                if isinstance(watermark, str):
                    # Create text watermark
                    txt_layer = Image.new('RGBA', base_img.size, (255, 255, 255, 0))
                    # Implementation of text drawing will go here
                    base_img.paste(txt_layer, (0, 0), txt_layer)
                else:
                    # Image watermark
                    if position is None:
                        position = (base_img.width - watermark.width - 10,
                                  base_img.height - watermark.height - 10)
                    base_img.paste(watermark, position, watermark)
                base_img.save(output_path, quality=95, optimize=True)
            logger.info(f"Added watermark to: {image_path}")
            return True
        except Exception as e:
            logger.error(f"Watermark addition failed: {str(e)}")
            return False
            
    def convert_to_pdf(self, image_paths: list, output_path: str) -> bool:
        """Convert image(s) to PDF"""
        try:
            with open(output_path, "wb") as f:
                f.write(img2pdf.convert([image_path for image_path in image_paths
                                       if self.validate_image(image_path)]))
            logger.info(f"Converted images to PDF: {output_path}")
            return True
        except Exception as e:
            logger.error(f"PDF conversion failed: {str(e)}")
            return False
            
    def convert_from_pdf(self, pdf_path: str, output_dir: str) -> bool:
        """Convert PDF to images"""
        try:
            images = convert_from_path(pdf_path)
            for i, image in enumerate(images):
                image.save(os.path.join(output_dir, f'page_{i+1}.png'), 'PNG')
            logger.info(f"Converted PDF to images: {pdf_path}")
            return True
        except Exception as e:
            logger.error(f"PDF to image conversion failed: {str(e)}")
            return False

    def process_with_verification(self, operation_func, input_path: str, 
                                output_path: str, **kwargs) -> bool:
        """Process file with disk space verification"""
        try:
            if not self.verify_disk_space(input_path, output_path):
                return False
            return operation_func(input_path, output_path, **kwargs)
        except Exception as e:
            logger.error(f"Processing failed: {str(e)}")
            return False 