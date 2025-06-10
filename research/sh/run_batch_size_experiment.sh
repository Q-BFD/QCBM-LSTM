#!/bin/bash

# Batch Size Experiment Script
# Usage: bash sh/run_batch_size_experiment.sh

set -e

# =============================================================================
# Configuration
# =============================================================================

BATCH_SIZES=(32 64 128 256 512)
EXPERIMENT_BASE_DIR="./results/batch_size_experiments"
SETTINGS_DIR="./python/settings"
CONFIG_PREFIX="batch_experiment"

# =============================================================================
# Functions
# =============================================================================

create_batch_config() {
    local batch_size=$1
    local config_file="$SETTINGS_DIR/${CONFIG_PREFIX}_${batch_size}.json"
    
    cat > "$config_file" << EOF
{
    "prior_model": "QCBM",
    "batch_size": ${batch_size},
    "experiment_root": "${EXPERIMENT_BASE_DIR}/batch_${batch_size}"
}
EOF
    
    echo "$config_file"
}

run_experiment() {
    local batch_size=$1
    local config_file=$2
    
    echo "=============================================="
    echo "Running Batch Size Experiment: ${batch_size}"
    echo "=============================================="
    
    mkdir -p "${EXPERIMENT_BASE_DIR}/batch_${batch_size}"
    
    # Dry run - just show what would be executed
    echo "Would execute: python main.py --config_file ../$(basename $config_file)"
    echo "Experiment directory: ${EXPERIMENT_BASE_DIR}/batch_${batch_size}"
    echo ""
}

cleanup_configs() {
    echo "Cleaning up temporary config files..."
    rm -f "${SETTINGS_DIR}/${CONFIG_PREFIX}_"*.json
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo "=============================================="
    echo "Batch Size Sensitivity Experiment"
    echo "=============================================="
    echo "Batch sizes: ${BATCH_SIZES[*]}"
    echo "Results will be saved to: ${EXPERIMENT_BASE_DIR}"
    echo "=============================================="
    echo ""
    
    mkdir -p "$EXPERIMENT_BASE_DIR"
    
    for batch_size in "${BATCH_SIZES[@]}"; do
        config_file=$(create_batch_config "$batch_size")
        echo "Created config: $config_file"
        echo "Content:"
        cat "$config_file"
        echo ""
        
        run_experiment "$batch_size" "$config_file"
    done
    
    cleanup_configs
    
    echo "=============================================="
    echo "All batch size experiments configured!"
    echo "=============================================="
}

# Check if we're in the research root directory
if [[ ! -f "python/main.py" ]]; then
    echo "Error: Please run this script from the research root directory"
    exit 1
fi

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 