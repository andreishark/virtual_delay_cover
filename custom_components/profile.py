from enum import StrEnum
from typing import List, Tuple
import bisect


class MovementMode(StrEnum):
    LINEAR = "linear"
    END_SLOWDOWN = "end_slowdown"
    CUSTOM = "custom"


class MotorProfile:
    """Handles the different time-position movements of the motor"""

    def __init__(
        self, mode: MovementMode, custom_points: List[Tuple[float, float]] = None
    ) -> None:
        self.mode: MovementMode = mode
        self._points: List[Tuple[float, float]] = []

        if mode == MovementMode.LINEAR:
            self._points = [(0.0, 0.0), (1.0, 1.0)]
        elif mode == MovementMode.END_SLOWDOWN:
            self._points = [
                (0.0, 0.0),
                (0.5, 0.55),
                (0.7, 0.78),
                (0.85, 0.92),
                (0.93, 0.97),
                (1.0, 1.0),
            ]
        elif mode == MovementMode.CUSTOM and custom_points:
            self._points = sorted(custom_points, key=lambda x: x[0])
            if self._points[0][0] > 0.0:
                self._points.insert(0, (0.0, 0.0))
            if self._points[-1][0] < 1.0:
                self._points.append((1.0, 1.0))

        else:
            self._points = [(0.0, 0.0), (1.0, 1.0)]

    def calculate_position(self, linear_progress: float) -> float:
        """Interpolates the points to match a linear progress indicator"""
        if linear_progress <= 0.0:
            return 0.0
        if linear_progress >= 1.0:
            return 1.0

        time_points: List[float] = [point[0] for point in self._points]
        idx: int = bisect.bisect_right(time_points, linear_progress)

        point_left: Tuple[float, float] = self._points[idx - 1]
        point_right: Tuple[float, float] = self._points[idx]

        time_delta: float = point_right[0] - point_left[0]
        if time_delta == 0.0:
            return point_left[1]

        local_time: float = (linear_progress - point_left[0]) / time_delta
        return point_left[1] + local_time * (point_right[1] - point_left[0])
