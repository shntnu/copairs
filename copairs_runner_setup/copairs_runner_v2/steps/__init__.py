# steps/__init__.py
from typing import Dict, Callable

import pandas as pd

_STEP_REG: Dict[str, Callable[[pd.DataFrame, dict], pd.DataFrame]] = {}


def register(name: str):
    def decorator(fn: Callable[[pd.DataFrame, dict], pd.DataFrame]):
        _STEP_REG[name] = fn
        return fn

    return decorator


def run_step(df: pd.DataFrame, step_type: str, params: dict) -> pd.DataFrame:
    if step_type not in _STEP_REG:
        raise KeyError(f"Unknown preprocessing step: {step_type}")
    return _STEP_REG[step_type](df.copy(), params)


# --- example step implementation -------
@register("filter")
def _filter(df: pd.DataFrame, p: dict) -> pd.DataFrame:
    return df.query(p["query"])
