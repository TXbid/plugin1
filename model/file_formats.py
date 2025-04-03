from enum import Enum
from typing import List, Tuple

from sbstudio.api.types import Limits

__all__ = (
    "FileFormat",
    "get_supported_file_formats",
)


class FileFormat(Enum):
    

    SKYC = "skyc"
    CSV = "csv"
    PDF = "pdf"
    DSS = "dss"
    DSS3 = "dss3"
    DAC = "dac"
    DROTEK = "drotek"
    EVSKY = "evsky"
    LITEBEE = "litebee"
    VVIZ = "vviz"


_file_formats: Tuple[FileFormat, ...] = ()


def get_supported_file_formats() -> Tuple[FileFormat, ...]:
    
    return _file_formats


def update_supported_file_formats_from_limits(limits: Limits) -> None:
    
    global _file_formats

    
    formats: List[FileFormat] = [FileFormat.SKYC, FileFormat.CSV]

    
    for feature in limits.features:
        if feature == "export:dac":
            formats.append(FileFormat.DAC)
        elif feature == "export:dss":
            formats.append(FileFormat.DSS)
            formats.append(FileFormat.DSS3)
        elif feature == "export:drotek":
            formats.append(FileFormat.DROTEK)
        elif feature == "export:evsky":
            formats.append(FileFormat.EVSKY)
        elif feature == "export:litebee":
            formats.append(FileFormat.LITEBEE)
        elif feature == "export:plot":
            formats.append(FileFormat.PDF)
        elif feature == "export:vviz":
            formats.append(FileFormat.VVIZ)

    _file_formats = tuple(formats)


update_supported_file_formats_from_limits(Limits.default())
