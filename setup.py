from setuptools import setup, find_packages
import pathlib

# Read the contents of your README file
here = pathlib.Path(__file__).parent.resolve()
long_description = (here / "README.md").read_text(encoding="utf-8") if (here / "README.md").exists() else ""

setup(
    name="terminator",
    version="1.0.0",
    description="Textual-based AI chat application with conversation history and pagination.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="alxWwang",
    
    # --- CRITICAL FIX: NAMESPACE SAFETY ---
    # This ensures only the 'terminator' folder and its subfolders are installed.
    # It prevents "Data" or "Controller" from polluting the global Python library.
    packages=find_packages(include=["terminator_app", "terminator_app.*"]),
    
    # Automatically include any data files specified in MANIFEST.in
    include_package_data=True,
    
    install_requires=[
        "textual>=0.47.0",
        "google-genai",       # The new v1.0+ SDK
        "python-dotenv>=1.0.0",
        # Removed Pillow if you aren't actually processing images locally, 
        # but keep it if you plan to handle clipboard images.
        "Pillow>=9.0.0", 
    ],
    
    entry_points={
        "console_scripts": [
            # syntax: command_name = package.module:function
            "terminator = terminator_app.main:main"
        ]
    },
    
    # Metadata for better professionalism
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
    ],
    
    python_requires='>=3.10',
)