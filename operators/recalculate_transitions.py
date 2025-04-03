from dataclasses import dataclass
from enum import Enum
from functools import partial
from math import inf
from typing import Callable, Iterable, List, Optional, Sequence, Tuple, Union, cast

import bpy
from bpy.types import Collection, Mesh, MeshVertex, Object

from bpy.props import EnumProperty

from sbstudio.api.errors import SkybrushStudioAPIError
from sbstudio.api.types import Mapping
from sbstudio.errors import SkybrushStudioError
from sbstudio.plugin.actions import (
    cleanup_actions_for_object,
    ensure_action_exists_for_object,
)
from sbstudio.plugin.api import get_api
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.keyframes import set_keyframes
from sbstudio.plugin.model.formation import (
    get_markers_and_related_objects_from_formation,
    get_world_coordinates_of_markers_from_formation,
)
from sbstudio.plugin.model.storyboard import Storyboard, StoryboardEntry
from sbstudio.plugin.tasks.safety_check import invalidate_caches
from sbstudio.plugin.utils import create_internal_id
from sbstudio.plugin.utils.evaluator import create_position_evaluator
from sbstudio.plugin.utils.transition import (
    create_transition_constraint_between,
    find_transition_constraint_between,
    set_constraint_name_from_storyboard_entry,
)
from sbstudio.utils import constant

from .base import StoryboardOperator

__all__ = ("RecalculateTransitionsOperator",)


class InfluenceCurveTransitionType(Enum):
    

    LINEAR = "linear"
    SMOOTH_FROM_LEFT = "smoothFromLeft"
    SMOOTH_FROM_RIGHT = "smoothFromRight"
    SMOOTH = "smooth"


@dataclass
class InfluenceCurveDescriptor:
    

    scene_start_frame: int
    """The start frame of the entire scene."""

    windup_start_frame: Optional[int]
    """The windup start frame, i.e. the _last_ frame when the influence curve
    should still be zero before winding up to full influence. `None` means that
    it is the same as the start frame of the scene.

    When this frame is earlier than the start frame of the scene, it is assumed
    to be equal to the start frame of the scene.
    """

    start_frame: int
    """The first frame when the influence should become equal to 1. Must be
    larger than the windup start frame; when it is smaller or equal, it is
    assumed to be one larger than the windup start frame.
    """

    end_frame: Optional[int] = None
    """The last frame when the influence is still equal to 1; ``None`` means
    that the influence curve stays 1 infinitely.

    The end frame must be larger than or equal to the start frame; when it is
    smaller, it is assumed to be equal to the start frame.
    """

    windup_type: InfluenceCurveTransitionType = InfluenceCurveTransitionType.SMOOTH
    """The type of the windup transition."""

    def __init__(
        self,
        scene_start_frame: int,
        windup_start_frame: Optional[int],
        start_frame: int,
        end_frame: Optional[int] = None,
        windup_type: InfluenceCurveTransitionType = InfluenceCurveTransitionType.SMOOTH,
    ):
        
        
        self.scene_start_frame = round(scene_start_frame)
        self.windup_start_frame = (
            None if windup_start_frame is None else round(windup_start_frame)
        )
        self.start_frame = round(start_frame)
        self.end_frame = None if end_frame is None else round(end_frame)
        self.windup_type = windup_type

    def apply(self, object, data_path: str) -> None:
        
        
        
        
        
        
        

        is_first = self.scene_start_frame == self.start_frame
        keyframes: List[Tuple[int, float]] = [
            (self.scene_start_frame - (1 if is_first else 0), 0.0)
        ]

        
        if (
            not is_first
            and self.windup_start_frame is not None
            and self.windup_start_frame > self.scene_start_frame
        ):
            keyframes.append((self.windup_start_frame, keyframes[-1][1]))

        
        frame = max(self.start_frame, keyframes[-1][0] + 1)
        start_of_transition = len(keyframes) - 1
        keyframes.append((frame, 1.0))

        
        if self.end_frame is not None:
            end_frame = max(self.end_frame, frame)
            if end_frame > frame:
                keyframes.append((end_frame, 1.0))

            
            
            
            
            

        keyframe_objs = set_keyframes(
            object,
            data_path,
            keyframes,
            clear_range=(None, inf),
            interpolation="LINEAR",
        )

        if self.windup_type != InfluenceCurveTransitionType.LINEAR:
            kf = keyframe_objs[start_of_transition]
            kf.interpolation = "BEZIER"
            if self.windup_type == InfluenceCurveTransitionType.SMOOTH_FROM_RIGHT:
                kf.handle_right_type = "VECTOR"
            else:
                kf.handle_right_type = "AUTO_CLAMPED"
            if self.windup_type == InfluenceCurveTransitionType.SMOOTH_FROM_LEFT:
                kf.handle_left_type = "VECTOR"
            else:
                kf.handle_left_type = "AUTO_CLAMPED"


class _LazyFormationTargetList:
    

    _formation: Optional[Collection] = None
    """The formation of the storyboard entry."""

    _items: Optional[List[Union[Object, MeshVertex]]] = None

    def __init__(self, entry: Optional[StoryboardEntry]):
        self._formation = entry.formation if entry else None

    def find(self, item, *, default: int = 0) -> int:
        if item is None:
            return default

        if self._items is None:
            self._items = self._validate_items()

        try:
            return self._items.index(item)
        except ValueError:
            return default

    def _validate_items(self) -> List[Union[Object, MeshVertex]]:
        if self._formation is None:
            return []
        else:
            return [
                v
                for v, _ in get_markers_and_related_objects_from_formation(
                    self._formation
                )
            ]


def get_coordinates_of_formation(formation, *, frame: int) -> List[Tuple[float, ...]]:
    
    return [
        tuple(pos)
        for pos in get_world_coordinates_of_markers_from_formation(
            formation, frame=frame
        )
    ]


def calculate_mapping_for_transition_into_storyboard_entry(
    entry: StoryboardEntry, source, *, num_targets: int
) -> Mapping:
    
    formation = entry.formation
    if formation is None:
        raise RuntimeError(
            "mapping function called for storyboard entry with no formation"
        )

    num_drones = len(source)

    result: Mapping = [None] * num_drones

    
    
    
    if entry.transition_type == "AUTO":
        
        target = get_coordinates_of_formation(formation, frame=entry.frame_start)
        try:
            match, clearance = get_api().match_points(source, target, radius=0)
        except Exception as ex:
            if not isinstance(ex, SkybrushStudioAPIError):
                raise SkybrushStudioAPIError from ex
            else:
                raise

        
        
        
        
        for target_index, drone_index in enumerate(match):
            if drone_index is not None:
                result[drone_index] = target_index

    else:
        
        length = min(num_drones, num_targets)
        result[:length] = range(length)

    return result


def _vertex_index_to_vertex_group_name(index: int) -> str:
    
    return create_internal_id(f"Vertex {index}")


def _vertex_group_name_to_vertex_index(name: str) -> Optional[int]:
    
    if (
        name.startswith("Skybrush[Vertex ")
        and name.endswith("]")
        and name[16:-1].isdigit()
    ):
        return int(name[16:-1])
    else:
        return None


def calculate_departure_index_of_drone(
    drone,
    drone_index: int,
    previous_entry: Optional[StoryboardEntry],
    previous_entry_index: int,
    previous_mapping: Optional[Mapping],
    targets_in_previous_formation: _LazyFormationTargetList,
) -> int:
    
    
    
    
    if previous_mapping:
        previous_target_index = previous_mapping[drone_index]
        if previous_target_index is None:
            
            return 0
        else:
            return previous_target_index

    
    
    
    

    if previous_entry is None:
        
        
        
        
        return drone_index

    previous_constraint = find_transition_constraint_between(
        drone=drone, storyboard_entry=previous_entry
    )
    if previous_constraint is None:
        
        
        
        return drone_index if previous_entry_index == 0 else 0

    previous_obj = previous_constraint.target

    if previous_constraint.subtarget:
        
        
        
        try:
            vertex_group = previous_obj.vertex_groups[previous_constraint.subtarget]
        except KeyError:
            
            return 0

        
        
        
        
        
        
        
        
        
        vertex_index = _vertex_group_name_to_vertex_index(previous_constraint.subtarget)
        previous_mesh = cast(Mesh, previous_obj.data)
        if vertex_index is not None:
            previous_target = previous_mesh.vertices[vertex_index]
        else:
            for vertex in previous_mesh.vertices:
                try:
                    if vertex_group.weight(vertex.index) > 0:
                        previous_target = vertex
                        break
                except Exception:
                    pass
            else:
                
                return 0

    else:
        previous_target = previous_constraint.target

    return targets_in_previous_formation.find(previous_target)


def update_transition_constraint_properties(drone, entry: StoryboardEntry, marker, obj):
    
    constraint = find_transition_constraint_between(drone=drone, storyboard_entry=entry)
    if marker is None:
        
        
        
        if constraint is not None:
            drone.constraints.remove(constraint)
        return None

    
    
    if constraint is None:
        constraint = create_transition_constraint_between(
            drone=drone, storyboard_entry=entry
        )
    else:
        
        
        set_constraint_name_from_storyboard_entry(constraint, entry)

    
    
    if marker is obj:
        
        
        constraint.target = marker
    else:
        
        
        
        index = marker.index
        vertex_group_name = _vertex_index_to_vertex_group_name(index)
        vertex_groups = obj.vertex_groups
        try:
            vertex_group = vertex_groups[vertex_group_name]
        except KeyError:
            
            vertex_group = vertex_groups.new(name=vertex_group_name)

        
        
        
        
        vertex_group.add([index], 1, "REPLACE")

        constraint.target = obj
        constraint.subtarget = vertex_group_name

    return constraint


def update_transition_constraint_influence(
    drone, constraint, descriptor: InfluenceCurveDescriptor
) -> None:
    
    
    
    key = f"constraints[{constraint.name!r}].influence".replace("'", '"')

    
    ensure_action_exists_for_object(drone)

    
    descriptor.apply(drone, key)


def update_transition_for_storyboard_entry(
    entry: StoryboardEntry,
    entry_index: int,
    drones,
    *,
    get_positions_of,
    previous_entry: Optional[StoryboardEntry],
    previous_mapping: Optional[Mapping],
    start_of_scene: int,
    start_of_next: Optional[int],
) -> Optional[Mapping]:
    
    if entry.is_locked:
        
        return None

    formation = entry.formation
    if formation is None:
        
        return None

    markers_and_objects = get_markers_and_related_objects_from_formation(formation)
    num_markers = len(markers_and_objects)
    end_of_previous = previous_entry.frame_end if previous_entry else start_of_scene

    
    
    
    
    
    
    if previous_entry:
        start_points = get_positions_of(drones, frame=end_of_previous)
    else:
        start_points = get_positions_of(
            (marker for marker, _ in markers_and_objects), frame=end_of_previous
        )
        if len(drones) != len(start_points):
            raise SkybrushStudioError(
                f"First formation has {len(start_points)} markers but the scene "
                f'contains {len(drones)} drones. Check the "Drones" collection '
                f"and the first formation for consistency."
            )

    mapping = calculate_mapping_for_transition_into_storyboard_entry(
        entry,
        start_points,
        num_targets=num_markers,
    )

    
    entry.update_mapping(mapping)

    
    num_drones_transitioning = sum(
        1 for target_index in mapping if target_index is not None
    )

    
    
    objects_in_formation = _LazyFormationTargetList(entry)
    objects_in_previous_formation = _LazyFormationTargetList(previous_entry)

    
    
    schedule_override_map = entry.get_enabled_schedule_override_map()

    
    
    
    todo: List[Callable[[], None]] = []
    for drone_index, drone in enumerate(drones):
        target_index = mapping[drone_index]
        if target_index is None:
            marker, obj = None, None
        else:
            marker, obj = markers_and_objects[target_index]

        constraint = update_transition_constraint_properties(drone, entry, marker, obj)

        if constraint is not None:
            
            

            windup_start_frame = end_of_previous
            start_frame = entry.frame_start
            departure_delay = 0
            arrival_delay = 0
            departure_index: Optional[int] = None

            if entry.is_staggered:
                
                
                departure_index = calculate_departure_index_of_drone(
                    drone,
                    drone_index,
                    previous_entry,
                    entry_index - 1,
                    previous_mapping,
                    objects_in_previous_formation,
                )
                arrival_index = objects_in_formation.find(marker)

                departure_delay = entry.pre_delay_per_drone_in_frames * departure_index
                arrival_delay = -entry.post_delay_per_drone_in_frames * (
                    num_drones_transitioning - arrival_index - 1
                )

            if schedule_override_map:
                
                
                
                
                if departure_index is None:
                    departure_index = calculate_departure_index_of_drone(
                        drone,
                        drone_index,
                        previous_entry,
                        entry_index - 1,
                        previous_mapping,
                        objects_in_previous_formation,
                    )

                override = schedule_override_map.get(departure_index)
                if override:
                    departure_delay = override.pre_delay
                    arrival_delay = -override.post_delay

            windup_start_frame += departure_delay
            start_frame += arrival_delay

            if previous_entry is None:
                
                
                
                start_frame = windup_start_frame = start_of_scene
            else:
                if windup_start_frame >= start_frame:
                    raise SkybrushStudioError(
                        f"Not enough time to plan staggered transition to "
                        f"formation {entry.name!r} at drone index {drone_index + 1} "
                        f"(1-based). Try decreasing departure or arrival delay "
                        f"or allow more time for the transition."
                    )

            
            
            descriptor = InfluenceCurveDescriptor(
                scene_start_frame=start_of_scene,
                windup_start_frame=windup_start_frame,
                start_frame=start_frame,
                end_frame=start_of_next,
            )

            
            
            
            todo.append(
                partial(
                    update_transition_constraint_influence,
                    drone,
                    constraint,
                    descriptor,
                )
            )

    
    for func in todo:
        func()

    return mapping


@dataclass
class RecalculationTask:
    

    entry: StoryboardEntry
    """The _target_ entry of the transition to recalculate."""

    entry_index: int
    """Index of the target entry of the transition."""

    previous_entry: Optional[StoryboardEntry] = None
    """The entry that precedes the target entry in the storyboard; `None` if the
    target entry is the first one.
    """

    start_frame_of_next_entry: Optional[int] = None
    """The start frame of the _next_ entry in the storyboard; `None` if the
    target entry is the last one.
    """

    @classmethod
    def for_entry_by_index(cls, entries: Sequence[StoryboardEntry], index: int):
        return cls(
            entries[index],
            index,
            entries[index - 1] if index > 0 else None,
            entries[index + 1].frame_start if index + 1 < len(entries) else None,
        )


def recalculate_transitions(
    tasks: Iterable[RecalculationTask], *, start_of_scene: int
) -> None:
    drones = Collections.find_drones().objects
    if not drones:
        return

    
    
    
    
    
    
    
    previous_mapping: Optional[Mapping] = None

    with create_position_evaluator() as get_positions_of:
        
        
        for task in tasks:
            previous_mapping = update_transition_for_storyboard_entry(
                task.entry,
                task.entry_index,
                drones,
                get_positions_of=get_positions_of,
                previous_entry=task.previous_entry,
                previous_mapping=previous_mapping,
                start_of_scene=start_of_scene,
                start_of_next=task.start_frame_of_next_entry,
            )

    
    for drone in drones:
        try:
            cleanup_actions_for_object(drone)
        except Exception:
            pass

    bpy.ops.skybrush.fix_constraint_ordering()
    invalidate_caches(clear_result=True)


class RecalculateTransitionsOperator(StoryboardOperator):
    

    bl_idname = "skybrush.recalculate_transitions"
    bl_label = "Recalculate Transitions"
    bl_description = (
        "Recalculates all transitions in the show based on the current storyboard"
    )
    bl_options = {"UNDO"}

    scope = EnumProperty(
        items=[
            ("ALL", "Entire storyboard", "", "SEQUENCE", 1),
            ("CURRENT_FRAME", "Current frame", "", "EMPTY_SINGLE_ARROW", 2),
            None,
            (
                "TO_SELECTED",
                "To selected formation",
                "",
                "TRACKING_BACKWARDS_SINGLE",
                3,
            ),
            (
                "FROM_SELECTED",
                "From selected formation",
                "",
                "TRACKING_FORWARDS_SINGLE",
                4,
            ),
            (
                "FROM_SELECTED_TO_END",
                "From selected formation to end",
                "",
                "TRACKING_FORWARDS",
                5,
            ),
        ],
        name="Scope",
        description=(
            "Scope of the operator that defines which transitions must be recalculated"
        ),
        default="ALL",
    )

    only_with_valid_storyboard = True

    def execute_on_storyboard(self, storyboard: Storyboard, entries, context):
        
        drones = Collections.find_drones().objects

        
        if not drones:
            self.report({"ERROR"}, "You need to create some drones first")
            return {"CANCELLED"}

        
        
        tasks = self._get_transitions_to_process(storyboard, entries)
        if not tasks:
            self.report({"ERROR"}, "No transitions match the selected scope")
            return {"CANCELLED"}

        
        start_of_scene = min(context.scene.frame_start, storyboard.frame_start)

        
        tasks = [task for task in tasks if not task.entry.is_locked]
        if not tasks:
            self.report(
                {"INFO"},
                "All transitions in the selected scope are locked; nothing to do.",
            )
            return {"CANCELLED"}

        try:
            recalculate_transitions(tasks, start_of_scene=start_of_scene)
        except SkybrushStudioAPIError:
            self.report(
                {"ERROR"},
                (
                    "Error while invoking transition planner on the Skybrush "
                    "Studio server"
                ),
            )
            return {"CANCELLED"}
        except SkybrushStudioError as ex:
            self.report({"ERROR"}, str(ex))
            return {"CANCELLED"}

        return {"FINISHED"}

    def _get_transitions_to_process(
        self, storyboard: Storyboard, entries: Sequence[StoryboardEntry]
    ) -> List[RecalculationTask]:
        
        tasks: List[RecalculationTask] = []
        active_index = int(storyboard.active_entry_index)
        num_entries = len(entries)

        if self.scope == "FROM_SELECTED":
            condition = (
                (active_index + 1).__eq__
                if active_index < num_entries - 1
                else constant(False)
            )
        elif self.scope == "TO_SELECTED":
            condition = active_index.__eq__
        elif self.scope == "FROM_SELECTED_TO_END":
            condition = active_index.__le__
        elif self.scope == "CURRENT_FRAME":
            frame = bpy.context.scene.frame_current
            index = storyboard.get_index_of_entry_after_frame(frame)
            condition = index.__eq__
        elif self.scope == "ALL":
            condition = constant(True)
        else:
            condition = constant(False)

        for index in range(len(entries)):
            if condition(index):
                tasks.append(RecalculationTask.for_entry_by_index(entries, index))

        return tasks
