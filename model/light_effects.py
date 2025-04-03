from __future__ import annotations

import types
import bpy

from collections.abc import Callable, Iterable, Sequence
from functools import partial
from operator import itemgetter
from typing import cast, Optional
from uuid import uuid4

from bpy.path import abspath
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import (
    ColorRamp,
    Context,
    Image,
    ImageTexture,
    PropertyGroup,
    Mesh,
    Object,
    Texture,
)
from mathutils import Vector
from mathutils.bvhtree import BVHTree

from sbstudio.math.colors import blend_in_place, BlendMode
from sbstudio.math.rng import RandomSequence
from sbstudio.model.plane import Plane
from sbstudio.model.types import Coordinate3D, MutableRGBAColor
from sbstudio.plugin.constants import DEFAULT_LIGHT_EFFECT_DURATION
from sbstudio.plugin.meshes import use_b_mesh
from sbstudio.plugin.model.pixel_cache import PixelCache
from sbstudio.plugin.utils import remove_if_unused, with_context
from sbstudio.plugin.utils.collections import pick_unique_name
from sbstudio.plugin.utils.color_ramp import update_color_ramp_from
from sbstudio.plugin.utils.evaluator import get_position_of_object
from sbstudio.utils import constant, distance_sq_of, load_module, negate

from .mixins import ListMixin


__all__ = ("ColorFunctionProperties", "LightEffect", "LightEffectCollection")


def object_has_mesh_data(self, obj) -> bool:
    
    return obj.data and isinstance(obj.data, Mesh)


CONTAINMENT_TEST_AXES = (Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1)))
"""Pre-constructed vectors for a quick containment test using raycasting and BVH-trees"""

OUTPUT_TYPE_TO_AXIS_SORT_KEY = {
    "GRADIENT_XYZ": (0, 1, 2),
    "GRADIENT_XZY": (0, 2, 1),
    "GRADIENT_YXZ": (1, 0, 2),
    "GRADIENT_YZX": (1, 2, 0),
    "GRADIENT_ZXY": (2, 0, 1),
    "GRADIENT_ZYX": (2, 1, 0),
    "default": (0, 0, 0),
}
"""Axis mapping for the gradient-based output types"""

OUTPUT_TYPE_TO_AXIS_SORT_KEY = {
    key: itemgetter(*value) for key, value in OUTPUT_TYPE_TO_AXIS_SORT_KEY.items()
}

OUTPUT_ITEMS = [
    ("FIRST_COLOR", "First color", "", 1),
    ("LAST_COLOR", "Last color", "", 2),
    ("INDEXED_BY_DRONES", "Indexed by drones", "", 3),
    ("INDEXED_BY_FORMATION", "Indexed by formation", "", 13),
    ("GRADIENT_XYZ", "Gradient (XYZ)", "", 4),
    ("GRADIENT_XZY", "Gradient (XZY)", "", 5),
    ("GRADIENT_YXZ", "Gradient (YXZ)", "", 6),
    ("GRADIENT_YZX", "Gradient (YZX)", "", 7),
    ("GRADIENT_ZXY", "Gradient (ZXY)", "", 8),
    ("GRADIENT_ZYX", "Gradient (ZYX)", "", 9),
    ("TEMPORAL", "Temporal", "", 10),
    ("DISTANCE", "Distance from mesh", "", 11),
    ("CUSTOM", "Custom expression", "", 12),
]
"""Output types of light effects, determining the indexing
of drones to a given axis of the light effect color space"""


def effect_type_supports_randomization(type: str) -> bool:
    
    return type == "COLOR_RAMP" or type == "IMAGE"


def output_type_supports_mapping_mode(type: str) -> bool:
    
    return type == "DISTANCE" or type.startswith("GRADIENT_")


def test_containment(bvh_tree: Optional[BVHTree], point: Coordinate3D) -> bool:
    
    global CONTAINMENT_TEST_AXES

    if not bvh_tree:
        return True

    for axis in CONTAINMENT_TEST_AXES:
        _, _, _, dist = bvh_tree.ray_cast(point, axis)
        if dist is None or dist == -1:
            return False

    return True


def test_is_in_front_of(plane: Optional[Plane], point: Coordinate3D) -> bool:
    
    if plane:
        return plane.is_front(point)
    else:
        return True


_always_true = constant(True)


def get_color_function_names(self, context: Context) -> list[tuple[str, str, str]]:
    names: list[str]

    if self.path:
        absolute_path = abspath(self.path)
        module = load_module(absolute_path)
        names = [
            name
            for name in dir(module)
            if isinstance(getattr(module, name), types.FunctionType)
        ]
    else:
        names = []

    
    
    names.insert(0, "")
    return [(name, name, "") for name in names]


class ColorFunctionProperties(PropertyGroup):
    path = StringProperty(
        name="Color Function File",
        description="Path to the custom color function file",
        subtype="FILE_PATH",
    )

    name = EnumProperty(
        name="Color Function Name",
        description="Name of the custom color function",
        items=get_color_function_names,
        default=0,
    )

    def update_from(self, other):
        self.path = other.path
        if other.name:
            self.name = other.name


def _get_frame_end(self: LightEffect) -> int:
    return self.frame_start + self.duration - 1


def _set_frame_end(self: LightEffect, value: int) -> None:
    
    if value <= self.frame_start:
        self.frame_start = value
        self.duration = 1
    else:
        self.duration = value - self.frame_start + 1


def texture_updated(self: LightEffect, context):
    self.invalidate_color_image()


_pixel_cache = PixelCache()
"""Global cache for the pixels of images in image-based light effects."""


def invalidate_pixel_cache(static: bool = True, dynamic: bool = True) -> None:
    
    global _pixel_cache
    if static:
        _pixel_cache.clear()
    elif dynamic:
        _pixel_cache.clear_dynamic()


class LightEffect(PropertyGroup):
    

    

    maybe_uuid_do_not_use = StringProperty(
        name="Identifier",
        description=(
            "Unique identifier for this storyboard entry; must not change "
            "throughout the lifetime of the entry."
        ),
        default="",
        options={"HIDDEN"},
    )

    enabled = BoolProperty(
        name="Enabled",
        description="Whether this light effect is enabled",
        default=True,
        options=set(),
    )

    type = EnumProperty(
        name="Effect Type",
        description="Type of the light effect: color ramp-based, image-based or custom function",
        items=[
            ("COLOR_RAMP", "Color ramp", "", 1),
            ("IMAGE", "Image", "", 2),
            ("FUNCTION", "Function", "", 3),
        ],
        default="COLOR_RAMP",
    )

    frame_start = IntProperty(
        name="Start Frame",
        description="Frame when this light effect should start in the show",
        default=0,
        options=set(),
    )
    duration = IntProperty(
        name="Duration",
        description="Duration of this light effect",
        min=1,
        default=1,
        options=set(),
    )
    frame_end = IntProperty(
        name="End Frame",
        description="Frame when this light effect should end in the show",
        get=_get_frame_end,
        set=_set_frame_end,
        options=set(),
    )
    fade_in_duration = IntProperty(
        name="Fade in",
        description="Duration of the fade-in part of this light effect",
        default=0,
        options=set(),
    )
    fade_out_duration = IntProperty(
        name="Fade out",
        description="Duration of the fade-out part of this light effect",
        default=0,
        options=set(),
    )

    output = EnumProperty(
        name="Output X",
        description="Output function that determines the value that is passed through the color ramp or image horizontal (X) axis to obtain the color to assign to a drone",
        items=OUTPUT_ITEMS,
        default="LAST_COLOR",
    )

    output_function = PointerProperty(
        type=ColorFunctionProperties,
        name="Output X Function",
        description="Custom function for the output X",
    )

    output_y = EnumProperty(
        name="Output Y",
        description="Output function that determines the value that is passed through the image vertical (Y) axis to obtain the color to assign to a drone",
        items=OUTPUT_ITEMS,
        default="LAST_COLOR",
    )

    output_function_y = PointerProperty(
        type=ColorFunctionProperties,
        name="Output Y Function",
        description="Custom function for the output Y",
    )

    output_mapping_mode = EnumProperty(
        name="Mapping X",
        description="Specifies how the output value should be mapped to the [0; 1] range of the color ramp or image X axis",
        items=[("ORDERED", "Ordered", "", 1), ("PROPORTIONAL", "Proportional", "", 2)],
    )

    output_mapping_mode_y = EnumProperty(
        name="Mapping Y",
        description="Specifies how the output value should be mapped to the [0; 1] range of the image Y axis",
        items=[("ORDERED", "Ordered", "", 1), ("PROPORTIONAL", "Proportional", "", 2)],
    )

    influence = FloatProperty(
        name="Influence",
        description="Influence of this light effect on the final color of drones",
        default=1,
        soft_min=0,
        soft_max=1,
        min=0,
    )

    texture = PointerProperty(
        type=Texture,
        name="Texture",
        description=(
            "Texture of the light effect, used to hold the color ramp or the "
            "image that controls how the colors of the drones are determined"
        ),
        options={"HIDDEN"},
        update=texture_updated,
    )

    color_function = PointerProperty(
        type=ColorFunctionProperties,
        name="Color Function",
        description="Color function of the light effect",
    )

    mesh = PointerProperty(
        type=Object,
        name="Mesh",
        description=(
            'Mesh related to the light effect; used when the output is set to "Distance" or to limit the '
            'light effect to the inside or one side of this mesh when "Inside the mesh" or '
            '"Front side of plane" is checked'
        ),
        poll=object_has_mesh_data,
    )

    target = EnumProperty(
        name="Target",
        description=(
            "Specifies whether to apply this light effect to all drones or only"
            " to those drones that are inside the given mesh or are in front of"
            " the plane of the first face of the mesh. See also the 'Invert'"
            " property"
        ),
        items=[
            ("ALL", "All drones", "", 1),
            ("INSIDE_MESH", "Inside the mesh", "", 2),
            ("FRONT_SIDE", "Front side of plane", "", 3),
        ],
        default="ALL",
    )

    randomness = FloatProperty(
        name="Randomness",
        description=(
            "Offsets the output value of each drone randomly, wrapped around"
            "the edges of the color ramp; this property defines the maximum"
            "range of the offset"
        ),
        default=0,
        min=0,
        soft_min=0,
        soft_max=1,
        precision=2,
    )

    blend_mode = EnumProperty(
        name="Blend mode",
        description="Specifies the blending mode of this light effect",
        items=[
            (member.name, member.description, "", member.value) for member in BlendMode
        ],
        default=BlendMode.NORMAL.name,
    )

    invert_target = BoolProperty(
        name="Invert target",
        description=(
            "Invert the effect target; when checked, applies the effect to"
            " those drones that do not match the target"
        ),
        default=False,
        options=set(),
    )

    

    def apply_on_colors(
        self,
        colors: Sequence[MutableRGBAColor],
        positions: Sequence[Coordinate3D],
        mapping: Optional[list[int]],
        *,
        frame: int,
        random_seq: RandomSequence,
    ) -> None:
        

        def get_output_based_on_output_type(
            output_type: str,
            mapping_mode: str,
            output_function,
        ) -> tuple[Optional[list[Optional[float]]], Optional[float]]:
            
            outputs: Optional[list[Optional[float]]] = None
            common_output: Optional[float] = None
            order: Optional[list[int]] = None

            if output_type == "FIRST_COLOR":
                common_output = 0.0
            elif output_type == "LAST_COLOR":
                common_output = 1.0
            elif output_type == "TEMPORAL":
                common_output = time_fraction
            elif output_type_supports_mapping_mode(output_type):
                
                
                
                
                
                
                
                
                
                
                proportional = mapping_mode == "PROPORTIONAL"

                if output_type == "DISTANCE":
                    if self.mesh:
                        position_of_mesh = get_position_of_object(self.mesh)
                        sort_key = lambda index: distance_sq_of(
                            positions[index], position_of_mesh
                        )
                    else:
                        sort_key = None

                    
                else:
                    query_axes = (
                        OUTPUT_TYPE_TO_AXIS_SORT_KEY.get(output_type)
                        or OUTPUT_TYPE_TO_AXIS_SORT_KEY["default"]
                    )
                    if proportional:
                        
                        
                        sort_key = lambda index: query_axes(positions[index])[0]
                    else:
                        
                        
                        sort_key = lambda index: query_axes(positions[index])

                outputs = [1.0] * num_positions  
                order = list(range(num_positions))
                if num_positions > 1:
                    if proportional and sort_key is not None:
                        
                        
                        
                        
                        evaluated_sort_keys = [sort_key(i) for i in order]
                        min_value, max_value = (
                            min(evaluated_sort_keys),
                            max(evaluated_sort_keys),
                        )
                        diff = max_value - min_value
                        if diff > 0:
                            outputs = [
                                (value - min_value) / diff
                                for value in evaluated_sort_keys
                            ]
                    else:
                        if sort_key is not None:
                            order.sort(key=sort_key)

                        assert outputs is not None
                        for u, v in enumerate(order):
                            outputs[v] = u / (num_positions - 1)

            elif output_type == "INDEXED_BY_DRONES":
                
                if num_positions > 1:
                    np_m1 = num_positions - 1
                    outputs = [index / np_m1 for index in range(num_positions)]
                else:
                    common_output = 1.0

            elif output_type == "INDEXED_BY_FORMATION":
                
                if mapping is not None:
                    assert num_positions == len(mapping)

                    
                    
                    
                    

                    
                    
                    if None in mapping:
                        sorted_valid_mapping = sorted(
                            x for x in mapping if x is not None
                        )
                        np_m1 = max(len(sorted_valid_mapping) - 1, 1)
                        outputs = [
                            None if x is None else sorted_valid_mapping.index(x) / np_m1
                            for x in mapping
                        ]
                    
                    else:
                        np_m1 = max(num_positions - 1, 1)
                        outputs = [None if x is None else x / np_m1 for x in mapping]
                else:
                    
                    outputs = [None] * num_positions  

            elif output_type == "CUSTOM":
                absolute_path = abspath(output_function.path)
                module = load_module(absolute_path) if absolute_path else None
                if self.output_function.name:
                    fn = getattr(module, self.output_function.name)
                    outputs = [
                        fn(
                            frame=frame,
                            time_fraction=time_fraction,
                            drone_index=index,
                            formation_index=(
                                mapping[index] if mapping is not None else None
                            ),
                            position=positions[index],
                            drone_count=num_positions,
                        )
                        for index in range(num_positions)
                    ]
                else:
                    common_output = 1.0

            else:
                
                common_output = 1.0

            return outputs, common_output

        
        if not self.enabled or not self.contains_frame(frame):
            return

        time_fraction = (frame - self.frame_start) / max(self.duration - 1, 1)
        num_positions = len(positions)

        color_ramp = self.color_ramp
        color_image = self.color_image
        color_function_ref = self.color_function_ref
        new_color = [0.0] * 4

        outputs_x, common_output_x = get_output_based_on_output_type(
            self.output, self.output_mapping_mode, self.output_function
        )
        if color_image is not None:
            outputs_y, common_output_y = get_output_based_on_output_type(
                self.output_y, self.output_mapping_mode_y, self.output_function_y
            )

        
        
        condition = self._get_spatial_effect_predicate()

        for index, position in enumerate(positions):
            
            color = colors[index]

            
            
            if common_output_x is not None:
                output_x = common_output_x
            else:
                assert outputs_x is not None
                
                
                if outputs_x[index] is None:
                    continue
                output_x = outputs_x[index]
            assert isinstance(output_x, float)

            if color_image is not None:
                if common_output_y is not None:
                    output_y = common_output_y
                else:
                    assert outputs_y is not None
                    
                    
                    if outputs_y[index] is None:
                        continue
                    output_y = outputs_y[index]
                assert isinstance(output_y, float)

            
            if self.randomness != 0:
                offset_x = (random_seq.get_float(index) - 0.5) * self.randomness
                output_x = (offset_x + output_x) % 1.0
                if color_image is not None:
                    offset_y = (random_seq.get_float(index) - 0.5) * self.randomness
                    output_y = (offset_y + output_y) % 1.0

            
            
            alpha = max(
                min(self._evaluate_influence_at(position, frame, condition), 1.0), 0.0
            )

            if color_function_ref is not None:
                try:
                    new_color[:] = color_function_ref(
                        frame=frame,
                        time_fraction=time_fraction,
                        drone_index=index,
                        formation_index=(
                            mapping[index] if mapping is not None else None
                        ),
                        position=position,
                        drone_count=num_positions,
                    )
                except Exception as exc:
                    raise RuntimeError("ERROR_COLOR_FUNCTION") from exc
            elif color_image is not None:
                width, height = color_image.size
                pixels = self.get_image_pixels()

                x = int((width - 1) * output_x)
                y = int((height - 1) * output_y)
                offset = (x + y * width) * 4
                pixel_color = pixels[offset : offset + 4]

                
                
                
                if len(pixel_color) == len(new_color):
                    new_color[:] = pixel_color
            elif color_ramp:
                new_color[:] = color_ramp.evaluate(output_x)
            else:
                
                new_color[:] = (1.0, 1.0, 1.0, 1.0)

            new_color[3] *= alpha

            
            blend_in_place(new_color, color, BlendMode[self.blend_mode])  

    @property
    def color_ramp(self) -> Optional[ColorRamp]:
        
        return self.texture.color_ramp if self.type == "COLOR_RAMP" else None

    @property
    def color_image(self) -> Optional[Image]:
        
        return (
            self.texture.image
            if self.type == "IMAGE" and isinstance(self.texture, ImageTexture)
            else None
        )

    @color_image.setter
    def color_image(self, image: Optional[Image]):
        
        
        if not isinstance(self.texture, ImageTexture):
            self._remove_texture()
            self._create_texture()

        tex = self.texture
        if tex.image is not None:
            remove_if_unused(tex.image, from_=bpy.data.images)
        tex.image = image

        self.invalidate_color_image()

    @property
    def color_function_ref(self) -> Optional[Callable]:
        if self.type != "FUNCTION" or not self.color_function:
            return None
        absolute_path = abspath(self.color_function.path)
        module = load_module(absolute_path)
        return getattr(module, self.color_function.name, None)

    def contains_frame(self, frame: int) -> bool:
        
        return 0 <= (frame - self.frame_start) < self.duration

    def create_color_image(self, name: str, width: int, height: int) -> Image:
        
        self.color_image = bpy.data.images.new(name=name, width=width, height=height)
        return self.color_image

    def get_image_pixels(self) -> Sequence[float]:
        
        global _pixel_cache
        pixels = _pixel_cache.get(self.id)
        if pixels is None and self.color_image is not None:
            pixels = self.color_image.pixels[:]
            _pixel_cache.add(
                self.id, pixels, is_static=self.color_image.frame_duration <= 1
            )

        return pixels or ()

    @property
    def id(self) -> str:
        
        if not self.maybe_uuid_do_not_use:
            
            self.maybe_uuid_do_not_use = uuid4().hex
        return self.maybe_uuid_do_not_use

    def invalidate_color_image(self) -> None:
        
        global _pixel_cache
        try:
            _pixel_cache.remove(self.id)
        except KeyError:
            pass  

    def update_from(self, other: "LightEffect") -> None:
        
        
        self.enabled = other.enabled
        self.frame_start = other.frame_start
        self.duration = other.duration
        self.fade_in_duration = other.fade_in_duration
        self.fade_out_duration = other.fade_out_duration
        self.output = other.output
        self.output_y = other.output_y
        self.influence = other.influence
        self.mesh = other.mesh
        self.target = other.target
        self.randomness = other.randomness
        self.output_mapping_mode = other.output_mapping_mode
        self.output_mapping_mode_y = other.output_mapping_mode_y
        self.blend_mode = other.blend_mode
        self.type = other.type
        self.color_image = other.color_image
        self.invert_target = other.invert_target

        self.color_function.update_from(other.color_function)
        self.output_function.update_from(other.output_function)
        self.output_function_y.update_from(other.output_function_y)

        if self.color_ramp is not None:
            assert other.color_ramp is not None  
            update_color_ramp_from(self.color_ramp, other.color_ramp)

    def _evaluate_influence_at(
        self, position, frame: int, condition: Optional[Callable[[Coordinate3D], bool]]
    ) -> float:
        
        
        if condition and not condition(position):
            return 0.0

        influence = self.influence

        
        if self.fade_in_duration > 0:
            diff = frame - self.frame_start + 1
            if diff < self.fade_in_duration:
                influence *= diff / self.fade_in_duration

        
        if self.fade_out_duration > 0:
            diff = self.frame_end - frame
            if diff < self.fade_out_duration:
                influence *= diff / self.fade_out_duration

        return influence

    def _get_bvh_tree_from_mesh(self) -> Optional[BVHTree]:
        
        if self.mesh and self.mesh.data:
            depsgraph = bpy.context.evaluated_depsgraph_get()
            mesh = self.mesh

            obj = depsgraph.objects.get(mesh.name)
            if obj and obj.data:
                
                
                ev_mesh = cast(Mesh, obj.data)
                ev_mesh.transform(mesh.matrix_world)
                tree = BVHTree.FromObject(obj, depsgraph, deform=True)
                ev_mesh.transform(mesh.matrix_world.inverted())
            else:
                
                
                with use_b_mesh() as b_mesh:
                    b_mesh.from_mesh(mesh.data)
                    b_mesh.transform(mesh.matrix_world)
                    tree = BVHTree.FromBMesh(b_mesh)
            return tree

    def _get_plane_from_mesh(self) -> Optional[Plane]:
        
        if self.mesh:
            mesh = self.mesh.data
            local_to_world = self.mesh.matrix_world
            for polygon in mesh.polygons:
                normal = local_to_world.to_3x3() @ polygon.normal
                center = local_to_world @ polygon.center
                try:
                    return Plane.from_normal_and_point(normal, center)
                except Exception:
                    
                    pass

    def _get_spatial_effect_predicate(self) -> Optional[Callable[[Coordinate3D], bool]]:
        if self.target == "INSIDE_MESH":
            bvh_tree = self._get_bvh_tree_from_mesh()
            func = partial(test_containment, bvh_tree)
        elif self.target == "FRONT_SIDE":
            plane = self._get_plane_from_mesh()
            func = partial(test_is_in_front_of, plane)
        else:
            func = None

        if self.invert_target:
            func = negate(func or _always_true)

        return func

    def _create_texture(self) -> ImageTexture:
        
        tex = bpy.data.textures.new(
            name=f"Texture for light effect {self.name!r}", type="IMAGE"
        )
        tex.use_color_ramp = True
        tex.image = None

        
        elts = tex.color_ramp.elements
        for elt in elts:
            elt.color[3] = 1.0

        self.texture = tex
        return self.texture

    def _remove_texture(self) -> None:
        
        if isinstance(self.texture, ImageTexture):
            if self.texture.image is not None:
                remove_if_unused(self.texture.image, from_=bpy.data.images)

        remove_if_unused(self.texture, from_=bpy.data.textures)


class LightEffectCollection(PropertyGroup, ListMixin):
    

    
    entries = CollectionProperty(type=LightEffect)

    
    active_entry_index = IntProperty(
        name="Selected index",
        description="Index of the light effect currently being edited",
    )

    @property
    def active_entry(self) -> Optional[LightEffect]:
        
        index = self.active_entry_index
        if index is not None and index >= 0 and index < len(self.entries):
            return self.entries[index]
        else:
            return None

    @with_context
    def append_new_entry(
        self,
        name: str,
        frame_start: Optional[int] = None,
        duration: Optional[int] = None,
        *,
        select: bool = False,
        context: Optional[Context] = None,
    ) -> LightEffect:
        
        assert context is not None

        scene = context.scene

        fps = scene.render.fps
        if frame_start is None:
            
            
            frame_start = scene.frame_start

        if duration is None or duration <= 0:
            duration = fps * DEFAULT_LIGHT_EFFECT_DURATION

        entry: LightEffect = cast(LightEffect, self.entries.add())
        entry.type = "COLOR_RAMP"
        entry.frame_start = frame_start
        entry.duration = duration
        entry.name = name

        texture = entry._create_texture()

        
        if hasattr(scene, "skybrush") and hasattr(scene.skybrush, "led_control"):
            led_control = scene.skybrush.led_control
            elts = texture.color_ramp.elements
            last_elt = len(elts) - 1
            for i in range(3):
                elts[0].color[i] = led_control.primary_color[i]
                if last_elt > 0:
                    elts[last_elt].color[i] = led_control.secondary_color[i]

        if select:
            self.active_entry_index = len(self.entries) - 1

        return entry

    @with_context
    def duplicate_selected_entry(
        self,
        *,
        select: bool = False,
        context: Optional[Context] = None,
    ) -> LightEffect:
        
        active_entry = self.active_entry
        if not active_entry:
            raise RuntimeError("no selected entry in light effect list")

        index = self.active_entry_index
        assert index is not None

        entry = self.append_new_entry(
            name=pick_unique_name(active_entry.name, self.entries)
        )

        
        
        
        entry_to_duplicate = self.entries[index]

        entry.update_from(entry_to_duplicate)
        self.entries.move(len(self.entries) - 1, index + 1)

        if select:
            self.active_entry_index = index + 1

        return entry

    @property
    def frame_end(self) -> int:
        
        return (
            max(entry.frame_end for entry in self.entries)
            if self.entries
            else self.frame_start
        )

    @property
    def frame_start(self) -> int:
        
        return (
            min(entry.frame_start for entry in self.entries)
            if self.entries
            else bpy.context.scene.frame_start
        )

    def get_index_of_entry_containing_frame(self, frame: int) -> int:
        
        for index, entry in enumerate(self.entries):
            if entry.contains_frame(frame):
                return index
        return -1

    def iter_active_effects_in_frame(self, frame: int) -> Iterable[LightEffect]:
        
        
        
        for entry in self.entries:
            if entry.enabled and entry.influence > 0 and entry.contains_frame(frame):
                yield entry

    def _on_removing_entry(self, entry) -> bool:
        entry._remove_texture()
        return True
