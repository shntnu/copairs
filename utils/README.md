# Utils Module - Detailed Documentation

## Overview

The `utils` directory contains a Python-based analysis framework for performing phenotypic profiling of compound data from high-content imaging experiments. It's part of the JUMP (Joint Undertaking in Morphological Profiling) production analysis pipeline.

## What This Module Does

The utils module is designed to perform two main types of analyses on cell painting data:

1. **Phenotypic Activity Analysis** - Determines which compounds show significant biological activity compared to controls (DMSO)
2. **Phenotypic Consistency Analysis** - Evaluates whether compounds with the same molecular targets have consistent phenotypic profiles

## Core Architecture

The utils module is built around the `CopairsRunner` class in `copairs_runner.py`, which implements a configurable pipeline for phenotypic profiling analysis. It uses the `copairs` library as its computational engine for calculating morphological similarity metrics.

## Configuration System

The runner uses YAML configuration files to define analysis parameters:

- **Data paths and column identification patterns**
- **Preprocessing steps** (filtering, aggregation, transformations)
- **Analysis parameters** for similarity calculations
- **Output settings** including plotting options

## Data Flow and Processing

### Input Data Format
- CSV files containing cell painting data with two types of columns:
  - **Metadata columns** (prefixed with "Metadata_"): compound info, targets, concentrations, plate info
  - **Feature columns**: ~500+ morphological measurements (e.g., Cells_AreaShape_*, Cytoplasm_*, Nuclei_*)

### Processing Pipeline (copairs_runner.py:601-641)

1. **Data Loading** (`load_data`): Reads CSV/Parquet files
2. **Preprocessing** (`preprocess_data`): Applies configurable transformations
3. **Feature Extraction** (`extract_data`): Separates metadata from features
4. **Average Precision Calculation** (`run_average_precision`): Computes similarity scores
5. **Statistical Significance** (`run_mean_average_precision`): Permutation testing
6. **Visualization** (`plot_map_results`): Creates scatter plots
7. **Results Saving** (`save_results`): Outputs CSV/Parquet files

## Preprocessing Operations (copairs_runner.py:185-323)

The runner supports various preprocessing steps:

- **filter**: SQL-like queries to subset data
- **apply_assign_reference**: Marks control samples (e.g., DMSO)
- **dropna**: Removes rows with missing values
- **remove_nan_features**: Drops feature columns containing NaN
- **split_multilabel**: Converts pipe-separated strings to lists
- **filter_by_external_csv**: Filters based on previous analysis results
- **aggregate_replicates**: Median aggregation of technical replicates
- **add_column_from_query**: Creates new metadata columns via expressions

## Similarity Calculation

### Average Precision (AP)
- Measures how well replicates cluster together compared to random pairs
- Uses cosine similarity by default (configurable)
- Supports both single-label and multi-label analyses

### Positive/Negative Pair Definition
- **Positive pairs**: Samples that should be similar (e.g., replicates)
- **Negative pairs**: Samples that should be different (e.g., compound vs control)
- Configured via `pos_sameby`, `pos_diffby`, `neg_sameby`, `neg_diffby`

## Statistical Analysis

### Mean Average Precision (mAP)
- Aggregates AP scores by grouping variable (compound or target)
- Performs permutation testing to assess significance
- Parameters:
  - `null_size`: Number of permutations (typically 1,000,000)
  - `threshold`: p-value cutoff (0.05)
  - `seed`: Random seed for reproducibility

## Two Analysis Types

### Phenotypic Activity Analysis (activity_analysis.yaml)
- **Goal**: Identify compounds that significantly alter cell morphology
- **Positive pairs**: Replicates of same compound
- **Negative pairs**: Compound vs DMSO control
- **Output**: List of phenotypically active compounds with p-values

### Phenotypic Consistency Analysis (consistency_analysis.yaml)
- **Goal**: Evaluate if compounds with same target have similar phenotypes
- **Preprocessing**: 
  - Filters to only active compounds (from activity analysis)
  - Aggregates replicates by compound-target combinations
  - Handles multi-target compounds (pipe-separated)
- **Positive pairs**: Compounds sharing targets
- **Negative pairs**: Compounds with different targets
- **Output**: Assessment of target-phenotype consistency

## Visualization

The plotting system creates scatter plots showing:
- X-axis: Mean Average Precision (0-1 scale)
- Y-axis: -log10(p-value)
- Blue dots: Statistically significant results
- Gray dots: Non-significant results
- Horizontal line: p=0.05 threshold
- Annotation: Percentage of significant results

## Key Dependencies and Libraries

- **copairs**: Core similarity calculation engine
- **pandas/numpy**: Data manipulation and numerical operations
- **matplotlib/seaborn**: Visualization
- **pyyaml**: Configuration file parsing

## Execution Flow

```bash
# Activity analysis
python copairs_runner.py configs/activity_analysis.yaml --verbose

# Consistency analysis (depends on activity results)
python copairs_runner.py configs/consistency_analysis.yaml --verbose
```

## Advanced Features

- **Batch processing**: Handles large datasets via configurable batch_size
- **Multi-label support**: Handles compounds with multiple targets
- **Parallel processing**: Uses multiprocessing for permutation testing
- **Flexible configuration**: All copairs parameters can be overridden
- **Multiple output formats**: CSV, Parquet, PNG/PDF/SVG plots

## Statistical Interpretation

- **High mAP + Low p-value**: Strong evidence of biological activity/consistency
- **Null hypothesis**: Observed similarity could occur by chance
- **Permutation testing**: Creates null distribution by shuffling labels
- **Multiple testing correction**: Applied to control false discovery rate

## Configuration Examples

### Basic Activity Analysis Configuration
```yaml
data:
  path: "data/cell_painting_data.csv"
  metadata_regex: "^Metadata"

preprocessing:
  - type: apply_assign_reference
    params:
      condition: "Metadata_broad_sample == 'DMSO'"
      reference_col: "Metadata_reference_index"
      default_value: -1

average_precision:
  params:
    pos_sameby: ["Metadata_broad_sample", "Metadata_reference_index"]
    pos_diffby: []
    neg_sameby: []
    neg_diffby: ["Metadata_broad_sample", "Metadata_reference_index"]

mean_average_precision:
  params:
    sameby: ["Metadata_broad_sample"]
    null_size: 1000000
    threshold: 0.05
    seed: 0

output:
  path: "results/activity_map.csv"
  save_ap_scores: true

plotting:
  enabled: true
  path: "plots/activity_plot.png"
  title: "Phenotypic Activity Assessment"
```

### Preprocessing Step Examples

```yaml
preprocessing:
  # Filter compounds by concentration
  - type: filter
    query: "Metadata_mmoles_per_liter > 0.1"
  
  # Remove missing data
  - type: dropna
    columns: ["Metadata_target"]
  
  # Aggregate technical replicates
  - type: aggregate_replicates
    groupby: ["Metadata_broad_sample", "Metadata_target"]
  
  # Add derived column
  - type: add_column_from_query
    query: '(Metadata_moa == "kinase inhibitor") & (Metadata_mmoles_per_liter > 1)'
    column_name: "Metadata_is_high_dose_kinase_inhibitor"
    fill_value: False
```

## Output Files

### Activity Analysis
- **activity_map_runner.csv**: Contains mAP scores and p-values for each compound
- **activity_map_runner_ap_scores.csv**: Raw AP scores for each comparison
- **map_activity_plot.png**: Visualization of activity results

### Consistency Analysis
- **target_maps_runner.csv**: Contains mAP scores and p-values for each target
- **map_consistency_plot.png**: Visualization of consistency results

## Troubleshooting

### Common Issues

1. **Memory errors with large datasets**
   - Increase `batch_size` in average_precision params
   - Process data in chunks

2. **Slow permutation testing**
   - Reduce `null_size` (though this reduces statistical power)
   - Increase `max_workers` for more parallel processing

3. **Missing dependencies**
   - Install with: `pip install copairs pandas numpy matplotlib seaborn pyyaml`

## Purpose in JUMP Production

This module appears to be a critical component for:
- Quality control of compound screening data
- Identifying biologically active compounds from morphological screens
- Validating that compounds hit their intended targets
- Supporting the broader JUMP consortium's goal of creating comprehensive morphological profiles for drug discovery

The framework is highly configurable and designed to handle large-scale screening data with proper statistical validation.