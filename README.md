# ZImage - Image Processing Utility

A Python-based Windows utility for batch image processing with a modern GUI interface.

## Features

1. **Enhance Quality**
   - Maximize image quality settings
   - Optimize for best visual results

2. **Resize Image**
   - Maintain aspect ratio
   - Choose between width or height constraint
   - High-quality resizing algorithm

3. **Reduce File Size**
   - Target specific file size
   - Smart compression
   - Preserve visual quality

4. **Image to PDF**
   - Single or multiple images
   - Customizable layout
   - Quality settings

5. **PDF to Image**
   - Extract images from PDFs
   - High-quality conversion
   - Batch processing support

6. **Upscale Image (Waifu2x)**
   - AI-powered upscaling
   - Noise reduction
   - Best for anime/manga style images

7. **Image Rotation**
   - 90°, 180°, or 270° rotation options

8. **Add Watermark**
   - Add text watermark to images

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

6. **Image to PDF**
   - Convert single or multiple images to PDF

7. **PDF to Image**
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