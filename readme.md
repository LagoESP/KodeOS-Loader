kodeOS Loader

<p align="center">
<img src="images/logo.png" alt="kodeOS Logo" width="150"/>
</p>

<p align="center">
A user-friendly Python GUI for flashing ESP32-S3 microcontrollers.
</p>

This tool provides a simple, clean interface for esptool, allowing you to flash and erase your ESP32-S3 device with ease. It's built with Flet for a modern, cross-platform, and multi-language UI.

✨ Key Features

🚀 Dual Flash Modes: Flash standard firmware (to 0x0) or a dedicated Kode OS App (to 0x400000) with specific parameters.

🔥 Factory Erase: A dedicated, safety-red button to completely erase_flash the device (with confirmation).

🌍 Multi-Language: Toggle between English, Spanish, and German at runtime.

🔌 Smart Port Detection: Automatically lists and filters for connected USB serial ports, with a refresh button.

📋 Live Log Output: View the esptool output directly in the app's log window.

🎨 Modern UI: A clean, responsive interface built with Flet.

Application Versions

This repository contains two versions of the loader:

kodeOS_flet.py (Recommended): The main, supported application built with Flet. This version is used for all official builds and includes multi-language support and a modern UI.

kodeOS.py (Legacy): An older, stable alpha version built with Tkinter. This version is no longer actively developed or supported but remains functional.

How to Run from Source (Flet Version)

To run the main application directly from the source code:

Clone the repository:

git clone [https://github.com/lagoesp/kodeos-loader.git](https://github.com/lagoesp/kodeos-loader.git)
cd kodeos-loader


Create a virtual environment (Recommended):

python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


Install the required packages:

pip install -r requirements.txt


Run the application:

python3 kodeOS_flet.py


How to Build the Executable

This project is configured to be built into distributable packages for each OS.

Build for Linux (Ubuntu/Debian)

This process creates a .deb package that will install the app, add it to the application menu, and set the correct icon.

Install build tools:
You need PyInstaller and the Debian packaging tools.

pip install pyinstaller
sudo apt-get install dpkg-dev


Run the build script:
The kodeOS_flet_build_linux.py script automates the entire process.

python3 kodeOS_flet_build_linux.py


Get your package:
Your final distributable file will be in the release/ folder (e.g., release/kodeos-loader_1.0.0-1_amd64.deb).

Build for Windows (Placeholder)

(Instructions to be added. This will involve a kodeOS_flet_build_windows.py script that uses PyInstaller to create a standalone .exe installer.)

Build for macOS (Placeholder)

(Instructions to be added. This will involve a build script to create a .dmg file.)

How to Install (For End-Users)

Linux (Ubuntu/Debian)

Download the .deb file from the GitHub Releases page.

Double-click the .deb file to open it in the Ubuntu Software Center and click "Install".

Alternatively, use the terminal:

# 1. Try to install the package
sudo dpkg -i kodeos-loader_..._amd64.deb

# 2. If you see dependency errors, run this command to fix them:
sudo apt install -f


The application will then be available in your application menu as "kodeOS Loader".

Legacy (Tkinter) Version

To run the older, unsupported Tkinter version (kodeOS.py), you will need its specific dependencies:

pip install pyserial esptool Pillow


Then run python3 kodeOS.py.