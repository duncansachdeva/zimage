# ZImage (Beta)

A powerful and user-friendly image processing application built with Python and PyQt6.

## Features

### Image Enhancement
- **Quality Enhancement**: Improve image quality with three levels (High, Medium, Low)
- **Upscale Image**: AI-powered upscaling using Waifu2x technology
- **Batch Processing**: Process multiple images simultaneously
- **Memory-Optimized**: Efficient processing of large batches (50+ files) with automatic memory management

### Image Conversion
- **Format Conversion**: Support for various image formats (PNG, JPG, TIFF)
- **PDF Conversion**:
  - Convert images to PDF (single or multiple pages)
  - Convert PDF to images with customizable settings
  - Combine multiple images into a single PDF
  - Control PDF quality and page layout

### Image Manipulation
- **Resize Images**: 
  - Custom width and height settings
  - Maintain aspect ratio option
  - Batch resize capability
- **File Size Reduction**: 
  - Target size specification in MB
  - Quality-aware compression
  - Batch optimization support

### User Interface
- **Modern UI**: Clean and intuitive interface
- **Drag & Drop**: Easy file loading
- **Preview**: Real-time image preview
- **Progress Tracking**: Visual progress indicators for all operations
- **Dark/Light Theme**: Customizable application appearance

### File Management
- **Custom Output Naming**:
  - Keep original filenames
  - Add custom suffixes
  - Sequential numbering
- **Output Directory**: Configurable output location
- **Action Queue**:
  - Create and save custom processing queues
  - Load saved queues for repeated tasks
  - Reorder processing steps
  - Enable/disable specific actions

### Advanced Features
- **Memory Management**:
  - Batch processing with memory optimization
  - Automatic garbage collection
  - Temporary file cleanup
- **Error Handling**:
  - Detailed error logging
  - Recovery from processing failures
  - Batch operation resilience

## System Requirements
- Windows 10 or later
- 4GB RAM minimum (8GB recommended for large batches)
- 500MB free disk space

## Installation
1. Download `ZImage_Beta.exe` from the releases page
2. Run the executable - no installation required
3. First run will create necessary configuration files

## Usage
1. Launch ZImage
2. Drag and drop images or use the file selector
3. Choose desired processing actions
4. Configure action parameters if needed
5. Click "Process Files" to begin
6. Find processed files in the selected output directory

## Notes
- Processing time varies based on file size and selected actions
- Large batch operations are automatically optimized for memory usage
- Temporary files are automatically cleaned up
- Settings are preserved between sessions

## Support
- For issues and feature requests, please use the issue tracker
- Check the wiki for detailed usage instructions
- Join our community for discussions and tips

## License
[License details to be added]

---
*ZImage is currently in beta. While fully functional, you may encounter occasional issues. Please report any problems through our issue tracker.* 