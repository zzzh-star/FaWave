@echo off
echo Building FaWave...

:: Check for PyInstaller
where pyinstaller >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo PyInstaller not found. Please install it using: pip install pyinstaller
    pause
    goto :eof
)

:: Check for Icon
if not exist "assets\app_icon.ico" (
    echo Generating app_icon.ico...
    python tools\generate_app_icon.py
    if %ERRORLEVEL% neq 0 (
        echo Warning: Failed to generate icon. Building without icon...
        set ICON_ARG=
    ) else (
        set ICON_ARG=--icon "assets/app_icon.ico"
    )
) else (
    set ICON_ARG=--icon "assets/app_icon.ico"
)

:: Run PyInstaller
pyinstaller --noconfirm --clean --windowed ^
  --name FaWave ^
  %ICON_ARG% ^
  --add-data "assets;assets" ^
  --add-data "config;config" ^
  --add-data "src/ui/themes;src/ui/themes" ^
  main.py

if %ERRORLEVEL% neq 0 (
    echo Build failed.
    pause
    goto :eof
)

echo Build complete. Check the dist\FaWave\ folder.
pause
