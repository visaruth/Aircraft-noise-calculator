# run_segmentation_comparison.ps1
# Automates the comparison between Original and Segmented analysis for a specific airport.
# Default airport: vtbs

$AIRPORT = if ($args[0]) { $args[0] } else { "vtbs" }
$MODELS = @("dbscan", "msa")

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "   Performance Comparison: Segmentation vs Original ($AIRPORT)" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# Detect venv
if (Test-Path "venv/Scripts/activate.ps1") {
    . venv/Scripts/activate.ps1
}

$PYTHON_EXE = ".\venv\Scripts\python.exe"

# 1. Models and Range
$MODELS = @("dbscan", "msa")
$K_RANGE = @(10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120)

foreach ($M in $MODELS) {
    if ($M -eq "dbscan") {
        $P_ARGS = @("-eps", "150")
    }
    else {
        $P_ARGS = @("-bandwidth", "150.0")
    }
    
    # 2. Run Original (non-segmented, sequential)
    Write-Host "`n>>> Running $AIRPORT Original ($M, Sequential)..." -ForegroundColor Yellow
    & $PYTHON_EXE main.py -ap $AIRPORT -m $M @P_ARGS --mode s -r
    
    # 3. Run Segmented (sequential) for range K=10..120
    foreach ($K in $K_RANGE) {
        Write-Host ">>> Running $AIRPORT Segmented ($M, K=$K, Sequential)..." -ForegroundColor Yellow
        & $PYTHON_EXE main.py -ap $AIRPORT -m $M @P_ARGS --segment --K $K --mode s -r
    }
}

# 4. Generate Performance Plots
Write-Host "`n[3/4] Generating Segmentation Performance Plots (PDF)..." -ForegroundColor Yellow
& $PYTHON_EXE plot_segmentation_performance.py -ap $AIRPORT

# 5. Show Performance Log (Per-Site)
Write-Host "`n[4/4] Performance Summary (from result/execution_times.json):" -ForegroundColor Yellow
if (Test-Path "result/execution_times.json") {
    $log = Get-Content result/execution_times.json | ConvertFrom-Json
    $log | Where-Object { $_.airport -eq $AIRPORT } | Select-Object -Last 100 | Format-Table -AutoSize
}
else {
    Write-Host "Warning: No execution time log found." -ForegroundColor Red
}

Write-Host "`n====================================================" -ForegroundColor Green
Write-Host "   Comparison Complete! Graphs saved in result/comparison/" -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
