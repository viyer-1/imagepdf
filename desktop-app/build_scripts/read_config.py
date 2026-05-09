#!/usr/bin/env python3
"""
Config Reader for Build Scripts
Reads branding and version info from config/app_config.json
Can be called from shell scripts or used to generate config files
"""

import json
import sys
from pathlib import Path


def get_project_root():
    """Get the project root directory"""
    return Path(__file__).parent.parent


def load_config():
    """Load the app config file"""
    config_path = get_project_root() / "config" / "app_config.json"
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def get_value(key_path):
    """
    Get a config value using dot notation
    Example: branding.app_name or version.full
    """
    config = load_config()
    keys = key_path.split(".")
    value = config
    for key in keys:
        value = value[key]
    return value


def print_all_values():
    """Print all config values in a shell-friendly format"""
    config = load_config()

    def flatten(d, prefix=""):
        for key, value in d.items():
            if key.startswith("_"):
                continue
            if isinstance(value, dict):
                flatten(value, f"{prefix}{key}.")
            else:
                print(f"{prefix}{key}={value}")

    flatten(config)


def generate_windows_iss():
    """Generate Inno Setup script header with config values"""
    config = load_config()
    branding = config["branding"]
    version = config["version"]
    build = config["build"]

    iss_header = f"""#define MyAppName "{branding["app_name"]}"
#define MyAppVersion "{version["full"]}"
#define MyAppPublisher "{branding["company_name"]}"
#define MyAppURL "{branding["company_website"]}"
#define MyAppExeName "{branding["app_name_executable"]}.exe"
#define AppId "{build["windows_installer_guid"]}"
#define UpgradeCode "{build["windows_upgrade_code"]}"
"""
    return iss_header


def generate_macos_plist():
    """Generate macOS plist info with config values"""
    config = load_config()
    branding = config["branding"]
    version = config["version"]
    build = config["build"]

    plist = {
        "CFBundleName": branding["app_name"],
        "CFBundleDisplayName": branding["app_name"],
        "CFBundleIdentifier": branding["bundle_identifier"],
        "CFBundleVersion": version["full"],
        "CFBundleShortVersionString": version["full"],
        "NSHighResolutionCapable": "True",
        "NSRequiresAquaSystemAppearance": "False",
        "LSMinimumSystemVersion": build["macos_min_version"],
        "NSHumanReadableCopyright": branding["copyright"],
    }
    return json.dumps(plist, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  read_config.py <key.path>     # Get single value")
        print("  read_config.py --all          # Print all values")
        print("  read_config.py --windows-iss  # Generate Windows ISS header")
        print("  read_config.py --macos-plist  # Generate macOS plist")
        print("\nExamples:")
        print("  read_config.py branding.app_name")
        print("  read_config.py version.full")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--all":
        print_all_values()
    elif arg == "--windows-iss":
        print(generate_windows_iss())
    elif arg == "--macos-plist":
        print(generate_macos_plist())
    else:
        try:
            print(get_value(arg))
        except KeyError:
            print(f"ERROR: Key '{arg}' not found in config", file=sys.stderr)
            sys.exit(1)
