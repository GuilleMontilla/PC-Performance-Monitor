# PC-Performance-Monitor (IN PROGRESS)
A low-power performance monitoring system for Windows PCs using Python, LibreHardwareMonitor, Arduino and Windows API. This monitor reads real-time CPU, GPU, and memory metrics of your pc and displays them on a 0.96” OLED via serial communication, combining embedded development with desktop diagnostics.

The system consists of two main **modules**:

 - 🐍 ***Python Script:*** Collects real-time hardware metrics using Windows APIs and the LibreHardwareMonitor DLL, compacts the data, and sends it via serial communication to the Arduino.
 - 🔌 ***Arduino + OLED Display:*** Receives the compacted data through the serial port, parses it, and dynamically displays CPU, GPU, VRAM, and RAM information on a connected SSD1306 OLED screen.

✨ **Why This Matters:** 
This hardware-based monitor offers a fresh alternative to traditional software tools like MSI Afterburner, AMD Adrenalin Software, and even the Windows Task Manager. Unlike these software-only solutions, this project provides real-time performance metrics on a dedicated physical display, freeing up screen space, minimizes system resource usage and reducing on-screen distractions during gaming, benchmarking, or development sessions. It brings monitoring to the next level — external, visible, and minimalistic.

---

# Table of contents

  - [🛠 Technologies Used](#-technologies-used)
    - [🖥 Platform & Paradigm](#-platform--paradigm)
    - [⚙ Development Environment & Tools](#-development-environment--tools)
    - [📕 Libraries Used](#-libraries-used)
    - [📑 Project Architecture](#-project-architecture)
    - [🧠 Algorithms](#-algorithms)
  - [📐 Methology](#-methology)
  - [💾 Installation](#-installation)
  - [📝 How to Use it](#-how-to-use-it)
  - [📸 Example Output/Screenshots](#-example-outputscreenshots)
  - [🌐 Applications](#-applications)
  - [🚀 Future Improvements](#-future-improvements)
  - [📩 Contact](#-contact)
---
