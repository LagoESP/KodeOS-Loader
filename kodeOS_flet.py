#!/usr/bin/env python3
"""
kodeOS Loader – GUI to flash ESP32-S3 builds
Built with Flet for a consistent cross-platform UI.

Requirements:
  python3 -m pip install flet pyserial esptool Pillow
"""
import sys
import io
import threading
import pathlib
import re
import flet as ft # Flet en lugar de Tkinter
from serial.tools import list_ports
import esptool

try:
    from PIL import Image, ImageChops
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# --- OPTIMIZED FOR PILLOW > 10 ---
if PIL_AVAILABLE:
    RESAMPLE_FILTER = Image.Resampling.LANCZOS
else:
    RESAMPLE_FILTER = None
# --- END OPTIMIZATION ---

# --- Helper function for PyInstaller ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = pathlib.Path(sys._MEIPASS)
    except Exception:
        # Not in a PyInstaller bundle, so use the script's directory
        base_path = pathlib.Path(__file__).resolve().parent
    
    return str(base_path / relative_path)

BAUD_RATE = 460800
# Original color palette with orange and gray
WHITE = "#FFFFFF"
BG = "#E1E1E1"
ACCENT = "#FF7F1F"
ACCENT_HOVER = "#FFB184"
TEXT_DARK = "#222222"
TEXT_LIGHT = "#FFFFFF"
GRAY_LIGHT = "#CCCCCC"
GRAY_MID = "#888888"
LOG_BG = "#F0F0F0"

# Notification colors
COLOR_SUCCESS = "#28A745"
COLOR_ERROR = "#DC3545"
COLOR_ERROR_HOVER = "#E4606D"
COLOR_INFO = TEXT_DARK

# Improved typography
FONT_FAMILY = "Segoe UI"
FONT_SIZE = 11
FONT_SIZE_BOLD = 12

# ──────────────────────────  Language Strings ──────────────────────────
LANGUAGES = {
    'en': {
        'window_title': "kodeOS Loader",
        'serial_port_label': "Serial Port:",
        'firmware_label': "Firmware (.bin):",
        'flash_app_checkbox': "Flash Kode OS App (0x400000)",
        'refresh_button': "Refresh",
        'browse_button': "Browse",
        'load_button': "Flash",
        'load_button_loading': "Flashing...",
        'erase_button': "Erase",
        'erase_button_erasing': "Erasing...",
        'ports_loading': "Loading ports...",
        'no_ports_found': "No USB ports found",
        'select_port_prompt': "Select your upload USB port", # New
        'browse_dialog_title': "Select firmware .bin",
        'status_ready': "Ready to flash",
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
        'flash_app_checkbox': "Flashear App Kode OS (0x400000)",
        'refresh_button': "Refrescar",
        'browse_button': "Buscar",
        'load_button': "Flashear",
        'load_button_loading': "Flasheando...",
        'erase_button': "Borrar",
        'erase_button_erasing': "Borrando...",
        'ports_loading': "Buscando puertos...",
        'no_ports_found': "No se encontraron puertos USB",
        'select_port_prompt': "Seleccione su puerto USB", # New
        'browse_dialog_title': "Seleccionar firmware .bin",
        'status_ready': "Listo para flashear",
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

# ──────────────────────────  Main Application  ──────────────────────────

def main(page: ft.Page):
    
    # --- Configuración de la Página (Ventana) ---
    page.title = LANGUAGES['en']['window_title']
    page.bgcolor = BG
    page.window_resizable = False
    page.window_width = 750
    page.window_height = 640
    page.padding = 15
    page.fonts = {
        "Segoe UI": "https://path.to/segoe_ui.ttf" 
    }
    
    INPUT_HEIGHT = 28
    
    # --- Carga de Icono Multiplataforma ---
    try:
        icon_path = resource_path("icon.png") 
        if not pathlib.Path(icon_path).is_file():
             icon_path = resource_path("icon.ico")
        page.window_icon = icon_path
    except Exception as e:
        print(f"Icon not found ({e}), using default.")

    # --- Estado de la Aplicación ---
    lang = 'en'
    current_notification = None

    # --- Referencias a Controles ---
    port_dropdown = ft.Ref[ft.Dropdown]()
    port_dropdown_container = ft.Ref[ft.Container]() # Contenedor para "destruir" el dropdown
    firmware_path = ft.Ref[ft.TextField]()
    flash_app_check = ft.Ref[ft.Checkbox]()
    load_btn = ft.Ref[ft.ElevatedButton]()
    erase_btn = ft.Ref[ft.ElevatedButton]()
    refresh_btn = ft.Ref[ft.ElevatedButton]()
    browse_btn = ft.Ref[ft.ElevatedButton]()
    notification_icon = ft.Ref[ft.Icon]()
    notification_text = ft.Ref[ft.Text]()
    log_view = ft.Ref[ft.ListView]()
    en_lang_button = ft.Ref[ft.Text]()
    es_lang_button = ft.Ref[ft.Text]()
    serial_label_text = ft.Ref[ft.Text]()
    firmware_label_text = ft.Ref[ft.Text]()
    dialog_title_ref = ft.Ref[ft.Text]()
    dialog_content_ref = ft.Ref[ft.Text]()
    
    # --- Diálogo de Confirmación de Borrado ---
    confirm_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(ref=dialog_title_ref, value=LANGUAGES[lang]['erase_confirm_title']),
        content=ft.Text(ref=dialog_content_ref, value=LANGUAGES[lang]['erase_confirm_message']),
        actions_alignment=ft.MainAxisAlignment.END,
    )
    page.dialog = confirm_dialog
    
    def on_erase_confirmed(e):
        close_dialog(e)
        _clear_log_area()
        _set_controls_disabled(True)
        erase_btn.current.text = get_string('erase_button_erasing')
        _show_notification('status_erasing', 'info')
        
        port = port_dropdown.current.value
        threading.Thread(target=_erase_thread, args=(port,), daemon=True).start()

    def close_dialog(e):
        confirm_dialog.open = False
        page.update()
        
    confirm_dialog.actions = [
        ft.TextButton("Yes", on_click=on_erase_confirmed),
        ft.TextButton("No", on_click=close_dialog),
    ]

    # --- Lógica de la Aplicación (Funciones anidadas) ---

    def get_string(key):
        return LANGUAGES.get(lang, LANGUAGES['en']).get(key, f"<{key}>")

    def _update_lang_switcher_ui():
        if lang == 'en':
            en_lang_button.current.weight = ft.FontWeight.BOLD
            en_lang_button.current.color = ACCENT
            es_lang_button.current.weight = ft.FontWeight.NORMAL
            es_lang_button.current.color = GRAY_MID
        else:
            en_lang_button.current.weight = ft.FontWeight.NORMAL
            en_lang_button.current.color = GRAY_MID
            es_lang_button.current.weight = ft.FontWeight.BOLD
            es_lang_button.current.color = ACCENT
        page.update()

    def _update_ui_text():
        page.title = get_string('window_title')
        serial_label_text.current.value = get_string('serial_port_label')
        firmware_label_text.current.value = get_string('firmware_label')
        flash_app_check.current.label = get_string('flash_app_checkbox')
        refresh_btn.current.text = get_string('refresh_button')
        browse_btn.current.text = get_string('browse_button')

        if not load_btn.current.disabled:
            load_btn.current.text = get_string('load_button')
        if not erase_btn.current.disabled:
            erase_btn.current.text = get_string('erase_button')
        
        dialog_title_ref.current.value = get_string('erase_confirm_title')
        dialog_content_ref.current.value = get_string('erase_confirm_message')

        _refresh_ports(update_text=True) 
        
        if current_notification:
            key, level = current_notification
            if not key.startswith('flashing_progress') and not key.startswith('status_erasing'):
                _show_notification(key, level)
        elif not load_btn.current.disabled:
            _show_notification('status_ready', 'info')

        page.update()

    def _set_language(e, new_lang):
        if load_btn.current.disabled:
            return
        nonlocal lang
        if lang == new_lang:
            return
        lang = new_lang
        _update_ui_text()
        _update_lang_switcher_ui()

    def _list_ports():
        ports = list_ports.comports()
        usb_ports = [
            p.device for p in ports 
            if p.vid is not None or "USB" in p.hwid.upper() or "USB" in p.description.upper()
        ]
        return usb_ports

    def _create_port_dropdown():
        """Crea una nueva instancia de Dropdown para limpiar el estado."""
        # El estilo de texto se define en body_style
        body_style = ft.TextStyle(size=FONT_SIZE, font_family=FONT_FAMILY, color=TEXT_DARK)
        
        new_dd = ft.Dropdown(
            ref=port_dropdown, # Asigna la ref al nuevo control
            label_style=ft.TextStyle(size=FONT_SIZE, font_family=FONT_FAMILY, color=GRAY_MID),
            expand=True,
            border_color=GRAY_LIGHT,
            border_width=1.5,
            content_padding=10,
            text_style=body_style, # <-- FIX: Color de texto aplicado
        )
        return new_dd

    def _refresh_ports(e=None, update_text=False):
        # --- FIX: Lógica de "Destruir y Rehacer" ---
        
        # 1. Guardar el valor antiguo (si existe) ANTES de destruir
        old_value = port_dropdown.current.value if port_dropdown.current else None
        
        # 2. Crear y asignar un Dropdown completamente nuevo
        new_dropdown = _create_port_dropdown()
        port_dropdown_container.current.content = new_dropdown
        page.update() # Forzar redibujo inmediato

        # 3. Rellenar el nuevo dropdown
        ports = _list_ports()
        
        if ports:
            new_dropdown.options.clear() # Limpiar (aunque es new, por si acaso)
            for p in ports:
                new_dropdown.options.append(ft.dropdown.Option(p))
            
            # Comprobar si el valor antiguo sigue siendo válido
            if old_value in ports and not update_text:
                new_dropdown.value = old_value # Restaurar valor
                new_dropdown.label = None
            else:
                new_dropdown.value = None # No seleccionar nada
                new_dropdown.label = get_string('select_port_prompt')
            
            new_dropdown.disabled = False
        else:
            # No hay puertos
            new_dropdown.value = None
            new_dropdown.label = get_string('no_ports_found')
            new_dropdown.disabled = True
            
        page.update()

    def _on_file_picked(e: ft.FilePickerResultEvent):
        if e.files and len(e.files) > 0:
            firmware_path.current.value = e.files[0].path
            page.update()
            
    def _browse_file_picker(e):
        file_picker.pick_files(
            dialog_title=get_string('browse_dialog_title'),
            allowed_extensions=["bin"]
        )

    def _show_notification(key, level='info'):
        nonlocal current_notification
        current_notification = (key, level)
        message = get_string(key)
        
        notification_icon.current.name = None
        notification_icon.current.color = None
        
        if level == 'success':
            notification_icon.current.name = ft.Icons.CHECK_CIRCLE
            notification_icon.current.color = COLOR_SUCCESS
            notification_text.current.color = COLOR_SUCCESS
        elif level == 'error':
            notification_icon.current.name = ft.Icons.ERROR
            notification_icon.current.color = COLOR_ERROR
            notification_text.current.color = COLOR_ERROR
        else:
            notification_text.current.color = COLOR_INFO
            
        notification_text.current.value = message
        page.update()

    def _clear_log_area():
        log_view.current.controls.clear()
        page.update()

    def _update_log_area_safe(message):
        log_view.current.controls.append(
            ft.Text(message, size=10, font_family="Monospace", selectable=True, color=TEXT_DARK)
        )
        if len(log_view.current.controls) > 0:
            log_view.current.update()

    def _update_log_area(message):
        page.run_thread(_update_log_area_safe, message)

    def _set_controls_disabled(disabled=True):
        """Disables or enables all interactive controls."""
        load_btn.current.disabled = disabled
        erase_btn.current.disabled = disabled
        refresh_btn.current.disabled = disabled
        browse_btn.current.disabled = disabled
        firmware_path.current.disabled = disabled
        flash_app_check.current.disabled = disabled
        
        # --- FIX: Lógica de habilitación/deshabilitación del dropdown ---
        if disabled:
            port_dropdown.current.disabled = True
        else:
            # Al habilitar, solo habilitar si hay opciones en la lista
            port_dropdown.current.disabled = (len(port_dropdown.current.options) == 0)

        page.update()

    # --- Logica de Flasheo y Borrado ---

    def _flash_thread(bin_file, port, is_app_flash):
        base_args = ["--chip", "esp32s3",
                     "--port", port,
                     "--baud", str(BAUD_RATE)]
        
        if is_app_flash:
            flash_args = ["write_flash", 
                          "--flash-freq", "80m", 
                          "--flash-mode", "dio", 
                          "--flash-size", "32MB", 
                          "0x400000", bin_file]
        else:
            flash_args = ["write_flash", "-z", "0x0", bin_file]
            
        args = base_args + flash_args
        
        all_logs = []
        return_code = 1
        _update_log_area(f"Executing esptool.main with args: {args}\n")

        regex = re.compile(r"\(\s*(\d{1,3})\s*%\s*\)")
        
        class _StreamLogger(io.StringIO):
            def write(inner_self, data):
                super(_StreamLogger, inner_self).write(data)
                for part in data.splitlines(True):
                    _update_log_area(part)
                    m = regex.search(part)
                    if m:
                        pct = int(m.group(1))
                        msg = get_string('flashing_progress').format(pct=pct)
                        page.run_thread(
                            lambda: notification_text.current.set_value(msg)
                        )
        
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
            _update_log_area(f"\nException during esptool.main: {e}\n")
            return_code = 1
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            captured_output = stream_logger.getvalue()
            all_logs.append(captured_output)
            page.run_thread(_flash_complete, return_code, "".join(all_logs))

    def _start_flash(e):
        port = port_dropdown.current.value
        build = firmware_path.current.value
        
        if not port:
             _show_notification('error_missing_port', 'error')
             return
        if not build:
            _show_notification('error_missing_params', 'error')
            return
            
        _clear_log_area()
        _set_controls_disabled(True)
        load_btn.current.text = get_string('load_button_loading')
        _show_notification('status_starting', 'info')
        
        is_app = flash_app_check.current.value == True
        
        threading.Thread(target=_flash_thread, args=(build, port, is_app), daemon=True).start()

    def _flash_complete(rc, logs):
        _set_controls_disabled(False)
        load_btn.current.text = get_string('load_button')
        _refresh_ports() # <-- FIX: Refrescar estado del puerto al finalizar
        if rc == 0:
            _show_notification('flash_success', 'success')
            _update_log_area(f"\n{get_string('flash_success')}!\n")
        else:
            _show_notification('flash_error_generic', 'error')
            _update_log_area(f"\nError during flash (Return Code: {rc}). See details above.\n")

    # --- Lógica de Borrado ---
    
    def _erase_thread(port):
        args = ["--chip", "esp32s3",
                "--port", port,
                "--baud", str(BAUD_RATE),
                "erase_flash"]
        
        all_logs = []
        return_code = 1
        _update_log_area(f"Executing esptool.main with args: {args}\n")

        class _StreamLogger(io.StringIO):
            def write(inner_self, data):
                super(_StreamLogger, inner_self).write(data)
                for part in data.splitlines(True):
                    _update_log_area(part)
        
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
            _update_log_area(f"\nException during esptool.main: {e}\n")
            return_code = 1
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            captured_output = stream_logger.getvalue()
            all_logs.append(captured_output)
            page.run_thread(_erase_complete, return_code, "".join(all_logs))
            
    def _start_erase(e):
        port = port_dropdown.current.value
        if not port:
            _show_notification('error_missing_port', 'error')
            return
            
        confirm_dialog.open = True
        page.update()

    def _erase_complete(rc, logs):
        _set_controls_disabled(False)
        load_btn.current.text = get_string('load_button')
        erase_btn.current.text = get_string('erase_button')
        _refresh_ports() # <-- FIX: Refrescar estado del puerto al finalizar
        
        if rc == 0:
            _show_notification('erase_success', 'success')
            _update_log_area(f"\n{get_string('erase_success')}!\n")
        else:
            _show_notification('erase_error', 'error')
            _update_log_area(f"\nError during erase (Return Code: {rc}). See details above.\n")
            
    # --- File Picker Overlay ---
    file_picker = ft.FilePicker(on_result=_on_file_picked)
    page.overlay.append(file_picker)

    # --- Creación del Layout de la UI ---
    
    button_style_small = ft.ButtonStyle(
        bgcolor={
            "": ACCENT,
            "hovered": ACCENT_HOVER,
        },
        color=TEXT_LIGHT,
        shape=ft.RoundedRectangleBorder(radius=10),
        padding=5
    )
    button_style_flash = ft.ButtonStyle(
        bgcolor={
            "": ACCENT,
            "hovered": ACCENT_HOVER,
            "disabled": GRAY_LIGHT,
        },
        color={
            "": TEXT_LIGHT,
            "disabled": GRAY_MID,
        },
        shape=ft.RoundedRectangleBorder(radius=19),
        padding=ft.padding.symmetric(vertical=9),
        overlay_color=ACCENT_HOVER,
    )
    button_style_erase = ft.ButtonStyle(
        bgcolor={
            "": COLOR_ERROR,
            "hovered": COLOR_ERROR_HOVER,
            "disabled": GRAY_LIGHT,
        },
        color={
            "": TEXT_LIGHT,
            "disabled": GRAY_MID,
        },
        shape=ft.RoundedRectangleBorder(radius=19),
        padding=ft.padding.symmetric(vertical=9),
        overlay_color=COLOR_ERROR_HOVER,
    )
    
    # Estilos de texto
    label_style = ft.TextStyle(weight=ft.FontWeight.BOLD, size=FONT_SIZE_BOLD, font_family=FONT_FAMILY, color=TEXT_DARK)
    body_style = ft.TextStyle(size=FONT_SIZE, font_family=FONT_FAMILY, color=TEXT_DARK)
    
    # --- Construir la página ---
    page.add(
        ft.Row(
            [
                # --- Columna Izquierda (Logo/Pet) ---
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Image(
                                src="logo.png",
                                width=100, 
                                fit=ft.ImageFit.CONTAIN
                            ),
                            ft.Image(
                                src="pet.png", 
                                width=140, 
                                fit=ft.ImageFit.CONTAIN
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=0,
                    ),
                    padding=ft.padding.only(top=20, right=10),
                    width=160 
                ),
                
                # --- Columna Derecha (Controles) ---
                ft.Column(
                    [
                        # --- Fila Serial Port ---
                        ft.Row(
                            [
                                ft.Text(ref=serial_label_text, value=get_string('serial_port_label'), style=label_style, width=110, text_align=ft.TextAlign.RIGHT),
                                # --- FIX: Contenedor para "destruir y rehacer" el dropdown ---
                                ft.Container(
                                    ref=port_dropdown_container,
                                    content=_create_port_dropdown(), # Crear la instancia inicial
                                    expand=True
                                ),
                                ft.ElevatedButton(
                                    ref=refresh_btn,
                                    text=get_string('refresh_button'),
                                    on_click=_refresh_ports,
                                    style=button_style_small,
                                    width=90,
                                    height=INPUT_HEIGHT+10
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=5
                        ),
                        
                        # --- Fila Firmware ---
                        ft.Row(
                            [
                                ft.Text(ref=firmware_label_text, value=get_string('firmware_label'), style=label_style, width=110, text_align=ft.TextAlign.RIGHT),
                                ft.TextField(
                                    ref=firmware_path,
                                    expand=True,
                                    read_only=True,
                                    border=ft.InputBorder.OUTLINE,
                                    border_color=GRAY_LIGHT,
                                    text_size=FONT_SIZE,
                                    content_padding=10,
                                    text_style=body_style, # <-- FIX: Color aplicado
                                ),
                                ft.ElevatedButton(
                                    ref=browse_btn,
                                    text=get_string('browse_button'),
                                    on_click=_browse_file_picker,
                                    style=button_style_small,
                                    width=90,
                                    height=INPUT_HEIGHT+10
                                ),
                            ],
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=5
                        ),
                        
                        # --- Checkbox ---
                        ft.Checkbox(
                            ref=flash_app_check,
                            label=get_string('flash_app_checkbox'),
                            label_style=ft.TextStyle( # <-- FIX: Color de texto añadido
                                size=FONT_SIZE, 
                                font_family=FONT_FAMILY, 
                                weight=ft.FontWeight.NORMAL, 
                                color=TEXT_DARK
                            ),
                            check_color=ACCENT,
                            fill_color=WHITE,
                        ),
                        
                        # --- Botones Flash/Erase ---
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    ref=load_btn,
                                    text=get_string('load_button'),
                                    on_click=_start_flash,
                                    style=button_style_flash,
                                    width=160,
                                    height=38
                                ),
                                ft.ElevatedButton(
                                    ref=erase_btn,
                                    text=get_string('erase_button'),
                                    on_click=_start_erase,
                                    style=button_style_erase,
                                    width=160,
                                    height=38
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_EVENLY,
                            spacing=10
                        ),
                        
                        # --- Notificación ---
                        ft.Row(
                            [
                                ft.Icon(ref=notification_icon, size=18, color=COLOR_INFO),
                                ft.Text(ref=notification_text, value=get_string('status_ready'), 
                                        weight=ft.FontWeight.BOLD, size=FONT_SIZE_BOLD, 
                                        font_family=FONT_FAMILY, color=COLOR_INFO),
                            ],
                            alignment=ft.MainAxisAlignment.CENTER,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            height=30
                        ),
                        
                        # --- Área de Log ---
                        ft.Container(
                            content=ft.ListView(
                                ref=log_view,
                                expand=True,
                                spacing=2,
                                auto_scroll=True,
                                padding=10
                            ),
                            expand=True,
                            border=ft.border.all(1.5, GRAY_LIGHT),
                            border_radius=5,
                            bgcolor=LOG_BG
                        ),
                        
                        # --- Selector de Idioma ---
                        ft.Row(
                            [
                                ft.Container(
                                    content=ft.Text(ref=en_lang_button, value="English", style=body_style, data='en'),
                                    on_click=lambda e: _set_language(e, 'en'),
                                    padding=ft.padding.symmetric(horizontal=5)
                                ),
                                ft.Text("|", color=GRAY_MID),
                                ft.Container(
                                    content=ft.Text(ref=es_lang_button, value="Español", style=body_style, data='es'),
                                    on_click=lambda e: _set_language(e, 'es'),
                                    padding=ft.padding.symmetric(horizontal=5)
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.END,
                            spacing=5
                        )
                    ],
                    expand=True,
                    spacing=5
                )
            ],
            vertical_alignment=ft.CrossAxisAlignment.START,
            expand=True
        )
    )
    
    # --- Carga Inicial ---
    page.update()
    _refresh_ports()
    _update_lang_switcher_ui()

# --- Ejecutar la App ---
if __name__ == "__main__":
    ft.app(
        target=main, 
        assets_dir=resource_path("images")
    )