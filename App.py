import os
import math
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser

TEMPLATES_DIR = "templates"

##TODO this works for solid but not glowing metallic, multiple RGB values not working

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
# Color math (ported 1:1)
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
        rgb = {}

        for key, ftype, var in self.fields:
            val = var.get()

            if key == "colourname":
                out = out.replace("!ColourName!", val)
                out = out.replace("!ColourNameSetting!", format_for_colour_name_setting(val))

            elif key == "colourid":
                out = out.replace("!ColourID!", val)

            elif key.endswith("rvalue"):
                rgb["r"] = int(val)
                out = out.replace("!ColourRValue!", str(int(val) / 255))

            elif key.endswith("gvalue"):
                rgb["g"] = int(val)
                out = out.replace("!ColourGValue!", str(int(val) / 255))

            elif key.endswith("bvalue"):
                rgb["b"] = int(val)
                out = out.replace("!ColourBValue!", str(int(val) / 255))

            elif ftype == "text":
                out = out.replace("!text!", val)
            elif ftype == "number":
                out = out.replace("!number!", val)
            elif ftype == "checkbox":
                out = out.replace("!checkbox!", "0.62" if var.get() else "1.0")

        if len(rgb) == 3:
            out = out.replace("!Hex!", rgb_to_hex(**rgb))
            out = out.replace("!ColourCategory!", str(closest_color(rgb)))

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
