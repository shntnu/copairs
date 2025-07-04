# Configuration Files for Phenotypic Profiling Analyses

This directory contains YAML configuration files for running phenotypic profiling analyses using the `copairs_runner.py` script.

## Directory Structure

```
configs/
├── base/                    # Base configuration templates
│   ├── activity_base.yaml   # Common settings for activity analyses
│   └── consistency_base.yaml # Common settings for consistency analyses
├── activity/               # Phenotypic activity analysis configs
│   ├── compounds*.yaml     # Compound perturbations
│   ├── crispr*.yaml       # CRISPR perturbations
│   └── orf*.yaml          # ORF (overexpression) perturbations
└── consistency/           # Phenotypic consistency analysis configs
    ├── compounds*.yaml    # Target consistency for compounds
    ├── orf_crispr*.yaml  # CORUM complex consistency
    └── *_rephub*.yaml    # RepHub annotation-based analyses
```

## Configuration Naming Convention

- `*_target2.yaml` - TARGET2 plate analyses
- `*_pca.yaml` - Analyses using PCA-transformed features
- `*_integrated_*.yaml` - Cross-modality integrated analyses
- `*_rephub_*.yaml` - Analyses using RepHub annotations
- `*_corum_*.yaml` - Analyses using CORUM complex annotations

## Important Notes

### 1. Data Path Requirements
All configurations assume the profile data is located at:
- Non-PCA: `../profiles/profiles_*.parquet`
- PCA: `../profiles/integrated/PCA/profiles_*.parquet`
- Integrated: `../profiles/integrated/profiles_*.parquet`

### 2. Missing Preprocessing Steps
Some configurations reference preprocessing steps that need to be implemented in the runner:
- `merge_metadata`: For loading external annotation files
- `filter_single_replicates`: For removing perturbations with only one replicate
- Control type assignment based on metadata

### 3. Metadata Requirements
The configurations assume certain metadata columns exist in the data:
- `Metadata_JCP2022`: Perturbation identifier
- `Metadata_PlateType`: Type of plate (COMPOUND, CRISPR, ORF, TARGET2)
- `Metadata_Source`: Data source identifier
- `Metadata_control_type`: Control type (trt, negcon, poscon)
- `Metadata_target`: Target annotation (for consistency analyses)

### 4. Output Files
All outputs are saved to the `output/` directory with compressed CSV format (`.csv.gz`)

## Usage

Run a single analysis:
```bash
python copairs_runner.py configs/activity/compounds.yaml --verbose
```

Run all analyses:
```bash
./run_all_analyses.sh
```

## Customization

To create a new analysis configuration:

1. Copy an existing config that's similar to what you need
2. Modify the preprocessing steps, parameters, and output path
3. Test with a small subset of data first
4. Add to the batch processing script if needed

## Extending the Runner

To fully support all configurations, the following extensions to `copairs_runner.py` are recommended:

1. **Add merge_metadata preprocessing step**:
   ```python
   elif step_type == "merge_metadata":
       source_df = pd.read_csv(step["source"])
       df = df.merge(source_df, on=step["on"], how="left")
   ```

2. **Add filter_single_replicates preprocessing step**:
   ```python
   elif step_type == "filter_single_replicates":
       counts = df.groupby(step["groupby"]).size()
       keep = counts[counts > 1].index
       df = df[df[step["groupby"][0]].isin(keep)]
   ```

3. **Support for abs_cosine distance metric** in the copairs library

4. **YAML include functionality** to avoid duplication of base configurations