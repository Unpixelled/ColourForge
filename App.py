import os
import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser

TEMPLATES_DIR = "templates"

##TODO Known errors
## - Multiple pickers do not work because RGB values are fixed variables, subsequent ones use the first values
## - Numbers do not get applied in sequence

# -------------------------
# Utility functions
# -------------------------

def normalize_label(label: str) -> str:
    return "".join(c for c in label.lower().strip() if c.isalnum())


def format_for_colour_name_setting(value: str) -> str:
    return value.upper().replace(" ", "_")


def rgb_to_hex(r, g, b):
    return f"#{r:02x}{g:02x}{b:02x}"


# -------------------------
# Color math
# -------------------------

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


def delta_e(l1, l2):
    return math.sqrt(
        (l2["L"] - l1["L"]) ** 2 +
        (l2["a"] - l1["a"]) ** 2 +
        (l2["b"] - l1["b"]) ** 2
    )


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


def closest_color(rgb):
    input_lab = rgb_to_lab(rgb)
    best, dist = None, float("inf")
    for c in COLOR_LIST:
        d = delta_e(input_lab, rgb_to_lab(c["rgb"]))
        if d < dist:
            best, dist = c["id"], d
    return best


# -------------------------
# Main App
# -------------------------

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

        ttk.Button(btns, text="Copy to Clipboard", command=self.copy_code).pack(side="left", padx=5)
        ttk.Button(btns, text="Save to File", command=self.save_code).pack(side="left", padx=5)
        ttk.Button(btns, text="Clear", command=self.clear_form).pack(side="left", padx=5)

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

    def generate_output(self):
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

    def copy_code(self):
        self.clipboard_clear()
        self.clipboard_append(self.generate_output())
        messagebox.showinfo("Copied", "Code copied to clipboard")

    def save_code(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.generate_output())


if __name__ == "__main__":
    FormFactoryApp().mainloop()