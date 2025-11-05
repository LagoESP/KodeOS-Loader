# kodeOS Loader

<p align="center">
  <img src="images/logo.png" alt="kodeOS Logo" width="150"/>
</p>

<p align="center">
  A user-friendly Python GUI for flashing ESP32-S3 microcontrollers.
</p>

---

This tool provides a simple, clean interface for `esptool`, allowing you to flash and erase your ESP32-S3 device with ease. It's built with **Flet** for a modern, cross-platform, and multi-language UI.

## ✨ Key Features

* **🚀 Dual Flash Modes:** Flash standard firmware (to `0x0`) or a dedicated **Kode OS App** (to `0x400000`) with specific parameters.
* **🔥 Factory Erase:** A dedicated, safety-red button to completely `erase_flash` the device (with confirmation).
* **🌍 Multi-Language:** Toggle between English, Spanish, and German at runtime.
* **🔌 Smart Port Detection:** Automatically lists and filters for connected USB serial ports, with a refresh button.
* **📋 Live Log Output:** View the `esptool` output directly in the app's log window.
* **🎨 Modern UI:** A clean, responsive interface built with Flet.

## Application Versions

This repository contains two versions of the loader:

* **`kodeOS_flet.py` (Recommended):** The main, supported application built with **Flet**. This version is used for all official builds.
* **`kodeOS.py` (Legacy):** An older, stable alpha version built with **Tkinter**. This version is no longer actively developed or supported but remains functional.

---

## How to Run from Source (Flet Version)

To run the main application directly from the source code:

1.  **Clone the repository:**
    ```sh
    git clone [https://github.com/lagoesp/kodeos-loader.git](https://github.com/lagoesp/kodeos-loader.git)
    cd kodeos-loader
    ```

2.  **Create a virtual environment (Recommended):**
    *We recommend using the name `KodeOS-Loader` as it's required for the build scripts.*
    ```sh
    # For Windows
    python -m venv KodeOS-Loader
    .\KodeOS-Loader\Scripts\activate
    
    # For Linux/macOS
    python3 -m venv KodeOS-Loader
    source KodeOS-Loader/bin/activate
    ```

3.  **Install the required packages:**
    ```sh
    pip install -r requirements.txt
    ```

4.  **Run the application:**
    ```sh
    python3 kodeOS_flet.py
    ```

---

## How to Build from Source (For Developers)

This project is configured to be built into distributable packages for each OS.

### Build for Windows (Portable .exe)

This process uses `flet pack` and requires a **specifically named virtual environment** (`KodeOS-Loader`) to correctly find and bundle the `esptool` dependencies.

1.  **Clone the repository** (if not already done):
    ```sh
    git clone [https://github.com/lagoesp/kodeos-loader.git](https://github.com/lagoesp/kodeos-loader.git)
    cd kodeos-loader
    ```

2.  **Create a venv NAMED `KodeOS-Loader`:**
    *This name is **required** for the build script to find dependencies.*
    ```sh
    python -m venv KodeOS-Loader
    ```

3.  **Activate the venv and install dependencies:**
    ```sh
    .\KodeOS-Loader\Scripts\activate
    pip install -r requirements.txt
    ```

4.  **Run the build script:**
    This Python script automates the `flet pack` command with all the correct flags.
    ```sh
    python kodeOS_flet_build_windows.py
    ```

5.  **Get your package:**
    Your final portable `.exe` will be in the `release/` folder (e.g., `release/kodeOS-Loader-v1.0.0-Portable.exe`).

### Build for Linux (Ubuntu/Debian)

This process creates a `.deb` package that will install the app, add it to the application menu, and set the correct icon.

1.  **Install build tools:**
    ```sh
    pip install pyinstaller
    sudo apt-get install dpkg-dev
    ```

2.  **Run the build script:**
    ```sh
    python3 kodeOS_flet_build_linux.py
    ```

3.  **Get your package:**
    Your final distributable file will be in the `release/` folder (e.g., `release/kodeos-loader_1.0.0-1_amd64.deb`).

### Build for macOS (Placeholder)

*(Instructions to be added. This will involve a build script to create a `.dmg` file.)*

---

## How to Install (For End-Users)

### Windows

1.  Download the `...-Portable.exe` file from the [GitHub Releases](https://github.com/lagoesp/kodeos-loader/releases) page.
2.  Place the `.exe` file in any folder you like.
3.  Double-click to run. It's a portable application, so no installation is needed.

### Linux (Ubuntu/Debian)

1.  Download the `.deb` file from the [GitHub Releases](https://github.com/lagoesp/kodeos-loader/releases) page.
2.  Double-click the `.deb` file to open it in the Ubuntu Software Center and click "Install".
3.  Alternatively, use the terminal:
    ```sh
    # 1. Try to install the package
    sudo dpkg -i kodeos-loader_..._amd64.deb
    
    # 2. If you see dependency errors, run this command to fix them:
    sudo apt install -f
    ```
    The application will then be available in your application menu as "kodeOS Loader".

---
## Legacy (Tkinter) Version

To run the older, unsupported Tkinter version (`kodeOS.py`), you will need its specific dependencies (note the **lack of `flet`**):

```sh
pip install pyserial esptool Pillow