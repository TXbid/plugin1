from dataclasses import dataclass
from mathutils import Vector

__all__ = (
    "Color3D",
    "Color4D",
)


@dataclass
class Color3D:
    

    
    r: int

    
    g: int

    
    b: int

    def at_time(self, t: float, is_fade: bool = True) -> "Color4D":
        
        return Color4D(t=t, r=self.r, g=self.g, b=self.b, is_fade=is_fade)

    def as_vector(self) -> Vector:
        
        return Vector((self.r / 255, self.g / 255, self.b / 255, 1))


@dataclass
class Color4D:
    

    
    t: float

    
    r: int

    
    g: int

    
    b: int

    
    
    
    is_fade: bool = True

    def as_vector(self) -> Vector:
        
        return Vector((self.r / 255, self.g / 255, self.b / 255, 1))
