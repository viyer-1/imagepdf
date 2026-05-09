# Building with GitHub Actions (Cloud Builds)

**Perfect for Raspberry Pi users and developers without access to Windows/macOS/Linux x86 machines**

This guide explains how to use GitHub Actions to build executables for all platforms in the cloud, then download them to your local machine.

## Table of Contents
1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start](#quick-start)
4. [Workflow Details](#workflow-details)
5. [Downloading Builds](#downloading-builds)
6. [Automated Releases](#automated-releases)
7. [Troubleshooting](#troubleshooting)

---

## Overview

### What This Gives You

- ✅ **Build Windows executables** without a Windows PC
- ✅ **Build macOS DMG installers** without a Mac
- ✅ **Build Linux x86_64 packages** from ARM (Raspberry Pi)
- ✅ **Parallel builds** - all platforms build simultaneously
- ✅ **Automated releases** - create GitHub releases with one command
- ✅ **Free** - GitHub Actions provides free build minutes for public repos

---

## Prerequisites

### 1. GitHub Repository

Push your project to GitHub:

```bash
# If not already a git repo
cd imagepdf-oss
git init
git add .
git commit -m "Initial commit"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

### 2. Install GitHub CLI (for downloading builds)

Install the `gh` CLI for your platform to download artifacts easily.

---

## Quick Start

### Method 1: Manual Trigger (Recommended for Testing)

1. **Push your code to GitHub:**
   ```bash
   git add .
   git commit -m "Ready to build"
   git push
   ```

2. **Trigger the build manually:**
   - Go to your repository on GitHub
   - Click **Actions** tab
   - Click **Build Multi-Platform Executables** workflow
   - Click **Run workflow** button

3. **Wait for builds to complete** (~15-20 minutes).

4. **Download the builds:**
   ```bash
   cd desktop-app
   ./build_scripts/download_builds.sh latest
   ```

### Method 2: Create a Release (Recommended for Distribution)

This creates a GitHub Release with all platform builds attached:

```bash
# 1. Update version in config/app_config.json
# 2. Create and push a tag:
git tag v1.1.0-oss
git push origin v1.1.0-oss

# GitHub Actions will:
# - Build all platforms
# - Create a GitHub Release
# - Attach all executables to the release
# - Generate release notes automatically
```

Users can then download directly from: `https://github.com/YOUR_USERNAME/YOUR_REPO/releases`

---

## Workflow Details

### What Platforms Are Built

| Platform | Output Format | Build Time | File Size |
|----------|--------------|------------|-----------|
| **Windows** | `.exe` installer + portable `.exe` | ~8-12 min | 80-120 MB |
| **macOS** | `.dmg` disk image | ~10-15 min | 90-130 MB |
| **Linux x86_64** | `.AppImage` + `.tar.gz` | ~8-12 min | 100-140 MB |

**Note:** Linux ARM (Raspberry Pi) builds should still be done locally on your Pi using `./build_scripts/linux_arm/build_linux_arm.sh`.

### Build Process

Each platform build checks out your code, sets up Python 3.11, installs dependencies, runs the build script, and uploads artifacts. Tag-triggered builds also create a GitHub Release.

### Build Configuration

All builds read from `config/app_config.json`. To change branding or version, edit that file and push.

---

## Downloading Builds

### Download Latest Successful Build

```bash
cd desktop-app
./build_scripts/download_builds.sh latest
```

This downloads all platform executables to `dist/downloaded-builds-TIMESTAMP/`.

---

## Automated Releases

1. **Update version** in `config/app_config.json`.
2. **Commit and push** the change.
3. **Create and push tag** (e.g., `v1.1.0-oss`).
4. **GitHub Actions automatically** builds all platforms and creates a release.

---

## Troubleshooting

### Build Fails on GitHub Actions
Check the logs in the Actions tab. Ensure all dependencies are in `requirements.txt`.

### Download Script Issues
Ensure `gh` CLI is installed and configured.

---

## Summary (For Raspberry Pi users)

1. **Setup:** Install `gh` CLI.
2. **Release:** Tag your commit (`v1.x.x`) and push the tag.
3. **Download:** Run `./build_scripts/download_builds.sh latest` after ~20 minutes.

---

**Last Updated:** May 2026
