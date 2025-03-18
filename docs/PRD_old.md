Python based windows utility using PyQt6
Use pillow and Lanczos libraries or any other optimized image processing libraries.
Modular design with performance optimization.

Core Features:
1. Image Enhancement
   - Increase image quality to 100%
   - Add watermark (text/image)
   - Status indicator for each operation

2. Image Resizing (with aspect ratio maintenance)
   - Enlarge image while preserving details
   - Reduce to specified dimensions
   - Reduce file size (small: ~300KB, medium: ~800KB, large: ~2MB)

3. Image Transformation
   - Rotate image (90°, 180°, 270°)
   - Convert to PDF
   - Convert PDF to images

4. Batch Processing
   - Process multiple images simultaneously
   - Input/Output folder selection
   - Drag and drop support
   - Progress tracking for each file

5. File Management
   - Output Naming Options:
     * Same filename (if output in different folder)
     * Custom naming: [original_name]_[user_input]
     * Sequential naming: [original_name]_[1,2,3...]
   - Output folder structure preservation

Performance Considerations:
- Multi-threaded processing for batch operations
- Memory-efficient large file handling
- Operation cancellation support
- Detailed progress tracking

User Interface:
- Clean, modern design
- Operation status indicators
- Progress bars for batch processing
- Simple drag-and-drop interface
- Preview capability for single images

Error Handling:
- Comprehensive error logging
- User-friendly error messages
- Invalid file detection
- Disk space verification