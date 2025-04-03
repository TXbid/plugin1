from bpy.props import BoolProperty, StringProperty
from bpy.types import AddonPreferences, Context
from typing import Optional

from sbstudio.plugin.operators.set_server_url import SetServerURLOperator
from sbstudio.plugin.utils import with_context

__all__ = ("DroneShowAddonGlobalSettings",)


class DroneShowAddonGlobalSettings(AddonPreferences):
    

    bl_idname = "ui_skybrush_studio"

    license_file = StringProperty(
        name="License file",
        description=(
            "Full path to the license file to be used as the API Key "
            "(this feature is currently not available)"
        ),
        subtype="FILE_PATH",
    )

    api_key = StringProperty(
        name="API Key",
        description="API Key that is used when communicating with the Skybrush Studio server",
    )

    server_url = StringProperty(
        name="Server URL",
        description=(
            "URL of a dedicated Skybrush Studio server if you are using a "
            "dedicated server. Leave it empty to use the server provided for "
            "the community for free"
        ),
    )

    enable_experimental_features = BoolProperty(
        name="Enable experimental features",
        description=(
            "Whether to enable experimental features in the add-on. Experimental "
            "features are currently in a testing phase and may be changed, "
            "disabled or removed in future versions without notice"
        ),
        default=False,
    )

    def draw(self, context):
        layout = self.layout

        layout.prop(self, "api_key")
        
        layout.prop(self, "server_url")

        row = layout.row()
        op = row.operator(SetServerURLOperator.bl_idname, text="Use local server")
        op.url = "http://localhost:8000"

        op = row.operator(SetServerURLOperator.bl_idname, text="Use community server")
        op.url = ""

        layout.prop(self, "enable_experimental_features")


@with_context
def get_preferences(context: Optional[Context] = None) -> DroneShowAddonGlobalSettings:
    
    assert context is not None
    prefs = context.preferences
    return prefs.addons[DroneShowAddonGlobalSettings.bl_idname].preferences
