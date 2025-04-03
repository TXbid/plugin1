from bpy.props import BoolProperty, IntProperty, StringProperty

from sbstudio.model.file_formats import FileFormat

from .base import ExportOperator

__all__ = ("SkybrushExportOperator",)







class SkybrushExportOperator(ExportOperator):
    

    bl_idname = "export_scene.skybrush"
    bl_label = "Export Skybrush SKYC"
    bl_options = {"REGISTER"}

    
    filter_glob = StringProperty(default="*.skyc", options={"HIDDEN"})
    filename_ext = ".skyc"

    
    output_fps = IntProperty(
        name="Trajectory FPS",
        default=4,
        description="Number of samples to take from trajectories per second",
    )

    
    light_output_fps = IntProperty(
        name="Light FPS",
        default=4,
        description="Number of samples to take from light programs per second",
    )

    
    use_yaw_control = BoolProperty(
        name="Export yaw",
        description="Specifies whether the yaw angle of each drone should be controlled during the show",
        default=False,
    )

    
    export_cameras = BoolProperty(
        name="Export cameras",
        description="Specifies whether cameras defined in Blender should be exported into the show file",
        default=False,
    )

    def get_format(self) -> FileFormat:
        
        return FileFormat.SKYC

    def get_operator_name(self) -> str:
        return ".skyc exporter"

    def get_settings(self):
        return {
            "output_fps": self.output_fps,
            "light_output_fps": self.light_output_fps,
            "use_yaw_control": self.use_yaw_control,
            "export_cameras": self.export_cameras,
        }
