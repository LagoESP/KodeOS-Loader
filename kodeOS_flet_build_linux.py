#!/usr/bin/env python3
import os
import shutil
import subprocess
from pathlib import Path

# --- 0. Project Configuration ---
# Edit these variables based on your project
APP_NAME = "kodeOS-Loader"
SCRIPT_FILE = "kodeOS_flet.py"
ICON_FILE = "images/favicon.png"
VERSION = "1.0.0"
ARCH = "amd64" # "amd64" is for 64-bit (most common)

# TODO: Edit this line with your information!
MAINTAINER = "Jose Lago <jose@lago.dev>"

# --- -------------------------- ---

# Package and directory names
PKG_NAME_LOWER = APP_NAME.lower().replace("_", "-")
PKG_VERSION_NAME = f"{PKG_NAME_LOWER}_{VERSION}-1_{ARCH}"
RELEASE_DIR = Path.cwd() / "release"
PKG_DIR = Path.cwd() / PKG_VERSION_NAME
FINAL_DEB_FILE = RELEASE_DIR / f"{PKG_VERSION_NAME}.deb"

def run_command(command, error_message):
    """Executes a shell command and fails if there is an error."""
    try:
        print(f"-> Executing: {' '.join(command)}")
        # We capture output to avoid polluting the build log unless there's an error
        subprocess.run(command, check=True, text=True, capture_output=True, encoding='utf-8')
    except subprocess.CalledProcessError as e:
        print(f"--- ERROR! ---")
        print(f"{error_message}")
        print("STDOUT:", e.stdout)
        print("STDERR:", e.stderr)
        raise

def cleanup():
    """Cleans up all temporary build files and folders."""
    print("--- 8. Cleaning up intermediate files ---")
    shutil.rmtree("build", ignore_errors=True)
    shutil.rmtree("dist", ignore_errors=True)
    shutil.rmtree(PKG_DIR, ignore_errors=True)
    
    spec_file = Path.cwd() / f"{APP_NAME}.spec"
    if spec_file.exists():
        os.remove(spec_file)

def main():
    # Ensure we are in the correct directory
    os.chdir(Path(__file__).parent)

    print(f"Starting build for {APP_NAME} v{VERSION}...")

    # --- 1. Initial Cleanup ---
    print("--- 1. Cleaning up previous builds ---")
    cleanup()
    shutil.rmtree(RELEASE_DIR, ignore_errors=True)
    RELEASE_DIR.mkdir() # Create the release folder

    # --- 2. Create executable with PyInstaller ---
    print("--- 2. Creating executable with PyInstaller ---")
    pyinstaller_cmd = [
        "pyinstaller",
        "--onefile",
        f"--name={APP_NAME}",
        "--collect-data=esptool",
        "--add-data=images:images",
        SCRIPT_FILE
    ]
    run_command(pyinstaller_cmd, "PyInstaller failed.")

    # --- 3. Create .deb directory structure ---
    print("--- 3. Creating .deb directory structure ---")
    (PKG_DIR / "DEBIAN").mkdir(parents=True)
    (PKG_DIR / "usr/bin").mkdir(parents=True)
    (PKG_DIR / "usr/share/applications").mkdir(parents=True)
    (PKG_DIR / "usr/share/pixmaps").mkdir(parents=True)

    # --- 4. Create 'control' file (Package Metadata) ---
    print("--- 4. Creating 'control' file ---")
    
    # Flet dependencies for Ubuntu 22.04 (old) AND 24.04+ (new)
    flet_depends = "libwebkit2gtk-4.1-0 | libwebkit2gtk-4.0-37, libgstreamer1.0-0, libgstreamer-plugins-base1.0-0"
    
    control_content = f"""Package: {PKG_NAME_LOWER}
Version: {VERSION}-1
Architecture: {ARCH}
Maintainer: {MAINTAINER}
Description: A graphical loader for flashing kodeOS builds.
Depends: {flet_depends}

"""
    (PKG_DIR / "DEBIAN/control").write_text(control_content, encoding="utf-8")

    # --- 5. Create '.desktop' file (Menu Entry) ---
    print("--- 5. Creating '.desktop' file ---")
    desktop_content = f"""[Desktop Entry]
Name=kodeOS Loader
Comment=Graphical flasher for ESP32-S3
Exec=/usr/bin/{APP_NAME}
Icon={APP_NAME}
Terminal=false
Type=Application
Categories=Utility;Development;
StartupWMClass=flet
"""
    (PKG_DIR / f"usr/share/applications/{APP_NAME}.desktop").write_text(desktop_content, encoding="utf-8")

    # --- 6. Copy files ---
    print("--- 6. Copying build files ---")
    
    # Copy the executable
    shutil.copy2(
        Path.cwd() / "dist" / APP_NAME,
        PKG_DIR / "usr/bin/"
    )
    
    # Copy the icon (renaming it as expected by the .desktop file)
    shutil.copy2(
        Path.cwd() / ICON_FILE,
        PKG_DIR / f"usr/share/pixmaps/{APP_NAME}.png"
    )

    # --- 7. Build the .deb package ---
    print("--- 7. Building the .deb package ---")
    dpkg_cmd = [
        "dpkg-deb",
        "--build",
        "--root-owner-group",
        str(PKG_DIR)
    ]
    run_command(dpkg_cmd, "Failed to build the .deb package.")
    
    # Move the final .deb to the 'release' folder
    shutil.move(
        Path.cwd() / f"{PKG_VERSION_NAME}.deb",
        FINAL_DEB_FILE
    )

    print("\n" + "="*30)
    print("  SUCCESS!  ")
    print("="*30)
    print(f"Your package is ready at: {FINAL_DEB_FILE.resolve()}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n--- BUILD FAILED! ---")
        print(f"Error: {e}")
    finally:
        # --- 8. Final Cleanup ---
        cleanup()