#!/bin/bash
# Batch processing script to run all phenotypic analyses using the runner

# Set up logging
LOGDIR="logs"
mkdir -p $LOGDIR

# Function to run analysis with logging
run_analysis() {
    local config=$1
    local name=$(basename $config .yaml)
    local logfile="$LOGDIR/${name}_$(date +%Y%m%d_%H%M%S).log"
    
    echo "Running $name..."
    echo "Config: $config"
    echo "Log: $logfile"
    
    # Run the analysis with logging
    python copairs_runner.py "$config" --verbose > "$logfile" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "✓ $name completed successfully"
    else
        echo "✗ $name failed - check $logfile for details"
    fi
    echo ""
}

# Check if runner exists
if [ ! -f "copairs_runner.py" ]; then
    echo "Error: copairs_runner.py not found in current directory"
    exit 1
fi

# Create output directory if it doesn't exist
mkdir -p output

echo "============================================"
echo "Running Phenotypic Activity Analyses"
echo "============================================"
echo ""

# Run all activity analyses
for config in configs/activity/*.yaml; do
    if [ -f "$config" ]; then
        run_analysis "$config"
    fi
done

echo "============================================"
echo "Running Phenotypic Consistency Analyses"
echo "============================================"
echo ""

# Run all consistency analyses
for config in configs/consistency/*.yaml; do
    if [ -f "$config" ]; then
        run_analysis "$config"
    fi
done

echo "============================================"
echo "All analyses complete!"
echo "============================================"
echo ""
echo "Results are in the 'output' directory"
echo "Logs are in the '$LOGDIR' directory"

# Optional: Generate summary report
echo ""
echo "Generating summary report..."
echo ""

# Count successful outputs
activity_count=$(ls -1 output/phenotypic-activity-*.csv.gz 2>/dev/null | wc -l)
consistency_count=$(ls -1 output/phenotypic-consistency-*.csv.gz 2>/dev/null | wc -l)

echo "Summary:"
echo "- Activity analyses completed: $activity_count"
echo "- Consistency analyses completed: $consistency_count"

# List any missing expected outputs
echo ""
echo "Checking for expected outputs..."

# Define expected outputs (you can customize this list)
expected_outputs=(
    "output/phenotypic-activity-var_mad_int_featselect_harmony.csv.gz"
    "output/phenotypic-activity-var_mad_int_featselect_harmony-target2.csv.gz"
    "output/phenotypic-activity-var_mad_int_featselect_harmony-crispr.csv.gz"
    "output/phenotypic-activity-var_mad_int_featselect_harmony-orf.csv.gz"
    "output/phenotypic-consistency-var_mad_int_featselect_harmony-target-retrieval.csv.gz"
    "output/phenotypic-consistency-var_mad_int_featselect_harmony-target2-target-retrieval.csv.gz"
)

missing=0
for expected in "${expected_outputs[@]}"; do
    if [ ! -f "$expected" ]; then
        echo "⚠ Missing: $expected"
        ((missing++))
    fi
done

if [ $missing -eq 0 ]; then
    echo "✓ All expected outputs are present"
else
    echo "⚠ $missing expected outputs are missing"
fi