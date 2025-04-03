from typing import MutableSequence, Tuple, Union

__all__ = ("Coordinate3D", "RGBAColor", "Rotation3D")



Coordinate3D = Tuple[float, float, float]


RGBAColor = Tuple[float, float, float, float]


MutableRGBAColor = MutableSequence[float]


RGBAColorLike = Union[RGBAColor, MutableRGBAColor]


Rotation3D = Tuple[float, float, float]
