from operator import attrgetter
from typing import Optional, Sequence

from sbstudio.utils import simplify_path

from .color import Color4D

__all__ = ("LightProgram",)


def _simplify_color_distance_func(keypoints, start, end):
    
    timespan = end.t - start.t

    result = []

    for point in keypoints:
        ratio = (point.t - start.t) / timespan if timespan > 0 else 0.5
        interp = (
            start.r + ratio * (end.r - start.r),
            start.g + ratio * (end.g - start.g),
            start.b + ratio * (end.b - start.b),
        )

        diff = max(
            abs(interp[0] - point.r),
            abs(interp[1] - point.g),
            abs(interp[2] - point.b),
        )
        result.append(diff)

    return result


class LightProgram:
    

    def __init__(self, colors: Optional[Sequence[Color4D]] = None):
        self.colors = sorted(colors, key=attrgetter("t")) if colors is not None else []

    def append(self, color: Color4D) -> None:
        
        if self.colors and self.colors[-1].t > color.t:
            raise ValueError("New color must come after existing light code in time")
        self.colors.append(color)

    def as_dict(self, ndigits: int = 3):
        
        return {
            "data": [
                [
                    round(color.t, ndigits=ndigits),
                    [int(color.r), int(color.g), int(color.b)],
                    1 if color.is_fade else 0,
                ]
                for color in self.colors
            ],
            "version": 1,
        }

    def simplify(self) -> "LightProgram":
        
        new_items = simplify_path(
            list(self.colors), eps=4, distance_func=_simplify_color_distance_func
        )

        return LightProgram(new_items)
