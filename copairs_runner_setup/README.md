# Copairs Runner v2

> ⚠️ **CRITICAL WARNING: EXPERIMENTAL & UNTESTED CODE** ⚠️
> 
> **DO NOT USE IN PRODUCTION**
> 
> This is a work-in-progress prototype that has NOT been tested. It likely contains:
> - Missing dependencies and import errors
> - Incomplete implementations
> - Bugs and edge cases
> - Untested code paths
> 
> This codebase is provided as a reference architecture only. Significant development
> and testing work is required before any production use.

## Problem Statement — Why this codebase exists

High-content imaging screens (e.g. Cell Painting) can generate hundreds of thousands of cellular phenotypes per experiment. To quantify the biological signal in those data, we run copairs, an in-memory Python pipeline that
	1.	loads a feature table (.csv/.parquet) and accompanying metadata,
	2.	applies a configurable series of DataFrame preprocessing steps,
	3.	computes average precision (AP) and mean average precision (mAP) scores that tell us “how well do replicates of the same treatment look alike compared with everything else?”,
	4.	writes results + diagnostic plots to disk.

The scientific questions are straightforward—Which compounds are phenotypically active? How reproducible is a screen?—but the engineering challenges are not:
- Reproducibility & provenance: Every run must be traceable (exact parameters, code version, input hashes) so results can be cited in papers and audits.
- Parameter exploration: We often sweep dozens of input files, dose thresholds, and AP/mAP knobs; manually typing CLI overrides is error-prone.
- Scalability: A small pilot executes on a laptop; a full-scale screen may require hundreds of CPU-hours on an HPC cluster or AWS Batch.
- Maintainability: The DataFrame pipeline evolves weekly; we need typed configs, unit-tested steps, and minimal boilerplate to add new metrics.

This codebase is the opinionated answer to those needs. It packages the core analytical logic into a lightweight, Pydantic-validated runner; uses Hydra for config composition and local sweeps; and offers two interchangeable orchestration layers—Nextflow or Snakemake—for cluster/cloud fan-out. The goal is to let scientists focus on biological interpretation while giving engineers the hooks they need for reproducible, scalable computation.

---

## **0. Top-level repo layout**

```
copairs_runner_setup/
├── copairs_runner_v2/          # <= Python package
│   ├── __init__.py
│   ├── config.py            # Pydantic v2 models
│   ├── steps/               # pluggable DataFrame ops
│   │   ├── __init__.py      # step registry
│   │   └── *.py             # individual steps
│   ├── runner.py            # thin orchestrator
│   └── cli.py               # Hydra entry-point (single-run)
│
├── conf/
│   ├── base.yaml            # default config (mirrors RunnerCfg)
│   ├── jobs_list.yaml       # heterogeneous sweep (pattern C)
│   ├── sweep_product.yaml   # grid sweep (pattern A)   ← optional
│   └── sweep_params.yaml    # grid sweep (pattern B)   ← optional
│
├── run_jobs_loop.py         # Python loop over jobs_list.yaml
│                             #  (good for local dev)
├── main.nf                  # Nextflow fan-out (pattern 2)
└── Snakefile                # Snakemake fan-out (alt. to Nextflow)
```

---

## **1. Core facts that never change**

| Concern                        | Solution                                   | Notes                                             |
| ------------------------------ | ------------------------------------------ | ------------------------------------------------- |
| **Typed config & validation**  | copairs_runner/config.py (Pydantic v2)     | Fast, runtime-checked; raise if YAML/CLI invalid. |
| **In-memory pipeline**         | copairs_runner/runner.py + steps/ registry | Thin orchestrator; easy unit tests.               |
| **Future "heavier" framework** | *drop-in* Kedro (QuantumBlack) later       | Swap when you need DataCatalog & multiple DAGs.   |

---

## **2. Execution options (choose at launch time, no code edits)**

| #     | For …                                   | Command                                                                                                        | What fans-out                                | Provenance granularity                              |
| ----- | --------------------------------------- | -------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | --------------------------------------------------- |
| **1** | Quick laptop grids (≤ ~300 runs)        | `python -m copairs_runner.cli -m data.path=a,b seed=1,2` *or* `python -m copairs_runner.cli -m +sweep_product` | Hydra multirun                               | One Hydra "outputs/…" folder with subdirs           |
| **2** | Heterogeneous jobs while prototyping    | `python run_jobs_loop.py`                                                                                      | Python loop over jobs_list.yaml              | One log line per job; still single Hydra run each   |
| **3** | HPC / cloud scale, retry, cost tracking | `nextflow run main.nf -profile slurm`                                                                          | Nextflow channel (reads same jobs_list.yaml) | **One Nextflow task per job** → full trace, retry   |
| **4** | Same as #3 but team prefers Python DSL  | `snakemake -j 200 --profile awsbatch`                                                                          | Snakemake rule grid: (parses jobs_list.yaml) | Per-rule job stats; simpler syntax for Python users |

*Choosing #3 vs #4 is purely taste & infra availability; both call `python cli.py ...` once per row.*

---

## **3. Key file excerpts (ready to copy-paste)**

### **3-a. conf/jobs_list.yaml — heterogeneous sweep**

```yaml
jobs:
  - name: file1_lowdose_seed1
    overrides:
      - data.path=data/file1.csv
      - preprocessing[0].params.query="dose < 1"
      - mean_average_precision.seed=1

  - name: file2_highdose_seed42
    overrides:
      - data.path=data/file2.csv
      - preprocessing[0].params.query="dose >= 1"
      - mean_average_precision.seed=42
      - mean_average_precision.threshold=0.10
```

### **3-b. run_jobs_loop.py — local loop driver**

```python
import yaml, hydra, omegaconf
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
```

### **3-c. main.nf — Nextflow fan-out**

```groovy
nextflow.enable.dsl = 2
params.jobs_yaml = 'conf/jobs_list.yaml'

Channel
    .fromPath(params.jobs_yaml)
    .map { yaml ->
        def txt = "python - <<'PY'\nimport yaml, json, sys, pathlib; " +
                  "import yaml as y; print('\\n'.join(json.dumps(j) " +
                  "for j in y.safe_load(open(sys.argv[1]))['jobs']))\nPY\n${yaml}"
        txt.execute().text.readLines()
    }
    .flatten()
    .map { line -> groovy.json.JsonSlurper.newInstance().parseText(line) }
    .set { JOBS }

process copairs {
    tag   { job.name }
    input:
      val job from JOBS
    script:
      """
      python cli.py ${ job.overrides.join(' ') }
      """
}
```

### **3-d. Snakefile — Snakemake fan-out (optional)**

```python
import yaml, os

with open("conf/jobs_list.yaml") as fh:
    JOBS = yaml.safe_load(fh)["jobs"]

rule all:
    input: expand("results/{name}.done", name=[j["name"] for j in JOBS])

rule grid:
    output: touch("results/{name}.done")
    params: overrides=lambda wildcards: " ".join(next(j["overrides"] for j in JOBS if j["name"]==wildcards.name))
    shell:  "python cli.py {params.overrides}"
```

---

## **4. Future path**

| When this happens …                                     | You do …                                                                                          |
| ------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| More than one pipeline, strict I/O lineage, larger team | Promote steps/ into **Kedro** nodes & DataCatalog; keep Hydra for config.                         |
| Need to mix GPU + CPU tasks, burst to multiple clouds   | Keep same Nextflow channel fan-out; add process.executor, container, resource directives per job. |
| Business users want a "dashboard" of results            | Bolt on W&B sweeps or Prefect 2 UI without touching Nextflow layer.                               |

---

### **TL;DR**

* **Hydra** = config brain, validation, optional local sweep engine.
* **Nextflow** (or Snakemake) = scheduler muscle for cluster/cloud.
* **Pydantic** keeps the contracts tight; **Kedro** stays on deck for future scaling.

You can now clone, run any of the four entry points, and scale up or down without rewriting the core runner code.

---

## **5. Current Status & Known Issues**

### **Implementation Status**
- ✅ Core architecture defined
- ✅ Pydantic v2 config models
- ✅ Basic runner skeleton
- ❌ Missing __init__.py files for Python packages
- ❌ Only one preprocessing step implemented ("filter")
- ❌ No base.yaml config file
- ❌ Output path configuration missing
- ❌ Import paths need adjustment (copairs_runner vs copairs_runner_v2)
- ❌ No tests
- ❌ No dependency management files

### **Before You Can Run This**
1. Create missing `__init__.py` files in package directories
2. Create `conf/base.yaml` with proper defaults
3. Fix import paths throughout the codebase
4. Install dependencies: `hydra-core`, `pydantic>=2`, `copairs`, `pandas`, `numpy`, etc.
5. Implement remaining preprocessing steps
6. Add proper error handling and logging

---

## **6. Future improvements</

### **Improvements**

| Area                                   | Suggested Add-on                                                                                                | Benefit                                                                                  |
| -------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| **Dependency pinning**                 | Add a requirements.txt or pyproject.toml (e.g., hydra-core\>=1.3, pydantic\>=2, plus any runner-specific libs). | Ensures the project is reproducible on new machines or CI without guesswork.             |
| **Central logging config**             | Drop a logging.yaml in conf/ and include \- logging in base.yaml’s defaults: list.                              | Hydra auto-loads the file, giving uniform, configurable logs across all execution modes. |
| **Hydra config groups**                | Organize frequent variants under folders like conf/data/, conf/model/, etc.                                     | Lets you use comma-list sweeps (pattern A) cleanly, keeps base.yaml minimal.             |
| **Helper script for Nextflow**         | Move the inline YAML→JSON logic to scripts/parse\_jobs.py; call that from main.nf.                              | Shortens the Nextflow file, improves readability and re-use.                             |
| **Container / environment spec**       | Provide a Dockerfile or Conda environment.yml.                                                                  | Guarantees identical runtime environments for local dev, HPC, and cloud nodes.           |
| **README badges & quick-start matrix** | Add CI badge, PyPI version (if packaged), and a table of the four launch commands (local → cluster).            | New contributors instantly understand how to run and scale the project.                  |

---

## **7. Development Roadmap**

### **Phase 1: Make it Work (Current Focus)**
- [ ] Add missing `__init__.py` files
- [ ] Create `conf/base.yaml` with minimal working config
- [ ] Fix all import paths
- [ ] Create requirements.txt with pinned dependencies
- [ ] Implement core preprocessing steps from utils/copairs_runner.py
- [ ] Add basic smoke tests

### **Phase 2: Make it Right**
- [ ] Add comprehensive unit tests
- [ ] Add integration tests with sample data
- [ ] Implement proper logging configuration
- [ ] Add input validation and error handling
- [ ] Create Docker container
- [ ] Add CI/CD pipeline

### **Phase 3: Make it Fast**
- [ ] Profile and optimize bottlenecks
- [ ] Add caching for expensive operations
- [ ] Implement parallel preprocessing where applicable
- [ ] Add resource monitoring
- [ ] Benchmark against utils/ implementation

---

## **Contributing**

Given the experimental nature of this codebase, contributions should focus on:
1. Fixing the known issues listed above
2. Adding tests
3. Improving documentation
4. Validating against real Cell Painting datasets

Please do not use this code for production workloads until it has been properly tested and validated.
