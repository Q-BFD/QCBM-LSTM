#!/bin/bash

# Temperature Experiment Script
# Usage: bash sh/run_temperature_experiment.sh

set -e  # Exit on any error

# =============================================================================
# Configuration
# =============================================================================

TEMP_START=0.1
TEMP_END=0.5
TEMP_STEP=0.1
EXPERIMENT_BASE_DIR="./outputs/temperature_experiments"
SETTINGS_DIR="./python/settings"
TEMP_CONFIG_PREFIX="temp_experiment"

# =============================================================================
# Helper Functions
# =============================================================================

create_temp_config() {
    local temp_value=$1
    # Format temperature value to ensure valid JSON format (e.g., 0.3 instead of .3)
    local formatted_temp=$(printf "%.1f" "$temp_value")
    local config_file="$SETTINGS_DIR/${TEMP_CONFIG_PREFIX}_${formatted_temp}.json"
    
    cat > "$config_file" << EOF
{
    "prior_model": "QCBM",
    "temprature": ${formatted_temp},
    "experiment_root": "${EXPERIMENT_BASE_DIR}/temp_${formatted_temp}",
    "experiment_name": "temp_${formatted_temp}_experiment"
}
EOF
    
    echo "$config_file"
}

run_experiment() {
    local temp_value=$1
    local config_file=$2
    
    echo "=============================================="
    echo "Running Temperature Experiment: ${temp_value}"
    echo "=============================================="
    
    # Create experiment directory
    mkdir -p "${EXPERIMENT_BASE_DIR}/temp_${temp_value}"
    
    # Run the experiment
    cd python
    python main.py --config_file "../${config_file}"
    cd ..
    
    echo "Experiment completed for temperature: ${temp_value}"
    echo ""
}

cleanup_temp_configs() {
    echo "Cleaning up temporary config files..."
    rm -f "${SETTINGS_DIR}/${TEMP_CONFIG_PREFIX}_"*.json
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    echo "=============================================="
    echo "Temperature Sensitivity Experiment"
    echo "=============================================="
    echo "Temperature range: ${TEMP_START} to ${TEMP_END} (step: ${TEMP_STEP})"
    echo "Results will be saved to: ${EXPERIMENT_BASE_DIR}"
    echo "=============================================="
    echo ""
    
    # Create base experiment directory
    mkdir -p "$EXPERIMENT_BASE_DIR"
    
    # Run experiments for each temperature value
    temp_value=$TEMP_START
    while (( $(echo "$temp_value <= $TEMP_END" | bc -l) )); do
        # Create temporary config file
        config_file=$(create_temp_config "$temp_value")
        
        # Run experiment
        if run_experiment "$temp_value" "$config_file"; then
            echo "✅ Success: Temperature ${temp_value}"
        else
            echo "❌ Failed: Temperature ${temp_value}"
        fi
        
        # Increment temperature
        temp_value=$(echo "$temp_value + $TEMP_STEP" | bc -l)
    done
    
    # Cleanup
    cleanup_temp_configs
    
    echo "=============================================="
    echo "All temperature experiments completed!"
    echo "Results saved in: ${EXPERIMENT_BASE_DIR}"
    echo "=============================================="
}

# =============================================================================
# Script Entry Point
# =============================================================================

# Check if bc is available for floating point arithmetic
if ! command -v bc &> /dev/null; then
    echo "Error: 'bc' command is required for floating point arithmetic"
    echo "Please install bc: sudo apt-get install bc"
    exit 1
fi

# Check if we're in the research root directory
if [[ ! -f "python/main.py" ]]; then
    echo "Error: Please run this script from the research root directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 