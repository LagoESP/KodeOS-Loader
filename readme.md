# kodeOS Loader

<p align="center">
  <img src="images/logo.png" alt="kodeOS Logo" width="150"/>
</p>

<p align="center">
  A user-friendly Python GUI for flashing ESP32-S3 microcontrollers.
</p>

---

*This tool provides a simple, clean interface for `esptool`, allowing you to flash and erase your ESP32-S3 device with ease. It's built with Tkinter and features multi-language support and specialized flash modes.*

## ✨ Key Features

* **🚀 Dual Flash Modes:** Flash standard firmware (to `0x0`) or a dedicated **Kode OS App** (to `0x400000`) with specific parameters.
* **🔥 Factory Erase:** A dedicated, safety-red button to completely `erase_flash` on the device (with confirmation).
* **🌍 Multi-Language:** Toggle between English and Spanish at runtime.
* **🔌 Smart Port Detection:** Automatically lists and filters for connected USB serial ports.
* **📋 Live Log Output:** View the `esptool` output directly in the app's log window.
* **🎨 Custom UI:** A modern interface built with custom Tkinter widgets.

---

## 🔧 Installation

1.  **Clone the repository:**
    ```sh
    git clone [YOUR_REPOSITORY_URL]
    cd [YOUR_REPOSITORY_FOLDER]
    ```

2.  **Create a virtual environment (Recommended):**
    ```sh
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install the required packages:**
    ```sh
    pip install -r requirements.txt
    ```

---

## 🚀 How to Use

1.  **Run the application:**
    ```sh
    python3 kodeos_loader.py
    ```

2.  **Connect your ESP32-S3** and select its port from the **Serial Port** dropdown.
    * Click **Refresh** if it doesn't appear.

3.  Click **Browse** to select your firmware `.bin` file.

4.  **Choose your flash mode:**
    * **Standard Flash:** Leave the "Flash Kode OS App" box **unchecked**. This will flash your firmware to the default address (`0x0`).
    * **Kode OS App Flash:** **Check** the "Flash Kode OS App" box. This will flash your firmware to the application address (`0x400000`) using the required `80m` / `dio` / `32MB` parameters.

5.  Click **Flash** to begin.

### To Erase the Device

1.  Select the correct **Serial Port**.
2.  Click the red **Erase** button.
3.  Confirm the action in the popup dialog.

---

## 📦 Requirements

This script requires the following Python packages, as listed in `requirements.txt`:

```txt
pyserial
esptool>=5.0.2
Pillow>10.0.0