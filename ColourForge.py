### Created By Unpixelled ###

import os
import re
import sys
import time
import math
import json
import shutil
import platform
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser

#Version
VERSION = "1.0.0"

# Current base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Directory where template files are stored (absolute path)
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# Path to settings.cfg
SETTINGS_CFG = os.path.join(BASE_DIR, "settings.cfg")

# File names for Stud.io export
DEFINITION_FILE = "CustomColorDefinition.txt"
SETTINGS_FILE = "CustomColorSettings.xml"

# Parsed Text Markers
END_OF_FORM = "end of form"
SETTINGS_ENDING = "</eyesight>"
DEFINITION_MARKER = "<<< Colour Definition >>>\n"
SETTINGS_MARKER = "<<< Colour Settings >>>\n"

# Fade Duration for splash screen
FADE_DURATION = 2.0

# Checkbox substitution values
CHECKBOX_CHECKED_VALUE = "0.62"
CHECKBOX_UNCHECKED_VALUE = "1.0"

# Size of dropdown box
DROPDOWN_WIDTH = 50

# Colour bar dimensions (next to picker buttons)
COLOUR_BAR_WIDTH = 80  # Width in pixels
COLOUR_BAR_HEIGHT = 20  # Height in pixels

# Miscellaneous constants
CHUNK_SIZE = 8192  # For file copying in chunks to avoid memory issues with large files
TAIL_READ = 16384  # Read last 16KB of file to check for existing entries without loading whole file into memory

############################################################
# Unpixelled's ColourForge
############################################################

# ----------------------------------------------------------
# This application dynamically generates a XML colour code for Bricklink's Stud.io
# based on a template file, by users entering input, and produces output code by replacing 
# placeholders in the template with the provided values. Supports numbers, text, checkboxes,
# and multiple RGB colour pickers.
# Through this method, the app is expandable to as many templates as desired, without needing
# to modify the application code itself.
# ----------------------------------------------------------

##TODO:
# - Scrollbar or dynamic resizing for long forms
# - Scan for group inclusion and add predefined group code if needed (big feature)
# - Gradient support (big feature)
# - Improve error handling and user feedback
# - Multiple OS support
# - Dictionary to support multiple languages

# Check System requirements - OS and Python version
def checkSystemRequirements():
    if sys.version_info < (3, 9):
        print("This application requires Python 3.9 or higher.")
        return False
    
    currentSystem = platform.system()
    if currentSystem not in {"Windows", "Darwin", "Linux"}:
        print(f"Unsupported operating system: {currentSystem}")
        return False

    # On Linux, a display session is required for the GUI
    if currentSystem == "Linux":
        hasDisplay = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        if not hasDisplay:
            print("No GUI display session detected. Please run from a desktop session.")
            return False

    return True

# Initial Logo Splash Screen
def splashLogoAtStart(imagePath: str, fadeDuration: float):
    root = tk.Tk()
    root.withdraw()

    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    splash.attributes("-topmost", True)

    # Load image ##TODO if no image, just skip splash instead of exiting
    try:
        img = tk.PhotoImage(file=imagePath)
    except Exception as e:
        splash.destroy()
        root.destroy()
        print(f"Splash image not found: {e}")
        sys.exit(1)

    label = tk.Label(splash, image=img, borderwidth=0)
    label.image = img  # prevent GC
    label.pack()

    # Center splash
    splash.update_idletasks()
    w = splash.winfo_width()
    h = splash.winfo_height()
    x = (splash.winfo_screenwidth() - w) // 2
    y = (splash.winfo_screenheight() - h) // 2
    splash.geometry(f"{w}x{h}+{x}+{y}")

    splash.attributes("-alpha", 1.0)
    splash.update()

    # Fade logic
    steps = 30
    delay = fadeDuration / steps
    alpha = 1.0
    delta = alpha / steps

    # Fade out
    for _ in range(steps):
        alpha -= delta
        splash.attributes("-alpha", max(alpha, 0))
        splash.update()
        time.sleep(delay)

    splash.destroy()
    root.destroy()

############################################################
# Utility functions for label/colour formatting
############################################################

# Normalises a label by making it lowercase and removing non-alphanumeric characters
# Formats a colour name for use as a setting (uppercase, underscores)
# Converts RGB values to a hex string

def normaliseLabel(label: str) -> str:
    return "".join(c for c in label.lower().strip() if c.isalnum())

def formatColourName(value: str) -> str:
    return value.upper().replace(" ", "_")

def rgbToHex(r, g, b):
    # Be tolerant of floats/strings and clamp to valid 0-255 ints
    try:
        r, g, b = (max(0, min(255, int(round(float(v))))) for v in (r, g, b))
    except (ValueError, TypeError):
        r, g, b = 0, 0, 0
    return f"#{r:02x}{g:02x}{b:02x}"

def readFileLocationFromConfig():
    if not os.path.isfile(SETTINGS_CFG):
        return None
    with open(SETTINGS_CFG, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("FileLocation:"):
                sourceDir = line.split("FileLocation:", 1)[1].strip()
                # Return None if empty or not a valid directory
                return sourceDir if sourceDir and os.path.isdir(sourceDir) else None
    return None

############################################################
# Colour math and colour matching
############################################################

# Converts an RGB dictionary to CIE LAB colour space for colour comparison
# Calculates the Euclidean distance between two LAB colours
# List of known colours for closest colour matching
# Finds the closest colour in COLOUR_LIST to the given RGB value

# Converts an RGB dictionary to CIE LAB colour space for colour comparison
def rgbToLab(rgb):
    r, g, b = rgb["r"] / 255, rgb["g"] / 255, rgb["b"] / 255

    def gamma(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = gamma(r), gamma(g), gamma(b)

    x = (r * 0.4124564 + g * 0.3575761 + b * 0.1804375) / 0.95047
    y = (r * 0.2126729 + g * 0.7151522 + b * 0.0721750)
    z = (r * 0.0193339 + g * 0.1191920 + b * 0.9503041) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else (7.787 * t) + (16 / 116)

    return {
        "L": 116 * f(y) - 16,
        "a": 500 * (f(x) - f(y)),
        "b": 200 * (f(y) - f(z)),
    }

# Calculates the Euclidean distance between two LAB colours
def deltaECalculation(l1, l2):
    return math.sqrt(
        (l2["L"] - l1["L"]) ** 2 +
        (l2["a"] - l1["a"]) ** 2 +
        (l2["b"] - l1["b"]) ** 2
    )

# List of known colours for closest colour matching
# Some are directly from Stud.io, the names are only here for user clarification
COLOUR_LIST = [
    {"id": -1, "name": "black", "rgb": {"r": 0, "g": 0, "b": 0}},
    {"id": -1, "name": "gray", "rgb": {"r": 51, "g": 51, "b": 51}},
    {"id": -1, "name": "gray", "rgb": {"r": 102, "g": 102, "b": 102}},
    {"id": -1, "name": "gray", "rgb": {"r": 153, "g": 153, "b": 153}},
    {"id": -1, "name": "gray", "rgb": {"r": 204, "g": 204, "b": 204}},
    {"id": -1, "name": "white", "rgb": {"r": 255, "g": 255, "b": 255}},
    {"id": 0, "name": "pink", "rgb": {"r": 255, "g": 173, "b": 201}},
    {"id": 1, "name": "red", "rgb": {"r": 153, "g": 17.85, "b": 2}},
    {"id": 2, "name": "orange-red", "rgb": {"r": 102, "g": 53, "b": 6}},
    {"id": 3, "name": "reddish-brown", "rgb": {"r": 40.8, "g": 11.6, "b": 5.5}},
    {"id": 4, "name": "brown", "rgb": {"r": 40.8, "g": 13.8, "b": 5.5}},
    {"id": 5, "name": "orange", "rgb": {"r": 255, "g": 53, "b": 0}},
    {"id": 6, "name": "tan", "rgb": {"r": 209.1, "g": 176.35, "b": 99.9}},
    {"id": 7, "name": "dark-yellow", "rgb": {"r": 170, "g": 84.15, "b": 0}},
    {"id": 8, "name": "yellow", "rgb": {"r": 255, "g": 170, "b": 0}},
    {"id": 9, "name": "yellow-green", "rgb": {"r": 199.7, "g": 255, "b": 89.25}},
    {"id": 11, "name": "light-green", "rgb": {"r": 125.2, "g": 204, "b": 109.65}},
    {"id": 12, "name": "green", "rgb": {"r": 0, "g": 66.3, "b": 20.4}},
    {"id": 13, "name": "aqua", "rgb": {"r": 137.7, "g": 221.85, "b": 203.2}},
    {"id": 14, "name": "azure", "rgb": {"r": 30.6, "g": 147.9, "b": 183.6}},
    {"id": 15, "name": "turquoise", "rgb": {"r": 0, "g": 76.5, "b": 65.3}},
    {"id": 16, "name": "light-blue", "rgb": {"r": 147.3, "g": 194.75, "b": 219.45}},
    {"id": 17, "name": "blue", "rgb": {"r": 0, "g": 26.775, "b": 127.5}},
    {"id": 18, "name": "violet", "rgb": {"r": 7.65, "g": 7.65, "b": 73.95}},
    {"id": 19, "name": "dark-purple", "rgb": {"r": 23.49, "g": 12.4, "b": 63.75}},
    {"id": 20, "name": "purple", "rgb": {"r": 41.25, "g": 6.25, "b": 63.75}},
    {"id": 21, "name": "magenta", "rgb": {"r": 105, "g": 3, "b": 47}},
]

# RGB Field Suffixes
RGB_SUFFIXES = ("rvalue", "gvalue", "bvalue")

# Finds the closest colour in COLOUR_LIST to the given RGB value
def closestColour(rgb):
    inputLAB = rgbToLab(rgb)
    best, dist = None, float("inf")
    for c in COLOUR_LIST:
        d = deltaECalculation(inputLAB, rgbToLab(c["rgb"]))
        if d < dist:
            best, dist = c["id"], d
    return best

############################################################
# Reserved Terms and input sanitisation
############################################################

RESERVED_TERMS = [
    "chrome",
    "glitter",
    "metal",
    "milky",
    "pearl",
    "rubber",
    "satin",
    "solid",
    "speckle",
    "trans"
]


############################################################
# Main Application Class
############################################################

# Main application class for the ColourForge form generator
# List of tuples: (key, field type, tk variable)
# Populated in createField()
# Holds the code block (template) loaded from the selected template file
# Build the GUI widgets and load available templates
# Create the top bar with template selection
# Frame where form fields will be dynamically created
# Loads available template files from the templates directory
# Clears all form fields and resets the code block
# Loads the selected template and parses it to build the form
# Parses the template file, creating form fields and extracting the code block
# Dynamically creates a form field of the given type and label
# Key is a normalised version of the label, used for variable lookup
# Create the appropriate Tkinter variable and widget for each field type
# Store the field for later use in output generation
# Opens a colour picker dialog and sets the selected colour
# If there are associated rvalue/gvalue/bvalue fields, set them as well

class FormFactoryApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Unpixelled's ColourForge V{VERSION}")
        self.geometry("900x700")

        self.fields = []
        self.codeBlock = ""
        self.colourBars = {}  # Maps picker key to (canvas, var) for colour preview bars
        self.updatingFromPicker = False

        self.createWidgets()
        self.loadTemplates()

    def createWidgets(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Label(top, text="Template:").pack(side="left")
        self.templateVar = tk.StringVar()
        self.templateCombo = ttk.Combobox(top, textvariable=self.templateVar, state="readonly", width=DROPDOWN_WIDTH)
        self.templateCombo.pack(side="left", padx=5)
        self.templateCombo.bind("<<ComboboxSelected>>", self.loadTemplate)

        # Scrollable form area
        container = ttk.Frame(self)
        container.pack(fill="both", expand=True, padx=10, pady=10)

        canvas = tk.Canvas(container)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.formFrame = ttk.Frame(canvas)

        self.formFrame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.formFrame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=10)

        # Left-aligned buttons
        ttk.Button(btns, text="Copy to Clipboard", command=self.copyCode).pack(side="left", padx=5)
        ttk.Button(btns, text="Save to File", command=self.saveCode).pack(side="left", padx=5)
        ttk.Button(btns, text="Export", command=self.exportCode).pack(side="left", padx=5)
        ttk.Button(btns, text="Clear", command=self.clearForm).pack(side="left", padx=5)

        # Right-aligned buttons
        ttk.Button(btns, text="Settings", command=self.openSettings).pack(side="right", padx=5)
        ttk.Button(btns, text="Backup", command=self.backup).pack(side="right", padx=5)

    # Loads available template files from the templates directory
    def loadTemplates(self):
        if not os.path.isdir(TEMPLATES_DIR):
            os.makedirs(TEMPLATES_DIR)
        files = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".txt")]
        self.templateCombo["values"] = files

    # Clears all form fields and resets the code block
    def clearForm(self):
        for w in self.formFrame.winfo_children():
            w.destroy()
        self.fields.clear()
        self.codeBlock = ""

    # Loads the selected template and parses it to build the form
    def loadTemplate(self, *_):
        self.clearForm()
        path = os.path.join(TEMPLATES_DIR, self.templateVar.get())
        with open(path, "r", encoding="utf-8") as f:
            self.parseTemplate(f.read())

    # Parses the template file, creating form fields and extracting the code block
    def parseTemplate(self, content):
        lines = content.splitlines()
        section = None
        parsingCode = False
        codeLines = []

        for line in lines:
            raw = line
            line = line.strip()
            if not line or line.startswith("//"):
                continue

            if line == END_OF_FORM:
                parsingCode = True
                continue

            if parsingCode:
                if line.startswith("code"):
                    continue
                # Preserve original leading whitespace for code lines
                codeLines.append(raw)
                continue

            if line.startswith("section"):
                parts = line.split(None, 1)
                title = parts[1].strip() if len(parts) > 1 else ""
                section = ttk.LabelFrame(self.formFrame, text=title)
                section.pack(fill="x", pady=5)
                continue

            t, *label = line.split()
            label = " ".join(label)
            self.createField(section, t, label)

        self.codeBlock = "\n".join(codeLines)

    # Dynamically creates a form field of the given type and label
    def createField(self, parent, ftype, label):

        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=2)

        ttk.Label(frame, text=label).pack(side="left", padx=5)
        key = normaliseLabel(label)

        if ftype == "checkbox":
            var = tk.BooleanVar()
            widget = ttk.Checkbutton(frame, variable=var)
        elif ftype == "number":
            var = tk.StringVar()
            widget = ttk.Entry(frame, textvariable=var)
            # If this is an RGB field, add a trace to update the picker for updates
            if key.endswith("rvalue") or key.endswith("gvalue") or key.endswith("bvalue"):
                var.trace_add("write", lambda *_, k=key: self.onRgbFieldChanged(k))
        elif ftype == "text":
            var = tk.StringVar()
            widget = ttk.Entry(frame, textvariable=var)
        elif ftype == "lightType":
            var = tk.StringVar()
            widget = ttk.Combobox(
                frame,
                textvariable=var,
                state="readonly",
                values=["Fresnel","Facing"]
            )
            widget.current(0)
        elif ftype == "picker":
            var = tk.StringVar(value="#ffffff")
            widget = ttk.Button(
                frame,
                text="Pick",
                command=lambda v=var, k=key: self.pickColour(v, k)
            )
            # Create colour preview bar next to picker
            colourBar = tk.Canvas(frame, width=COLOUR_BAR_WIDTH, height=COLOUR_BAR_HEIGHT, bg="#ffffff", highlightthickness=1, highlightbackground="#888888")
            colourBar.pack(side="left", padx=5)
            self.colourBars[key] = (colourBar, var)
            # Add trace to update colour bar when var changes
            var.trace_add("write", lambda *_, k=key: self.updateColourBar(k))
        elif ftype == "desc":
            var = None
            widget = ttk.Label(frame, text=label)
            return
        else:
            return

        widget.pack(side="left")
        # Store label too so we can show friendly error messages on validation
        self.fields.append((key, ftype, var, label))

    # Opens a colour picker dialog and sets the selected colour
    def pickColour(self, var, key):
        c = colorchooser.askcolor()[0]
        if not c:
            return
        r, g, b = map(int, c)
        var.set(rgbToHex(r, g, b))

        # Temporarily disable RGB field traces to avoid feedback loop
        self.updatingFromPicker = True
        for suffix, value in zip(("rvalue", "gvalue", "bvalue"), (r, g, b)):
            for k, _, v, _ in self.fields:
                if k == f"{key.replace('colourpicker','colour')}{suffix}":
                    v.set(str(value))
        self.updatingFromPicker = False

        # Update the colour bar
        self.updateColourBar(key)

    # Updates the colour bar canvas for a given picker key
    def updateColourBar(self, pickerKey):
        if pickerKey not in self.colourBars:
            return
        colourBar, var = self.colourBars[pickerKey]
        hex_colour = var.get()
        # Validate hex format
        if hex_colour.startswith("#") and len(hex_colour) == 7:
            try:
                colourBar.configure(bg=hex_colour)
            except tk.TclError:
                messagebox.showerror("Colour update to colour bar failed. Invalid colour value.")
                colourBar.configure(bg="#ff00ff")  # Magenta = error indicator
                pass  # Invalid colour, ignore

    # Updates the picker hex value when RGB number fields are manually changed
    def onRgbFieldChanged(self, changedKey):
        if getattr(self, 'updatingFromPicker', False):
            return

        prefix = None
        for suffix in RGB_SUFFIXES:
            if changedKey.endswith(suffix):
                prefix = changedKey[:-len(suffix)]
                break
        if not prefix:
            return

        # Create a mapping of keys to variables for easy lookup through pickers
        fieldMap = {k: v for k, _, v, _ in self.fields}
        
        rgb = []
        for suffix in RGB_SUFFIXES:
            key = f"{prefix}{suffix}"
            try:
                val = int(fieldMap.get(key, tk.StringVar()).get())
            except (ValueError, tk.TclError):
                val = 0
            rgb.append(val)  # Let rgbToHex handle clamping

        pickerKey = f"{prefix}picker"
        if pickerKey in fieldMap:
            fieldMap[pickerKey].set(rgbToHex(*rgb))

    ############################################################
    # Output Generation Logic
    ############################################################
    def generateOutput(self):
        # Generates the output code by replacing placeholders in the template with user-provided values.
        # Fields are collected in order of appearance.
        # Only the first RGB picker fills !Hex! and !ColourCategory! as it is considered the "main" colour.
        # Each picker fills its own indexed RGB placeholders, supporting multiple colours.
        # Number, text, and checkbox fields are filled sequentially.

        out = self.codeBlock

        # Collect all values by type in order, but keep pickers and numbers separate
        textValues = []
        numberValues = []
        checkboxValues = []
        pickers = []  # Each picker is a dict with r, g, b
        colourname = None
        colourid = None
        lightType = None
        rgbFields = {}

        if not self.validateFields():
            return None

        # Ensure pickers are appended in the order they appear in the form
        for key, ftype, var, label in self.fields:
            val = var.get()
            if key == "colourname":
                colourname = val
            elif key == "colourid":
                colourid = val
            elif key == "lighttype":
                lightType = val
            elif ftype == "text":
                textValues.append(val)
            elif ftype == "number":
                # Exclude number fields that are part of RGB (rvalue, gvalue, bvalue)
                if not (key.endswith("rvalue") or key.endswith("gvalue") or key.endswith("bvalue")):
                    # Validate numeric input
                    if val is None or str(val).strip() == "":
                        messagebox.showerror("Input Error", f"Number field '{label}' is empty. Please enter a numeric value.")
                        return None
                    try:
                        float(val)
                        numberValues.append(val)
                    except Exception:
                        messagebox.showerror("Input Error", f"Invalid number in field '{label}'. Please enter a numeric value.")
                        return None
            elif ftype == "checkbox":
                checkboxValues.append(CHECKBOX_CHECKED_VALUE if var.get() else CHECKBOX_UNCHECKED_VALUE)
            elif ftype == "picker":
                hex_val = val
                if hex_val.startswith("#") and len(hex_val) == 7:
                    r = int(hex_val[1:3], 16)
                    g = int(hex_val[3:5], 16)
                    b = int(hex_val[5:7], 16)
                    pickers.append({"r": r, "g": g, "b": b, "_order": len(pickers)})

            # For legacy rvalue/gvalue/bvalue fields from JS version - validate integers
            if key.endswith("rvalue"):
                try:
                    r_val = int(val)
                    if not (0 <= r_val <= 255):
                        raise ValueError("RGB value out of range")
                    rgbFields.setdefault(key[:-6], {})["r"] = r_val
                except Exception:
                    messagebox.showerror("Input Error", f"Invalid R value in field '{label}'. Please enter an integer between 0 and 255.")
                    return None
            elif key.endswith("gvalue"):
                try:
                    g_val = int(val)
                    if not (0 <= g_val <= 255):
                        raise ValueError("RGB value out of range")
                    rgbFields.setdefault(key[:-6], {})["g"] = g_val
                except Exception:
                    messagebox.showerror("Input Error", f"Invalid G value in field '{label}'. Please enter an integer between 0 and 255.")
                    return None
            elif key.endswith("bvalue"):
                try:
                    b_val = int(val)
                    if not (0 <= b_val <= 255):
                        raise ValueError("RGB value out of range")
                    rgbFields.setdefault(key[:-6], {})["b"] = b_val
                except Exception:
                    messagebox.showerror("Input Error", f"Invalid B value in field '{label}'. Please enter an integer between 0 and 255.")
                    return None

        # Sort pickers by their order of appearance (just in case)
        pickers.sort(key=lambda x: x.get("_order", 0))
        for p in pickers:
            if "_order" in p:
                del p["_order"]

        # Replace all !number!, !text!, !checkbox! sequentially (do NOT use picker values for numbers)
        def replaceSequentially(template, placeholder, values):
            idx = 0
            while placeholder in template and idx < len(values):
                template = template.replace(placeholder, str(values[idx]), 1)
                idx += 1

            return template

        out = replaceSequentially(out, "!number!", numberValues)
        out = replaceSequentially(out, "!text!", textValues)
        out = replaceSequentially(out, "!checkbox!", checkboxValues)

        # Only the first picker fills !Hex! and !ColourCategory!; all pickers fill their RGB value placeholders
        if pickers:
            for i, rgb in enumerate(pickers):
                if i == 0:
                    out = out.replace("!ColourRValue!", str(rgb["r"] / 255), 1)
                    out = out.replace("!ColourGValue!", str(rgb["g"] / 255), 1)
                    out = out.replace("!ColourBValue!", str(rgb["b"] / 255), 1)
                    out = out.replace("!Hex!", rgbToHex(**rgb), 1)
                    out = out.replace("!ColourCategory!", str(closestColour(rgb)), 1)

                idx = i + 1
                out = out.replace(f"!ColourRValue{idx}!", str(rgb["r"] / 255), 1)
                out = out.replace(f"!ColourGValue{idx}!", str(rgb["g"] / 255), 1)
                out = out.replace(f"!ColourBValue{idx}!", str(rgb["b"] / 255), 1)

            # Remove any indexed !HexN! and !ColourCategoryN! placeholders if present
            out = re.sub(r"!Hex\d+!", "", out)
            out = re.sub(r"!ColourCategory\d+!", "", out)

        elif rgbFields:
            # Fallback: legacy behaviour for rvalue/gvalue/bvalue fields from JS version
            for idx, (prefix, rgb) in enumerate(rgbFields.items()):
                if all(k in rgb for k in ("r", "g", "b")):
                    if idx == 0:
                        out = out.replace("!ColourRValue!", str(rgb["r"] / 255), 1)
                        out = out.replace("!ColourGValue!", str(rgb["g"] / 255), 1)
                        out = out.replace("!ColourBValue!", str(rgb["b"] / 255), 1)
                        out = out.replace("!Hex!", rgbToHex(**rgb), 1)
                        out = out.replace("!ColourCategory!", str(closestColour(rgb)), 1)

                    idx1 = idx + 1
                    out = out.replace(f"!ColourRValue{idx1}!", str(rgb["r"] / 255), 1)
                    out = out.replace(f"!ColourGValue{idx1}!", str(rgb["g"] / 255), 1)
                    out = out.replace(f"!ColourBValue{idx1}!", str(rgb["b"] / 255), 1)
                    out = out.replace(f"!Hex{idx1}!", rgbToHex(**rgb), 1)
                    out = out.replace(f"!ColourCategory{idx1}!", str(closestColour(rgb)), 1)

        # Replace colourname, colourid, and lightType
        if colourname is not None:
            out = out.replace("!ColourName!", colourname)
            out = out.replace("!ColourNameSetting!", formatColourName(colourname))
        if colourid is not None:
            out = out.replace("!ColourID!", colourid)
        if lightType is not None:
            while "!lightType!" in out:
                out = out.replace("!lightType!", lightType)

        return out
    
    # Confirm fields are valid before output generation
    def validateFields(self):
        # First check fields exist and the page isn't empty
        if not self.fields:
            messagebox.showerror("Input Error", "No fields found in the form. Please select a valid template.")
            return False
        # Loop through fields to validate, one loop multiple checks for efficiency
        for key, ftype, var, label in self.fields:
            # First check that no fields are empty
            val = var.get()
            if ftype in ("text", "number", "picker") and (val is None or str(val).strip() == ""):
                messagebox.showerror("Input Error", f"Field '{label}' is empty. Please provide a value.")
                return False
            
            # Check name does not contain keywords used by Stud.io at the start of colour names
            if key == "colourname":
                if any(val.lower().startswith(term) for term in RESERVED_TERMS):
                    messagebox.showerror("Input Error", f"Colour Name '{val}' contains a reserved keyword in Stud.io. Please choose a different name.")
                    return False
            
            # Confirm the colour ID is an integer within range of 0-100,000,000 (Stud.io's colour ID limit)
            if key == "colourid":
                if not val.isdigit():
                    messagebox.showerror("Input Error", f"Colour ID '{val}' is not a valid Number!")
                    return False
                val = int(var.get())
                if val > 100000000 or val < 0:
                    messagebox.showerror("Input Error", f"Colour ID '{val}' is out of range. This will not appear in Stud.io's colour list.")
                    return False

        return True

    # Copies the generated code to the clipboard
    def copyCode(self):
        out = self.generateOutput()

        if out is None:
            return
        
        # Add a little comment to the end of the inserted settings
        out = out + f"<!-- Added by Unpixelled's ColourForge on {time.strftime('%Y-%m-%d %H:%M:%S')} -->"

        # Copy to clipboard
        self.clipboard_clear()
        self.clipboard_append(out)
        messagebox.showinfo("Copied", "Code copied to clipboard")

    # Saves the generated code to a file
    def saveCode(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt")

        if not path:
            return
        
        out = self.generateOutput()
        if out is None:
            return
        
        # Add a little comment to the end of the inserted settings
        out = out + f"<!-- Added by Unpixelled's ColourForge on {time.strftime('%Y-%m-%d %H:%M:%S')} -->"

        # Write to file
        with open(path, "w", encoding="utf-8") as f:
            f.write(out)

    # Export code to stud.io files
    def exportCode(self):

        out = self.generateOutput()
        if out is None:
            return None
        
        defIdentifier = out.find(DEFINITION_MARKER)
        setIdentifier = out.find(SETTINGS_MARKER)

        if defIdentifier == -1 or setIdentifier == -1 or defIdentifier > setIdentifier:
            messagebox.showerror("Export Error", "Definition/Settings headers not found or in wrong order in generated output.")
            return None

        # Extract definition and settings sections
        definition = out[defIdentifier + len(DEFINITION_MARKER):setIdentifier].strip()
        # Keep raw settings (do NOT strip) so leading whitespace/indentation is preserved
        settings = out[setIdentifier + len(SETTINGS_MARKER):]

        # Write to files
        self.writeDefinition(definition)
        self.writeSettings(settings)

        return definition, settings

    # Writes the definition to the appropriate file
    def writeDefinition(self, definition):
        # Read FileLocation from cfg, confirm files from settings.cfg exist
        sourceDir = readFileLocationFromConfig()
        if not sourceDir:
            messagebox.showerror("Definition Write Error", "Invalid or missing FileLocation in settings.cfg.")
            return

        # Write definition to file, making sure to write at the end of the file on a new line
        defPath = os.path.join(sourceDir, DEFINITION_FILE)
        try:
            with open(defPath, "a", encoding="utf-8") as f:
                if os.path.getsize(defPath) > 0:
                    f.write("\n")
                f.write(definition)
            messagebox.showinfo("Definition Write Complete", f"Definition written to {DEFINITION_FILE}, proceed to settings export.")
        except Exception as e:
            messagebox.showerror("Definition Write Error", str(e))

        return

    # Writes the settings to the appropriate file
    def writeSettings(self, settings):
        # Read FileLocation from cfg, confirm files from settings.cfg exist
        sourceDir = readFileLocationFromConfig()
        if not sourceDir:
            messagebox.showerror("Settings Write Error", "Invalid or missing FileLocation in settings.cfg.")
            return

        # Write settings into the settings file, inserting them before SETTINGS_ENDING
        settingsPath = os.path.join(sourceDir, SETTINGS_FILE)
        tempPath = settingsPath + ".tmp"
        tempCreated = False

        try:
            # Read only the tail of the file to locate SETTINGS_ENDING so we don't 
            # load the entire multi-MB settings file into memory (at least mine is 2mb+)
            size = os.path.getsize(settingsPath)
            readSize = min(size, TAIL_READ)

            with open(settingsPath, "rb") as fr:
                # Seek to the tail area and read it
                if size > readSize:
                    fr.seek(-readSize, os.SEEK_END)
                else:
                    fr.seek(0)
                tailBytes = fr.read()
            try:
                tail = tailBytes.decode("utf-8")
            except Exception:
                # Fallback decode permissively
                tail = tailBytes.decode("utf-8", errors="replace")

            posInTail = tail.find(SETTINGS_ENDING)
            if posInTail == -1:
                # If the ending marker is not present, consider the settings file invalid and abort
                messagebox.showerror("Settings Write Error", f"{SETTINGS_FILE} is missing expected ending marker {SETTINGS_ENDING}; file appears invalid.")
                return

            # Compute absolute byte position of the marker in the file
            if size > readSize:
                absPosInFile = size - readSize + posInTail
            else:
                absPosInFile = posInTail

            # Prepare text to insert (ensure newline at end)
            settingsToWrite = settings
            if not settingsToWrite.endswith("\n"):
                settingsToWrite += "\n"

            # Add a little comment to the end of the inserted settings :)
            settingsToWrite += f"<!-- Added by Unpixelled's ColourForge on {time.strftime('%Y-%m-%d %H:%M:%S')} -->\n\n"

            # Stream-copy: write a temp file by copying bytes up to absPosInFile,
            # then write the settings text (utf-8), then copy the remainder
            with open(settingsPath, "rb") as fr, open(tempPath, "wb") as fw:
                tempCreated = True

                # Copy up to absPosInFile
                remaining = absPosInFile
                while remaining > 0:
                    toRead = CHUNK_SIZE if remaining >= CHUNK_SIZE else remaining
                    data = fr.read(toRead)
                    if not data:
                        break
                    fw.write(data)
                    remaining -= len(data)

                # Ensure there's a newline before insertion if not present
                # Check last byte written in fileWrite (seek)
                fw.flush()

                # Write settings text as utf-8
                fw.write(settingsToWrite.encode("utf-8"))

                # Seek original to absPosInFile and copy rest
                fr.seek(absPosInFile)
                shutil.copyfileobj(fr, fw)

            # Replace original file atomically
            os.replace(tempPath, settingsPath)
            tempCreated = False  # Successfully replaced, no cleanup needed

            messagebox.showinfo("Settings Write Complete", f"Settings written to {SETTINGS_FILE}, colour write complete.")

        except Exception as e:
            messagebox.showerror("Settings Write Error", str(e))

        finally:
            # Clean up temp file if it still exists (indicates failure)
            if tempCreated and os.path.exists(tempPath):
                try:
                    os.remove(tempPath)
                except OSError:
                    pass

    # Backup function copy the existing custom colour definition and settings files
    def backup(self):
        try:
            # Read FileLocation from cfg, confirm files from settings.cfg exist
            sourceDir = readFileLocationFromConfig()
            if not sourceDir:
                messagebox.showerror("Backup Error", "Invalid or missing FileLocation in settings.cfg.")
                return

            backupDirectory = os.path.join(BASE_DIR, "backup")
            os.makedirs(backupDirectory, exist_ok=True)

            timestamp = time.strftime("%y%m%d_%H%M")
            filesToBackup = [DEFINITION_FILE, SETTINGS_FILE]

            copied = []

            for filename in filesToBackup:
                src = os.path.join(sourceDir, filename)
                if not os.path.isfile(src):
                    continue

                name, ext = os.path.splitext(filename)
                dst_name = f"{name}_{timestamp}{ext}"
                dst = os.path.join(backupDirectory, dst_name)

                shutil.copy2(src, dst)
                copied.append(dst_name)

            if copied:
                messagebox.showinfo(
                    "Backup Complete",
                    "Backed up files:\n" + "\n".join(copied)
                )
            else:
                messagebox.showwarning(
                    "Backup Warning",
                    "No files were backed up (files missing?)."
                )

        except Exception as e:
            messagebox.showerror("Backup Error", str(e))

    # Opens the settings file
    def openSettings(self):
        if not os.path.isfile(SETTINGS_CFG):
            messagebox.showerror("Settings Error", "settings.cfg was not found.")
            return
        
        try:
            systemName = platform.system()
            if systemName == "Windows":
                os.startfile(SETTINGS_CFG)
            elif systemName == "Darwin":  # macOS
                subprocess.run(["open", SETTINGS_CFG], check=False)
            elif systemName == "Linux":   # Ubuntu and other Linux distros
                subprocess.run(["xdg-open", SETTINGS_CFG], check=False)
            else:
                messagebox.showerror("Settings Error", f"Unsupported OS: {systemName}")
        except Exception as exc:
            messagebox.showerror("Settings Error", f"Could not open settings file: {exc}")
        
            ##TODO known error where this adds a newline to terminal
            
############################################################
# Main Execution
############################################################

if __name__ == "__main__":
    #Check System Requirements like OS and Python version
    if not checkSystemRequirements():
        sys.exit(1)

    #Show the splash screen logo
    splashLogoAtStart(os.path.join(BASE_DIR, "splash.png"), FADE_DURATION)

    #Begin main application
    FormFactoryApp().mainloop()