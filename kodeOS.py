#!/usr/bin/env python3
"""
kodeOS Loader – GUI to flash ESP32-S3 builds
Rounded orange "Load" button.
Requirements:
  python3 -m pip install pyserial esptool Pillow
"""
import json
import subprocess
import sys
import io # To capture esptool output
try:
    from PIL import Image, ImageChops, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

import esptool # To call directly

# --- OPTIMIZED FOR PILLOW > 10 ---
# With Pillow > 10, we only use the modern API.
if PIL_AVAILABLE:
    RESAMPLE_FILTER = Image.Resampling.LANCZOS
else:
    RESAMPLE_FILTER = None
# --- END OPTIMIZATION ---

import threading
import pathlib
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from serial.tools import list_ports

# --- Helper function for PyInstaller ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        # Note: sys._MEIPASS is a string, needs to be Path
        base_path = pathlib.Path(sys._MEIPASS)
    except Exception:
        # Not in a PyInstaller bundle, so use the script's directory
        base_path = pathlib.Path(__file__).resolve().parent
    
    return str(base_path / relative_path)

BAUD_RATE = 460800
# Original color palette with orange and gray
WHITE = "#FFFFFF"         # White
BG = "#E1E1E1"            # Original light gray background
ACCENT = "#FF7F1F"        # Original orange
ACCENT_HOVER = "#FFB184"  # Light orange for hover
TEXT_DARK = "#222222"     # Original dark text
TEXT_LIGHT = "#FFFFFF"    # Light/white text
GRAY_LIGHT = "#CCCCCC"    # Slightly darker light gray for progress bar trough
GRAY_MID = "#888888"      # Medium gray for secondary text

# Notification colors
COLOR_SUCCESS = "#28A745" # Green
COLOR_ERROR = "#DC3545"   # Red
COLOR_ERROR_HOVER = "#E4606D" # Lighter red for hover
COLOR_INFO = TEXT_DARK    # Normal

# Improved typography (using fonts commonly available on systems)
FONT = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 12, "bold")
TITLE_FONT = ("Segoe UI", 16, "bold")

# ──────────────────────────  Language Strings ──────────────────────────
LANGUAGES = {
    'en': {
        'window_title': "kodeOS Loader",
        'serial_port_label': "Serial Port:",
        'firmware_label': "Firmware (.bin):",
        'flash_app_checkbox': "Flash Kode OS App (0x400000)", # New
        'refresh_button': "Refresh",
        'browse_button': "Browse",
        'load_button': "Flash", # Changed
        'load_button_loading': "Flashing...", # Changed
        'erase_button': "Erase",
        'erase_button_erasing': "Erasing...",
        'ports_loading': "Loading ports...",
        'no_ports_found': "No USB ports found",
        'browse_dialog_title': "Select firmware .bin",
        'status_ready': "Ready to flash", # Changed
        'status_starting': "Starting flash...",
        'status_erasing': "Erasing flash...",
        'flashing_progress': "Flashing ({pct}%)...",
        'error_missing_params': "Select serial port and firmware .bin file.",
        'error_missing_port': "Please select a serial port.",
        'flash_success': "Flash completed successfully.",
        'flash_error_generic': "Error during flash. Check logs and retry.",
        'erase_success': "Flash erased successfully.",
        'erase_error': "Error during erase. Check logs.",
        'erase_confirm_title': "Confirm Erase",
        'erase_confirm_message': "This will ERASE THE ENTIRE FLASH on the device!\nThis cannot be undone.\n\nAre you sure?",
        'show_logs_label': "Show Logs",
        'hide_logs_label': "Hide Logs"
    },
    'es': {
        'window_title': "Cargador kodeOS",
        'serial_port_label': "Puerto Serial:",
        'firmware_label': "Firmware (.bin):",
        'flash_app_checkbox': "Flashear App Kode OS (0x400000)", # New
        'refresh_button': "Refrescar",
        'browse_button': "Buscar",
        'load_button': "Flashear", # Changed
        'load_button_loading': "Flasheando...", # Changed
        'erase_button': "Borrar",
        'erase_button_erasing': "Borrando...",
        'ports_loading': "Buscando puertos...",
        'no_ports_found': "No se encontraron puertos USB",
        'browse_dialog_title': "Seleccionar firmware .bin",
        'status_ready': "Listo para flashear", # Changed
        'status_starting': "Iniciando flasheo...",
        'status_erasing': "Borrando flash...",
        'flashing_progress': "Flasheando ({pct}%)...",
        'error_missing_params': "Seleccione un puerto serial y un archivo .bin.",
        'error_missing_port': "Por favor, seleccione un puerto serial.",
        'flash_success': "Flasheo completado con éxito.",
        'flash_error_generic': "Error durante el flasheo. Revise los logs e intente de nuevo.",
        'erase_success': "Flash borrada con éxito.",
        'erase_error': "Error durante el borrado. Revise los logs.",
        'erase_confirm_title': "Confirmar Borrado",
        'erase_confirm_message': "¡Esto BORRARÁ TODA LA FLASH del dispositivo!\nEsta acción no se puede deshacer.\n\n¿Está seguro?",
        'show_logs_label': "Mostrar Logs",
        'hide_logs_label': "Ocultar Logs"
    }
}


# ──────────────────────────  Custom Widgets  ──────────────────────────
class RoundedButton(tk.Canvas):
    def __init__(self, parent, text, command=None, radius=20, padding=10,
                 bg=ACCENT, fg=TEXT_LIGHT, active_bg=ACCENT_HOVER, **kwargs):
        tk.Canvas.__init__(self, parent, highlightthickness=0, bg=BG, **kwargs)
        self.radius = radius
        self.command = command
        self.active_bg = active_bg
        self._orig_bg = bg    # Save original color
        self.normal_bg = bg
        self.text = text
        self.fg = fg
        self.padding = padding
        self.state_disabled = False
        self._draw(normal=True)
        self.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _draw(self, normal=True, hover=False):
        self.delete("all")
        fill = self.normal_bg
        if not normal:
            fill = self.active_bg
        elif hover:
            fill = self.active_bg
            
        r = self.radius
        width = self.winfo_reqwidth() or 150
        height = self.winfo_reqheight() or 2*r
        self.configure(width=width, height=height)
        
        # Subtle shadow
        self.create_round_rect(3, 3, width, height, r, fill="#E0E0E0", outline="")
        # Main button
        self.create_round_rect(0, 0, width-3, height-3, r, fill=fill, outline="")
        # Button text
        self.create_text(width//2-1, height//2-1, text=self.text, fill=self.fg,
                         font=FONT_BOLD, tags="label")

    def _on_enter(self, event):
        if not self.state_disabled:
            self._draw(normal=True, hover=True)
    
    def _on_leave(self, event):
        if not self.state_disabled:
            self._draw(normal=True, hover=False)

    def create_round_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [x1+r, y1,
                  x2-r, y1,
                  x2, y1,
                  x2, y1+r,
                  x2, y2-r,
                  x2, y2,
                  x2-r, y2,
                  x1+r, y2,
                  x1, y2,
                  x1, y2-r,
                  x1, y1+r,
                  x1, y1]
        return self.create_polygon(points, smooth=True, **kwargs)

    def _on_click(self, event):
        if self.state_disabled:
            return
        self._draw(normal=False)
        if self.command:
            self.command()
        self.after(100, lambda: self._draw(normal=True))

    def set_text(self, text):
        self.text = text
        self.itemconfigure("label", text=text) # More efficient than _draw()

    def set_disabled(self, disabled=True):
        self.state_disabled = disabled
        # Use text color GRAY_MID for disabled state, but keep TEXT_LIGHT for red button
        text_fill = GRAY_MID if disabled and self._orig_bg != COLOR_ERROR else self.fg
        
        # Restore original color on activate, light gray on deactivate
        if disabled:
            self.normal_bg = GRAY_LIGHT
        else:
            self.normal_bg = self._orig_bg
        self.itemconfigure("label", fill=text_fill)
        self._draw(normal=True)

# ──────────────────────────  Main Application  ──────────────────────────
class LoaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # --- Language configuration ---
        self.lang = 'en' # Start language
        self.current_notification = None # (message_key, level)
        # --- End Language configuration ---
        
        self.title(self.get_string('window_title'))
        # --- PYINSTALLER FIX: Use resource_path for icon ---
        self.iconbitmap(resource_path("icon.ico"))
        self.configure(bg=BG)  # gray background window
        self.resizable(False, False)
        
        # Load icons and resources
        self._load_resources()
        self._build_ui()
        
        # Center the main window on the screen
        self._center_window()
        
    # --- Language Methods ---
    def get_string(self, key):
        """Gets the text string for the current language."""
        return LANGUAGES.get(self.lang, LANGUAGES['en']).get(key, f"<{key}>")

    def _set_language(self, lang):
        """Sets the new language and updates the UI."""
        if lang not in LANGUAGES or lang == self.lang:
            return
        self.lang = lang
        self._update_ui_text()
        self._update_lang_switcher_ui()

    def _update_lang_switcher_ui(self):
        """Updates the language switcher highlight."""
        if self.lang == 'en':
            self.en_label.config(font=FONT_BOLD, fg=ACCENT)
            self.es_label.config(font=FONT, fg=GRAY_MID)
        else:
            self.en_label.config(font=FONT, fg=GRAY_MID)
            self.es_label.config(font=FONT_BOLD, fg=ACCENT)
            
    def _update_ui_text(self):
        """Updates all text widgets with the current language."""
        self.title(self.get_string('window_title'))
        self.serial_label.config(text=self.get_string('serial_port_label'))
        self.firmware_label.config(text=self.get_string('firmware_label'))
        self.flash_app_check.config(text=self.get_string('flash_app_checkbox')) # New
        self.refresh_btn.set_text(self.get_string('refresh_button'))
        self.browse_btn.set_text(self.get_string('browse_button'))
        
        # Only update load button if it's not disabled
        if not self.load_btn.state_disabled:
            self.load_btn.set_text(self.get_string('load_button'))
        
        # Add update for erase button
        if not self.erase_btn.state_disabled:
            self.erase_btn.set_text(self.get_string('erase_button'))
        
        # Refresh port list (this will update "No ports found" if necessary)
        self._refresh_ports() 
        
        # Re-show the current notification/status in the new language
        if self.current_notification:
            key, level = self.current_notification
            # If progress is active, the thread will overwrite it, so we do nothing
            if key.startswith('flashing_progress') or key.startswith('status_erasing'):
                pass
            else:
                self._show_notification(key, level)
        elif not self.load_btn.state_disabled:
            # Show 'Ready' status
            self.result_label.config(text=self.get_string('status_ready'), fg=COLOR_INFO, image="")
        
        # Update port_var value if it's a status message
        current_port = self.port_var.get()
        if current_port in [LANGUAGES['en']['no_ports_found'], LANGUAGES['es']['no_ports_found']]:
            self.port_var.set(self.get_string('no_ports_found'))
        elif current_port in [LANGUAGES['en']['ports_loading'], LANGUAGES['es']['ports_loading']]:
             self.port_var.set(self.get_string('ports_loading'))

    # --- End Language Methods ---

    # --- OPTIMIZED FOR PILLOW > 10 ---
    def _load_resources(self):
        # Prepare for future icons if needed
        self.icons = {}
        
        # --- Load Logo ---
        self.logo_img = None
        # --- PYINSTALLER FIX: Use resource_path ---
        logo_path_str = resource_path("images/logo.png")
        if pathlib.Path(logo_path_str).is_file():
            try:
                if PIL_AVAILABLE:
                    with Image.open(logo_path_str) as pil_img: # 1. Open
                        # Assumed background color in top-left corner
                        bg_color = pil_img.getpixel((0, 0))
                        diff = ImageChops.difference(pil_img, Image.new(pil_img.mode, pil_img.size, bg_color))
                        bbox = diff.getbbox()
                        if bbox:
                            pil_img = pil_img.crop(bbox) # 2. Reassign to cropped image
                        else:
                            pil_img.load() # 3. Force load data if not cropping

                    # 4. File is closed. pil_img holds the image data.
                    max_dim = 100
                    pil_img.thumbnail((max_dim, max_dim), RESAMPLE_FILTER) # 5. Resize in-place
                    self.logo_img = ImageTk.PhotoImage(pil_img) # 6. Create Tk image
                
                else: # Fallback without PIL
                    img = tk.PhotoImage(file=logo_path_str)
                    max_dim = 100
                    if img.width() > max_dim or img.height() > max_dim:
                        factor = max(img.width()//max_dim, img.height()//max_dim)
                        img = img.subsample(factor, factor)
                    self.logo_img = img
            except Exception as e:
                print(f"Error loading logo: {e}") # Added for debugging
                self.logo_img = None

        # --- Load Pet ---
        self.pet_img = None
        # --- PYINSTALLER FIX: Use resource_path ---
        pet_path_str = resource_path("images/pet.png")
        if pathlib.Path(pet_path_str).is_file():
            try:
                if PIL_AVAILABLE:
                    with Image.open(pet_path_str) as pil_pet:
                        pil_pet.load() # Load data
                    
                    max_pet_dim = 140
                    pil_pet.thumbnail((max_pet_dim, max_pet_dim), RESAMPLE_FILTER) # Resize in-place
                    self.pet_img = ImageTk.PhotoImage(pil_pet)
                else: # Fallback without PIL
                    pet = tk.PhotoImage(file=pet_path_str)
                    max_pet_dim = 140
                    factor = max(1, max(pet.width()//max_pet_dim, pet.height()//max_pet_dim))
                    pet = pet.subsample(factor, factor)
                    self.pet_img = pet
            except Exception as e:
                print(f"Error loading pet: {e}") # Added for debugging
                self.pet_img = None

        # --- Load Result Icons ---
        icon_dim = 32 # Size for notification icon
        self.icon_success = None
        self.icon_error = None
        
        # --- PYINSTALLER FIX: Use resource_path ---
        success_path_str = resource_path("images/success.png")
        if pathlib.Path(success_path_str).is_file():
            try:
                if PIL_AVAILABLE:
                    with Image.open(success_path_str) as pil_succ:
                        pil_succ.load()
                    pil_succ.thumbnail((icon_dim, icon_dim), RESAMPLE_FILTER)
                    self.icon_success = ImageTk.PhotoImage(pil_succ)
                else: # Fallback without PIL
                    img = tk.PhotoImage(file=success_path_str)
                    w,h = img.width(), img.height()
                    factor = max(1, max(w//icon_dim, h//icon_dim))
                    self.icon_success = img.subsample(factor, factor)
            except Exception as e:
                print(f"Error loading success icon: {e}") # Added for debugging

        # --- PYINSTALLER FIX: Use resource_path ---
        fail_path_str = resource_path("images/fail.png")
        if pathlib.Path(fail_path_str).is_file():
            try:
                if PIL_AVAILABLE:
                    with Image.open(fail_path_str) as pil_fail:
                        pil_fail.load()
                    pil_fail.thumbnail((icon_dim, icon_dim), RESAMPLE_FILTER)
                    self.icon_error = ImageTk.PhotoImage(pil_fail)
                else: # Fallback without PIL
                    img = tk.PhotoImage(file=fail_path_str)
                    w,h = img.width(), img.height()
                    factor = max(1, max(w//icon_dim, h//icon_dim))
                    self.icon_error = img.subsample(factor, factor)
            except Exception as e:
                print(f"Error loading fail icon: {e}") # Added for debugging
    # --- END OPTIMIZATION ---

    # UI -----------------------------------------------------------------
    def _build_ui(self):
        # Use grid for a compact layout with margins
        self.configure(padx=15, pady=15)
        
        # --- Left frame for logo and pet ---
        left_frame = tk.Frame(self, bg=BG)
        # --- FIX: rowspan is 5 to cover rows 0-4 ---
        left_frame.grid(row=0, column=0, rowspan=5, sticky="nw", padx=(0,4), pady=0)
        # Show logo if it exists
        if getattr(self, 'logo_img', None):
            # Small logo, no extra padding
            tk.Label(left_frame, image=self.logo_img, bg=BG).pack(pady=(0,0))
        # Show pet below
        if getattr(self, 'pet_img', None):
            # Larger pet, close to the logo
            tk.Label(left_frame, image=self.pet_img, bg=BG).pack(pady=(0,0))
        
        # Input variables and constants
        INPUT_HEIGHT = 28
        LOGO_SIZE = 120  # Max size for the logo
        
        # --- Configure column expansion ---
        # Allow column 2 (inputs) to expand
        self.columnconfigure(0, weight=0) # Column 0: Image
        self.columnconfigure(1, weight=0) # Column 1: Labels
        self.columnconfigure(2, weight=1) # Column 2: Inputs (Expand)
        self.columnconfigure(3, weight=0) # Column 3: Buttons
        
        # Reduce space between rows (Rows 0-3)
        for i in range(4):
            self.rowconfigure(i, pad=1)
        
        # ROW 0: Serial Port
        LABEL_FONT = ("Segoe UI", 12, "bold")
        self.serial_label = tk.Label(self, text=self.get_string('serial_port_label'), bg=BG, fg=TEXT_DARK, font=LABEL_FONT)
        self.serial_label.grid(row=0, column=1, sticky="e", padx=(0,4), pady=0)
        
        self.port_var = tk.StringVar()
        initial_port_value = self.get_string('ports_loading')
        self.port_var.set(initial_port_value)
        
        self.port_combo = tk.OptionMenu(self, self.port_var, initial_port_value)
        self.port_combo.config(font=FONT, bg=BG, fg=TEXT_DARK, 
                               activebackground=ACCENT, activeforeground=TEXT_LIGHT,
                               highlightthickness=1, highlightbackground=GRAY_LIGHT, bd=0)
        self.port_combo.grid(row=0, column=2, sticky="ew")
        self.port_var.trace_add('write', lambda *args: self.port_combo.config(fg=TEXT_DARK))
        
        self.refresh_btn = RoundedButton(self, text=self.get_string('refresh_button'), command=self._refresh_ports,
                                      width=80, height=INPUT_HEIGHT, bg=ACCENT, fg=TEXT_LIGHT,
                                      active_bg=ACCENT_HOVER)
        self.refresh_btn.grid(row=0, column=3, padx=(2,0), pady=0)
        
        # ROW 1: Build Folder
        self.firmware_label = tk.Label(self, text=self.get_string('firmware_label'), bg=BG, fg=TEXT_DARK, font=LABEL_FONT)
        self.firmware_label.grid(row=1, column=1, sticky="e", padx=(0,4), pady=0)
        
        self.build_var = tk.StringVar()
        self.build_entry = tk.Entry(self, textvariable=self.build_var, 
                                  font=FONT, bg=BG, fg=TEXT_DARK, 
                                  relief=tk.FLAT, highlightthickness=1, 
                                  highlightbackground=GRAY_LIGHT,
                                  width=30) # Set a minimum width
        self.build_entry.grid(row=1, column=2, sticky="ew", padx=0, pady=0)

        self.browse_btn = RoundedButton(self, text=self.get_string('browse_button'), command=self._browse,
                                      width=80, height=INPUT_HEIGHT, bg=ACCENT, fg=TEXT_LIGHT,
                                      active_bg=ACCENT_HOVER)
        self.browse_btn.grid(row=1, column=3, padx=(2,0), pady=0)

        # --- ROW 2: Flash App Checkbox ---
        self.flash_app_var = tk.IntVar(value=0)
        self.flash_app_check = tk.Checkbutton(self, 
                                             text=self.get_string('flash_app_checkbox'),
                                             variable=self.flash_app_var,
                                             bg=BG, fg=TEXT_DARK, font=FONT,
                                             activebackground=BG, activeforeground=TEXT_DARK,
                                             selectcolor=WHITE,
                                             highlightthickness=0, bd=0)
        self.flash_app_check.grid(row=2, column=1, columnspan=2, sticky="w", padx=0, pady=(5,0))


        # --- ROW 3: LOAD and ERASE buttons ---
        button_frame = tk.Frame(self, bg=BG)
        button_frame.grid(row=3, column=1, columnspan=2, pady=(10,2), sticky="ew")
        button_frame.grid_columnconfigure(0, weight=1) # Left side
        button_frame.grid_columnconfigure(1, weight=1) # Right side

        self.load_btn = RoundedButton(button_frame, text=self.get_string('load_button'), width=160, height=38, 
                                      command=self._start_flash, bg=ACCENT, fg=TEXT_LIGHT)
        self.load_btn.grid(row=0, column=0, padx=5, sticky='e') 

        self.erase_btn = RoundedButton(button_frame, text=self.get_string('erase_button'), width=160, height=38,
                                       command=self._start_erase, 
                                       bg=COLOR_ERROR, fg=TEXT_LIGHT, 
                                       active_bg=COLOR_ERROR_HOVER) 
        self.erase_btn.grid(row=0, column=1, padx=5, sticky='w') 
        
        
        # --- ROW 4: Label for result/notification (below the button) ---
        self.result_label = tk.Label(self, text=self.get_string('status_ready'), 
                                     bg=BG, fg=COLOR_INFO, font=FONT_BOLD, 
                                     compound=tk.LEFT, 
                                     anchor="center", justify=tk.CENTER) # Centered text
        self.result_label.grid(row=4, column=1, columnspan=2, sticky="ew", padx=0, pady=(4,0))


        # --- ROW 5: Log Area (Permanent) ---
        self.log_frame = tk.Frame(self, bg=BG)
        self.log_frame.grid(row=5, column=0, columnspan=4, sticky="nsew", pady=(10,0))
        self.log_frame.grid_columnconfigure(0, weight=1)
        self.log_frame.grid_rowconfigure(0, weight=1)

        self.log_text = tk.Text(self.log_frame, wrap=tk.WORD, state=tk.DISABLED,
                                height=10, bg="#F0F0F0", fg=TEXT_DARK,
                                relief=tk.FLAT, highlightthickness=1,
                                highlightbackground=GRAY_LIGHT, font=("Courier New", 9))
        self.log_text.grid(row=0, column=0, sticky="nsew")

        log_scrollbar = tk.Scrollbar(self.log_frame, command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        
        # Configure row 5 (the log's row) to expand
        self.rowconfigure(5, weight=1)

        # --- ROW 6: Language Switcher ---
        lang_frame = tk.Frame(self, bg=BG)
        lang_frame.grid(row=6, column=0, columnspan=4, sticky="e", pady=(5,0))
        
        # Added from right to left
        self.es_label = tk.Label(lang_frame, text="Español", bg=BG, fg=GRAY_MID, font=FONT, cursor="hand2")
        self.es_label.pack(side=tk.RIGHT, padx=5)
        self.es_label.bind("<Button-1>", lambda e: self._set_language('es'))
        
        tk.Label(lang_frame, text="|", bg=BG, fg=GRAY_MID, font=FONT).pack(side=tk.RIGHT)

        self.en_label = tk.Label(lang_frame, text="English", bg=BG, fg=ACCENT, font=FONT_BOLD, cursor="hand2")
        self.en_label.pack(side=tk.RIGHT, padx=5)
        self.en_label.bind("<Button-1>", lambda e: self._set_language('en'))

        # Initialize ports
        self._refresh_ports()
        
    # --- Notifications ---
    def _show_notification(self, message_key, level='info'):
        """Shows a notification in self.result_label."""
        self.current_notification = (message_key, level) # Save the key
        message = self.get_string(message_key)
        icon = None
        color = COLOR_INFO

        if level == 'success':
            icon = self.icon_success
            color = COLOR_SUCCESS
        elif level == 'error':
            icon = self.icon_error
            color = COLOR_ERROR
        
        self.result_label.config(text=message, image=icon, fg=color)

    def _clear_notification(self):
        """Clears the notification area."""
        self.current_notification = None
        self.result_label.config(text="", image="", fg=COLOR_INFO)

    # Helpers ------------------------------------------------------------
    def _list_ports(self):
        """Gets a list of serial ports that appear to be USB."""
        ports = list_ports.comports()
        # Filter only ports that look like USB (have VID/PID or "USB" in their description/hwid)
        usb_ports = [
            p.device for p in ports 
            if p.vid is not None or "USB" in p.hwid.upper() or "USB" in p.description.upper()
        ]
        return usb_ports

    def _refresh_ports(self):
        menu = self.port_combo['menu']
        menu.delete(0, 'end')
        ports = self._list_ports()
        if ports:
            for p in ports:
                menu.add_command(label=p, command=lambda v=p, var=self.port_var: var.set(v))
            
            # Don't overwrite if a port is already selected
            current_val = self.port_var.get()
            if current_val in [self.get_string('no_ports_found'), self.get_string('ports_loading')] or current_val not in ports:
                 self.port_var.set(ports[0]) # Select the first one
        else:
            no_ports_msg = self.get_string('no_ports_found')
            self.port_var.set(no_ports_msg)
            menu.add_command(label=no_ports_msg, state="disabled")

    def _browse(self):
        path = filedialog.askopenfilename(
            title=self.get_string('browse_dialog_title'),
            filetypes=[("ESP32 firmware", "*.bin")]
        )
        if path:
            self.build_var.set(path)

    def _clear_log_area(self):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _update_log_area(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, message)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    # --- Button state management ---
    def _set_controls_disabled(self, disabled=True):
        """Disables or enables all interactive controls."""
        self.load_btn.set_disabled(disabled)
        self.erase_btn.set_disabled(disabled)
        
        # Also disable/enable the non-custom buttons
        for btn in [self.refresh_btn, self.browse_btn]:
            if btn: # Check if it exists
                btn.set_disabled(disabled)
        
        # Disable standard tkinter widgets
        combo_state = tk.DISABLED if disabled else tk.NORMAL
        entry_state = "readonly" if disabled else tk.NORMAL # Use readonly for Entry
        self.port_combo.config(state=combo_state)
        self.build_entry.config(state=entry_state)
        self.flash_app_check.config(state=combo_state) # Disable checkbox


    # Flash logic --------------------------------------------------------
    def _start_flash(self):
        port = self.port_var.get(); build = self.build_var.get()
        if not port or not build or port == self.get_string('no_ports_found') or port == self.get_string('ports_loading'):
            self._show_notification('error_missing_params', 'error')
            return
        # UI changes
        self._clear_log_area() # Clear logs before starting
        self._clear_notification() # Clear previous notification
        self._set_controls_disabled(True) # Disable all controls
        self.load_btn.set_text(self.get_string('load_button_loading'))
        self._show_notification('status_starting', 'info')
        self._skip_initial_progress = True
        self.after(0, self._update_log_area, self.get_string('status_starting') + "\n") # Initial log
        threading.Thread(target=self._flash_thread, args=(build, port), daemon=True).start()

    def _flash_thread(self, bin_file, port):
        # --- NEW: Build args based on checkbox ---
        base_args = ["--chip", "esp32s3", # Corrected typo
                     "--port", port,
                     "--baud", str(BAUD_RATE)]
        
        if self.flash_app_var.get() == 1:
            # Kode OS App Flash (0x400000)
            flash_args = ["write_flash", 
                          "--flash-freq", "80m", 
                          "--flash-mode", "dio", 
                          "--flash-size", "32MB", 
                          "0x400000", bin_file]
        else:
            # Default Flash (0x0)
            flash_args = ["write_flash", "-z", "0x0", bin_file]
            
        args = base_args + flash_args
        # --- End new args logic ---
        
        all_logs = []
        return_code = 1 # Default to error

        self.after(0, self._update_log_area, f"Executing esptool.main with args: {args}\n")

        # Stream esptool.main logs and parse percentage in parentheses
        regex = re.compile(r"\(\s*(\d{1,3})\s*%\s*\)")
        class _StreamLogger(io.StringIO):
            def write(inner_self, data):
                # Internal buffer
                super(_StreamLogger, inner_self).write(data)
                # Send partial lines to UI and extract progress, skipping the first 100%
                for part in data.splitlines(True):
                    self.after(0, self._update_log_area, part)
                    m = regex.search(part)
                    if m:
                        pct = int(m.group(1))
                        # Update status notification
                        msg = self.get_string('flashing_progress').format(pct=pct)
                        self.after(0, self.result_label.config, {"text": msg, "fg": COLOR_INFO, "image": ""})
                        self.after(0, setattr, self, 'current_notification', None) # Not a final notification
        
        stream_logger = _StreamLogger()
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = stream_logger
        sys.stderr = stream_logger

        try:
            esptool.main(args)
            return_code = 0
        except SystemExit as e:
            return_code = e.code if isinstance(e.code, int) else 1
        except Exception as e:
            self.after(0, self._update_log_area, f"\nException during esptool.main: {e}\n")
            return_code = 1
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

        # Get complete logs and store them
        captured_output = stream_logger.getvalue()
        all_logs.append(captured_output)
        
        self.after(0, self._flash_complete, return_code, "".join(all_logs))

    def _flash_complete(self, rc, logs):
        self._set_controls_disabled(False) # Re-enable all controls
        self.load_btn.set_text(self.get_string('load_button'))
        if rc == 0:
            self._show_notification('flash_success', 'success')
            self.after(0, self._update_log_area, f"\n{self.get_string('flash_success')}!\n")
        else:
            self._show_notification('flash_error_generic', 'error')
            self.after(0, self._update_log_area, f"\nError during flash (Return Code: {rc}). See details above.\n")

    # Erase logic --------------------------------------------------------
    def _start_erase(self):
        port = self.port_var.get()
        if not port or port == self.get_string('no_ports_found') or port == self.get_string('ports_loading'):
            self._show_notification('error_missing_port', 'error')
            return

        # Show confirmation dialog
        title = self.get_string('erase_confirm_title')
        msg = self.get_string('erase_confirm_message')
        if not messagebox.askyesno(title, msg, parent=self): # Set parent to self
            return
            
        # UI changes
        self._clear_log_area()
        self._clear_notification()
        self._set_controls_disabled(True) # Disable all controls
        self.erase_btn.set_text(self.get_string('erase_button_erasing'))
        self._show_notification('status_erasing', 'info')
        self.after(0, self._update_log_area, self.get_string('status_erasing') + "\n")
        threading.Thread(target=self._erase_thread, args=(port,), daemon=True).start()

    def _erase_thread(self, port):
        args = ["--chip", "esp32s3",
                "--port", port,
                "--baud", str(BAUD_RATE),
                "erase_flash"]
        
        all_logs = []
        return_code = 1 # Default to error

        self.after(0, self._update_log_area, f"Executing esptool.main with args: {args}\n")

        # Re-use StreamLogger; it will just pipe output without finding progress
        regex = re.compile(r"THIS_WILL_NOT_MATCH") # No progress bar for erase
        class _StreamLogger(io.StringIO):
            def write(inner_self, data):
                super(_StreamLogger, inner_self).write(data)
                for part in data.splitlines(True):
                    self.after(0, self._update_log_area, part)
                    # No progress parsing needed for erase
        
        stream_logger = _StreamLogger()
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        sys.stdout = stream_logger
        sys.stderr = stream_logger

        try:
            esptool.main(args)
            return_code = 0
        except SystemExit as e:
            return_code = e.code if isinstance(e.code, int) else 1
        except Exception as e:
            self.after(0, self._update_log_area, f"\nException during esptool.main: {e}\n")
            return_code = 1
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

        captured_output = stream_logger.getvalue()
        all_logs.append(captured_output)
        
        self.after(0, self._erase_complete, return_code, "".join(all_logs))

    def _erase_complete(self, rc, logs):
        self._set_controls_disabled(False) # Re-enable all controls
        self.load_btn.set_text(self.get_string('load_button'))
        self.erase_btn.set_text(self.get_string('erase_button'))
        
        if rc == 0:
            self._show_notification('erase_success', 'success')
            self.after(0, self._update_log_area, f"\n{self.get_string('erase_success')}!\n")
        else:
            self._show_notification('erase_error', 'error')
            self.after(0, self._update_log_area, f"\nError during erase (Return Code: {rc}). See details above.\n")

    def _center_window(self):
        # Centers the main window on the screen
        self.update_idletasks() # Make sure widget dimensions are calculated
        
        # Get final window size
        w = self.winfo_width()
        h = self.winfo_height()
        
        # Get screen size
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        
        # Calculate x, y
        x = (ws - w) // 2
        y = (hs - h) // 2
        
        self.geometry(f"{w}x{h}+{x}+{y}")

if __name__ == "__main__":
    app = LoaderApp()
    app.mainloop()