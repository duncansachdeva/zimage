# ZImage - Image Processing Utility

A Python-based Windows utility for batch image processing with a modern GUI interface.

## Features

- Image quality enhancement
- Image resizing with aspect ratio maintenance
- File size reduction
- Image rotation
- Watermark addition
- PDF conversion (both ways)
- Batch processing support
- Drag and drop interface

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/zimage.git
cd zimage
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
.\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python src/main.py
```

2. Using the application:
   - Drag and drop images into the application window
   - Select the desired operation from the dropdown menu
   - Configure operation-specific options if needed
   - Click "Process Files" and select output directory
   - Wait for processing to complete

## Supported Operations

1. **Enhance Quality**
   - Increases image quality to 100%

2. **Resize Image**
   - Enlarge or reduce image size while maintaining aspect ratio
   - Specify target dimensions

3. **Reduce File Size**
   - Small (~300KB)
   - Medium (~800KB)
   - Large (~2MB)

4. **Rotate Image**
   - 90°, 180°, or 270° rotation options

5. **Add Watermark**
   - Add text watermark to images

6. **Convert to PDF**
   - Convert single or multiple images to PDF

7. **Convert from PDF**
   - Extract images from PDF files

## Error Handling

- The application includes comprehensive error logging
- Logs are stored in the `logs` directory
- Invalid files are automatically detected and skipped
- User-friendly error messages are displayed

## Requirements

- Windows 10 or later
- Python 3.8 or later
- See requirements.txt for Python package dependencies

## License

MIT License - see LICENSE file for details 