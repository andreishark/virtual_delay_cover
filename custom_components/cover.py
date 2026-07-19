import logging
import math
import asyncio
import time
from .profile import MotorProfile, MovementMode
from homeassistant.components.cover import (
    CoverEntity,
    CoverEntityFeature,
    ATTR_POSITION,
)
from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import (
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING,
    CONF_ENTITY_ID,
    SERVICE_TURN_ON,
)
from homeassistant.helpers.event import async_track_time_interval
from datetime import timedelta
from .const import (
    DOMAIN,
    CONF_MOTOR_SWITCH,
    CONF_TIME_OPEN,
    CONF_TIME_CLOSE,
    CONF_PROFILE_MODE,
    CONF_CUSTOM_POINTS,
    PLATFORM_SCHEMA,
)

from typing import Any, Callable, Optional, Final, List, Tuple
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER: Final[logging.Logger] = logging.getLogger(DOMAIN)


async def async_setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    async_add_entities: Callable[[list[CoverEntity]], None],
    discovery_info: Optional[DiscoveryInfoType] = None,
):
    custom_raw: Optional[List[List[float]]] = config.get(CONF_CUSTOM_POINTS)
    processed_points: Optional[List[Tuple[float, float]]] = None

    if custom_raw:
        processed_points = [(float(pt[0]), float(pt[1])) for pt in custom_raw]

    async_add_entities(
        [
            CurveMotorCover(
                hass,
                str(config[CONF_MOTOR_SWITCH]),
                float(config[CONF_TIME_OPEN]),
                float(config[CONF_TIME_CLOSE]),
                str(config[CONF_PROFILE_MODE]),
                processed_points,
            )
        ]
    )


class CurveMotorCover(CoverEntity):
    """The Cover for the motor used"""

    def __init__(
        self,
        hass: HomeAssistant,
        motor_switch: str,
        time_open: float,
        time_close: float,
        profile_mode: MovementMode,
        custom_points: Optional[List[Tuple[float, float]]],
    ) -> None:
        self.hass = hass
        self._motor_switch: str = motor_switch
        self._time_open: float = time_open
        self._time_close: float = time_close

        self._profile: MotorProfile = MotorProfile(profile_mode, custom_points)

        self._state: str = STATE_CLOSED
        self._current_position: float = 0.0
        self._linear_time_tracker: float = 0.0
        self._next_direction: str = STATE_OPENING

        self._last_update_time: Optional[float] = None
        self._unsub_interval: Optional[Callable[[], None]] = None

    @property
    def name(self) -> str:
        return "Motor Virtual Cover"

    @property
    def is_closed(self) -> bool:
        return self._current_position <= 0.0

    @property
    def is_opening(self) -> bool:
        return self._state == STATE_OPENING

    @property
    def is_closing(self) -> bool:
        return self._state == STATE_CLOSING

    @property
    def current_cover_position(self) -> int:
        return int(round(self._current_position))

    @property
    def supported_features(self) -> CoverEntityFeature:
        return (
            CoverEntityFeature.OPEN | CoverEntityFeature.CLOSE | CoverEntityFeature.STOP
        )

    @property
    def assumed_state(self) -> bool:
        return True

    async def _fire_relay(self) -> None:
        await self.hass.services.async_call(
            SWITCH_DOMAIN,
            SERVICE_TURN_ON,
            {CONF_ENTITY_ID: self._motor_switch},
            blocking=True,
        )

    def _stop_engine(self) -> None:
        if self._unsub_interval:
            self._unsub_interval()
            self._unsub_interval = None

    async def _engine_tick(self) -> None:
        if self._last_update_time is None:
            self._last_update_time = time.time()
            return

        current_time: float = time.time()
        elapsed_time: float = current_time - self._last_update_time
        self._last_update_time = current_time

        if self._state == STATE_OPENING:
            self._linear_time_tracker += elapsed_time / self._time_open

            if self._linear_time_tracker >= 1.0:
                self._current_position = 100.0
                self._state = STATE_OPEN
                self._stop_engine()
            else:
                curved_progress: float = self._profile.calculate_position(
                    self._linear_time_tracker
                )
                self._current_position = curved_progress * 100.0

        elif self._state == STATE_CLOSING:
            self._linear_time_tracker -= elapsed_time / self._time_close

            if self._linear_time_tracker <= 0.0:
                self._current_position = 0.0
                self._state = STATE_CLOSED
                self._stop_engine()
            else:
                curved_progress: float = self._profile.calculate_position(
                    self._linear_time_tracker
                )
                self._current_position = curved_progress * 100.0

        self.async_write_ha_state()

    def _start_engine(self) -> None:
        self._stop_engine()
        self._last_update_time = time.time()

        self._linear_time_tracker = self._current_position / 100.0
        self._unsub_interval = async_track_time_interval(
            self.hass, self._engine_tick, timedelta(seconds=0.1)
        )

    async def async_stop_cover(self, **kwargs: Any) -> None:
        if self._state in [STATE_OPENING, STATE_CLOSING]:
            await self._fire_relay()
            self._stop_engine()

            if self._state == STATE_OPENING:
                self._next_direction = STATE_CLOSING
            else:
                self._next_direction = STATE_OPENING

            self._state = STATE_OPEN
            self.async_write_ha_state()

    async def async_open_cover(self, **kwargs: Any) -> None:
        if self._state in [STATE_OPENING, STATE_CLOSING]:
            await self.async_stop_cover()
            return
        if self._current_position >= 100.0:
            return

        await self._fire_relay()
        self._state = STATE_OPENING
        self._start_engine()

    async def async_close_cover(self, **kwargs: Any) -> None:
        if self._state in [STATE_OPENING, STATE_CLOSING]:
            await self.async_stop_cover()
            return
        if self._current_position <= 0.0:
            return

        await self._fire_relay()
        self._state = STATE_CLOSING
        self._start_engine()
