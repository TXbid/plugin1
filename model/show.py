from bpy.props import PointerProperty
from bpy.types import PropertyGroup

from .formations_panel import FormationsPanelProperties
from .led_control import LEDControlPanelProperties
from .light_effects import LightEffectCollection
from .safety_check import SafetyCheckProperties
from .settings import DroneShowAddonFileSpecificSettings
from .storyboard import Storyboard

__all__ = ("DroneShowAddonProperties",)


class DroneShowAddonProperties(PropertyGroup):
    

    formations: FormationsPanelProperties = PointerProperty(
        type=FormationsPanelProperties
    )
    led_control: LEDControlPanelProperties = PointerProperty(
        type=LEDControlPanelProperties
    )
    light_effects: LightEffectCollection = PointerProperty(type=LightEffectCollection)
    safety_check: SafetyCheckProperties = PointerProperty(type=SafetyCheckProperties)
    settings: DroneShowAddonFileSpecificSettings = PointerProperty(
        type=DroneShowAddonFileSpecificSettings
    )
    storyboard: Storyboard = PointerProperty(type=Storyboard)
