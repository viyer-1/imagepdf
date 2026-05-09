# Build Instructions for Image-PDF Converter

This guide covers building installers for distribution to end-users across all supported platforms: Windows, macOS, Linux x86_64, and Linux ARM (Raspberry Pi).

## ⚡ Quick Start: GitHub Actions (Recommended)

Build all platforms in the cloud without needing Windows/macOS/Linux x86 machines!

Perfect for Raspberry Pi users and developers without access to multiple platforms.

👉 **[See Complete GitHub Actions Guide](GITHUB_ACTIONS_BUILD.md)** 👈

**Quick summary:**
1. Push code to GitHub
2. Trigger build via Actions tab (or automatic on push/tag)
3. Download executables with: `./build_scripts/download_builds.sh latest`
4. All platforms built in parallel in ~15-20 minutes

**For traditional local builds**, continue reading below.

---

## Table of Contents
1. [Build Architecture Overview](#build-architecture-overview)
2. [Configuration Management](#configuration-management)
3. [Quick Start - Distribution Builds](#quick-start---distribution-builds)
4. [Platform-Specific Builds](#platform-specific-builds)
5. [Cross-Platform Build Orchestration](#cross-platform-build-orchestration)
6. [Distribution Formats](#distribution-formats)
7. [Troubleshooting](#troubleshooting)
8. [Advanced Configuration](#advanced-configuration)

---

## Build Architecture Overview

**Two Build Approaches:**

### 1. GitHub Actions (Recommended) ⭐
- **Build all platforms in the cloud**
- No need for Windows/macOS/Linux x86 hardware
- Automated, parallel builds
- Perfect for Raspberry Pi developers
- [Complete Guide →](GITHUB_ACTIONS_BUILD.md)

### 2. Local/Multi-Machine Builds (Traditional)
- **Build on actual hardware**
- Requires access to each target platform
- Faster if you have powerful local machines
- Full control over build environment
- Documented below

### Platform Build Matrix

| Platform | GitHub Actions | Local Build | Cross-Compile |
|----------|---------------|-------------|---------------|
| **Linux ARM** | ❌ (build locally) | ✓ Raspberry Pi | ✓ Native |
| **Linux x86_64** | ✅ Automatic | x86 Linux | via Docker (slow) |
| **macOS** | ✅ Automatic | macOS only | ✗ No |
| **Windows** | ✅ Automatic | Windows only | ✗ No |

**Recommended Strategy:**
- Use **GitHub Actions** for Windows, macOS, and Linux x86_64
- Build **Linux ARM locally** on your Raspberry Pi
- Combine artifacts for complete distribution

---

## Configuration Management

### Single Source of Truth: `config/app_config.json`

All branding, product names, company information, and versioning is centralized in this file:

```json
{
  "branding": {
    "app_name": "Image ↔ PDF Converter",
    "app_name_short": "Image-PDF",
    "app_name_executable": "Image-PDF-Converter",
    "company_name": "Image-PDF Open Source",
    "company_website": "https://github.com/viyer-1/imagepdf",
    "support_email": "github-issues@imagepdf.oss",
    "bundle_identifier": "org.imagepdf.converter",
    "copyright": "Copyright © 2026 Image-PDF Open Source Project"
  },
  "version": {
    "major": 1,
    "minor": 1,
    "patch": 0,
    "full": "1.1.0-oss"
  }
}
```

### How Build Scripts Use Config

All build scripts automatically read from `app_config.json`:

```bash
# Extract values in shell scripts
APP_NAME=$(python3 build_scripts/read_config.py branding.app_name)
VERSION=$(python3 build_scripts/read_config.py version.full)
```

**To rebrand the entire application:**
1. Edit `config/app_config.json`
2. Run builds - all files will use new values automatically
3. No need to search/replace across multiple files

### Config Reader Utility

Located at [`build_scripts/read_config.py`](build_scripts/read_config.py), this script provides:

- **CLI tool**: Extract single values for shell scripts
- **Generators**: Create platform-specific config files
- **Validation**: Ensure consistent branding across platforms

```bash
# Examples
python3 build_scripts/read_config.py branding.app_name
python3 build_scripts/read_config.py --all
python3 build_scripts/read_config.py --windows-iss
python3 build_scripts/read_config.py --macos-plist
```

---

## Pre-Build Checklist

**Before building for production distribution:**

### 1. Update Version
Edit `config/app_config.json`:
```json
{
  "version": {
    "major": 1,
    "minor": 1,
    "patch": 0,
    "full": "1.1.0-oss"
  }
}
```

### 2. Update CHANGELOG.md
Document what's new in this release.

---

## Quick Start - Distribution Builds

### Option 1: GitHub Actions Cloud Build ⭐ (Recommended)

Build all platforms without needing multiple machines:

```bash
# One-time setup
git push origin main  # Push to GitHub

# For each release
git tag v1.1.0-oss && git push origin v1.1.0-oss  # Create release
# Wait ~15-20 minutes for builds
./build_scripts/download_builds.sh latest  # Download all executables
```

See [GITHUB_ACTIONS_BUILD.md](GITHUB_ACTIONS_BUILD.md) for complete guide.

### Option 2: Local Automated Build

Use the distribution orchestrator to build all compatible platforms:

```bash
cd desktop-app
chmod +x build_scripts/build_for_distribution.sh
./build_scripts/build_for_distribution.sh
```

### Option 3: Build Single Platform

For testing or platform-specific builds:

**Linux/macOS:**
```bash
cd desktop-app
chmod +x build_scripts/build.sh
./build_scripts/build.sh
```

**Windows:**
```batch
cd desktop-app
build_scripts\build.bat
```

---

## Platform-Specific Builds

### Linux ARM (Raspberry Pi) - Native Build

**Build Process:**
```bash
cd desktop-app
chmod +x build_scripts/linux_arm/build_linux_arm.sh
./build_scripts/linux_arm/build_linux_arm.sh
```

---

### Linux x86_64 - Requires x86 Machine

**Build on x86 Linux machine:**
```bash
cd desktop-app
chmod +x build_scripts/linux_x86/build_linux_x86.sh
./build_scripts/linux_x86/build_linux_x86.sh
```

---

### macOS - Requires Mac Hardware

**Build Process:**
```bash
cd desktop-app
chmod +x build_scripts/macos/build_macos.sh
./build_scripts/macos/build_macos.sh
```

---

### Windows - Requires Windows Machine

**Build Process:**
```batch
cd desktop-app
build_scripts\windows\build_windows.bat
```

---

## Distribution Formats

| Platform | Primary Format | Alternative | Installation |
|----------|---------------|-------------|-------------|
| **Windows** | `.exe` installer | Portable `.exe` | Run installer |
| **macOS** | `.dmg` | `.app` bundle | Drag to Applications |
| **Linux x86** | `.AppImage` | `.tar.gz` | Make executable & run |
| **Linux ARM** | `.AppImage` | `.tar.gz` | Make executable & run |

---

## Troubleshooting

### Common Issues

#### "Config value not found" error
**Cause**: `app_config.json` is missing or malformed
**Solution:** Validate JSON syntax with `python3 -m json.tool config/app_config.json`.

#### macOS: "App is damaged and can't be opened"
**Solution:** Remove quarantine attribute: `xattr -cr "dist/Image ↔ PDF Converter.app"`

---

## Support & Documentation

**Build script files:**
- `build_scripts/build_for_distribution.sh` - Cross-platform orchestrator
- `build_scripts/read_config.py` - Config reader utility
- `build_scripts/windows/build_windows.bat` - Windows build
- `build_scripts/macos/build_macos.sh` - macOS build
- `build_scripts/linux_x86/build_linux_x86.sh` - Linux x86 build
- `build_scripts/linux_arm/build_linux_arm.sh` - Linux ARM build

**Config files:**
- `config/app_config.json` - **Master config** for all branding/versioning
- `build_scripts/windows/installer.iss` - Inno Setup script (reads from config)
- `build_scripts/*/jpg2pdf*.spec` - PyInstaller specs (read from config)

---

**Last Updated:** May 2026
**Product Version:** 1.1.0-oss
**Build System:** Config-driven multi-platform distribution
