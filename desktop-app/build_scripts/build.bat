@echo off
REM Universal build script for JPG2PDF Converter - Windows wrapper
REM This is a simple wrapper that calls the Windows-specific build script

echo ============================================
echo JPG2PDF Converter - Universal Build Script
echo ============================================
echo.

cd /d "%~dp0\.."

echo Detected platform: Windows
echo.

set /p CONFIRM=Proceed with build? (y/n):
if /i not "%CONFIRM%"=="y" (
    echo Build cancelled
    exit /b 0
)

echo.
echo Starting Windows build...
echo.

call build_scripts\windows\build_windows.bat

echo.
echo ============================================
echo Build completed!
echo ============================================
echo.
