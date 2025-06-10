#!/bin/bash

# KRAS Drug Discovery - Main Execution Script
# Usage: bash sh/run.sh [experiment_name]

set -e  # Exit on any error

# =============================================================================
# Configuration Section
# =============================================================================

# Default experiment settings
DEFAULT_CONFIG="./settings/benchmark_models_settings_qcbm.json"
PYTHON_DIR="./python"
MAIN_SCRIPT="main.py"

# Experiment configurations - Add more as needed
declare -A EXPERIMENTS
EXPERIMENTS[default]=""  # Use default values from TrainingArgs
EXPERIMENTS[qcbm]=""     # Use default values from TrainingArgs
# EXPERIMENTS[classical]="./python/settings/classical_config.json"  # Optional override configs
# EXPERIMENTS[test]="./python/settings/test_config.json"             # Optional override configs

# =============================================================================
# Helper Functions
# =============================================================================

show_usage() {
    echo "Usage: bash sh/run.sh [experiment_name] [additional_args...]"
    echo ""
    echo "Available experiments:"
    for exp in "${!EXPERIMENTS[@]}"; do
        echo "  - $exp: ${EXPERIMENTS[$exp]}"
    done
    echo ""
    echo "Examples:"
    echo "  bash sh/run.sh                    # Run default experiment"
    echo "  bash sh/run.sh qcbm              # Run QCBM experiment"
    echo "  bash sh/run.sh default --help    # Show help"
    echo ""
    echo "Additional arguments will be passed directly to main.py"
}

check_environment() {
    # Check if we're in the research root directory
    if [[ ! -f "python/main.py" ]]; then
        echo "Error: Please run this script from the research root directory"
        echo "Current directory: $(pwd)"
        exit 1
    fi
    
    # Check if Python is available
    if ! command -v python &> /dev/null; then
        echo "Error: Python is not available in PATH"
        exit 1
    fi
    
    # Check if python directory exists
    if [[ ! -d "python" ]]; then
        echo "Error: python directory not found"
        exit 1
    fi
}

# =============================================================================
# Main Execution
# =============================================================================

main() {
    local experiment_name="default"
    local additional_args=()
    
    # Parse arguments
    if [[ $# -ge 1 ]]; then
        if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
            show_usage
            exit 0
        fi
        experiment_name="$1"
        shift
        additional_args=("$@")
    fi
    
    # Validate experiment name
    if [[ ! -v "EXPERIMENTS[$experiment_name]" ]]; then
        echo "Error: Unknown experiment '$experiment_name'"
        echo ""
        show_usage
        exit 1
    fi
    
    # Get config file for the experiment
    local config_file="${EXPERIMENTS[$experiment_name]}"
    
    # Check if config file exists (only if specified)
    if [[ -n "$config_file" && ! -f "$config_file" ]]; then
        echo "Error: Config file not found: $config_file"
        exit 1
    fi
    
    # Environment checks
    check_environment
    
    # Print experiment info
    echo "=============================================="
    echo "KRAS Drug Discovery Experiment"
    echo "=============================================="
    echo "Experiment: $experiment_name"
    echo "Config file: $config_file"
    echo "Working directory: $(pwd)"
    echo "Python directory: $PYTHON_DIR"
    echo "Additional args: ${additional_args[*]}"
    echo "=============================================="
    echo ""
    
    # Change to python directory and run the experiment
    cd "$PYTHON_DIR"
    
    # Build the command
    if [[ -n "$config_file" ]]; then
        local cmd=(python "$MAIN_SCRIPT" --config_file "../$config_file" "${additional_args[@]}")
        echo "Running command: ${cmd[*]}"
    else
        local cmd=(python "$MAIN_SCRIPT" "${additional_args[@]}")
        echo "Running command: ${cmd[*]} (using default configuration)"
    fi
    
    echo ""
    
    # Execute the main script
    exec "${cmd[@]}"
}

# =============================================================================
# Script Entry Point
# =============================================================================

# Check if script is being sourced or executed
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi 