# runner.py
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from copairs import map  # underlying library

from .steps import run_step
from .config import RunnerCfg

log = logging.getLogger("copairs-runner")


class CopairsRunner:
    def __init__(self, cfg: RunnerCfg):
        self.cfg = cfg

    # ---------- IO ----------
    def _load(self) -> pd.DataFrame:
        path = self.cfg.data.path
        log.info("Loading %s", path)
        return pd.read_parquet(path) if path.suffix == ".parquet" else pd.read_csv(path)

    def _save_results(self, df: pd.DataFrame, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)

    # ---------- pipeline ----------
    def run(self):
        df = self._load()

        for step in self.cfg.preprocessing:
            log.info("Running step: %s", step.type)
            df = run_step(df, step.type, step.params)

        ap = map.average_precision(df, **self.cfg.average_precision.model_dump())

        out_path = Path(self.cfg.output.path)  # set in YAML
        self._save_results(ap, out_path)

        if self.cfg.mean_average_precision:
            mapr = map.mean_average_precision(
                ap, **self.cfg.mean_average_precision.model_dump()
            )
            self._save_results(mapr, out_path.with_suffix(".mapr.csv"))

        if self.cfg.plotting and self.cfg.plotting.enabled:
            self._plot(ap if not self.cfg.mean_average_precision else mapr)

    # ---------- plotting ----------
    def _plot(self, df):
        import matplotlib.pyplot as plt

        plt.figure(figsize=self.cfg.plotting.figsize, dpi=self.cfg.plotting.dpi)
        plt.scatter(df["mAP"], -np.log10(df["pvalue"]))
        plt.xlabel("mAP")
        plt.ylabel("-log10(p)")
        plt.tight_layout()
        plt.savefig(self.cfg.plotting.path)
