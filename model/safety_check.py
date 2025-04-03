from __future__ import annotations

from bpy.props import BoolProperty, EnumProperty, FloatProperty, StringProperty
from bpy.types import Context, PropertyGroup
from typing import Optional, List, Sequence, Tuple, overload, TYPE_CHECKING

from sbstudio.model.safety_check import SafetyCheckResult
from sbstudio.model.types import Coordinate3D

if TYPE_CHECKING:
    from sbstudio.plugin.overlays.safety_check import SafetyCheckOverlay, Marker

__all__ = ("SafetyCheckProperties",)




_overlay = None



_safety_check_result = SafetyCheckResult()


@overload
def get_overlay() -> SafetyCheckOverlay: ...


@overload
def get_overlay(create: bool) -> Optional[SafetyCheckOverlay]: ...


def get_overlay(create: bool = True):
    global _overlay

    if _overlay is None and create:
        
        from sbstudio.plugin.overlays.safety_check import SafetyCheckOverlay

        _overlay = SafetyCheckOverlay()

    return _overlay


def altitude_warning_enabled_updated(self, context: Optional[Context] = None):
    
    self.ensure_overlays_enabled_if_needed()
    self._refresh_overlay()


def altitude_warning_threshold_updated(self, context: Optional[Context] = None):
    
    self._refresh_overlay()


def proximity_warning_enabled_updated(self, context: Optional[Context] = None):
    
    self.ensure_overlays_enabled_if_needed()
    self._refresh_overlay()


def proximity_warning_target_updated(self, context: Optional[Context] = None):
    self._refresh_overlay()


def proximity_warning_threshold_updated(self, context: Optional[Context] = None):
    self._refresh_overlay()


def velocity_warning_enabled_updated(self, context: Optional[Context] = None):
    
    self.ensure_overlays_enabled_if_needed()
    self._refresh_overlay()


def velocity_warning_threshold_updated(self, context: Optional[Context] = None):
    self._refresh_overlay()


def acceleration_warning_enabled_updated(self, context: Optional[Context] = None):
    self.ensure_overlays_enabled_if_needed()
    self._refresh_overlay()


def acceleration_warning_threshold_updated(self, context: Optional[Context] = None):
    self._refresh_overlay()


class SafetyCheckProperties(PropertyGroup):
    

    formation_status = StringProperty(
        name="Formation status",
        description="The string representation of the formation status at the given frame",
        default="",
    )

    enabled = BoolProperty(
        name="Enable safety checks",
        description=(
            "Enables real-time safety checks that compare the altitudes, distances and "
            "velocities of drones with a safety threshold in every frame. Turn this off "
            "if performance suffers during playback"
        ),
        default=True,
    )

    min_distance = FloatProperty(
        name="Min distance",
        description="Minimum distance along all possible pairs of drones in the current frame, calculated between their centers of mass",
        unit="LENGTH",
        default=0.0,
    )

    min_altitude = FloatProperty(
        name="Min altitude",
        description="Minimum altitude of all drones in the current frame",
        unit="LENGTH",
        default=0.0,
    )

    max_altitude = FloatProperty(
        name="Max altitude",
        description="Maximum altitude of all drones in the current frame",
        unit="LENGTH",
        default=0.0,
    )

    max_velocity_xy = FloatProperty(
        name="Max XY velocity",
        description="Maximum horizontal velocity of all drones in the current frame",
        unit="VELOCITY",
        default=0.0,
    )

    max_velocity_z_up = FloatProperty(
        name="Max Z velocity up",
        description="Maximum vertical velocity of all drones in the current frame upwards",
        unit="VELOCITY",
        default=0.0,
    )

    max_velocity_z_down = FloatProperty(
        name="Max Z velocity down",
        description="Maximum vertical velocity of all drones in the current frame downwards",
        unit="VELOCITY",
        default=0.0,
    )

    max_acceleration = FloatProperty(
        name="Max acceleration",
        description="Maximum acceleration of all drones in the current frame",
        unit="ACCELERATION",
        default=0.0,
    )

    proximity_warning_enabled = BoolProperty(
        name="Show proximity warnings",
        description=(
            "Specifies whether Blender should show a warning in this panel when"
            " the minimum distance is less than the proximity warning threshold"
        ),
        update=proximity_warning_enabled_updated,
        default=True,
    )

    proximity_warning_threshold = FloatProperty(
        name="Proximity warning threshold",
        description="Minimum allowed distance between drones without triggering a proximity warning",
        unit="LENGTH",
        default=3.0,
        min=0.0,
        soft_min=0.0,
        soft_max=10.0,
        update=proximity_warning_threshold_updated,
    )

    altitude_warning_enabled = BoolProperty(
        name="Show altitude warnings",
        description=(
            "Specifies whether Blender should show a warning when the altitude of a "
            "drone is larger than the altitude warning threshold"
        ),
        update=altitude_warning_enabled_updated,
        default=True,
    )

    altitude_warning_threshold = FloatProperty(
        name="Altitude warning threshold",
        description="Maximum allowed altitude for a single drone without triggering an altitude warning",
        unit="LENGTH",
        default=150.0,
        min=0.0,
        soft_min=0.0,
        soft_max=1000.0,
        update=altitude_warning_threshold_updated,
    )

    velocity_warning_enabled = BoolProperty(
        name="Show velocity warnings",
        description=(
            "Specifies whether Blender should show a warning when the velocity of a "
            "drone is larger than the velocity warning threshold"
        ),
        update=velocity_warning_enabled_updated,
        default=True,
    )

    acceleration_warning_enabled = BoolProperty(
        name="Show acceleration warnings",
        description=(
            "Specifies whether Blender should show a warning when the acceleration of a "
            "drone is larger than the acceleration warning threshold"
        ),
        update=acceleration_warning_enabled_updated,
        default=True,
    )

    velocity_xy_warning_threshold = FloatProperty(
        name="Maximum XY velocity",
        description="Maximum velocity allowed in the horizontal plane",
        default=10,
        min=1,
        soft_min=1,
        soft_max=10,
        unit="VELOCITY",
        update=velocity_warning_threshold_updated,
    )

    velocity_z_warning_threshold = FloatProperty(
        name="Maximum Z velocity",
        description="Maximum velocity allowed in the vertical direction",
        default=2,
        min=0,
        soft_min=0.1,
        soft_max=5,
        unit="VELOCITY",
        update=velocity_warning_threshold_updated,
    )

    velocity_z_warning_different_up = BoolProperty(
        name="Use separate Z velocity threshold upwards",
        description=(
            "When checked, the velocity threshold in the Z direction is allowed "
            "to be different upwards and downwards"
        ),
        update=velocity_warning_enabled_updated,
        default=False,
    )

    velocity_z_warning_threshold_up = FloatProperty(
        name="Maximum Z velocity (up)",
        description="Maximum velocity allowed upwards in the vertical direction",
        default=2,
        min=0,
        soft_min=0.1,
        soft_max=5,
        unit="VELOCITY",
        update=velocity_warning_threshold_updated,
    )

    acceleration_warning_threshold = FloatProperty(
        name="Maximum acceleration",
        description="Maximum acceleration allowed",
        default=4,
        min=0.1,
        soft_min=0.1,
        soft_max=10,
        unit="ACCELERATION",
        update=acceleration_warning_threshold_updated,
    )

    min_navigation_altitude = FloatProperty(
        name="Minimum navigation altitude",
        description="Altitude below which drones are not allowed to move sideways",
        unit="LENGTH",
        default=2.5,
        min=0.0,
        soft_min=0.0,
        soft_max=1000.0,
        update=altitude_warning_threshold_updated,
    )

    proximity_warning_target = EnumProperty(
        items=[
            ("ALL", "All drones", "All drones", 1),
            (
                "ABOVE_MIN_NAV_ALT",
                "Drones above min altitude",
                "Drones above minimum navigation altitude only",
                2,
            ),
        ],
        default="ABOVE_MIN_NAV_ALT",
        name="Check distances for",
        description="Selects the set of drones to calculate distances for in a single frame",
        update=proximity_warning_target_updated,
    )

    @property
    def effective_velocity_z_threshold_up(self) -> float:
        
        if self.velocity_z_warning_different_up:
            return self.velocity_z_warning_threshold_up
        else:
            return self.velocity_z_warning_threshold

    @property
    def effective_velocity_z_threshold_down(self) -> float:
        
        return self.velocity_z_warning_threshold

    @property
    def min_distance_is_valid(self) -> bool:
        
        
        
        return self.min_distance > 0 and self.min_distance < 100000

    @property
    def min_navigation_altitude_is_valid(self) -> bool:
        
        return self.min_navigation_altitude > 0

    @property
    def max_altitude_is_valid(self) -> bool:
        
        return self.max_altitude > 0

    @property
    def max_velocities_are_valid(self) -> bool:
        
        return (
            self.max_velocity_xy > 0
            or self.max_velocity_z_up > 0
            or self.max_velocity_z_down > 0
        )

    @property
    def max_acceleration_is_valid(self) -> bool:
        
        return self.max_acceleration > 0

    @property
    def should_show_altitude_warning(self) -> bool:
        
        return (
            self.altitude_warning_enabled
            and self.max_altitude_is_valid
            and self.min_navigation_altitude_is_valid
            and (
                self.max_altitude > self.altitude_warning_threshold
                or self.min_altitude < self.min_navigation_altitude
            )
        )

    @property
    def should_show_proximity_warning(self) -> bool:
        
        
        
        
        return (
            self.proximity_warning_enabled
            and self.min_distance_is_valid
            and self.min_distance + 1e-2 < self.proximity_warning_threshold
        )

    @property
    def should_show_velocity_warning(self) -> bool:
        
        return (
            self.velocity_warning_enabled
            and self.max_velocities_are_valid
            and (
                self.max_velocity_xy > self.velocity_xy_warning_threshold
                or self.max_velocity_z_up > self.effective_velocity_z_threshold_up
                or self.max_velocity_z_down > self.effective_velocity_z_threshold_down
            )
        )

    @property
    def should_show_velocity_xy_warning(self) -> bool:
        
        return (
            self.velocity_warning_enabled
            and self.max_velocities_are_valid
            and self.max_velocity_xy > self.velocity_xy_warning_threshold
        )

    @property
    def should_show_velocity_z_warning(self) -> bool:
        
        return (
            self.velocity_warning_enabled
            and self.max_velocities_are_valid
            and (
                self.max_velocity_z_up > self.effective_velocity_z_threshold_up
                or self.max_velocity_z_down > self.effective_velocity_z_threshold_down
            )
        )

    @property
    def should_show_acceleration_warning(self) -> bool:
        
        return (
            self.acceleration_warning_enabled
            and self.max_acceleration_is_valid
            and self.max_acceleration > self.acceleration_warning_threshold
        )

    @property
    def velocity_z_warning_threshold_up_or_none(self) -> Optional[float]:
        
        return (
            self.velocity_z_warning_threshold_up
            if self.velocity_z_warning_different_up
            else None
        )

    def clear_safety_check_result(self) -> None:
        
        global _safety_check_result

        self.formation_status = ""
        self.min_altitude = 0
        self.max_altitude = 0
        self.min_distance = 0
        self.max_velocity_xy = 0
        self.max_velocity_z_down = 0
        self.max_velocity_z_up = 0
        self.max_acceleration = 0

        _safety_check_result.clear()

        self._refresh_overlay()

    def ensure_overlays_enabled_if_needed(self) -> None:
        get_overlay().enabled = (
            self.altitude_warning_enabled
            or self.proximity_warning_enabled
            or self.velocity_warning_enabled
            or self.acceleration_warning_enabled
        )

    def get_positions_for_proximity_check(
        self, positions: Sequence[Coordinate3D]
    ) -> Sequence[Coordinate3D]:
        
        min_altitude: Optional[float] = None
        if self.min_navigation_altitude_is_valid:
            min_altitude = self.min_navigation_altitude

        if (
            self.proximity_warning_target == "ABOVE_MIN_NAV_ALT"
            and min_altitude is not None
        ):
            return [p for p in positions if p[2] >= min_altitude]
        else:
            return positions

    def set_safety_check_result(
        self,
        formation_status: Optional[str] = None,
        nearest_neighbors: Optional[Tuple[Coordinate3D, Coordinate3D, float]] = None,
        min_altitude: Optional[float] = None,
        max_altitude: Optional[float] = None,
        drones_over_max_altitude: Optional[List[Coordinate3D]] = None,
        max_velocity_xy: Optional[float] = None,
        drones_over_max_velocity_xy: Optional[List[Coordinate3D]] = None,
        max_velocity_z_up: Optional[float] = None,
        max_velocity_z_down: Optional[float] = None,
        drones_over_max_velocity_z: Optional[List[Coordinate3D]] = None,
        max_acceleration: Optional[float] = None,
        drones_over_max_acceleration: Optional[List[Coordinate3D]] = None,
        drones_below_min_nav_altitude: Optional[List[Coordinate3D]] = None,
        all_close_pairs: Optional[List[Tuple[Coordinate3D, Coordinate3D]]] = None,
    ) -> None:
        
        global _safety_check_result

        refresh = False

        if formation_status is not None:
            self.formation_status = formation_status
            refresh = True

        if nearest_neighbors is not None:
            first, second, distance = nearest_neighbors
            self.min_distance = distance
            _safety_check_result.closest_pair = (
                (first, second) if first is not None and second is not None else None
            )
            _safety_check_result.min_distance = distance
            refresh = True

        if max_altitude is not None:
            self.max_altitude = max_altitude
            refresh = True

        if min_altitude is not None:
            self.min_altitude = min_altitude
            refresh = True

        if drones_over_max_altitude is not None:
            _safety_check_result.drones_over_max_altitude = drones_over_max_altitude
            refresh = True

        if max_velocity_xy is not None:
            self.max_velocity_xy = max_velocity_xy
            refresh = True

        if drones_over_max_velocity_xy is not None:
            _safety_check_result.drones_over_max_velocity_xy = (
                drones_over_max_velocity_xy
            )
            refresh = True

        if max_velocity_z_up is not None:
            self.max_velocity_z_up = max_velocity_z_up
            refresh = True

        if max_velocity_z_down is not None:
            self.max_velocity_z_down = max_velocity_z_down
            refresh = True

        if drones_over_max_velocity_z is not None:
            _safety_check_result.drones_over_max_velocity_z = drones_over_max_velocity_z
            refresh = True

        if max_acceleration is not None:
            self.max_acceleration = max_acceleration
            refresh = True

        if drones_over_max_acceleration is not None:
            _safety_check_result.drones_over_max_acceleration = (
                drones_over_max_acceleration
            )
            refresh = True

        if drones_below_min_nav_altitude is not None:
            _safety_check_result.drones_below_min_nav_altitude = (
                drones_below_min_nav_altitude
            )
            refresh = True

        if all_close_pairs is not None:
            _safety_check_result.all_close_pairs = all_close_pairs
            refresh = True

        if refresh:
            self.ensure_overlays_enabled_if_needed()
            self._refresh_overlay()

    def _refresh_overlay(self) -> None:
        
        global _safety_check_result

        overlay = get_overlay(create=False)

        if overlay:
            markers: List[Marker] = []

            
            
            
            
            
            if (
                self.should_show_proximity_warning
                or _safety_check_result.all_close_pairs
            ):
                
                
                if _safety_check_result.all_close_pairs:
                    markers.extend(
                        (
                            (pair, "proximity")
                            for pair in _safety_check_result.all_close_pairs
                        )
                    )
                elif _safety_check_result.closest_pair is not None:
                    markers.append((_safety_check_result.closest_pair, "proximity"))

            if self.should_show_altitude_warning:
                markers.extend(
                    ([point], "altitude")
                    for point in _safety_check_result.drones_over_max_altitude
                )
                markers.extend(
                    ([point], "altitude")
                    for point in _safety_check_result.drones_below_min_nav_altitude
                )

            if self.should_show_velocity_xy_warning:
                markers.extend(
                    ([point], "velocity")
                    for point in _safety_check_result.drones_over_max_velocity_xy
                )

            if self.should_show_velocity_z_warning:
                markers.extend(
                    ([point], "velocity")
                    for point in _safety_check_result.drones_over_max_velocity_z
                )

            if self.should_show_acceleration_warning:
                markers.extend(
                    ([point], "acceleration")
                    for point in _safety_check_result.drones_over_max_acceleration
                )

            overlay.markers = markers


def get_proximity_warning_threshold(context: Context) -> float:
    
    return float(context.scene.skybrush.safety_check.proximity_warning_threshold)
