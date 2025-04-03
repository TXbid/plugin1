from typing import List, Optional, Union

from .point import Point3D, Point4D

__all__ = ("PointCloud",)


class PointCloud:
    

    def __init__(self, points: Optional[List[Union[Point3D, Point4D]]] = None):
        self._points = [Point3D(x=p.x, y=p.y, z=p.z) for p in points or []]

    def __getitem__(self, item):
        return self._points[item]

    def append(self, point: Union[Point3D, Point4D]) -> None:
        
        self._points.append(Point3D(x=point.x, y=point.y, z=point.z))

    def as_list(self, ndigits: int = 3):
        
        return [
            [
                round(point.x, ndigits=ndigits),
                round(point.y, ndigits=ndigits),
                round(point.z, ndigits=ndigits),
            ]
            for point in self._points
        ]

    @property
    def count(self):
        
        return len(self._points)
