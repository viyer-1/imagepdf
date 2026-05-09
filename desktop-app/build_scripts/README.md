# Build Scripts for JPG2PDF Converter

This directory contains automated build scripts for creating distributable packages across all supported platforms.

## Quick Start

### Universal Build (Recommended)
Run the build script for your current platform:

**Linux/macOS:**
```bash
chmod +x build.sh
./build.sh
```

**Windows:**
```batch
build.bat
```

The script automatically detects your platform and runs the appropriate build process.

## Directory Structure

```
build_scripts/
├── build.sh                    # Universal build script (Linux/macOS)
├── build.bat                   # Universal build script (Windows)
├── BUILD_INSTRUCTIONS.md       # Comprehensive build documentation
├── README.md                   # This file
├── windows/
│   ├── build_windows.bat       # Windows-specific build script
│   ├── jpg2pdf.spec           # PyInstaller specification for Windows
│   └── installer.iss          # Inno Setup script for .exe installer
├── macos/
│   ├── build_macos.sh         # macOS-specific build script
│   └── jpg2pdf_macos.spec     # PyInstaller specification for macOS
├── linux_x86/
│   └── build_linux_x86.sh     # Linux x86_64 build script (AppImage + tar.gz)
└── linux_arm/
    └── build_linux_arm.sh     # Linux ARM/Raspberry Pi build script
```

## Supported Platforms

| Platform | Output Format | Build Location |
|----------|--------------|----------------|
| Windows 10/11 | `.exe` + Inno Setup installer | `dist/windows/` |
| macOS 10.13+ | `.app` + `.dmg` | `dist/macos/` |
| Linux x86_64 | `.AppImage` + `.tar.gz` | `dist/linux_x86/` |
| Linux ARM (RPi) | `.AppImage` + `.tar.gz` | `dist/linux_arm/` |

## Platform-Specific Builds

If you need to run platform-specific builds directly:

### Windows
```batch
cd build_scripts\windows
build_windows.bat
```

### macOS
```bash
cd build_scripts/macos
chmod +x build_macos.sh
./build_macos.sh
```

### Linux x86_64
```bash
cd build_scripts/linux_x86
chmod +x build_linux_x86.sh
./build_linux_x86.sh
```

### Linux ARM (Raspberry Pi)
```bash
cd build_scripts/linux_arm
chmod +x build_linux_arm.sh
./build_linux_arm.sh
```

## Prerequisites

All builds require:
- Python 3.8 or later
- pip (Python package installer)
- Dependencies from `requirements.txt`

Platform-specific requirements are listed in `BUILD_INSTRUCTIONS.md`.

## Distribution Formats Explained

### Windows
- **Standalone executable**: Users can run the app without installation
- **Inno Setup installer**: Professional installer with Start Menu shortcuts and uninstall support

### macOS
- **.app bundle**: Standard macOS application
- **.dmg installer**: Drag-and-drop installer for easy distribution

### Linux
- **AppImage**: Single-file executable that works across distributions (recommended for users)
- **tar.gz**: Portable archive for advanced users or custom installations

## First-Time Build Tips

1. **Use a virtual environment** (recommended):
   ```bash
   python3 -m venv build-env
   source build-env/bin/activate  # Linux/macOS
   build-env\Scripts\activate      # Windows
   ```

2. **Install build dependencies**:
   ```bash
   pip install -r requirements.txt
   pip install pyinstaller
   ```

3. **Sign the configuration file** (required for production):
   ```bash
   python build_scripts/sign_config.py
   ```

   See [BUILD_INSTRUCTIONS.md - Pre-Build Checklist](BUILD_INSTRUCTIONS.md#pre-build-checklist) for details.

4. **Run the build**:
   ```bash
   ./build_scripts/build.sh  # Linux/macOS
   build_scripts\build.bat   # Windows
   ```

5. **Find your distribution**:
   Check the `dist/` directory for platform-specific subdirectories

## Customization

Before building for production:

1. **Update version numbers**: Edit the version in each build script
2. **Company information**: Update in `installer.iss` (Windows) and spec files
3. **Application icon**: Replace `assets/icon.png` with your custom icon
4. **Bundle identifier**: Update in `jpg2pdf_macos.spec` (macOS)

See `BUILD_INSTRUCTIONS.md` for detailed customization options.

## Common Issues

### Scripts not executable (Linux/macOS)
```bash
chmod +x build_scripts/**/*.sh
```

### Missing Python modules
```bash
pip install -r requirements.txt
pip install pyinstaller
```

### Build fails on clean system
Install platform-specific build tools:
- **Windows**: Visual C++ Redistributable
- **macOS**: Xcode Command Line Tools (`xcode-select --install`)
- **Linux**: `sudo apt-get install build-essential`

For more troubleshooting, see `BUILD_INSTRUCTIONS.md`.

## Complete Documentation

For comprehensive build instructions, troubleshooting, and advanced configuration, see:
- **[BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md)** - Complete build guide

## Build Output

All builds create files in the `dist/` directory:

```
dist/
├── windows/
│   └── JPG2PDF-Converter-Setup-1.0.0-Windows.exe
├── macos/
│   └── JPG2PDF-Converter-1.0.0-macOS.dmg
├── linux_x86/
│   ├── JPG2PDF-Converter-1.0.0-x86_64.AppImage
│   └── JPG2PDF-Converter-1.0.0-linux-x86_64.tar.gz
└── linux_arm/
    ├── JPG2PDF-Converter-1.0.0-aarch64.AppImage
    └── JPG2PDF-Converter-1.0.0-linux-aarch64.tar.gz
```

## Testing Builds

After building, test on a clean system (VM or different computer) to ensure:
- All dependencies are bundled correctly
- The application launches successfully
- All features work as expected
- File conversions complete properly

## Next Steps

After successful builds:
1. Test each platform's distribution
2. Create checksums for verification (`sha256sum` on Linux/macOS)
3. Sign executables (Windows code signing, macOS notarization)
4. Upload to distribution platform
5. Update download links and documentation

---

**For detailed instructions, see [BUILD_INSTRUCTIONS.md](BUILD_INSTRUCTIONS.md)**
