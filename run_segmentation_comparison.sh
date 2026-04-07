#!/bin/bash
# run_segmentation_comparison.sh
# Automates the comparison between Original and Segmented analysis.
# Usage: ./run_segmentation_comparison.sh [airport_code]
# Default airport: vtbs

AIRPORT=${1:-vtbs}
MODELS=("dbscan" "msa")

echo "===================================================="
echo "   Performance Comparison: Segmentation vs Original ($AIRPORT)"
echo "===================================================="

# Determine Python command
PYTHON_CMD="python"
if ! command -v python &> /dev/null; then
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    fi
fi

# Detect venv
if [ -d "venv" ]; then
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$OSTYPE" == "win32" ]]; then
        [ -f "venv/Scripts/activate" ] && source venv/Scripts/activate
    else
        [ -f "venv/bin/activate" ] && source venv/bin/activate
    fi
fi

# 1. Models and Range
MODELS=("dbscan" "msa")
K_RANGE=(10 20 30 40 50 60 70 80 90 100 110 120)

for m in "${MODELS[@]}"; do
    if [ "$m" == "dbscan" ]; then
        P_FLAG="-eps"
        P_VAL="150"
    else
        P_FLAG="-bandwidth"
        P_VAL="150.0"
    fi
    
    # 2. Run Original (non-segmented, sequential)
    echo -e "\n>>> Running $AIRPORT Original ($m, Sequential)..."
    $PYTHON_CMD main.py -ap "$AIRPORT" -m "$m" "$P_FLAG" "$P_VAL" --mode s --recalculate
    
    # 3. Run Segmented (sequential) for range K=10..120
    for k in "${K_RANGE[@]}"; do
        echo ">>> Running $AIRPORT Segmented ($m, K=$k, Sequential)..."
        $PYTHON_CMD main.py -ap "$AIRPORT" -m "$m" "$P_FLAG" "$P_VAL" --segment -K "$k" --mode s --recalculate
    done
done

# 4. Generate Performance Plots
echo -e "\n[3/4] Generating Segmentation Performance Plots (PDF)..."
$PYTHON_CMD plot_segmentation_performance.py -ap "$AIRPORT"

# 5. Show Performance Log (Per-Site)
echo -e "\n[4/4] Performance Summary (from result/execution_times.json):"
if [ -f "result/execution_times.json" ]; then
    $PYTHON_CMD -c "
import json, os, pandas as pd
log_file = 'result/execution_times.json'
if os.path.exists(log_file):
    with open(log_file, 'r') as f:
        data = json.load(f)
    if data:
        df = pd.DataFrame(data)
        # Ensure new columns exist for display
        cols = ['timestamp', 'airport', 'model', 'station', 'mode', 'K', 'duration_sec', 'precision', 'recall', 'f1']
        display_cols = [c for c in cols if c in df.columns]
        print(df[display_cols].tail(100).to_string(index=False))
"
else:
    echo "Warning: No execution time log found."
fi

echo -e "\n===================================================="
echo "   Comparison Complete! Graphs saved in result/comparison/"
echo "===================================================="
