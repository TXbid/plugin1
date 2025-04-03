

import logging

from bpy.path import basename
from bpy.types import Context

from itertools import groupby
from natsort import natsorted
from operator import attrgetter
from pathlib import Path
from typing import Any, Optional, cast

from sbstudio.api.base import SkybrushStudioAPI
from sbstudio.model.light_program import LightProgram
from sbstudio.model.safety_check import SafetyCheckParams
from sbstudio.model.trajectory import Trajectory
from sbstudio.model.yaw import YawSetpointList
from sbstudio.plugin.model.storyboard import (
    StoryboardEntry,
    StoryboardEntryPurpose,
    get_storyboard,
)
from sbstudio.plugin.constants import Collections
from sbstudio.plugin.errors import SkybrushStudioExportWarning
from sbstudio.model.file_formats import FileFormat
from sbstudio.plugin.props.frame_range import resolve_frame_range
from sbstudio.plugin.tasks.light_effects import suspended_light_effects
from sbstudio.plugin.tasks.safety_check import suspended_safety_checks
from sbstudio.plugin.utils import with_context
from sbstudio.plugin.utils.cameras import get_cameras_from_context
from sbstudio.plugin.utils.sampling import (
    frame_range,
    sample_colors_of_objects,
    sample_positions_of_objects,
    sample_positions_and_colors_of_objects,
    sample_positions_and_yaw_of_objects,
    sample_positions_colors_and_yaw_of_objects,
)
from sbstudio.plugin.utils.time_markers import get_time_markers_from_context
from sbstudio.utils import get_ends

__all__ = ("get_drones_to_export", "export_show_to_file_using_api")


log = logging.getLogger(__name__)


class _default_settings:
    output_fps = 4
    light_output_fps = 4






def get_drones_to_export(selected_only: bool = False):
    
    drone_collection = Collections.find_drones(create=False)
    if not drone_collection:
        return []

    to_export = [
        drone
        for drone in drone_collection.objects
        if not selected_only or drone.select_get()
    ]

    return natsorted(to_export, key=attrgetter("name"))


@with_context
def _get_frame_range_from_export_settings(
    settings, *, context: Optional[Context] = None
) -> Optional[tuple[int, int]]:
    
    return resolve_frame_range(settings["frame_range"], context=context)


@with_context
def _get_segments(context: Optional[Context] = None) -> dict[str, tuple[float, float]]:
    
    result: dict[str, tuple[float, float]] = {}
    storyboard = get_storyboard(context=context)
    fps = context.scene.render.fps

    entry_purpose_groups = groupby(storyboard.entries, lambda e: cast(str, e.purpose))

    takeoff_entries: list[StoryboardEntry] | None = None
    show_entries: list[StoryboardEntry] | None = None
    landing_entries: list[StoryboardEntry] | None = None
    show_valid = True
    for purpose, entries in entry_purpose_groups:
        if purpose == StoryboardEntryPurpose.TAKEOFF.name:
            if not (show_entries is None and landing_entries is None):
                show_valid = False
                break

            takeoff_entries = list(entries)
        elif purpose == StoryboardEntryPurpose.SHOW.name:
            if landing_entries is not None:
                show_valid = False
                break

            show_entries = list(entries)
        elif purpose == StoryboardEntryPurpose.LANDING.name:
            landing_entries = list(entries)

    if show_valid:
        if ends := get_ends(takeoff_entries):
            result["takeoff"] = (ends[0].frame_start / fps, ends[1].frame_end / fps)
        if ends := get_ends(show_entries):
            result["show"] = (ends[0].frame_start / fps, ends[1].frame_end / fps)
        if ends := get_ends(landing_entries):
            result["landing"] = (ends[0].frame_start / fps, ends[1].frame_end / fps)

    return result


@with_context
def _get_trajectories_and_lights(
    drones,
    settings: dict[str, Any],
    bounds: tuple[int, int],
    *,
    context: Optional[Context] = None,
) -> tuple[dict[str, Trajectory], dict[str, LightProgram]]:
    
    trajectory_fps = settings.get("output_fps", _default_settings.output_fps)
    light_fps = settings.get("light_output_fps", _default_settings.light_output_fps)

    trajectories: dict[str, Trajectory]
    lights: dict[str, LightProgram]

    if trajectory_fps == light_fps:
        
        with suspended_safety_checks():
            result = sample_positions_and_colors_of_objects(
                drones,
                frame_range(bounds[0], bounds[1], fps=trajectory_fps, context=context),
                context=context,
                by_name=True,
                simplify=True,
            )

        trajectories = {}
        lights = {}

        for key, (trajectory, light_program) in result.items():
            trajectories[key] = trajectory
            lights[key] = light_program.simplify()

    else:
        
        
        with suspended_safety_checks():
            with suspended_light_effects():
                trajectories = sample_positions_of_objects(
                    drones,
                    frame_range(
                        bounds[0], bounds[1], fps=trajectory_fps, context=context
                    ),
                    context=context,
                    by_name=True,
                    simplify=True,
                )

            lights = sample_colors_of_objects(
                drones,
                frame_range(bounds[0], bounds[1], fps=light_fps, context=context),
                context=context,
                by_name=True,
                simplify=True,
            )

    return trajectories, lights


@with_context
def _get_trajectories_lights_and_yaw_setpoints(
    drones,
    settings: dict[str, Any],
    bounds: tuple[int, int],
    *,
    context: Optional[Context] = None,
) -> tuple[dict[str, Trajectory], dict[str, LightProgram], dict[str, YawSetpointList]]:
    
    trajectory_fps = settings.get("output_fps", _default_settings.output_fps)
    light_fps = settings.get("light_output_fps", _default_settings.light_output_fps)

    trajectories: dict[str, Trajectory]
    lights: dict[str, LightProgram]
    yaw_setpoints: dict[str, YawSetpointList]

    if trajectory_fps == light_fps:
        
        with suspended_safety_checks():
            result = sample_positions_colors_and_yaw_of_objects(
                drones,
                frame_range(bounds[0], bounds[1], fps=trajectory_fps, context=context),
                context=context,
                by_name=True,
                simplify=True,
            )

        trajectories = {}
        lights = {}
        yaw_setpoints = {}

        for key, (trajectory, light_program, yaw_curve) in result.items():
            trajectories[key] = trajectory
            
            lights[key] = light_program.simplify()
            yaw_setpoints[key] = yaw_curve

    else:
        
        
        with suspended_safety_checks():
            with suspended_light_effects():
                result = sample_positions_and_yaw_of_objects(
                    drones,
                    frame_range(
                        bounds[0], bounds[1], fps=trajectory_fps, context=context
                    ),
                    context=context,
                    by_name=True,
                    simplify=True,
                )

                trajectories = {}
                yaw_setpoints = {}

                for key, (trajectory, yaw_curve) in result.items():
                    trajectories[key] = trajectory
                    yaw_setpoints[key] = yaw_curve

            lights = sample_colors_of_objects(
                drones,
                frame_range(bounds[0], bounds[1], fps=light_fps, context=context),
                context=context,
                by_name=True,
                simplify=True,
            )

    return trajectories, lights, yaw_setpoints


def export_show_to_file_using_api(
    api: SkybrushStudioAPI,
    context: Context,
    settings: dict[str, Any],
    filepath: Path,
    format: FileFormat,
) -> None:
    

    log.info(f"Exporting show content to {filepath}")

    
    log.info("Getting frame range from {}".format(settings.get("frame_range")))
    frame_range = _get_frame_range_from_export_settings(settings, context=context)
    if frame_range is None:
        raise SkybrushStudioExportWarning("Selected frame range is empty")

    
    export_selected_only: bool = settings.get("export_selected", False)
    drones = list(get_drones_to_export(selected_only=export_selected_only))
    if not drones:
        if export_selected_only:
            raise SkybrushStudioExportWarning(
                "No objects were selected; export cancelled"
            )
        else:
            raise SkybrushStudioExportWarning(
                "There are no objects to export; export cancelled"
            )

    
    use_yaw_control: bool = settings.get("use_yaw_control", False)

    
    if use_yaw_control:
        log.info("Getting object trajectories, light programs and yaw setpoints")
        (
            trajectories,
            lights,
            yaw_setpoints,
        ) = _get_trajectories_lights_and_yaw_setpoints(
            drones, settings, frame_range, context=context
        )
    else:
        log.info("Getting object trajectories and light programs")
        (
            trajectories,
            lights,
        ) = _get_trajectories_and_lights(drones, settings, frame_range, context=context)
        yaw_setpoints = None

    
    show_title = str(basename(filepath).split(".")[0])

    
    scene_settings = getattr(context.scene.skybrush, "settings", None)
    show_type = (scene_settings.show_type if scene_settings else "OUTDOOR").lower()

    
    time_markers = get_time_markers_from_context(context)

    
    export_cameras = settings.get("export_cameras", False)
    if export_cameras:
        cameras = get_cameras_from_context(context)
    else:
        cameras = None

    
    safety_check = getattr(context.scene.skybrush, "safety_check", None)
    validation = SafetyCheckParams(
        max_velocity_xy=(
            safety_check.velocity_xy_warning_threshold if safety_check else 8
        ),
        max_velocity_z=safety_check.velocity_z_warning_threshold if safety_check else 2,
        max_velocity_z_up=(
            safety_check.velocity_z_warning_threshold_up_or_none
            if safety_check
            else None
        ),
        max_acceleration=(
            safety_check.acceleration_warning_threshold if safety_check else 4
        ),
        max_altitude=safety_check.altitude_warning_threshold if safety_check else 150,
        min_distance=safety_check.proximity_warning_threshold if safety_check else 3,
    )

    
    show_segments = _get_segments(context=context)

    renderer_params = {}

    
    if format is FileFormat.PDF:
        log.info("Exporting validation plots to .pdf")
        plots = settings.get("plots", ["pos", "vel", "drift", "nn"])
        fps = settings.get("output_fps", _default_settings.output_fps)
        api.generate_plots(
            trajectories=trajectories,
            output=filepath,
            validation=validation,
            plots=plots,
            fps=fps,
            time_markers=time_markers,
        )
    else:
        if format is FileFormat.SKYC:
            log.info("Exporting show to .skyc")
            renderer = "skyc"
        elif format is FileFormat.CSV:
            log.info("Exporting show to CSV")
            renderer = "csv"
            renderer_params = {**renderer_params, "fps": settings["output_fps"]}
        elif format is FileFormat.DAC:
            log.info("Exporting show to .dac format")
            renderer = "dac"
            renderer_params = {
                **renderer_params,
                "show_id": 1555,
                "title": "Skybrush show",
            }
        elif format is FileFormat.DROTEK:
            log.info("Exporting show to Drotek format")
            renderer = "drotek"
            renderer_params = {
                **renderer_params,
                "fps": settings["output_fps"],
                
            }
        elif format is FileFormat.DSS:
            log.info("Exporting show to DSS PATH format")
            renderer = "dss"
        elif format is FileFormat.DSS3:
            log.info("Exporting show to DSS PATH3 format")
            renderer = "dss3"
            renderer_params = {
                **renderer_params,
                "fps": settings["output_fps"],
                "light_fps": settings["light_output_fps"],
            }
        elif format is FileFormat.EVSKY:
            log.info("Exporting show to EVSKY format")
            renderer = "evsky"
            renderer_params = {
                **renderer_params,
                "fps": settings["output_fps"],
                "light_fps": settings["light_output_fps"],
            }
        elif format is FileFormat.LITEBEE:
            log.info("Exporting show to Litebee format")
            renderer = "litebee"
        elif format is FileFormat.VVIZ:
            log.info("Exporting show to Finale 3D .vviz format")
            renderer = "vviz"
            renderer_params = {
                **renderer_params,
                "fps": settings["output_fps"],
                "light_fps": settings["light_output_fps"],
            }
        else:
            raise RuntimeError(f"Unhandled format: {format!r}")

        api.export(
            show_title=show_title,
            show_type=show_type,
            show_segments=show_segments,
            validation=validation,
            trajectories=trajectories,
            lights=lights,
            yaw_setpoints=yaw_setpoints,
            output=filepath,
            time_markers=time_markers,
            cameras=cameras,
            renderer=renderer,
            renderer_params=renderer_params,
        )

    log.info("Export finished")
