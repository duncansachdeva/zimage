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
            shutil.rmtree(dir_name)
            logger.info(f"Removed {dir_name} directory")

def create_resources():
    """Create resources directory if needed"""
    logger.info("Setting up resources...")
    resources_dir = os.path.join('src', 'resources')
    os.makedirs(resources_dir, exist_ok=True)
    return resources_dir

def build_executable():
    """Build the executable using PyInstaller"""
    try:
        # Clean previous builds
        clean_previous_build()
        
        # Create resources directory
        resources_dir = create_resources()
        
        # PyInstaller command line arguments
        pyinstaller_args = [
            'pyinstaller',
            '--noconfirm',  # Replace existing spec file
            '--onedir',     # Create a single executable
            '--windowed',   # No console window in Windows
            '--name=ZImage',  # Name of the executable
            '--clean',      # Clean PyInstaller cache
            '--add-data=src/resources;resources',  # Include resources
            '--add-data=src/ui/icons;src/ui/icons',  # Include icons
            # Add hidden imports
            '--hidden-import=PIL._tkinter_finder',
            '--hidden-import=PyQt6.sip',
            '--hidden-import=PyQt6.QtCore',
            '--hidden-import=PyQt6.QtGui',
            '--hidden-import=PyQt6.QtWidgets',
            # Exclude unnecessary modules to reduce size
            '--exclude-module=matplotlib',
            '--exclude-module=numpy',
            '--exclude-module=pandas',
            '--exclude-module=scipy',
            '--exclude-module=tkinter',
            '--exclude-module=unittest',
            '--exclude-module=test',
            # Optimize Python bytecode
            '--python-option=O',
            'main.py'  # Main script
        ]
        
        # Run PyInstaller
        logger.info("Starting PyInstaller build...")
        os.system(' '.join(pyinstaller_args))
        
        logger.info("Build completed successfully!")
        logger.info("Executable can be found in the 'dist' directory")
        
    except Exception as e:
        logger.error(f"Build failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    # Setup logging
    logger.add("build.log", rotation="1 MB")
    logger.info("Starting build process...")
    
    # Run build
    build_executable() 