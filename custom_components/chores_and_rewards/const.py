"""Constants for Chores and Rewards."""

DOMAIN = "chores_and_rewards"
NAME = "Chores and Rewards"

CONF_PIN = "pin"
CONF_PIN_CONFIRM = "pin_confirm"
CONF_PIN_HASH = "pin_hash"

PIN_MIN_LEN = 4
PIN_MAX_LEN = 8

DB_FILENAME = "chores_and_rewards.db"

# Dispatcher signal after any data change (panel subscriptions and sensors listen).
SIGNAL_UPDATED = f"{DOMAIN}_updated"

SYSTEM_USER = "system"

PANEL_URL = "chores-and-rewards"
PANEL_ELEMENT = "chores-and-rewards-panel"
# Custom panels can't translate the sidebar title, so it follows the HA system language (D36).
PANEL_TITLES = {"nb": "Gjøremål", "en": "Chores"}


def panel_title(language: str) -> str:
    """Sidebar title for HA's system language: Norwegian variants → nb, else en."""
    norwegian = any(language == p or language.startswith(f"{p}-") for p in ("nb", "nn", "no"))
    return PANEL_TITLES["nb" if norwegian else "en"]


PANEL_ICON = "mdi:broom"
STATIC_URL = f"/{DOMAIN}_static"
