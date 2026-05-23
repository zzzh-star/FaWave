@echo off
echo Building FaWave...
pyinstaller --noconfirm --clean --windowed ^
  --name FaWave ^
  --icon "assets/app_icon.ico" ^
  --add-data "assets;assets" ^
  --add-data "config;config" ^
  --add-data "src/ui/themes;src/ui/themes" ^
  main.py
echo Build complete. Check the dist\FaWave\ folder.
pause
