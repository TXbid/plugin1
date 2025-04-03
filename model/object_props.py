from bpy.props import StringProperty
from bpy.types import PropertyGroup

__all__ = ("DroneShowAddonObjectProperties",)


class DroneShowAddonObjectProperties(PropertyGroup):
    

    formation_vertex_group = StringProperty(
        name="Formation vertex group",
        description="Name of the vertex group designated for containing the vertices that the drones should occupy when their parent object is placed in the storyboard",
        default="",
    )
