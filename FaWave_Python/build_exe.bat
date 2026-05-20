@echo off
echo Building FaWave_Python...
pyinstaller --onefile --windowed --name FaWave_Python --add-data "config;config" --add-data "src/ui/style.qss;src/ui" main.py
echo Build complete. Check the dist/ folder.
pause