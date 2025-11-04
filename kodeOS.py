#!/usr/bin/env python3
"""
kodeOS Loader – GUI to flash ESP32-S3 builds with progress bar
Rounded orange "Load" button, rounded progress bar.
Requirements:
  python3 -m pip install pyserial esptool Pillow
"""
import json
import subprocess
import sys
import io # Para capturar salida de esptool
try:
    from PIL import Image, ImageChops, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

import esptool # Para llamar directamente

# --- OPTIMIZED FOR PILLOW > 10 ---
# Con Pillow > 10, solo usamos la API moderna.
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

BAUD_RATE = 460800
# Paleta de colores con naranja y gris originales
BG = "#E1E1E1"            # Fondo gris claro original
ACCENT = "#FF7F1F"        # Naranja original
ACCENT_HOVER = "#FFB184"  # Naranjo claro para hover
TEXT_DARK = "#222222"     # Texto oscuro original
TEXT_LIGHT = "#FFFFFF"    # Texto claro/blanco
GRAY_LIGHT = "#CCCCCC"    # Gris claro ligeramente más oscuro para destacar la barra de progreso
GRAY_MID = "#888888"      # Gris medio para texto secundario

# Colores para notificaciones
COLOR_SUCCESS = "#28A745" # Verde
COLOR_ERROR = "#DC3545"   # Rojo
COLOR_INFO = TEXT_DARK    # Normal

# Tipografía mejorada (usando fuentes que suelen estar disponibles en sistemas)
FONT = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 12, "bold")
TITLE_FONT = ("Segoe UI", 16, "bold")

# ──────────────────────────  Language Strings ──────────────────────────
LANGUAGES = {
    'en': {
        'window_title': "kodeOS Loader",
        'serial_port_label': "Serial Port:",
        'firmware_label': "Firmware (.bin):",
        'refresh_button': "Refresh",
        'browse_button': "Browse",
        'load_button': "Load",
        'load_button_loading': "Loading...",
        'ports_loading': "Loading ports...",
        'no_ports_found': "No ports found",
        'browse_dialog_title': "Select firmware .bin",
        'status_ready': "Ready to load",
        'status_starting': "Starting flash...",
        'flashing_progress': "Flashing ({pct}%)...",
        'error_missing_params': "Select serial port and firmware .bin file.",
        'flash_success': "Flash completed successfully.",
        'flash_error_generic': "Error during flash. Check logs and retry."
    },
    'es': {
        'window_title': "Cargador kodeOS",
        'serial_port_label': "Puerto Serial:",
        'firmware_label': "Firmware (.bin):",
        'refresh_button': "Refrescar",
        'browse_button': "Buscar",
        'load_button': "Cargar",
        'load_button_loading': "Cargando...",
        'ports_loading': "Buscando puertos...",
        'no_ports_found': "No se encontraron puertos",
        'browse_dialog_title': "Seleccionar firmware .bin",
        'status_ready': "Listo para cargar",
        'status_starting': "Iniciando flasheo...",
        'flashing_progress': "Flasheando ({pct}%)...",
        'error_missing_params': "Seleccione un puerto serial y un archivo .bin.",
        'flash_success': "Flasheo completado con éxito.",
        'flash_error_generic': "Error durante el flasheo. Revise los logs e intente de nuevo."
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
        self._orig_bg = bg    # Guardar color original
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
        
        # Crear sombra sutil
        self.create_round_rect(3, 3, width, height, r, fill="#E0E0E0", outline="")
        # Crear botón principal
        self.create_round_rect(0, 0, width-3, height-3, r, fill=fill, outline="")
        # Texto del botón
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
        self.itemconfigure("label", text=text) # Más eficiente que _draw()

    def set_disabled(self, disabled=True):
        self.state_disabled = disabled
        fill = GRAY_MID if disabled else self.fg
        # Restaurar color original al activar, y gris claro al desactivar
        if disabled:
            self.normal_bg = GRAY_LIGHT
        else:
            self.normal_bg = self._orig_bg
        self.itemconfigure("label", fill=fill)
        self._draw(normal=True)

class RoundedProgress(tk.Canvas):
    def __init__(self, parent, width=400, height=20, bg=GRAY_LIGHT, fg=ACCENT, radius=10, **kwargs):
        tk.Canvas.__init__(self, parent, width=width, height=height, bg=BG,
                            highlightthickness=0, **kwargs)
        self.radius = radius
        self.fg = fg
        self.bg_color = bg
        self._pct = 0
        self._draw(0)

    def _draw(self, pct):
        self.delete("all")
        w = int(self['width']); h = int(self['height']); r = self.radius
        
        # Sombra sutil
        self.create_round_rect(2, 2, w, h, r, fill="#E5E5E5", outline="")
        
        # Fondo de la barra (trough)
        self.create_round_rect(0, 0, w-2, h-2, r, fill=self.bg_color, outline="")
        
        # Barra de progreso
        bar_w = max(r, int((w-2) * pct / 100))
        if bar_w > r * 2:  # Solo dibujar si hay suficiente progreso
            self.create_round_rect(0, 0, bar_w, h-2, r, fill=self.fg, outline="")
            
        # Texto de porcentaje
        if pct > 0:
            self.create_text(w//2, h//2, text=f"{int(pct)}%", 
                             fill=TEXT_LIGHT if pct > 50 else TEXT_DARK,
                             font=("Segoe UI", 9, "bold"))

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

    def set_pct(self, pct):
        self._pct = max(0, min(100, pct))
        self._draw(self._pct)

    def reset(self):
        self.set_pct(0)

# ──────────────────────────  Main Application  ──────────────────────────
class LoaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        
        # --- Configuración de idioma ---
        self.lang = 'en' # Idioma de inicio
        self.current_notification = None # (message_key, level)
        # --- Fin Configuración de idioma ---
        
        self.title(self.get_string('window_title'))
        self.iconbitmap("icon.ico")
        self.configure(bg=BG)  # ventana de fondo gris
        self.resizable(False, False)
        # Cargar iconos y recursos
        self._load_resources()
        self._build_ui()
        # Centrar ventana principal en pantalla
        self._center_window()
        
    # --- Métodos de Idioma ---
    def get_string(self, key):
        """Obtiene la cadena de texto para el idioma actual."""
        return LANGUAGES.get(self.lang, LANGUAGES['en']).get(key, f"<{key}>")

    def _set_language(self, lang):
        """Establece el nuevo idioma y actualiza la UI."""
        if lang not in LANGUAGES or lang == self.lang:
            return
        self.lang = lang
        self._update_ui_text()
        self._update_lang_switcher_ui()

    def _update_lang_switcher_ui(self):
        """Actualiza el resaltado del selector de idioma."""
        if self.lang == 'en':
            self.en_label.config(font=FONT_BOLD, fg=ACCENT)
            self.es_label.config(font=FONT, fg=GRAY_MID)
        else:
            self.en_label.config(font=FONT, fg=GRAY_MID)
            self.es_label.config(font=FONT_BOLD, fg=ACCENT)
            
    def _update_ui_text(self):
        """Actualiza todos los widgets de texto con el idioma actual."""
        self.title(self.get_string('window_title'))
        self.serial_label.config(text=self.get_string('serial_port_label'))
        self.firmware_label.config(text=self.get_string('firmware_label'))
        self.refresh_btn.set_text(self.get_string('refresh_button'))
        self.browse_btn.set_text(self.get_string('browse_button'))
        
        # Solo actualizar botón de carga si no está deshabilitado
        if not self.load_btn.state_disabled:
            self.load_btn.set_text(self.get_string('load_button'))
        
        # Actualizar lista de puertos (esto actualizará "No ports found" si es necesario)
        self._refresh_ports() 
        
        # Volver a mostrar la notificación/estado actual en el nuevo idioma
        if self.current_notification:
            key, level = self.current_notification
            # Si el progreso está activo, el hilo lo sobrescribirá, así que no hacemos nada
            if key.startswith('flashing_progress'):
                pass
            else:
                self._show_notification(key, level)
        elif not self.load_btn.state_disabled:
            # Mostrar estado 'Ready'
            self.result_label.config(text=self.get_string('status_ready'), fg=COLOR_INFO, image="")
        
        # Actualizar valor de port_var si es un mensaje de estado
        current_port = self.port_var.get()
        if current_port in [LANGUAGES['en']['no_ports_found'], LANGUAGES['es']['no_ports_found']]:
            self.port_var.set(self.get_string('no_ports_found'))
        elif current_port in [LANGUAGES['en']['ports_loading'], LANGUAGES['es']['ports_loading']]:
             self.port_var.set(self.get_string('ports_loading'))

    # --- Fin Métodos de Idioma ---

    # --- OPTIMIZED FOR PILLOW > 10 ---
    def _load_resources(self):
        # Preparar para futuros iconos si se necesitan
        self.icons = {}
        
        # --- Cargar Logo ---
        self.logo_img = None
        logo_path = pathlib.Path(__file__).resolve().parent / "images" / "logo.png"
        if logo_path.is_file():
            try:
                if PIL_AVAILABLE:
                    with Image.open(str(logo_path)) as pil_img: # 1. Open
                        # Color de fondo asumido en esquina superior izquierda
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
                
                else: # Fallback sin PIL
                    img = tk.PhotoImage(file=str(logo_path))
                    max_dim = 100
                    if img.width() > max_dim or img.height() > max_dim:
                        factor = max(img.width()//max_dim, img.height()//max_dim)
                        img = img.subsample(factor, factor)
                    self.logo_img = img
            except Exception as e:
                print(f"Error loading logo: {e}") # Añadido para depuración
                self.logo_img = None

        # --- Cargar Pet ---
        self.pet_img = None
        pet_path = pathlib.Path(__file__).resolve().parent / "images" / "pet.png"
        if pet_path.is_file():
            try:
                if PIL_AVAILABLE:
                    with Image.open(str(pet_path)) as pil_pet:
                        pil_pet.load() # Load data
                    
                    max_pet_dim = 140
                    pil_pet.thumbnail((max_pet_dim, max_pet_dim), RESAMPLE_FILTER) # Resize in-place
                    self.pet_img = ImageTk.PhotoImage(pil_pet)
                else: # Fallback sin PIL
                    pet = tk.PhotoImage(file=str(pet_path))
                    max_pet_dim = 140
                    factor = max(1, max(pet.width()//max_pet_dim, pet.height()//max_pet_dim))
                    pet = pet.subsample(factor, factor)
                    self.pet_img = pet
            except Exception as e:
                print(f"Error loading pet: {e}") # Añadido para depuración
                self.pet_img = None

        # --- Cargar Iconos de Resultado ---
        icon_dim = 32 # Tamaño para icono de notificación
        self.icon_success = None
        self.icon_error = None
        
        success_path = pathlib.Path(__file__).resolve().parent / "images" / "success.png"
        if success_path.is_file():
            try:
                if PIL_AVAILABLE:
                    with Image.open(str(success_path)) as pil_succ:
                        pil_succ.load()
                    pil_succ.thumbnail((icon_dim, icon_dim), RESAMPLE_FILTER)
                    self.icon_success = ImageTk.PhotoImage(pil_succ)
                else: # Fallback sin PIL
                    img = tk.PhotoImage(file=str(success_path))
                    w,h = img.width(), img.height()
                    factor = max(1, max(w//icon_dim, h//icon_dim))
                    self.icon_success = img.subsample(factor, factor)
            except Exception as e:
                print(f"Error loading success icon: {e}") # Añadido para depuración

        fail_path = pathlib.Path(__file__).resolve().parent / "images" / "fail.png"
        if fail_path.is_file():
            try:
                if PIL_AVAILABLE:
                    with Image.open(str(fail_path)) as pil_fail:
                        pil_fail.load()
                    pil_fail.thumbnail((icon_dim, icon_dim), RESAMPLE_FILTER)
                    self.icon_error = ImageTk.PhotoImage(pil_fail)
                else: # Fallback sin PIL
                    img = tk.PhotoImage(file=str(fail_path))
                    w,h = img.width(), img.height()
                    factor = max(1, max(w//icon_dim, h//icon_dim))
                    self.icon_error = img.subsample(factor, factor)
            except Exception as e:
                print(f"Error loading fail icon: {e}") # Añadido para depuración
    # --- END OPTIMIZATION ---

    # UI -----------------------------------------------------------------
    def _build_ui(self):
        # Usar grid para layout compacto con margen
        self.configure(padx=15, pady=15)
        # Frame izquierdo para logo y pet
        left_frame = tk.Frame(self, bg=BG)
        left_frame.grid(row=0, column=0, rowspan=5, sticky="nw", padx=(0,4), pady=0)
        # Mostrar logo si existe
        if getattr(self, 'logo_img', None):
            # Logo pequeño, sin padding extra
            tk.Label(left_frame, image=self.logo_img, bg=BG).pack(pady=(0,0))
        # Mostrar mascota pet debajo
        if getattr(self, 'pet_img', None):
            # Mascota más grande, pegada al logo
            tk.Label(left_frame, image=self.pet_img, bg=BG).pack(pady=(0,0))
        
        # Variables y constantes de entrada
        INPUT_HEIGHT = 28
        LOGO_SIZE = 120  # Tamaño máximo para el logo
        
        # Quitar expansión de columnas
        for i in range(4):
            self.columnconfigure(i, weight=0)
        
        # Reducir espacio entre filas
        for i in range(4):
            self.rowconfigure(i, pad=1)
        
        # FILA 0: Serial Port
        # Etiqueta Serial Port
        LABEL_FONT = ("Segoe UI", 12, "bold")
        self.serial_label = tk.Label(self, text=self.get_string('serial_port_label'), bg=BG, fg=TEXT_DARK, font=LABEL_FONT)
        self.serial_label.grid(row=0, column=1, sticky="e", padx=(0,4), pady=0)
        
        # Variable y combobox
        self.port_var = tk.StringVar()
        initial_port_value = self.get_string('ports_loading')
        self.port_var.set(initial_port_value)
        
        self.port_combo = tk.OptionMenu(self, self.port_var, initial_port_value)
        self.port_combo.config(font=FONT, bg=BG, fg=TEXT_DARK, 
                               activebackground=ACCENT, activeforeground=TEXT_LIGHT,
                               highlightthickness=1, highlightbackground=GRAY_LIGHT, bd=0)
        self.port_combo.grid(row=0, column=2, sticky="w")
        # Mantener color de texto oscuro tras selección
        self.port_var.trace_add('write', lambda *args: self.port_combo.config(fg=TEXT_DARK))
        
        # Refresh button
        self.refresh_btn = RoundedButton(self, text=self.get_string('refresh_button'), command=self._refresh_ports,
                                      width=80, height=INPUT_HEIGHT, bg=ACCENT, fg=TEXT_LIGHT,
                                      active_bg=ACCENT_HOVER)
        self.refresh_btn.grid(row=0, column=3, padx=(2,0), pady=0)
        
        # FILA 1: Build Folder
        self.firmware_label = tk.Label(self, text=self.get_string('firmware_label'), bg=BG, fg=TEXT_DARK, font=LABEL_FONT)
        self.firmware_label.grid(row=1, column=1, sticky="e", padx=(0,4), pady=0)
        
        # Entry para build folder
        self.build_var = tk.StringVar()
        self.build_entry = tk.Entry(self, textvariable=self.build_var, 
                                  font=FONT, bg=BG, fg=TEXT_DARK, 
                                  relief=tk.FLAT, highlightthickness=1, 
                                  highlightbackground=GRAY_LIGHT)
        self.build_entry.grid(row=1, column=2, sticky="w", padx=0, pady=0)

        # Browse button
        self.browse_btn = RoundedButton(self, text=self.get_string('browse_button'), command=self._browse,
                                      width=80, height=INPUT_HEIGHT, bg=ACCENT, fg=TEXT_LIGHT,
                                      active_bg=ACCENT_HOVER)
        self.browse_btn.grid(row=1, column=3, padx=(2,0), pady=0)

        # FILA 2: Progress Bar
        bar_frame = tk.Frame(self, bg=BG)
        bar_frame.grid(row=2, column=1, columnspan=3, sticky="w", padx=0, pady=(2,0))
        
        bar_height = 26
        self.progress = RoundedProgress(bar_frame, width=380, height=bar_height, 
                                      bg=GRAY_LIGHT, fg=ACCENT, radius=bar_height//2)
        self.progress.grid(row=0, column=0, sticky="w", padx=0, pady=0)
        
        # FILA 3: LOAD button
        button_frame = tk.Frame(self, bg=BG)
        button_frame.grid(row=3, column=1, columnspan=3, pady=(2,0))
        button_frame.grid_columnconfigure(0, weight=1)
        # Ocultar posible espacio alrededor
        button_frame.configure(padx=0, pady=0)
        
        # Botón Load
        self.load_btn = RoundedButton(button_frame, text=self.get_string('load_button'), width=160, height=38, 
                                      command=self._start_flash, bg=ACCENT, fg=TEXT_LIGHT)
        self.load_btn.grid(row=0, column=0, padx=0, pady=0)
        
        # FILA 4: Label para resultado/notificación (debajo del botón)
        self.result_label = tk.Label(self, text=self.get_string('status_ready'), 
                                     bg=BG, fg=COLOR_INFO, font=FONT_BOLD, 
                                     compound=tk.LEFT, anchor="w", justify=tk.LEFT)
        self.result_label.grid(row=4, column=1, columnspan=3, sticky="ew", padx=0, pady=(4,0))


        # FILA 5: Log Area
        log_frame = tk.Frame(self, bg=BG)
        log_frame.grid(row=5, column=0, columnspan=4, sticky="nsew", pady=(5,0)) # Span all columns including left_frame
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        self.log_text = tk.Text(log_frame, wrap=tk.WORD, state=tk.DISABLED,
                                height=10, bg="#F0F0F0", fg=TEXT_DARK,
                                relief=tk.FLAT, highlightthickness=1,
                                highlightbackground=GRAY_LIGHT, font=("Courier New", 9))
        self.log_text.grid(row=0, column=0, sticky="nsew")

        log_scrollbar = tk.Scrollbar(log_frame, command=self.log_text.yview)
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=log_scrollbar.set)
        
        # Configurar la fila 5 para que se expanda si la ventana cambia de tamaño (aunque es fija)
        self.rowconfigure(5, weight=1)

        # FILA 6: Language Switcher
        lang_frame = tk.Frame(self, bg=BG)
        lang_frame.grid(row=6, column=0, columnspan=4, sticky="e", pady=(5,0))
        
        # Añadidos de derecha a izquierda
        self.es_label = tk.Label(lang_frame, text="Español", bg=BG, fg=GRAY_MID, font=FONT, cursor="hand2")
        self.es_label.pack(side=tk.RIGHT, padx=5)
        self.es_label.bind("<Button-1>", lambda e: self._set_language('es'))
        
        tk.Label(lang_frame, text="|", bg=BG, fg=GRAY_MID, font=FONT).pack(side=tk.RIGHT)

        self.en_label = tk.Label(lang_frame, text="English", bg=BG, fg=ACCENT, font=FONT_BOLD, cursor="hand2")
        self.en_label.pack(side=tk.RIGHT, padx=5)
        self.en_label.bind("<Button-1>", lambda e: self._set_language('en'))

        # Inicializar los puertos
        self._refresh_ports()
        
    # --- Notificaciones ---
    def _show_notification(self, message_key, level='info'):
        """Muestra una notificación en self.result_label."""
        self.current_notification = (message_key, level) # Guardar la clave
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
        """Limpia el área de notificación."""
        self.current_notification = None
        self.result_label.config(text="", image="", fg=COLOR_INFO)

    # Helpers ------------------------------------------------------------
    def _list_ports(self):
        return [p.device for p in list_ports.comports()]

    def _refresh_ports(self):
        menu = self.port_combo['menu']
        menu.delete(0, 'end')
        ports = self._list_ports()
        if ports:
            for p in ports:
                menu.add_command(label=p, command=lambda v=p, var=self.port_var: var.set(v))
            
            # No sobreescribir si ya hay un puerto seleccionado
            current_val = self.port_var.get()
            if current_val in [self.get_string('no_ports_found'), self.get_string('ports_loading')] or current_val not in ports:
                 self.port_var.set(ports[0]) # Seleccionar el primero
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

    # Flash logic --------------------------------------------------------
    def _start_flash(self):
        port = self.port_var.get(); build = self.build_var.get()
        if not port or not build or port == self.get_string('no_ports_found') or port == self.get_string('ports_loading'):
            self._show_notification('error_missing_params', 'error')
            return
        # UI changes
        self._clear_log_area() # Limpiar logs antes de empezar
        self._clear_notification() # Limpiar notificación anterior
        self.load_btn.set_text(self.get_string('load_button_loading')); self.load_btn.set_disabled(True)
        self.progress.reset()
        self._show_notification('status_starting', 'info')
        self._skip_initial_progress = True
        self.after(0, self._update_log_area, self.get_string('status_starting') + "\n") # Log inicial
        threading.Thread(target=self._flash_thread, args=(build, port), daemon=True).start()

    def _flash_thread(self, bin_file, port):
        args = ["--chip", "esp32s3",
                "--port", port,
                "--baud", str(BAUD_RATE),
                "write_flash", "-z", "0x0", bin_file]
        
        all_logs = []
        return_code = 1 # Default a error

        self.after(0, self._update_log_area, f"Executing esptool.main with args: {args}\n")

        # Streaming de logs de esptool.main y parseo de porcentaje dentro de paréntesis
        regex = re.compile(r"\(\s*(\d{1,3})\s*%\s*\)")
        class _StreamLogger(io.StringIO):
            def write(inner_self, data):
                # Buffer interno
                super(_StreamLogger, inner_self).write(data)
                # Enviar líneas parciales a la UI y extraer progreso, omitiendo el primer 100%
                for part in data.splitlines(True):
                    self.after(0, self._update_log_area, part)
                    m = regex.search(part)
                    if m:
                        pct = int(m.group(1))
                        if pct < 100:
                            # Primer progreso real o intermedio
                            self._skip_initial_progress = False
                            self.after(0, self.progress.set_pct, pct)
                            # Actualizar notificación de estado
                            msg = self.get_string('flashing_progress').format(pct=pct)
                            self.after(0, self.result_label.config, {"text": msg, "fg": COLOR_INFO, "image": ""})
                            self.after(0, setattr, self, 'current_notification', None) # No es una notificación final
                        elif pct == 100 and not self._skip_initial_progress:
                            # Solo mostrar 100% si ya hubo progreso menor
                            self.after(0, self.progress.set_pct, pct)
                            msg = self.get_string('flashing_progress').format(pct=pct)
                            self.after(0, self.result_label.config, {"text": msg, "fg": COLOR_INFO, "image": ""})
                            self.after(0, setattr, self, 'current_notification', None)
        
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

        # Obtener logs completos y almacenarlos
        captured_output = stream_logger.getvalue()
        all_logs.append(captured_output)
        
        self.after(0, self._flash_complete, return_code, "".join(all_logs))

    def _flash_complete(self, rc, logs):
        self.load_btn.set_text(self.get_string('load_button')); self.load_btn.set_disabled(False); self.progress.reset()
        if rc == 0:
            self._show_notification('flash_success', 'success')
            self.after(0, self._update_log_area, f"\n{self.get_string('flash_success')}!\n")
        else:
            self._show_notification('flash_error_generic', 'error')
            self.after(0, self._update_log_area, f"\nError during flash (Return Code: {rc}). See details above.\n")

    def _center_window(self):
        # Centra la ventana principal en el centro de la pantalla
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        ws = self.winfo_screenwidth()
        hs = self.winfo_screenheight()
        x = (ws - w) // 2
        y = (hs - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

if __name__ == "__main__":
    app = LoaderApp()
    app.mainloop()