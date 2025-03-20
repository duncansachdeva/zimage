from PIL import Image
import os
import shutil
from loguru import logger
from typing import Tuple, Optional, Union
import img2pdf
from pdf2image import convert_from_path
from io import BytesIO

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
            
    def resize_image(self, image_path, output_path, target_dimension, constrain_width=True, quality=100):
        """Resize an image while maintaining aspect ratio.
        
        Args:
            image_path (str): Path to the input image
            output_path (str): Path to save the resized image
            target_dimension (int): Target width or height in pixels
            constrain_width (bool): If True, target_dimension is width, else height
            quality (int): JPEG quality (1-100)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with Image.open(image_path) as img:
                # Calculate new dimensions
                orig_width, orig_height = img.size
                if constrain_width:
                    new_width = target_dimension
                    new_height = int(orig_height * (target_dimension / orig_width))
                else:
                    new_height = target_dimension
                    new_width = int(orig_width * (target_dimension / orig_height))
                
                # Use LANCZOS resampling for high quality
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # Determine format and save options
                format = img.format or 'JPEG'
                save_options = {}
                
                if format == 'JPEG':
                    save_options['quality'] = quality
                    save_options['optimize'] = True
                elif format == 'PNG':
                    save_options['optimize'] = True
                
                # Save the image
                resized_img.save(output_path, format=format, **save_options)
                logger.info(f"Resized image saved: {output_path} ({new_width}x{new_height})")
                return True
                
        except Exception as e:
            logger.error(f"Failed to resize image: {str(e)}")
            return False
            
    def reduce_file_size(self, input_path, output_path, target_size_mb):
        """Reduce file size to target size in MB while maintaining action chain compatibility"""
        try:
            # Get original file size and extension
            original_size = os.path.getsize(input_path) / (1024 * 1024)  # Convert to MB
            original_ext = os.path.splitext(input_path)[1].lower()
            
            with Image.open(input_path) as img:
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # If original is already smaller, still process through PIL but with max quality
                if original_size <= target_size_mb:
                    logger.info(f"File already smaller than target size: {original_size:.1f}MB <= {target_size_mb:.1f}MB")
                    # Save with maximum quality but still optimize
                    img.save(output_path, format='JPEG', quality=95, optimize=True)
                    return True
                
                # Start with estimated quality based on size ratio
                quality = min(95, max(5, int((target_size_mb / original_size) * 100)))
                max_attempts = 15  # Increased attempts for better accuracy
                attempt = 0
                best_result = {'quality': quality, 'size': float('inf'), 'diff': float('inf')}
                
                while attempt < max_attempts:
                    # Create a temporary buffer for size testing
                    temp_buffer = BytesIO()
                    img.save(temp_buffer, format='JPEG', quality=quality, optimize=True)
                    result_size = len(temp_buffer.getvalue()) / (1024 * 1024)  # Convert to MB
                    
                    # Calculate how far we are from target
                    size_diff = abs(result_size - target_size_mb)
                    
                    # Update best result if this is closer to target and not exceeding it by much
                    if size_diff < best_result['diff'] and (result_size <= target_size_mb * 1.05):
                        best_result = {
                            'quality': quality,
                            'size': result_size,
                            'diff': size_diff,
                            'data': temp_buffer.getvalue()  # Store the actual data
                        }
                    
                    # If we're within 2% of target size, we're done
                    if abs(result_size - target_size_mb) / target_size_mb <= 0.02:
                        with open(output_path, 'wb') as f:
                            f.write(temp_buffer.getvalue())
                        logger.info(f"Reduced file size: {output_path} "
                                  f"(Original: {original_size:.1f}MB, "
                                  f"Target: {target_size_mb:.1f}MB, "
                                  f"Final: {result_size:.1f}MB, "
                                  f"Quality: {quality}%)")
                        return True
                    
                    # Adjust quality based on how far we are from target
                    if result_size > target_size_mb:
                        # If we're too big, reduce quality
                        quality_change = max(1, int(quality * (1 - (result_size - target_size_mb) / target_size_mb * 0.5)))
                        quality = max(5, quality - quality_change)
                    else:
                        # If we're too small, increase quality more aggressively
                        quality_change = max(1, int(quality * ((target_size_mb - result_size) / target_size_mb * 0.5)))
                        quality = min(95, quality + quality_change)
                    
                    attempt += 1
                
                # Use the best result we found
                if 'data' in best_result:
                    with open(output_path, 'wb') as f:
                        f.write(best_result['data'])
                    logger.info(f"Using best result: {output_path} "
                              f"(Original: {original_size:.1f}MB, "
                              f"Target: {target_size_mb:.1f}MB, "
                              f"Final: {best_result['size']:.1f}MB, "
                              f"Quality: {best_result['quality']}%)")
                    return True
                else:
                    # If we couldn't find a good result, use the last attempt
                    img.save(output_path, format='JPEG', quality=quality, optimize=True)
                    logger.warning(f"Could not achieve target size after {max_attempts} attempts. "
                                 f"Final size: {result_size:.1f}MB "
                                 f"(Target: {target_size_mb:.1f}MB, Quality: {quality}%)")
                    return True
                
        except Exception as e:
            logger.error(f"Failed to reduce file size: {e}")
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

    def upscale_image_waifu2x(self, image_path: str, output_path: str, scale: float = 2.0, noise: int = 1) -> bool:
        """Upscale an image using the waifu2x-converter-cpp command-line tool.

        Parameters:
          image_path: Path to the input image.
          output_path: Path where the upscaled image will be saved.
          scale: Scaling factor (default 2.0).
          noise: Noise reduction level (default 1).

        Returns:
          True if the operation is successful, False otherwise.
        """
        import subprocess
        try:
            command = [
                'waifu2x-converter-cpp',
                '-i', image_path,
                '-o', output_path,
                '-s', str(scale),
                '-n', str(noise)
            ]
            result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if result.returncode != 0:
                logger.error(f"Waifu2x upscaling failed: {result.stderr}")
                return False
            logger.info(f"Upscaled image successfully: {image_path} -> {output_path}")
            return True
        except Exception as e:
            logger.error(f"Exception during Waifu2x upscaling: {e}")
            return False 