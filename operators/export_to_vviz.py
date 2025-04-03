from typing import Any, Dict

from bpy.props import BoolProperty, IntProperty, StringProperty

from sbstudio.model.file_formats import FileFormat

from .base import ExportOperator

__all__ = ("VVIZExportOperator",)







class VVIZExportOperator(ExportOperator):
    

    bl_idname = "export_scene.vviz"
    bl_label = "Export Finale 3D VVIZ format"
    bl_options = {"REGISTER"}

    
    filter_glob = StringProperty(default="*.vviz", options={"HIDDEN"})
    filename_ext = ".vviz"

    
    output_fps = IntProperty(
        name="Trajectory FPS",
        default=4,
        description="Number of samples to take from trajectories per second",
    )

    
    light_output_fps = IntProperty(
        name="Light FPS",
        default=24,
        description="Number of samples to take from light programs per second",
    )

    
    use_yaw_control = BoolProperty(
        name="Export yaw",
        description="Specifies whether the yaw angle of each drone should be controlled during the show",
        default=False,
    )

    def get_format(self) -> FileFormat:
        return FileFormat.VVIZ

    def get_operator_name(self) -> str:
        return "Finale 3D VVIZ exporter"

    def get_settings(self) -> Dict[str, Any]:
        return {
            "output_fps": self.output_fps,
            "light_output_fps": self.light_output_fps,
            "use_yaw_control": self.use_yaw_control,
        }
