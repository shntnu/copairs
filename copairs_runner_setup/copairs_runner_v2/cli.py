#!/usr/bin/env python
# copairs_runner/cli.py  ------------------------------------
"""
Universal entry-point.

• LOCAL   ──  python -m copairs_runner.cli -m data.path=a.csv,b.csv seed=1,2
• BATCH   ──  (Nextflow/Snakemake)  python -m copairs_runner.cli data.path=a.csv seed=1
"""

from pathlib import Path

import hydra
import omegaconf
from copairs_runner.config import RunnerCfg
from copairs_runner.runner import CopairsRunner

# Path to the top-level conf/ folder (adjust if you move it)
CONF_DIR = Path(__file__).resolve().parents[2] / "conf"


@hydra.main(
    version_base="1.3",
    config_path=str(CONF_DIR),
    config_name="base",
)
def main(cfg: omegaconf.DictConfig) -> None:
    """Validate Hydra config → Pydantic model → run once."""
    validated = RunnerCfg.model_validate(
        omegaconf.OmegaConf.to_container(cfg, resolve=True, throw_on_missing=True)
    )
    CopairsRunner(validated).run()


if __name__ == "__main__":
    main()
