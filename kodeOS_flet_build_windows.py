#!/usr/bin/env python3
import os
import shutil
import subprocess
from pathlib import Path

# --- 0. Project Configuration ---
# Edit these variables to match your project
APP_NAME = "kodeOS-Loader"
SCRIPT_FILE = "kodeOS_flet.py"
# --- FIX: Point to the icon inside the images folder ---
ICON_FILE = "images/icon.ico" # Must be a .ico file for Windows
VERSION = "1.0.0"

# --- -------------------------- ---

# Internal script variables
RELEASE_DIR = Path.cwd() / "release"
DIST_DIR = Path.cwd() / "dist"
BUILD_DIR = Path.cwd() / "build"
FINAL_PORTABLE_EXE = RELEASE_DIR / f"{APP_NAME}-v{VERSION}-Portable.exe"


def run_command(command, error_message):
    """Executes a shell command and fails if there is an error."""
    try:
        print(f"-> Executing: {' '.join(command)}")
        subprocess.run(command, check=True, text=True, capture_output=True, encoding='utf-8')
    except FileNotFoundError:
        print("--- ERROR! ---")
        print(f"Command '{command[0]}' not found.")
        if command[0] == "pyinstaller":
            print("PyInstaller not found. Did you run 'pip install pyinstaller'?")
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
    
    spec_file = Path.cwd() / f"{APP_NAME}.spec"
    if spec_file.exists():
        os.remove(spec_file)

def main():
    os.chdir(Path(__file__).parent)
    print(f"Starting Windows portable build for {APP_NAME} v{VERSION}...")

    # --- 1. Initial Cleanup ---
    print("--- 1. Cleaning up previous builds ---")
    cleanup()
    shutil.rmtree(RELEASE_DIR, ignore_errors=True)
    RELEASE_DIR.mkdir()

    # --- 2. Create executable with PyInstaller ---
    print("--- 2. Creating portable executable with PyInstaller ---")
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",      # Bundle everything into one .exe
        "--noconsole",    # This hides the terminal (critical for GUI apps)
        f"--name={APP_NAME}",
        f"--icon={ICON_FILE}", # This now uses images/icon.ico
        "--collect-data=esptool",     # Bundle esptool's JSON stubs
        "--add-data=images;images", # Bundle images (use ';' on Windows)
        SCRIPT_FILE
    ]
    run_command(pyinstaller_cmd, "PyInstaller failed.")

    # --- 3. Move final .exe to release/ ---
    print(f"--- 3. Moving executable to {RELEASE_DIR} ---")
    source_exe_path = DIST_DIR / f"{APP_NAME}.exe"
    
    if not source_exe_path.exists():
        print("--- ERROR! ---")
        print(f"Expected executable not found at: {source_exe_path}")
        raise FileNotFoundError("PyInstaller did not create the executable.")
        
    shutil.move(source_exe_path, FINAL_PORTABLE_EXE)
    
    # --- 4. Success! ---
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
        # --- 4. Final Cleanup ---
        cleanup()