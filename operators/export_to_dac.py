from bpy.props import StringProperty

from sbstudio.model.file_formats import FileFormat

from .base import ExportOperator

__all__ = ("DACExportOperator",)







class DACExportOperator(ExportOperator):
    

    bl_idname = "export_scene.dac"
    bl_label = "Export DAC"
    bl_options = {"REGISTER"}

    
    filter_glob = StringProperty(default="*.zip", options={"HIDDEN"})
    filename_ext = ".zip"

    def get_format(self) -> FileFormat:
        
        return FileFormat.DAC

    def get_operator_name(self) -> str:
        return ".dac exporter"

    def get_settings(self):
        return {"output_fps": 30, "light_output_fps": 30}
