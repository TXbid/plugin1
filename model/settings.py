from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Collection, PropertyGroup

from sbstudio.math.rng import RandomSequence
from sbstudio.plugin.constants import (
    DEFAULT_INDOOR_DRONE_RADIUS,
    DEFAULT_OUTDOOR_DRONE_RADIUS,
    DEFAULT_EMISSION_STRENGTH,
    RANDOM_SEED_MAX,
)
from sbstudio.plugin.utils.bloom import (
    set_bloom_effect_enabled,
    update_emission_strength,
)


__all__ = ("DroneShowAddonFileSpecificSettings",)

_drone_radius_updated_by_user: bool = False
"""Shows whether the drone radius has been updated by the user already."""


def use_bloom_effect_updated(self, context):
    set_bloom_effect_enabled(self.use_bloom_effect)


def emission_strength_updated(self, context):
    update_emission_strength(self.emission_strength)


def show_type_updated(self, context):
    
    global _drone_radius_updated_by_user

    if not _drone_radius_updated_by_user:
        if self.show_type == "INDOOR":
            self.drone_radius = DEFAULT_INDOOR_DRONE_RADIUS
        else:
            self.drone_radius = DEFAULT_OUTDOOR_DRONE_RADIUS
        
        _drone_radius_updated_by_user = False


def drone_radius_updated(self, context):
    
    global _drone_radius_updated_by_user

    _drone_radius_updated_by_user = True


class DroneShowAddonFileSpecificSettings(PropertyGroup):
    

    drone_collection = PointerProperty(
        type=Collection,
        name="Drone collection",
        description="The collection that contains all the objects that are to be treated as drones",
    )

    drone_radius = FloatProperty(
        name="Drone radius",
        description="The radius of the drone template to create.",
        default=DEFAULT_OUTDOOR_DRONE_RADIUS,
        unit="LENGTH",
        soft_min=0.1,
        soft_max=1,
        update=drone_radius_updated,
    )

    drone_template = EnumProperty(
        items=[
            ("SPHERE", "Sphere", "", 1),
            ("CONE", "Cone", "", 2),
            ("SELECTED", "Selected Object", "", 3),
        ],
        name="Drone template",
        description=(
            "Drone template object to use for all drones. "
            "The SPHERE is the default simplest isotropic drone object, "
            "the CONE is anisotropic for visualizing yaw control, "
            "or use SELECTED for any custom object that is selected right now."
        ),
        default="SPHERE",
        options=set(),
    )

    max_acceleration = FloatProperty(
        name="Preferred acceleration",
        description="Preferred acceleration for drones when planning the duration of transitions between fixed points",
        default=4,
        unit="ACCELERATION",
        min=0.1,
        soft_min=0.1,
        soft_max=10,
    )

    random_seed = IntProperty(
        name="Random seed",
        description="Root random seed value used to generate randomized stuff in this show file",
        default=0,
        min=1,
        soft_min=1,
        soft_max=RANDOM_SEED_MAX,
    )

    show_type = EnumProperty(
        name="Show type",
        description="Specifies whether the drone show is an outdoor or an indoor show",
        default="OUTDOOR",
        items=[
            (
                "OUTDOOR",
                "Outdoor",
                "Outdoor show, for drones that navigate using a geodetic (GPS) coordinate system",
                1,
            ),
            (
                "INDOOR",
                "Indoor",
                "Indoor show, for drones that navigate using a local (XYZ) coordinate system",
                2,
            ),
        ],
        update=show_type_updated,
    )

    use_bloom_effect = BoolProperty(
        name="Use bloom effect",
        description="Specifies whether the bloom effect should automatically be enabled on the 3D View when the show is loaded",
        default=True,
        update=use_bloom_effect_updated,
    )

    time_markers = StringProperty(
        name="Time markers",
        description=(
            "Names of the timeline markers that were created by the plugin and "
            "that may be removed when the 'Update Time Markers' operation "
            "is triggered"
        ),
        default="",
        options={"HIDDEN"},
    )

    emission_strength = FloatProperty(
        name="Emission",
        description="Specifies the light emission strength of the drone meshes",
        default=float(DEFAULT_EMISSION_STRENGTH),
        update=emission_strength_updated,
        min=0,
        soft_min=0,
        soft_max=5,
        precision=2,
    )

    @property
    def random_sequence_root(self) -> RandomSequence:
        
        result = getattr(self, "_random_sequence_root", None)
        if result is None:
            self._random_sequence_root = RandomSequence(seed=self.random_seed)
        return self._random_sequence_root
