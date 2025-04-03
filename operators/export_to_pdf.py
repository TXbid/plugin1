from bpy.props import BoolProperty, StringProperty, IntProperty

from sbstudio.model.file_formats import FileFormat

from .base import ExportOperator

__all__ = ("SkybrushPDFExportOperator",)







class SkybrushPDFExportOperator(ExportOperator):
    

    bl_idname = "export_scene.skybrush_pdf"
    bl_label = "Export Skybrush PDF"
    bl_options = {"REGISTER"}

    
    filter_glob = StringProperty(default="*.pdf", options={"HIDDEN"})
    filename_ext = ".pdf"

    
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

    plot_pos = BoolProperty(
        name="Plot positions",
        default=True,
        description=(
            "Include position plot. Uncheck to exclude position plot from the output."
        ),
    )
    plot_vel = BoolProperty(
        name="Plot velocities",
        default=True,
        description=(
            "Include velocity plot. Uncheck to exclude velocity plot from the output."
        ),
    )
    plot_drift = BoolProperty(
        name="Plot projected drift",
        default=True,
        description=(
            "Include projected drift plot. Uncheck to exclude projected drift plot from the output."
        ),
    )
    plot_nn = BoolProperty(
        name="Plot nearest neighbor",
        default=True,
        description=(
            "Include nearest neighbor plot. "
            "Uncheck to exclude nearest neighbor plot from the output."
        ),
    )
    plot_nnall = BoolProperty(
        name="Plot all nearest neighbors",
        default=False,
        description=(
            "Include all nearest neighbors plot. "
            "Uncheck to exclude all nearest neighbor plot from the output."
        ),
    )
    plot_indiv = BoolProperty(
        name="Create individual drone plots",
        default=False,
        description=(
            "Include individual drone plots."
            "Uncheck to exclude per-drone plots from the output."
        ),
    )

    def get_format(self) -> FileFormat:
        
        return FileFormat.PDF

    def get_operator_name(self) -> str:
        return ".pdf validation plot exporter"

    def get_settings(self):
        plots = {
            "pos": self.plot_pos,
            "vel": self.plot_vel,
            "drift": self.plot_drift,
            "nn": self.plot_nn,
            "nnall": self.plot_nnall,
            "indiv": self.plot_indiv,
        }
        plots = ["stats"] + [key for key, value in plots.items() if value]
        return {
            "output_fps": self.output_fps,
            "light_output_fps": self.light_output_fps,
            "plots": plots,
        }
