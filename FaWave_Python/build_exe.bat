@echo off
echo Building FaWave...
pyinstaller --onefile --windowed ^
  --name FaWave ^
  --add-data "assets;assets" ^
  --add-data "config;config" ^
  --add-data "src/ui/themes;src/ui/themes" ^
  main.py
echo Build complete. Check the dist/ folder.
pause