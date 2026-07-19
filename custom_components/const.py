"""Constants for the virtual_delay_cover integration."""

from typing import Final
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from .profile import MovementMode

DOMAIN = "virtual_delay_cover"

CONF_MOTOR_SWITCH: Final[str] = "motor_switch"
CONF_TIME_OPEN: Final[str] = "time_open"
CONF_TIME_CLOSE: Final[str] = "time_close"
CONF_PROFILE_MODE: Final[str] = "profile_mode"
CONF_CUSTOM_POINTS: Final[str] = "custom_points"

PLATFORM_SCHEMA: Final[vol.Schema] = cv.PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_MOTOR_SWITCH): cv.entity_id,
        vol.Required(CONF_TIME_OPEN): vol.Coerce(float),
        vol.Required(CONF_TIME_CLOSE): vol.Coerce(float),
        vol.Optional(CONF_PROFILE_MODE, default=MovementMode.LINEAR): vol.Coerce(
            MovementMode
        ),
        vol.Optional(CONF_CUSTOM_POINTS): vol.All(
            cv.ensure_list, [vol.ExactSequence([vol.Coerce(float), vol.Coerce(float)])]
        ),
    }
)
