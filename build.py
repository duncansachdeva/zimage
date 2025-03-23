import os
import shutil
import sys
from loguru import logger

def clean_previous_build():
    """Clean previous build artifacts"""
    logger.info("Cleaning previous build...")
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                logger.info(f"Removed {dir_name} directory")
            except Exception as e:
                logger.error(f"Failed to remove {dir_name}: {e}")

def create_resources():
    """Create necessary directories if needed"""
    logger.info("Setting up resources...")
    resources_dir = os.path.join('src', 'resources')
    icons_dir = os.path.join('src', 'ui', 'icons')
    
    try:
        # Create resources directory
        os.makedirs(resources_dir, exist_ok=True)
        logger.info(f"Created/verified resources directory: {resources_dir}")
        
        # Create icons directory
        os.makedirs(icons_dir, exist_ok=True)
        logger.info(f"Created/verified icons directory: {icons_dir}")
        
    except Exception as e:
        logger.error(f"Failed to create directories: {e}")
        raise
    
    return resources_dir, icons_dir

def build_executable():
    """Build the executable using PyInstaller"""
    try:
        # Clean previous builds
        clean_previous_build()
        
        # Create necessary directories
        resources_dir, icons_dir = create_resources()
        
        # PyInstaller command line arguments
        pyinstaller_args = [
            'pyinstaller',
            '--noconfirm',  # Replace existing spec file
            '--onefile',    # Create a single executable
            '--windowed',   # No console window in Windows
            '--name=ZImage',  # Name of the executable
            '--clean',      # Clean PyInstaller cache
            f'--add-data=src/resources;src/resources',  # Include resources
            f'--add-data=src/ui/icons;src/ui/icons',  # Include icons
            # Add hidden imports
            '--hidden-import=PIL._tkinter_finder',
            '--hidden-import=PyQt6.sip',
            '--hidden-import=PyQt6.QtCore',
            '--hidden-import=PyQt6.QtGui',
            '--hidden-import=PyQt6.QtWidgets',
            '--hidden-import=pdf2image',
            '--hidden-import=fitz',
            '--hidden-import=fpdf',
            '--hidden-import=fpdf.fpdf',
            '--hidden-import=fpdf.image_parsing',
            '--hidden-import=fpdf.svg',
            '--hidden-import=fpdf.output',
            '--hidden-import=fpdf.sign',
            '--hidden-import=unittest',
            # Exclude unnecessary modules to reduce size
            '--exclude-module=matplotlib',
            '--exclude-module=numpy',
            '--exclude-module=pandas',
            '--exclude-module=scipy',
            '--exclude-module=tkinter',
            '--exclude-module=test',
            # Optimize Python bytecode
            '--python-option=O',
            'main.py'  # Main script
        ]
        
        # Run PyInstaller
        logger.info("Starting PyInstaller build...")
        result = os.system(' '.join(pyinstaller_args))
        
        if result == 0:
            logger.info("Build completed successfully!")
            dist_path = os.path.join(os.getcwd(), 'dist')
            exe_path = os.path.join(dist_path, 'ZImage.exe')
            if os.path.exists(exe_path):
                logger.info(f"Executable created at: {exe_path}")
            else:
                logger.error("Executable not found in dist directory!")
        else:
            logger.error(f"Build failed with exit code: {result}")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Build failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    # Setup logging
    logger.remove()  # Remove default handler
    logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}")
    logger.add("build.log", rotation="1 MB")
    logger.info("Starting build process...")
    
    # Run build
    build_executable() 