"""Constants for the TP-Link Vigi integration."""

# Domain
DOMAIN = "tplink_vigi"

# Configuration
CONF_CAMERAS = "cameras"
CONF_CAMERA_ID = "camera_id"
CONF_WEBHOOK_ID = "webhook_id"
CONF_RESET_DELAY = "reset_delay"

# Default values
DEFAULT_RESET_DELAY = 1

# Validation limits
MIN_RESET_DELAY = 1
MAX_RESET_DELAY = 60

# Event types (adjust based on your camera's actual events)
EVENT_MOTION = "motion"
EVENT_PERSON = "person"
EVENT_VEHICLE = "vehicle"
EVENT_LINE_CROSSING = "line_crossing"
