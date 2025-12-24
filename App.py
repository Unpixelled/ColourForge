### Created By Unpixelled ###

import os
import sys
import time
import math
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser

# Directory where template files are stored
TEMPLATES_DIR = "templates"

# Unpixelled's ColourForge
# --------------------------
# This application dynamically generates a XML colour code for Bricklink's Stud.io
# based on a template file, by users entering input, and produces output code by replacing 
# placeholders in the template with the provided values. Supports numbers, text, checkboxes,
# and multiple RGB colour pickers.
# Through this method, the app is expandable to as many templates as desired, without needing
# to modify the application code itself.
# --------------------------

#Initial Logo Splash Screen
def splashLogoAtStart(image_path: str, fade_duration: float):
    """
    Displays a splash image and fades it out over fade_duration seconds.
    This is a blocking call and does NOT start mainloop().
    Intended to be called immediately before creating the main app.
    """

    root = tk.Tk()
    root.withdraw()

    splash = tk.Toplevel(root)
    splash.overrideredirect(True)
    splash.attributes("-topmost", True)

    # Load image
    try:
        img = tk.PhotoImage(file=image_path)
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
    delay = fade_duration / steps
    alpha = 1.0
    delta = alpha / steps

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

def normalize_label(label: str) -> str:
    return "".join(c for c in label.lower().strip() if c.isalnum())

def format_for_colour_name_setting(value: str) -> str:
    return value.upper().replace(" ", "_")

def rgb_to_hex(r, g, b):
    return f"#{r:02x}{g:02x}{b:02x}"

############################################################
# Colour math and colour matching
############################################################
    # Converts an RGB dictionary to CIE LAB colour space for colour comparison
    # Calculates the Euclidean distance between two LAB colours
    # List of known colours for closest colour matching
    # Finds the closest colour in COLOR_LIST to the given RGB value

# Converts an RGB dictionary to CIE LAB colour space for colour comparison
def rgb_to_lab(rgb):
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
def delta_e(l1, l2):
    return math.sqrt(
        (l2["L"] - l1["L"]) ** 2 +
        (l2["a"] - l1["a"]) ** 2 +
        (l2["b"] - l1["b"]) ** 2
    )

# List of known colours for closest colour matching
# Some are directly from Stud.io
COLOR_LIST = [
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

# Finds the closest colour in COLOR_LIST to the given RGB value
def closest_color(rgb):
    input_lab = rgb_to_lab(rgb)
    best, dist = None, float("inf")
    for c in COLOR_LIST:
        d = delta_e(input_lab, rgb_to_lab(c["rgb"]))
        if d < dist:
            best, dist = c["id"], d
    return best


############################################################
# Main Application Class
############################################################
    # Main application class for the ColourForge form generator
    # List of tuples: (key, field type, tk variable)
    # Populated in create_field()
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
        self.title("Unpixelled's ColourForge")
        self.geometry("900x700")

        self.fields = []
        self.code_block = ""

        self.create_widgets()
        self.load_templates()

    def create_widgets(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=10, pady=10)

        ttk.Label(top, text="Template:").pack(side="left")
        self.template_var = tk.StringVar()
        self.template_combo = ttk.Combobox(top, textvariable=self.template_var, state="readonly")
        self.template_combo.pack(side="left", padx=5)
        self.template_combo.bind("<<ComboboxSelected>>", self.load_template)

        self.form_frame = ttk.Frame(self)
        self.form_frame.pack(fill="both", expand=True, padx=10, pady=10)

        btns = ttk.Frame(self)
        btns.pack(fill="x", pady=10)

        # Left-aligned buttons
        ttk.Button(btns, text="Copy to Clipboard", command=self.copy_code).pack(side="left", padx=5)
        ttk.Button(btns, text="Save to File", command=self.save_code).pack(side="left", padx=5)
        ttk.Button(btns, text="Clear", command=self.clear_form).pack(side="left", padx=5)

        # Right-aligned buttons
        ttk.Button(btns, text="Settings", command=self.open_settings).pack(side="right", padx=5)
        ttk.Button(btns, text="Backup", command=self.backup).pack(side="right", padx=5)

    def load_templates(self):
        if not os.path.isdir(TEMPLATES_DIR):
            os.makedirs(TEMPLATES_DIR)
        files = [f for f in os.listdir(TEMPLATES_DIR) if f.endswith(".txt")]
        self.template_combo["values"] = files

    def clear_form(self):
        for w in self.form_frame.winfo_children():
            w.destroy()
        self.fields.clear()
        self.code_block = ""

    def load_template(self, *_):
        self.clear_form()
        path = os.path.join(TEMPLATES_DIR, self.template_var.get())
        with open(path, "r", encoding="utf-8") as f:
            self.parse_template(f.read())

    def parse_template(self, content):
        lines = content.splitlines()
        section = None
        parsing_code = False
        code_lines = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith("//"):
                continue

            if line == "end of form":
                parsing_code = True
                continue

            if parsing_code:
                if line.startswith("code"):
                    continue
                code_lines.append(line)
                continue

            if line.startswith("section"):
                section = ttk.LabelFrame(self.form_frame, text=line[8:].strip())
                section.pack(fill="x", pady=5)
                continue

            t, *label = line.split()
            label = " ".join(label)
            self.create_field(section, t, label)

        self.code_block = "\n".join(code_lines)

    def create_field(self, parent, ftype, label):
        frame = ttk.Frame(parent)
        frame.pack(fill="x", pady=2)

        ttk.Label(frame, text=label).pack(side="left", padx=5)
        key = normalize_label(label)

        if ftype == "checkbox":
            var = tk.BooleanVar()
            widget = ttk.Checkbutton(frame, variable=var)
        elif ftype == "number":
            var = tk.StringVar()
            widget = ttk.Entry(frame, textvariable=var)
        elif ftype == "text":
            var = tk.StringVar()
            widget = ttk.Entry(frame, textvariable=var)
        elif ftype == "picker":
            var = tk.StringVar(value="#ffffff")
            widget = ttk.Button(
                frame,
                text="Pick",
                command=lambda v=var, k=key: self.pick_color(v, k)
            )
        else:
            return

        widget.pack(side="left")
        self.fields.append((key, ftype, var))

    def pick_color(self, var, key):
        c = colorchooser.askcolor()[0]
        if not c:
            return
        r, g, b = map(int, c)
        var.set(rgb_to_hex(r, g, b))

        for suffix, value in zip(("rvalue", "gvalue", "bvalue"), (r, g, b)):
            for k, _, v in self.fields:
                if k == f"{key.replace('colourpicker','colour')}{suffix}":
                    v.set(str(value))

    ############################################################
    # Output Generation Logic
    ############################################################
    def generate_output(self):
        """
        Generates the output code by replacing placeholders in the template with user-provided values.
        - Fields are collected in order of appearance.
        - Only the first RGB picker fills !Hex! and !ColourCategory!.
        - Each picker fills its own indexed RGB placeholders.
        - Number, text, and checkbox fields are filled sequentially.
        """
            # Lists to hold values for each field type, in order of appearance
            # text_values: All text field values
            # number_values: All number field values (excluding RGB r/g/b fields)
            # checkbox_values: All checkbox field values (as strings)
            # pickers: Each picker is a dict with r, g, b
            # colourname: Value for !ColourName! placeholder
            # colourid: Value for !ColourID! placeholder
            # rgb_fields: For legacy rvalue/gvalue/bvalue fields
            # Collect all field values in order, and build picker/rgb lists
                        # Exclude number fields that are part of RGB (rvalue, gvalue, bvalue)
                        # Checkbox is 0.62 if checked, 1.0 if not
                        # Parse hex string to r/g/b and store in pickers list
                    # For legacy rvalue/gvalue/bvalue fields, group by prefix
            # Sort pickers by their order of appearance (defensive, should already be correct)
            # Helper to replace placeholders sequentially with values from a list
            # Replace !number!, !text!, !checkbox! in order of appearance
            # Replace RGB picker values in order
            # Only the first picker fills !Hex! and !ColourCategory!
                    # Remove any indexed !HexN! and !ColourCategoryN! placeholders if present
            # Fallback: legacy behaviour for rvalue/gvalue/bvalue fields
            # Replace colourname and colourid placeholders
            # Copies the generated code to the clipboard
            # Saves the generated code to a file
        out = self.code_block

        # Collect all values by type in order, but keep pickers and numbers separate
        text_values = []
        number_values = []
        checkbox_values = []
        pickers = []  # Each picker is a dict with r, g, b
        colourname = None
        colourid = None
        rgb_fields = {}

        # Ensure pickers are appended in the order they appear in the form
        for key, ftype, var in self.fields:
            val = var.get()
            if key == "colourname":
                colourname = val
            elif key == "colourid":
                colourid = val
            elif ftype == "text":
                text_values.append(val)
            elif ftype == "number":
                # Exclude number fields that are part of RGB (rvalue, gvalue, bvalue)
                if not (key.endswith("rvalue") or key.endswith("gvalue") or key.endswith("bvalue")):
                    number_values.append(val)
            elif ftype == "checkbox":
                checkbox_values.append("0.62" if var.get() else "1.0")
            elif ftype == "picker":
                hex_val = val
                if hex_val.startswith("#") and len(hex_val) == 7:
                    r = int(hex_val[1:3], 16)
                    g = int(hex_val[3:5], 16)
                    b = int(hex_val[5:7], 16)
                    pickers.append({"r": r, "g": g, "b": b, "_order": len(pickers)})
            # For legacy rvalue/gvalue/bvalue fields
            if key.endswith("rvalue"):
                rgb_fields.setdefault(key[:-6], {})["r"] = int(val)
            elif key.endswith("gvalue"):
                rgb_fields.setdefault(key[:-6], {})["g"] = int(val)
            elif key.endswith("bvalue"):
                rgb_fields.setdefault(key[:-6], {})["b"] = int(val)

        # Sort pickers by their order of appearance (just in case)
        pickers.sort(key=lambda x: x.get("_order", 0))
        for p in pickers:
            if "_order" in p:
                del p["_order"]

        # Replace all !number!, !text!, !checkbox! sequentially (do NOT use picker values for numbers)
        def replace_sequentially(template, placeholder, values):
            idx = 0
            while placeholder in template and idx < len(values):
                template = template.replace(placeholder, str(values[idx]), 1)
                idx += 1
            return template

        out = replace_sequentially(out, "!number!", number_values)
        out = replace_sequentially(out, "!text!", text_values)
        out = replace_sequentially(out, "!checkbox!", checkbox_values)

        # Only the first picker fills !Hex! and !ColourCategory!; all pickers fill their RGB value placeholders
        if pickers:
            for i, rgb in enumerate(pickers):
                if i == 0:
                    out = out.replace("!ColourRValue!", str(rgb["r"] / 255), 1)
                    out = out.replace("!ColourGValue!", str(rgb["g"] / 255), 1)
                    out = out.replace("!ColourBValue!", str(rgb["b"] / 255), 1)
                    out = out.replace("!Hex!", rgb_to_hex(**rgb), 1)
                    out = out.replace("!ColourCategory!", str(closest_color(rgb)), 1)
                idx = i + 1
                out = out.replace(f"!ColourRValue{idx}!", str(rgb["r"] / 255), 1)
                out = out.replace(f"!ColourGValue{idx}!", str(rgb["g"] / 255), 1)
                out = out.replace(f"!ColourBValue{idx}!", str(rgb["b"] / 255), 1)
            # Remove any indexed !HexN! and !ColourCategoryN! placeholders if present
            import re
            out = re.sub(r"!Hex\d+!", "", out)
            out = re.sub(r"!ColourCategory\d+!", "", out)
        elif rgb_fields:
            # Fallback: legacy behaviour for rvalue/gvalue/bvalue fields
            for idx, (prefix, rgb) in enumerate(rgb_fields.items()):
                if all(k in rgb for k in ("r", "g", "b")):
                    if idx == 0:
                        out = out.replace("!ColourRValue!", str(rgb["r"] / 255), 1)
                        out = out.replace("!ColourGValue!", str(rgb["g"] / 255), 1)
                        out = out.replace("!ColourBValue!", str(rgb["b"] / 255), 1)
                        out = out.replace("!Hex!", rgb_to_hex(**rgb), 1)
                        out = out.replace("!ColourCategory!", str(closest_color(rgb)), 1)
                    idx1 = idx + 1
                    out = out.replace(f"!ColourRValue{idx1}!", str(rgb["r"] / 255), 1)
                    out = out.replace(f"!ColourGValue{idx1}!", str(rgb["g"] / 255), 1)
                    out = out.replace(f"!ColourBValue{idx1}!", str(rgb["b"] / 255), 1)
                    out = out.replace(f"!Hex{idx1}!", rgb_to_hex(**rgb), 1)
                    out = out.replace(f"!ColourCategory{idx1}!", str(closest_color(rgb)), 1)

        # Replace colourname and colourid
        if colourname is not None:
            out = out.replace("!ColourName!", colourname)
            out = out.replace("!ColourNameSetting!", format_for_colour_name_setting(colourname))
        if colourid is not None:
            out = out.replace("!ColourID!", colourid)

        return out

    # Copies the generated code to the clipboard
    def copy_code(self):
        self.clipboard_clear()
        self.clipboard_append(self.generate_output())
        messagebox.showinfo("Copied", "Code copied to clipboard")

    # Saves the generated code to a file
    def save_code(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.generate_output())

    # Backup function copy the existing custom color definition and settings files
    def backup(self):
        try:
            baseDir = os.path.dirname(os.path.abspath(__file__))
            settingsPath = os.path.join(baseDir, "settings.cfg")

            if not os.path.isfile(settingsPath):
                messagebox.showerror("Backup Error", "settings.cfg not found in application directory.")
                return

            # Read FileLocation from cfg
            sourceDir = None
            with open(settingsPath, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("FileLocation:"):
                        sourceDir = line.split("FileLocation:", 1)[1].strip()
                        break

            if not sourceDir or not os.path.isdir(sourceDir):
                messagebox.showerror("Backup Error", "Invalid or missing FileLocation in config.cfg.")
                return

            backup_dir = os.path.join(baseDir, "backup")
            os.makedirs(backup_dir, exist_ok=True)

            timestamp = time.strftime("%y%m%d_%H%M")
            files_to_backup = ["CustomColorDefinition.txt", "CustomColorSettings.xml"]

            copied = []

            for filename in files_to_backup:
                src = os.path.join(sourceDir, filename)
                if not os.path.isfile(src):
                    continue

                name, ext = os.path.splitext(filename)
                dst_name = f"{name}_{timestamp}{ext}"
                dst = os.path.join(backup_dir, dst_name)

                shutil.copy2(src, dst)
                copied.append(dst_name)

            if copied:
                messagebox.showinfo(
                    "Backup Complete",
                    "Backed up files:\n" + "\n".join(copied)
                )
            else:
                messagebox.showwarning(
                    "Backup",
                    "No files were backed up (files missing?)."
                )

        except Exception as e:
            messagebox.showerror("Backup Error", str(e))

    # Opens the settings file
    def open_settings(self):
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.cfg")

        if not os.path.isfile(path):
            messagebox.showerror("Settings Error", "settings.cfg was not found.")
            return

        os.startfile(path)
            
############################################################
# Main Execution
############################################################

if __name__ == "__main__":
    #Show the splash screen logo
    splashLogoAtStart("splash.png", 2.0)

    #Begin main application
    FormFactoryApp().mainloop()