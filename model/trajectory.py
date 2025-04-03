from operator import attrgetter
from typing import List, Optional, Sequence, TypeVar

from .point import Point3D, Point4D

__all__ = ("Trajectory",)

C = TypeVar("C", bound="Trajectory")


class Trajectory:
    

    def __init__(self, points: Sequence[Point4D] = []):
        self.points = sorted(points, key=attrgetter("t"))

    @property
    def first_point(self) -> Optional[Point4D]:
        return self.points[0] if self.points else None

    def append(self, point: Point4D) -> None:
        
        if self.points and self.points[-1].t >= point.t:
            raise ValueError("New point must come after existing trajectory in time")
        self.points.append(point)

    def as_dict(self, ndigits: int = 3, *, version: int = 1):
        
        if version == 0:
            
            
            
            
            
            return {
                "points": [
                    [
                        round(point.t, ndigits=ndigits),
                        round(point.x, ndigits=ndigits),
                        round(point.y, ndigits=ndigits),
                        round(point.z, ndigits=ndigits),
                    ]
                    for point in self.points
                ],
                "version": 0,
            }
        else:
            
            return {
                "points": [
                    [
                        round(point.t, ndigits=ndigits),
                        [
                            round(point.x, ndigits=ndigits),
                            round(point.y, ndigits=ndigits),
                            round(point.z, ndigits=ndigits),
                        ],
                        [],
                    ]
                    for point in self.points
                ],
                "version": 1,
            }

    @property
    def duration(self) -> float:
        

        if len(self.points) < 2:
            return 0

        return self.points[-1].t - self.points[0].t

    def shift_in_place(self: C, offset: Point3D) -> C:
        
        self.points = [
            Point4D(
                t=point.t,
                x=point.x + offset.x,
                y=point.y + offset.y,
                z=point.z + offset.z,
            )
            for point in self.points
        ]
        return self

    def shift_time_in_place(self: C, delta: float) -> C:
        
        self.points = [
            Point4D(t=point.t + delta, x=point.x, y=point.y, z=point.z)
            for point in self.points
        ]
        return self

    def simplify_in_place(self: C) -> C:
        new_points: List[Point4D] = []
        if not self.points:
            return self

        first_point = self.points[0]

        
        last_point = Point4D(
            t=first_point.t - 1,
            x=first_point.x - 1,
            y=first_point.y - 1,
            z=first_point.z - 1,
        )

        keep_next = False
        for point in self.points:
            prev_is_same = (
                last_point.x == point.x
                and last_point.y == point.y
                and last_point.z == point.z
            )
            if keep_next or not prev_is_same:
                new_points.append(point)
            else:
                new_points[-1] = point
            keep_next = not prev_is_same
            last_point = point

        self.points = new_points
        return self
