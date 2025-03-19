from setuptools import setup, find_packages

setup(
    name="zimage",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "PyQt6>=6.4.0",
        "Pillow>=10.0.0",
        "pdf2image>=1.16.3",
        "img2pdf>=0.4.4",
        "loguru>=0.7.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.3.1",
            "black>=23.0.0",
            "flake8>=6.0.0",
        ],
    },
) 