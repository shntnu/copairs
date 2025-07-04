# config.py
from typing import Any, Dict, List, Optional
from pathlib import Path

from pydantic import Field, BaseModel


class DataCfg(BaseModel):
    path: Path
    metadata_regex: str = Field("^Metadata", min_length=1)


class PreprocessStep(BaseModel):
    type: str
    params: Dict[str, Any] = {}


class AvgPrecCfg(BaseModel):
    pos_sameby: List[str]
    pos_diffby: List[str]
    neg_sameby: List[str]
    neg_diffby: List[str]

    # any optional AP args are accepted transparently
    class Config:
        extra = "allow"


class MeanAvgPrecCfg(BaseModel):
    sameby: List[str]
    null_size: int
    threshold: float
    seed: int

    class Config:
        extra = "allow"


class PlotCfg(BaseModel):
    enabled: bool = False
    path: Path = Path("output/map_plot.png")
    figsize: tuple[int, int] = (8, 6)
    dpi: int = 100

    class Config:
        extra = "allow"


class RunnerCfg(BaseModel):
    data: DataCfg
    preprocessing: List[PreprocessStep] = []
    average_precision: AvgPrecCfg
    mean_average_precision: Optional[MeanAvgPrecCfg] = None
    plotting: Optional[PlotCfg] = None
