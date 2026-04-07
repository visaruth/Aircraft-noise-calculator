#!/bin/bash
# run_comparison.sh
# Automates noise analysis and comparison for a specific airport (e.g., vtbs, vtct).
# Usage: ./run_comparison.sh [airport_code]
# Default airport: vtbs

AIRPORT=${1:-vtbs}
PARAMS=(100 150 200 250 300 350 400 450 500)

echo "===================================================="
echo "   Starting Automated $AIRPORT Noise Analysis & Comparison"
echo "===================================================="

# Determine Python command
PYTHON_CMD="python"
if ! command -v python &> /dev/null; then
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    fi
fi

# Detect OS for venv activation
if [ -d "venv" ]; then
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
        # Windows environments (Git Bash, etc.)
        if [ -f "venv/Scripts/activate" ]; then
            source venv/Scripts/activate
        fi
    else
        # Linux/Mac
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
        fi
    fi
fi

# 0. Convert Raw Data
echo -e "\n[0/4] Converting raw data for $AIRPORT..."
$PYTHON_CMD convertfile.py -ap "$AIRPORT"

echo -e "\n[1/4] Running DBSCAN analysis for eps: 100, 200, 300..."
for p in "${PARAMS[@]}"; do
    echo ">>> Running $AIRPORT DBSCAN with eps=$p..."
    # Generate peaks and metrics
    $PYTHON_CMD main.py -ap "$AIRPORT" -m dbscan -eps "$p" -r
    # Generate station plots
    $PYTHON_CMD main_plot.py -ap "$AIRPORT" -m dbscan -eps "$p"
done

echo -e "\n[2/4] Running MSA analysis for bandwidth: 100, 200, 300..."
for p in "${PARAMS[@]}"; do
    echo ">>> Running $AIRPORT MSA with bandwidth=$p..."
    # Generate peaks and metrics
    $PYTHON_CMD main.py -ap "$AIRPORT" -m msa -bandwidth "$p" -r
    # Generate station plots
    $PYTHON_CMD main_plot.py -ap "$AIRPORT" -m msa -bandwidth "$p"
done

echo -e "\n[3/4] Generating Internal Comparisons..."
echo ">>> Comparing DBSCAN variations..."
$PYTHON_CMD compare_plots.py -ap "$AIRPORT" -m dbscan -er "100,300" --exclude ""

echo ">>> Comparing MSA variations..."
$PYTHON_CMD compare_plots.py -ap "$AIRPORT" -m msa -br "100,300" --exclude ""

echo -e "\n[4/4] Generating Cross-Model Comparison (MSA vs DBSCAN)..."
$PYTHON_CMD compare_plots.py -ap "$AIRPORT" -m msa_dbscan -br "100,300" -er "100,300" --exclude ""

echo -e "\n===================================================="
echo "   Analysis and Comparisons for $AIRPORT Complete!"
echo "   Check the 'result/comparison/' directory for results."
echo "===================================================="
