"""
Configuration manager for loading and managing application settings.

Open-Source Version: All features are unlocked by default. Tier-based limits
and cryptographic signature verification have been removed.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigManager:
    """Manages application configuration with all features unlocked."""

    def __init__(self):
        self._config: Optional[Dict[str, Any]] = None
        self._app_config: Optional[Dict[str, Any]] = None
        self._app_config_path = Path(__file__).parent.parent.parent / "config" / "app_config.json"

    def _log(self):
        """Lazy import of logger to avoid circular imports."""
        from .logger import get_logger
        return get_logger()

    def load_config(self) -> Dict[str, Any]:
        """
        Returns the unlocked configuration for the open-source version.
        """
        if self._config is not None:
            return self._config

        self._config = {
            "OPEN_SOURCE": {
                "max_files_per_conversion": -1,  # Unlimited
                "max_file_size_mb": -1,          # Unlimited
                "allowed_formats": ["jpg", "jpeg", "png", "tiff", "tif", "bmp", "webp", "pdf"],
                "features": {
                    "basic_conversion": True,
                    "batch_processing": True,
                    "selective_page_extraction": True,
                    "custom_page_sizes": True,
                    "local_api": True,
                    "metadata_stripping": True
                },
                "conversions_per_day": -1,       # Unlimited
                "badge_color": "#2ecc71"         # Green for Open Source
            }
        }
        return self._config

    def get_tier_limits(self) -> Dict[str, Any]:
        """Always returns the unlocked configuration."""
        config = self.load_config()
        return config["OPEN_SOURCE"]

    def can_use_feature(self, feature_name: str) -> bool:
        """All features are available in the open-source version."""
        return True

    def get_max_files(self) -> int:
        """Returns -1 for unlimited files."""
        return -1

    def get_allowed_formats(self) -> list:
        """Returns all supported formats."""
        return ["jpg", "jpeg", "png", "tiff", "tif", "bmp", "webp", "pdf"]

    def is_format_allowed(self, file_extension: str) -> bool:
        """All supported formats are allowed."""
        return file_extension.lower() in self.get_allowed_formats()

    def get_max_file_size_mb(self) -> int:
        """Returns -1 for unlimited file size."""
        return -1

    def reload_config(self):
        """Reloads configuration."""
        self._config = None
        self._app_config = None
        return self.load_config()

    def load_app_config(self) -> Dict[str, Any]:
        """Load application display settings and branding."""
        if self._app_config is not None:
            return self._app_config

        try:
            with open(self._app_config_path) as f:
                self._app_config = json.load(f)
            return self._app_config
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self._log().warning(f"App config error: {e}, using defaults")
            return self._get_default_app_config()

    def get_app_setting(self, *keys: str, default: Any = None) -> Any:
        """Get application setting by nested keys."""
        config = self.load_app_config()
        value = config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def _get_default_app_config(self) -> Dict[str, Any]:
        """Get hardcoded default app configuration."""
        return {
            "app_name": "Image ↔ PDF Converter",
            "app_name_short": "Image-PDF",
            "company_name": "Image-PDF Open Source",
            "version": "1.1.0-oss",
            "window": {"start_maximized": True, "min_width": 1000, "min_height": 700},
            "ui": {
                "thumbnail_size": 150,
                "thumbnail_quality": 85,
                "control_pane_width": 350,
                "control_pane_position": "right",
            },
        }


# Singleton instance
_config_manager_instance = None


def get_config_manager() -> ConfigManager:
    """Get singleton instance of ConfigManager."""
    global _config_manager_instance
    if _config_manager_instance is None:
        _config_manager_instance = ConfigManager()
    return _config_manager_instance
