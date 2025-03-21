from PIL import Image
import os
import shutil
from loguru import logger
from typing import Optional
from fpdf import FPDF
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
        # Letter size in inches converted to points (1 inch = 72 points)
        self.page_width = 8.5 * 72
        self.page_height = 11 * 72
        
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
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
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
            
    def convert_to_pdf(self, image_paths: list, output_path: str, combine_files=False,
                      orientation='Auto', images_per_page=1, fit_mode='Fit to page',
                      quality='High') -> bool:
        """Convert image(s) to PDF with enhanced options.
        
        Args:
            image_paths: List of image paths to convert
            output_path: Path to save the PDF(s)
            combine_files: Whether to combine all images into one PDF
            orientation: Page orientation ('Auto', 'Portrait', 'Landscape')
            images_per_page: Number of images per page (1, 2, 4, or 6)
            fit_mode: How to fit images ('Fit to page', 'Stretch to fill', 'Actual size')
            quality: PDF quality ('High', 'Medium', 'Low')
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure image_paths is a list of strings
            if isinstance(image_paths, str):
                image_paths = [image_paths]
            
            # Validate images first
            valid_images = []
            for img_path in image_paths:
                if self.validate_image(str(img_path)):
                    valid_images.append(str(img_path))
            
            if not valid_images:
                logger.error("No valid images to convert")
                return False
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
            if combine_files:
                return self._create_combined_pdf(valid_images, output_path, orientation,
                                              images_per_page, fit_mode, quality)
            else:
                return self._create_individual_pdfs(valid_images, output_path, orientation,
                                                 images_per_page, fit_mode, quality)
                
        except Exception as e:
            logger.error(f"PDF conversion failed: {str(e)}")
            return False
            
    def _create_individual_pdfs(self, image_paths, output_base_path, orientation,
                              images_per_page, fit_mode, quality):
        """Create individual PDFs for each image."""
        try:
            success = True
            output_dir = os.path.dirname(output_base_path)
            
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            for image_path in image_paths:
                # Generate output path
                filename = os.path.splitext(os.path.basename(image_path))[0]
                pdf_path = os.path.join(output_dir, f"{filename}.pdf")
                
                # Create PDF for single image
                pdf = FPDF()
                pdf.set_auto_page_break(auto=True, margin=15)
                self._add_images_to_page(pdf, [image_path], orientation, fit_mode, quality)
                pdf.output(pdf_path)
                logger.info(f"Created individual PDF: {pdf_path}")
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to create individual PDFs: {str(e)}")
            return False
            
    def _create_combined_pdf(self, image_paths, output_path, orientation,
                           images_per_page, fit_mode, quality):
        """Create a single PDF containing all images."""
        try:
            # Ensure output path has .pdf extension
            if not output_path.lower().endswith('.pdf'):
                output_path = os.path.splitext(output_path)[0] + '.pdf'
            
            # Create PDF
            pdf = FPDF()
            pdf.set_auto_page_break(auto=True, margin=15)
            
            # Process images in batches based on images_per_page
            images_per_page = int(images_per_page)  # Ensure it's an integer
            total_images = len(image_paths)
            
            for i in range(0, total_images, images_per_page):
                # Get current batch of images
                batch = image_paths[i:i + images_per_page]
                self._add_images_to_page(pdf, batch, orientation, fit_mode, quality)
                logger.info(f"Added page {i // images_per_page + 1} with {len(batch)} images")
            
            # Save the PDF
            pdf.output(output_path)
            logger.info(f"Created combined PDF: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create combined PDF: {str(e)}")
            return False

    def _add_images_to_page(self, pdf, image_paths, orientation, fit_mode, quality):
        """Add a batch of images to a single PDF page with dynamic layout."""
        try:
            # Determine page orientation based on first image if Auto
            first_image = Image.open(image_paths[0])
            auto_orientation = first_image.width > first_image.height
            first_image.close()
            
            if orientation == 'Auto':
                pdf.add_page('L' if auto_orientation else 'P')
            else:
                pdf.add_page('L' if orientation == 'Landscape' else 'P')
            
            # Get number of images for this page
            num_images = len(image_paths)
            
            # Calculate layout based on number of images
            layouts = self._calculate_layout(num_images)
            
            # Add images to page
            for image_path, layout in zip(image_paths, layouts):
                x1, y1, x2, y2 = layout
                with Image.open(image_path) as img:
                    # Calculate dimensions based on fit mode
                    if fit_mode == 'Stretch to fill':
                        w = (x2 - x1) * pdf.w
                        h = (y2 - y1) * pdf.h
                    elif fit_mode == 'Actual size':
                        w = min((x2 - x1) * pdf.w, img.width)
                        h = min((y2 - y1) * pdf.h, img.height)
                    else:  # Fit to page
                        rect_w = (x2 - x1) * pdf.w
                        rect_h = (y2 - y1) * pdf.h
                        img_ratio = img.width / img.height
                        rect_ratio = rect_w / rect_h
                        
                        if img_ratio > rect_ratio:
                            w = rect_w
                            h = rect_w / img_ratio
                        else:
                            h = rect_h
                            w = rect_h * img_ratio
                    
                    # Calculate position to center image in its cell
                    x = x1 * pdf.w + ((x2 - x1) * pdf.w - w) / 2
                    y = y1 * pdf.h + ((y2 - y1) * pdf.h - h) / 2
                    
                    # Convert quality setting to compression level
                    if quality == 'High':
                        compress = False
                    elif quality == 'Medium':
                        compress = True
                    else:  # Low
                        compress = True
                        w = w * 0.75  # Reduce image size for low quality
                        h = h * 0.75
                    
                    # Add image to PDF
                    pdf.image(image_path, x, y, w, h)
                    
        except Exception as e:
            logger.error(f"Failed to add images to page: {str(e)}")
            raise  # Re-raise to be caught by calling function

    def _calculate_layout(self, num_images):
        """Calculate layout coordinates for the given number of images."""
        if num_images == 1:
            return [(0, 0, 1, 1)]
        elif num_images == 2:
            return [(0, 0, 0.5, 1), (0.5, 0, 1, 1)]
        elif num_images <= 4:
            # 2x2 grid
            layouts = [
                (0, 0, 0.5, 0.5),     # Top-left
                (0.5, 0, 1, 0.5),     # Top-right
                (0, 0.5, 0.5, 1),     # Bottom-left
                (0.5, 0.5, 1, 1)      # Bottom-right
            ]
            return layouts[:num_images]  # Return only needed layouts
        else:
            # 3x2 grid (up to 6 images)
            layouts = [
                (0, 0, 0.33, 0.5),      # Top-left
                (0.33, 0, 0.66, 0.5),   # Top-middle
                (0.66, 0, 1, 0.5),      # Top-right
                (0, 0.5, 0.33, 1),      # Bottom-left
                (0.33, 0.5, 0.66, 1),   # Bottom-middle
                (0.66, 0.5, 1, 1)       # Bottom-right
            ]
            return layouts[:num_images]  # Return only needed layouts
            
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