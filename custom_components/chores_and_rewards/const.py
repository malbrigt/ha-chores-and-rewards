"""Constants for Chores and Rewards."""

DOMAIN = "chores_and_rewards"
NAME = "Chores and Rewards"

CONF_PIN = "pin"
CONF_PIN_CONFIRM = "pin_confirm"
CONF_PIN_HASH = "pin_hash"

PIN_MIN_LEN = 4
PIN_MAX_LEN = 8

DB_FILENAME = "chores_and_rewards.db"

# Fired on the HA bus / dispatcher after any data change (panel + sensors listen).
EVENT_UPDATED = f"{DOMAIN}_updated"
SIGNAL_UPDATED = f"{DOMAIN}_updated"

SYSTEM_USER = "system"

PANEL_URL = "chores-and-rewards"
PANEL_ELEMENT = "chores-and-rewards-panel"
PANEL_TITLE = "Gjøremål"  # custom panels can't translate the sidebar title (D36)
PANEL_ICON = "mdi:broom"
STATIC_URL = f"/{DOMAIN}_static"
