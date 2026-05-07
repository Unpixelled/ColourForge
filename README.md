# Unpixelled's ColourForge
A Custom Colour Maker for Bricklink's Stud.io

V1.0.2

## Features

- A variety of templates to choose from (easily expandable and supports custom types)
- Clipboad copy, text file export and direct export to Stud.io
- Backup system for Custom Colours
- Simple settings system (there's only one so far!)

## Requirements

- Python 3.9 or newer
- Bricklink Stud.io (for importing generated XML)
- Windows (tested platform)

## Templates

Templates are stored in the `templates/` directory.

- Templates define form layout and output structure
- New templates can be added without modifying the application
- Templates must use the `.txt` extension

## Running the Application

1. Ensure Python is installed and available on your PATH
2. Place all application files in a directory (keep them in the same folder)
3. Open the directory in the command line and type:
    python ColourForge.py

Using the following command, this can be made into a executable:
pyinstaller --onefile --noconsole App.py

This is still being tested as it massively inflates the file size.

## Improvements and planned features:
- Gradient field support and control in templates
- Custom group export/inclusion
- Language support (potential collaboration needed)
- Recommended values in templates or autofill
- Improve accuracy of estimated colour category
- Render a brick if possible as changes are made (the dream)
- Texture support