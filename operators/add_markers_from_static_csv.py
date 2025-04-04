import csv
import logging

from numpy import array, zeros
from numpy.typing import NDArray
from typing import Dict, Tuple

from bpy.path import ensure_ext
from bpy.props import BoolProperty, StringProperty
from bpy_extras.io_utils import ImportHelper

from .base import StaticMarkerCreationOperator, PointsAndColors

__all__ = ("AddMarkersFromStaticCSVOperator",)

log = logging.getLogger(__name__)






class AddMarkersFromStaticCSVOperator(StaticMarkerCreationOperator, ImportHelper):
    

    bl_idname = "skybrush.add_markers_from_static_csv"
    bl_label = "Import Skybrush static CSV"
    bl_options = {"REGISTER"}

    import_colors = BoolProperty(
        name="Import colors",
        description="Import colors from the CSV file into a light effect",
        default=True,
    )

    
    filter_glob = StringProperty(default="*.csv", options={"HIDDEN"})
    filename_ext = ".csv"

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}

    def _create_points(self, context) -> PointsAndColors:
        filepath = ensure_ext(self.filepath, self.filename_ext)
        point_color_pairs = parse_static_csv_zip(filepath)

        points = zeros((len(point_color_pairs), 3), dtype=float)
        colors = zeros((len(point_color_pairs), 4), dtype=float)

        for index, (p, c) in enumerate(point_color_pairs.values()):
            points[index, :] = p
            colors[index, :] = c / 255

        return PointsAndColors(points, colors)


Item = Tuple[NDArray[float], NDArray[int]]


def parse_static_csv_zip(filename: str) -> Dict[str, Item]:
    
    result: Dict[str, Item] = {}
    header_passed: bool = False

    with open(filename, "r") as csv_file:
        for row in csv.reader(csv_file, delimiter=","):
            
            if not row:
                continue

            
            if not header_passed:
                header_passed = True
                if row[0].lower().startswith("name"):
                    continue

            
            try:
                name = row[0]
                x, y, z = (float(value) for value in row[1:4])
                if len(row) > 4:
                    r, g, b = (int(value) for value in row[4:7])
                else:
                    r, g, b = 255, 255, 255
                header_passed = True
            except Exception:
                raise RuntimeError(
                    f"Invalid content in input CSV file {filename!r}, row {row!r}"
                ) from None

            
            if name in result:
                raise RuntimeError(f"Duplicate object name in input CSV file: {name}")

            
            result[name] = (
                array((x, y, z), dtype=float),
                array((r, g, b, 255), dtype=int),
            )

    return result
