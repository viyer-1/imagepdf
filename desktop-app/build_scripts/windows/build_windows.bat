@echo off
REM Build script for JPG2PDF Converter - Windows
REM This script creates a standalone executable and installer for Windows

echo ========================================
echo JPG2PDF Converter - Windows Build Script
echo ========================================
echo.

cd /d "%~dp0"
cd ..\..

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or later from https://python.org
    pause
    exit /b 1
)

REM Check if in virtual environment (optional but recommended)
echo Checking Python environment...
python -c "import sys; exit(0 if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) else 1)"
if errorlevel 1 (
    echo WARNING: Not running in a virtual environment
    echo It's recommended to use a virtual environment for building
    echo.
    REM Skip interactive prompt in CI environment
    if not defined CI (
        choice /C YN /M "Continue anyway?"
        if errorlevel 2 exit /b 1
    ) else (
        echo CI environment detected, continuing...
    )
)

REM Install/upgrade build dependencies
echo.
echo Installing build dependencies...
pip install --upgrade pip
pip install pyinstaller
pip install -r requirements.txt

if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)

REM Clean previous builds
echo.
echo Cleaning previous builds...
if exist "build" rmdir /s /q "build"
if exist "dist\JPG2PDF-Converter" rmdir /s /q "dist\JPG2PDF-Converter"
if exist "dist\JPG2PDF-Converter.exe" del /f /q "dist\JPG2PDF-Converter.exe"

REM Build with PyInstaller
echo.
echo Building executable with PyInstaller...
pyinstaller --clean build_scripts\windows\jpg2pdf.spec

if errorlevel 1 (
    echo ERROR: PyInstaller build failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Build completed successfully!
echo ========================================
echo.
echo Executable location: dist\JPG2PDF-Converter\JPG2PDF-Converter.exe
echo.
echo To create an installer, you need Inno Setup:
echo 1. Download from: https://jrsoftware.org/isdl.php
echo 2. Install Inno Setup
echo 3. Open build_scripts\windows\installer.iss in Inno Setup
echo 4. Click Build ^> Compile to create the installer
echo.
echo The installer will be created in: dist\windows\
echo.

REM Skip pause in CI environment
if not defined CI pause
