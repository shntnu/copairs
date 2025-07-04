import yaml
import hydra
import omegaconf
from copairs_runner.config import RunnerCfg
from copairs_runner.runner import CopairsRunner

with open("conf/jobs_list.yaml") as fh:
    jobs = yaml.safe_load(fh)["jobs"]

for job in jobs:
    overrides = job["overrides"]
    composed = hydra.compose(config_name="base", overrides=overrides)
    cfg = RunnerCfg.model_validate(omegaconf.OmegaConf.to_container(composed))
    print(f"\n>>> {job['name']}")
    CopairsRunner(cfg).run()
