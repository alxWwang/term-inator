from setuptools import setup, find_packages

setup(
    name="terminator",
    version="1.0.0",
    description="Textual-based AI chat application with conversation history and pagination.",
    author="alxWwang",
    packages=find_packages(),
    install_requires=[
        "textual>=0.47.0",
        "google-generativeai>=0.3.0",
        "Pillow>=9.0.0",
        "python-dotenv>=1.0.0"
    ],
    entry_points={
        "console_scripts": [
            "terminator = main:main"
        ]
    },
    include_package_data=True,
    python_requires='>=3.10',
)
