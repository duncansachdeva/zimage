# ZImage

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PyQt6: GPL v3](https://img.shields.io/badge/PyQt6-GPL%20v3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Made with Python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/)
[![GitHub Release](https://img.shields.io/github/v/release/navdeeps/zimage?include_prereleases)](https://github.com/navdeeps/zimage/releases)

A powerful and versatile image processing and PDF conversion application built with Python and PyQt6. ZImage offers comprehensive image enhancement capabilities, advanced PDF conversion features, and efficient batch processing, all wrapped in a user-friendly interface.

## Features

### Image Enhancement
- **Quality Enhancement**: Improve image quality with three levels (High, Medium, Low)
- **Upscale Image**: AI-powered upscaling using Waifu2x technology
- **Batch Processing**: Process multiple images simultaneously
- **Memory-Optimized**: Efficient processing of large batches (50+ files) with automatic memory management

### PDF Conversion & Management
- **Image to PDF Conversion**:
  - Convert single or multiple images to PDF
  - Customizable page layouts and orientations
  - Adjustable PDF quality settings
  - Smart page ordering for multiple files
  - Custom naming options for output files
- **PDF to Image Extraction**:
  - Extract all or selected pages from PDFs
  - Multiple output format options (PNG, JPG, TIFF)
  - Quality-preserving conversion
  - Batch extraction support
- **PDF Operations**:
  - Combine multiple images into a single PDF
  - Control PDF quality and compression
  - Custom page size and margins
  - Preserve image metadata (optional)
  - Preview PDF before saving

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
1. Download `ZImage.exe` from the releases page
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
- For issues and feature requests, please use our issue tracker
- Check the wiki for detailed usage instructions
- Join our community for discussions and tips

## License
ZImage is released under the MIT License. See the [LICENSE.txt](LICENSE.txt) file for details.

### Third-Party Components
This project uses several third-party components that are distributed under their respective licenses:
- PyQt6 (GPL v3)
- Pillow/PIL (PIL License)
- Waifu2x (MIT)
- PyMuPDF (GPL v3)

For detailed information about third-party components and their licenses, please see [THIRD_PARTY.txt](THIRD_PARTY.txt).

**Note**: While ZImage itself is MIT licensed, it incorporates GPL v3 licensed components (PyQt6, PyMuPDF). When redistributing ZImage, the terms of GPL v3 must be observed for these components.

---
*For issues and feature requests, please use our issue tracker.* 