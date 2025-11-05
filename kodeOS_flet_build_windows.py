#!/usr/bin/env python3
"""
Build script for Windows using 'flet pack' by activating the venv.

This script automates the 'flet pack' build by first calling the
'activate.bat' script from the venv and then chaining the 'flet' command
in the same shell session.

This requires the virtual environment to be named 'KodeOS-Loader'.
"""
import os
import shutil
import subprocess
from pathlib import Path

# --- 0. Project Configuration ---
APP_NAME = "kodeOS-Loader"
SCRIPT_FILE = "kodeOS_flet.py"
ICON_FILE = "images/icon.ico"
VERSION = "1.0.0"

# --- This is the key assumption ---
# The build MUST run with a venv of this name in the root
VENV_NAME = "KodeOS-Loader"

# --- -------------------------- ---

# Internal script variables
CWD = Path.cwd()
RELEASE_DIR = CWD / "release"
DIST_DIR = CWD / "dist"
BUILD_DIR = CWD / "build" # PyInstaller/Flet also creates this
FINAL_PORTABLE_EXE = RELEASE_DIR / f"{APP_NAME}-v{VERSION}-Portable.exe"

# Path to the activation script
# We must use 'activate.bat' for 'cmd.exe', which is what subprocess uses
ACTIVATE_SCRIPT = CWD / VENV_NAME / "Scripts" / "activate.bat"

# Path to the esptool data we must bundle manually
ESPTOOL_DATA_PATH = CWD / VENV_NAME / "Lib" / "site-packages" / "esptool" / "targets"
ESPTOOL_DEST_PATH = "esptool/targets" # The path *inside* the .exe

# Path to the images we must bundle
IMAGES_DATA_PATH = CWD / "images"
IMAGES_DEST_PATH = "images"

def run_command(command_string, error_message):
    """
    Executes a shell command string and fails if there is an error.
    We use shell=True here to allow for command chaining with '&&'.
    """
    try:
        print(f"-> Executing: {command_string}")
        # We MUST use shell=True to interpret '&&'
        subprocess.run(command_string, check=True, text=True, capture_output=True, shell=True)
    except FileNotFoundError:
        print("--- ERROR! ---")
        print(f"Command not found. This script requires a shell (cmd.exe) to run.")
        raise
    except subprocess.CalledProcessError as e:
        print(f"--- ERROR! ---")
        print(f"{error_message}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        raise

def cleanup():
    """Cleans up all temporary build files and folders."""
    print("--- 4. Cleaning up intermediate files ---")
    shutil.rmtree(BUILD_DIR, ignore_errors=True)
    shutil.rmtree(DIST_DIR, ignore_errors=True)
    
    spec_file = CWD / f"{APP_NAME}.spec"
    if spec_file.exists():
        os.remove(spec_file)

def check_build_env():
    """Checks that all required paths for the build exist."""
    print("--- 1. Verifying build environment ---")
    if not (CWD / VENV_NAME).is_dir():
        print(f"\n--- BUILD FAILED! ---")
        print(f"Virtual environment folder not found at: {CWD / VENV_NAME}")
        print(f"Please create a venv named '{VENV_NAME}' in the project root.")
        raise FileNotFoundError(f"Venv '{VENV_NAME}' not found.")
    
    if not ACTIVATE_SCRIPT.is_file():
        print(f"\n--- BUILD FAILED! ---")
        print(f"Activation script not found at: {ACTIVATE_SCRIPT}")
        print("Is your venv corrupted?")
        raise FileNotFoundError(f"activate.bat not found.")
        
    if not ESPTOOL_DATA_PATH.is_dir():
        print(f"\n--- BUILD FAILED! ---")
        print(f"'esptool' data not found at: {ESPTOOL_DATA_PATH}")
        print("Did you forget to install the requirements in your venv?")
        print(f"Run: .\\{VENV_NAME}\\Scripts\\activate")
        print("Then: pip install -r requirements.txt")
        raise FileNotFoundError(f"esptool data not found.")
    
    print("-> Build environment seems correct.")

def main():
    os.chdir(Path(__file__).parent)
    print(f"Starting Windows portable build for {APP_NAME} v{VERSION}...")

    # --- 1. Check environment ---
    check_build_env()

    # --- 2. Initial Cleanup ---
    print("--- 2. Cleaning up previous builds ---")
    cleanup()
    shutil.rmtree(RELEASE_DIR, ignore_errors=True)
    RELEASE_DIR.mkdir()

    # --- 3. Build the flet pack command ---
    print("--- 3. Creating portable executable with 'flet pack' ---")
    
    # Format for --add-data: "SOURCE;DESTINATION"
    images_data_arg = f"{IMAGES_DATA_PATH};{IMAGES_DEST_PATH}"
    esptool_data_arg = f"{ESPTOOL_DATA_PATH};{ESPTOOL_DEST_PATH}"

    # --- This is the new chained command ---
    # We quote the activate script path in case the project path has spaces.
    # The '&&' ensures 'flet pack' only runs if activation succeeds.
    flet_pack_command_string = (
        f'"{ACTIVATE_SCRIPT}" && '
        f'flet pack "{SCRIPT_FILE}" '
        f'--name "{APP_NAME}" '
        f'--icon "{ICON_FILE}" '
        f'--add-data "{images_data_arg}" '
        f'--add-data "{esptool_data_arg}"'
    )
    
    # Run the command
    run_command(flet_pack_command_string, "flet pack command failed.")

    # --- 4. Move final .exe to release/ ---
    print(f"--- 4. Moving executable to {RELEASE_DIR} ---")
    # flet pack puts the .exe in dist/
    source_exe_path = DIST_DIR / f"{APP_NAME}.exe"
    
    if not source_exe_path.exists():
        print("--- ERROR! ---")
        print(f"Expected executable not found at: {source_exe_path}")
        raise FileNotFoundError("'flet pack' did not create the executable.")
        
    shutil.move(source_exe_path, FINAL_PORTABLE_EXE)
    
    # --- 5. Success! ---
    print("\n" + "="*30)
    print("  SUCCESS!  ")
    print("="*30)
    print(f"Your portable app is ready at: {FINAL_PORTABLE_EXE.resolve()}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n--- BUILD FAILED! ---")
        print(f"An error occurred: {e}")
    finally:
        # --- 5. Final Cleanup ---
        cleanup()