from functools import lru_cache

from sts.config.models import AppSettings


@lru_cache
def get_app_settings() -> AppSettings:
    """Get the cached application settings instance.

    Returns:
        The singleton AppSettings instance.
    """
    return AppSettings()
