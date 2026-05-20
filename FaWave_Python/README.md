# FaWave Python

FaWave Force Acquisition System is a Python-based software for recording and visualizing 4-channel Ethernet-based force sensing data.

## Features
- Real-time plotting of 4-channel force data
- Support for TCP, UDP, and Mock communication modes
- Local data saving to CSV or XLSX format
- Configurable settings via JSON
- Modern, clean user interface

## Setup
1. Clone the repository.
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Running the Application
Run the main script:
```
python main.py
```

## Configuration
All communication, protocol, and UI parameters are defined in `config/default_config.json`. You can edit this file to configure default IPs, port numbers, communication modes, UI refresh rates, data offsets, and frame lengths.

## Build Executable
To package the application into a standalone executable (.exe), run:
```
build_exe.bat
```
The resulting executable will be generated in the `dist` folder.

## Modifying Protocol Parsing
If you need to adjust protocol structures (like endianness or offsets):
1. Adjust `float_endian` or `data_offset` in `config/default_config.json`.
2. For major logic modifications, edit `src/protocol/fawave_protocol.py`.

## Modifying UI Style
The visual style is stored in `src/ui/style.qss`. You can edit this file using QSS syntax (similar to CSS) to change colors, fonts, or element sizes.
