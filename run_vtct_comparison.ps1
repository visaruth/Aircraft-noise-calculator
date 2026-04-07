# run_vtct_comparison.ps1
# This script automates the noise analysis for VTCT (Mae Fah Luang Chiang Rai) airport
# using both DBSCAN and MSA models with parameters ranging from 100 to 300.
# It then generates internal and cross-model comparison reports.

$airport = "vtct"
$params = @(100, 150, 200, 250, 300, 350, 400, 450, 500)

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "   Starting Automated VTCT Noise Analysis & Comparison" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

# 0. Convert Raw Data
Write-Host "`n[0/4] Converting raw data for $airport..." -ForegroundColor Yellow
.\venv\Scripts\python convertfile.py -ap $airport

# 1. Run DBSCAN analysis
# Write-Host "`n[1/4] Running DBSCAN analysis for eps: 100, 200, 300..." -ForegroundColor Yellow
# foreach ($p in $params) {
#     Write-Host ">>> Running DBSCAN with eps=$p..." -ForegroundColor Gray
#     .\venv\Scripts\python main.py -ap $airport -m dbscan -eps $p -r --mode sequential
#     .\venv\Scripts\python main_plot.py -ap $airport -m dbscan -eps $p
# }

# # 2. Run MSA analysis
# Write-Host "`n[2/4] Running MSA analysis for bandwidth: 100, 200, 300..." -ForegroundColor Yellow
# foreach ($p in $params) {
#     Write-Host ">>> Running MSA with bandwidth=$p..." -ForegroundColor Gray
#     .\venv\Scripts\python main.py -ap $airport -m msa -bandwidth $p -r --mode sequential
#     .\venv\Scripts\python main_plot.py -ap $airport -m msa -bandwidth $p
# }

# 3. Internal comparisons
Write-Host "`n[3/4] Generating Internal Comparisons (Within same model)..." -ForegroundColor Yellow
Write-Host ">>> Comparing DBSCAN variations..." -ForegroundColor Gray
.\venv\Scripts\python compare_plots.py -ap $airport -m dbscan -er "100,500" --exclude ""

Write-Host ">>> Comparing MSA variations..." -ForegroundColor Gray
.\venv\Scripts\python compare_plots.py -ap $airport -m msa -br "100,500" --exclude ""

# 4. Cross-model comparison
Write-Host "`n[4/4] Generating Cross-Model Comparison (MSA vs DBSCAN)..." -ForegroundColor Yellow
.\venv\Scripts\python compare_plots.py -ap $airport -m msa_dbscan -br "100,500" -er "100,500" --exclude ""

Write-Host "`n====================================================" -ForegroundColor Green
Write-Host "   Analysis and Comparisons for $airport Complete!" -ForegroundColor Green
Write-Host "   Check the 'result/comparison/' directory for results." -ForegroundColor Green
Write-Host "====================================================" -ForegroundColor Green
