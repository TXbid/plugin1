from dataclasses import dataclass, field
from typing import Dict

__all__ = ("TimeMarkers",)


@dataclass
class TimeMarkers:
    

    markers: Dict[str, float] = field(default_factory=dict)
    """The dictionary of time markers where keys represent marker names and
    values represent time in seconds."""

    def as_dict(self, ndigits: int = 3):
        
        result = {
            "items": [
                {"name": key, "time": round(value, ndigits=ndigits)}
                for key, value in self.markers.items()
            ],
            "version": 1,
        }

        return result
