

from bpy.types import Action, FCurve
from typing import Optional

import bpy

from .utils.collections import ensure_object_exists_in_collection

__all__ = (
    "ensure_action_exists_for_object",
    "find_all_f_curves_for_data_path",
    "find_f_curve_for_data_path",
    "find_f_curve_for_data_path_and_index",
    "get_action_for_object",
    "get_name_of_action_for_object",
    "cleanup_actions_for_object",
)


def get_name_of_action_for_object(object) -> str:
    
    return f"{object.name} Action"


def ensure_action_exists_for_object(
    object, name: Optional[str] = None, *, clean: bool = False
) -> Action:
    
    action = get_action_for_object(object)
    if action is not None:
        return action

    if not object.animation_data:
        object.animation_data_create()

    action, _ = ensure_object_exists_in_collection(
        bpy.data.actions, name or get_name_of_action_for_object(object)
    )

    if clean:
        action.fcurves.clear()

    object.animation_data.action = action

    return action


def get_action_for_object(object) -> Action:
    
    if object and object.animation_data and object.animation_data.action:
        return object.animation_data.action


def find_f_curve_for_data_path(object_or_action, data_path: str) -> Optional[FCurve]:
    
    if not isinstance(object_or_action, Action):
        action = get_action_for_object(object_or_action)
        if not action:
            return None
    else:
        action = object_or_action

    for curve in action.fcurves:
        if curve.data_path == data_path:
            return curve

    return None


def find_f_curve_for_data_path_and_index(
    object_or_action, data_path: str, index: int
) -> Optional[FCurve]:
    
    if not isinstance(object_or_action, Action):
        action = get_action_for_object(object_or_action)
        if not action:
            return None
    else:
        action = object_or_action

    for curve in action.fcurves:
        if curve.data_path == data_path and curve.array_index == index:
            return curve

    return None


def find_all_f_curves_for_data_path(
    object_or_action, data_path: str
) -> Optional[FCurve]:
    
    if not isinstance(object_or_action, Action):
        action = get_action_for_object(object_or_action)
        if not action:
            return []
    else:
        action = object_or_action

    
    result = [curve for curve in action.fcurves if curve.data_path == data_path]
    return result


def cleanup_actions_for_object(object):
    
    action = get_action_for_object(object)

    to_delete = []
    for curve in action.fcurves:
        if curve.data_path:
            try:
                object.path_resolve(curve.data_path)
            except ValueError:
                to_delete.append(curve)

    while to_delete:
        action.fcurves.remove(to_delete.pop())
