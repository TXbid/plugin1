from __future__ import annotations

from typing import Iterable, Optional, TYPE_CHECKING, Tuple

if TYPE_CHECKING:
    from bpy.types import Area
    from bpy.types import SpaceView3D

from .utils import with_screen

__all__ = (
    "find_all_3d_views",
    "find_all_3d_views_and_their_areas",
    "find_one_3d_view",
    "find_one_3d_view_and_its_area",
)


@with_screen
def find_all_3d_views(screen: Optional[str] = None) -> Iterable[SpaceView3D]:
    
    for space, _area in _find_all_3d_views_and_their_areas(screen):
        yield space


@with_screen
def find_all_3d_views_and_their_areas(
    screen: Optional[str] = None,
) -> Iterable[Tuple[SpaceView3D, Area]]:
    
    
    return _find_all_3d_views_and_their_areas(screen)


def _find_all_3d_views_and_their_areas(
    screen: Optional[str] = None,
) -> Iterable[Tuple[SpaceView3D, Area]]:
    for area in screen.areas:  
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    yield space, area


@with_screen
def find_one_3d_view(screen: Optional[str] = None) -> Optional[SpaceView3D]:
    
    return find_one_3d_view_and_its_area(screen)[0]


@with_screen
def find_one_3d_view_and_its_area(
    screen: Optional[str] = None,
) -> Tuple[Optional[SpaceView3D], Optional[Area]]:
    
    for area in screen.areas:  
        if area.type == "VIEW_3D":
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    return space, area
    return None, None
