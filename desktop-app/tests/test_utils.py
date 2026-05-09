"""
Tests for utility modules.
"""

import pytest
from src.utils.config_manager import ConfigManager, get_config_manager


class TestConfigManager:
    """Test configuration manager."""

    def test_singleton(self):
        """Test config manager singleton."""
        manager1 = get_config_manager()
        manager2 = get_config_manager()

        assert manager1 is manager2

    def test_load_config(self):
        """Test loading configuration."""
        manager = ConfigManager()
        config = manager.load_config()

        assert isinstance(config, dict)
        assert "OPEN_SOURCE" in config

    def test_get_tier_limits(self):
        """Test getting unlocked limits."""
        manager = ConfigManager()
        limits = manager.get_tier_limits()

        assert isinstance(limits, dict)
        assert limits["max_files_per_conversion"] == -1
        assert "allowed_formats" in limits

    def test_can_use_feature(self):
        """Test feature access checking."""
        manager = ConfigManager()

        # All features should be available
        assert manager.can_use_feature("batch_processing") is True
        assert manager.can_use_feature("local_api") is True

    def test_get_max_files(self):
        """Test getting max files limit."""
        manager = ConfigManager()
        assert manager.get_max_files() == -1

    def test_get_allowed_formats(self):
        """Test getting allowed formats."""
        manager = ConfigManager()
        formats = manager.get_allowed_formats()
        assert "jpg" in formats
        assert "png" in formats
        assert "pdf" in formats

    def test_is_format_allowed(self):
        """Test format validation."""
        manager = ConfigManager()
        assert manager.is_format_allowed("jpg") is True
        assert manager.is_format_allowed("png") is True
        assert manager.is_format_allowed("webp") is True

    def test_get_max_file_size_mb(self):
        """Test getting max file size."""
        manager = ConfigManager()
        assert manager.get_max_file_size_mb() == -1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
