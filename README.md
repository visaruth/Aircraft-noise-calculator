# Aircraft Noise Calculator - Usage Guide

This guide describes how to use the scripts in this project for processing aircraft noise data, performing peak matching, and generating visualizations.

## 0. Initial Setup
Create a virtual environment and install dependencies:
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\activate
# Mac / Ubuntu Linux:
source venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

## 1. Prerequisites (venv)
Ensure you are using the virtual environment:
```bash
# Windows
.\venv\Scripts\activate

# Mac / Ubuntu Linux
source venv/bin/activate
```

## 2. Data Preparation (convertfile.py)
Convert raw RND noise files into CSV format.
```bash
python convertfile.py
```
- **Input:** All `.rnd` files in the current directory and its subfolders.
- **Output:** CSV files located in the `raw_data/` directory (e.g., `raw_data/vtbs/station_name_noise_data.csv`).

## 3. Main Processing Pipeline (main.py)
Process noise data to find peaks and match them with flight logs.
```bash
python main.py [options]
```
- **Options:**
  - `-ma, --match-algorithm`: Matching Logic Mode (Default: `legacy`)
    - `legacy`: Original basic matching. Extracts flight metadata (e.g., Airline Name API).
    - `121`: Peak-Unique 1-to-1 matching. Uses runway-direction priority and closest time lag.
    - `121e`: Exclusive 1-to-1. Same as 121 but assigns louder (Leq) peaks first and stops a single flight from matching multiple peaks.
    - `12m`: 1-to-Many. Connects all flights that touch the boundaries of a given peak window.
  - `-m, --model`: Clustering model (`dbscan` or `msa`). Default: `dbscan`.
  - `-eps`: EPS for DBSCAN (default: 150).
  - `-min_samples`: min_samples for DBSCAN (default: 10).
  - `-bandwidth`: Bandwidth for MSA (default: 150.0).
  - `-ap, --airport`: Airport code (default: vtbs).
  - `-se, --segment`: Enable signal segmentation (Efficient Algorithm).
  - `-K`: Number of segments for splitting (default: 100).
  - `--mode`: Processing mode: `p` or `parallel` (default), `s` or `sequential`.
- **Output:** Results in `result/<subfolder_name>/<airport>/`.
- **Performance Log:** Enriched execution time & accuracy is logged to `result/execution_times.json`.

## 4. Single-Run Plot Generation (main_plot.py)
Generate 12 standard PDF plots for a specific run.
```bash
python main_plot.py [options]
```
- **Options:**
  - `-m, --model`, `-eps`, `-min_samples`, `-bandwidth`: Should match the parameters used in `main.py`.
  - `-ap, --airport`: Airport code (e.g., `vtbs`). Default: `vtbs`.
  - `--exclude-accuracy`: List of stations to exclude from accuracy plots.
  - `--exclude-actype`: List of stations to exclude from ACTYPE plots.
- **Output:** PDF files in `result/<subfolder_name>/<airport>/plots/`.

## 5. Model Comparison (compare_plots.py)
Compare performance across multiple parameter sets or different models.
```bash
python compare_plots.py -m [model] [options]
```
- **Options:**
  - `-m, --model`: Single model (e.g., `msa`) or multiple models joined by underscore (e.g., `msa_dbscan`).
  - `-br, --bandwidth_range`: Filter MSA by bandwidth range (e.g., `-br 100,500`).
  - `-er, --eps_range`: Filter DBSCAN by EPS range (e.g., `-er 150,200`).
  - `-ap, --airport`: Airport code (e.g., `vtbs`). Default: `vtbs`.
- **Examples:**
  - Standard comparison: `python compare_plots.py -m msa`
  - Cross-model comparison (DBSCAN + MSA): `python compare_plots.py -m dbscan_msa`
  - Cross-model within specific ranges: `python compare_plots.py -m msa_dbscan -br 100,300 -er 100,200`
- **What it does:** Scans `result/` for relevant setup folders and generates:
  - **1_...**: Comparisons grouped by configuration (All stations in one view).
  - **2_...**: Comparisons grouped by Station (Multiple configurations in one view).
  - **Output:** Comparison reports saved in `result/comparison/`.

## 6. Segmentation Trend Analysis (plot_segmentation_performance.py)
Analyze the impact of the segmentation parameter $K$ on performance and accuracy.
```bash
python plot_segmentation_performance.py [options]
```
- **Options:**
  - `-f, --file`: Input JSON file (default: `result/execution_times.json`).
  - `-o, --output_dir`: Directory for plots (default: `result/comparison`).
- **Output:** 
  - `segmentation_performance_comparison.png` (2x2 grid of all metrics).
  - Separate plots for Precision, Recall, F1, and Duration vs K.

### Performance & Segmentation Comparison
Compare the efficiency and accuracy of the "Efficient Algorithm" (Segmentation) vs the original:
- **Windows:** `powershell -ExecutionPolicy Bypass -File .\run_segmentation_comparison.ps1 <airport>`
- **Bash:** `./run_segmentation_comparison.sh <airport>`

### Linux / Mac / Git Bash (Bash)
Use the cross-platform script for any airport:
- **Usage:** `./run_comparison.sh <airport_code>` (e.g., `./run_comparison.sh vtct`)
- **Note:** On Windows, this requires **Git Bash** or **WSL**.

## 7. Matching & Lag Analysis Suite
Tools for identifying and analyzing the time lag between noise peaks and flight events.

### Candidate Search (find_candidate.py)
Find all potential flight matches within a time window (default +/- 300s).
```bash
python find_candidate.py -p "result/<setup>/<airport>/Combined_Peak_Data.csv"
```
- **Output:** Multi-candidate CSV in `result/candidate/`.

### Lag Statistical Analysis (analyze_candidate_lag.py)
Determine characteristic lags by Station, Operation (Take-off/Landing), and ACTYPE using KDE and DBSCAN.
```bash
python analyze_candidate_lag.py -i "result/candidate/candidates_<airport>_....csv"
```
- **Output:** Individual PDF plots and summary tables (CSV/PDF) in `result/candidate/`.

### Flight Matching (match_flight.py)
A precise matching script that offers different modes for assigning flights to peaks.
```bash
python match_flight.py -p "result/<setup>/<airport>/Combined_Peak_Data.csv" -m [mode]
```
- **Modes:**
  - `-m 12m`: **1-to-Many** (Candidate Discovery). Finds all flights within the window.
  - `-m 121`: **1-to-1** (Peak-Unique). Each peak picks its best flight, but flights can be reused.
  - `-m 121e`: **1-to-1 Exclusive** (Universal Unique). Assigns each flight to only one peak (Priority: Leq & Direction).
- **Output:** Matched CSV in `result/matching/` (e.g., `result/matching/matched_121_....csv`).

### Matching Visualization (plot_matching_results.py)
Visualize the final matching outcomes including lag distribution and Leq vs Lag.
```bash
python plot_matching_results.py -i "result/matching/matched_1to1_....csv"
```
- **Output:** Final PDF reports in `result/matching/plots/`.

## 8. Peak Distribution Analysis (plot_peak.py)
Analyze the statistical distribution of noise event durations and Leq levels across all stations.
```bash
python plot_peak.py [options]
```
- **Options:**
  - `-i, --input`: Path to `Combined_Peak_Data.csv` (e.g., `result/<setup>/<airport>/Combined_Peak_Data.csv`).
  - `--orient`: Orientation of the bars: `v` (vertical - default) or `h` (horizontal).
  - `--exclude`: List of stations to exclude from the plot (e.g., `--exclude silapakorn`).
  - `--raw`: Plot the raw, unfiltered peak data instead of the filtered data (if available).
  - `--separate`: Generate individual PDF plots for each station rather than a single combined grid.
- **Features:**
  - Automatically detects model and airport from the input path.
  - **Academic Styling:** 4-column grid, black-edged histograms (no KDE).
  - **Statistical Indicators:** Mean values indicated by thick dashed black lines, and Outlier Boundaries (Prediction Interval - PI) shown as red dotted lines.
  - **Output:** PDF files in `plot/<model>/<airport>/`.

## 9. Map Plotting (map_plot.py)
Generate a PDF map showing the locations of the noise monitoring stations and Suvarnabhumi Airport (BKK).
```bash
python map_plot.py
```
- **Requirements:** Needs `contextily` and `geopandas` installed.
- **Features:** 
  - Automatically fetches station coordinates from `NMpostion.xlsx`.
  - Determines Suvarnabhumi Airport coordinates from `iata-icao.csv`.
  - Sizes the map appropriately with a 16:9 aspect ratio and English labels (CartoDB Voyager).
- **Output:** `bkk_stations_map.pdf` in the root directory.

## 10. Source Code Overview (`src/scripts/`)
Detailed breakdown of the internal logic and utility scripts.

### Core Logic
- **`aircraft_calculate.py`**: The primary engine for noise processing.
  - `NoiseCalculation`: Class handling peak discovery (`find_localpeak_alternative`).
  - `calculate_sound`: Extracts sound metrics (Leq, SEL), interval math, and IQR/PI Outlier filtering.
  - `calculate_station_peaks_worker`: Multiprocessing wrapper containing 10dB Down Validation context.
- **`data_processing.py`**: Orchestrates data aggregation and matching.
  - `process_combined_data`: Central entry point for processing accuracy.
  - `calculate_10db_validation_metrics`: Computes precision/recall of the 10dB rule.
  - `calculate_overall_metrics`, `calculate_station_metrics`, `calculate_metrics_by_hour`: Core TP/FP/FN logic.
  - `find_candidate_flights`, `match_1to1_exclusive`: Core business logic for time-lag matching.
  - `run_unified_matching`: Orchestrates the complex 12m, 121, and 121e flight matching mechanisms.
- **`matchingFlight.py`**: Implementation of the generic flight-to-peak matching logic based on time windows.
  - `find_flight_peak`: Initial broad search (1-to-M overlaps within boundaries).
  - `match_peak`: Secondary assignment within the lag width and lag direction.

### Modelling & Clustering (`src/scripts/modelling/`)
- **`dbscan_model.py`**: `find_peaks` (Core DBSCAN algorithm).
- **`msa_model.py`**: `find_peaks_msa` (Optimized Mean Shift via bin-seeding).
- **`k_means_model.py`**: `sound_clustering` (K-Means with elbow method).
- **`validate.py`**: `validate_10db_down` (Confirms legitimate aircraft noise events).

### Helpers & Utilities
- **`plot.py`**: Specialized visualization library.
  - Standard 12-Plot Logic (`generate_plot1...` to `generate_plot12...`).
  - Dashboard components (`plot_accuracy_metrics`, `plot_detailed_metrics_table`).
  - Comparison utilities (`compare_models_plot_grid`, `compare_stations_plot_grid_by_setup`).
  - Distribution reports (`plot_peak_distribution_grid`, `plot_peak_distribution_individual`).
  - Matching visualizations (`run_matching_plots`).
- **`preparation.py`**: Data ingestion and parsing.
  - `detect_metadata_from_path` & `get_param_from_folder`: Environment scanning and path interpretation.
  - `load_flight_logs`, `load_peak_data`: Data loading wrappers with safety checks.
  - `scan_folders`: Auto-discovers valid `result/` sub-folders for comparison mode.
- **`transform_data.py`**: Metadata conversion.
  - `load_with_cache`: Local SQLite caching for APIs.
  - `parse_date`, `to_time`, `phasedecide`: Standardization of dates/phases.
  - `call_airline_name`, `call_airport_name`, `call_airplane_name`: ICAO/IATA API extraction via web.
- **`util.py`**: Math and setup utilities.
  - `calculate_log_average`, `SoundAddition`, `computeL_eq_t`: Acoustic Logarithmic math.
  - `get_operation`, `determine_operation`: Validates physical runway operations based on routes (Take-off vs Landing).
  - `merge_intervals`, `is_time_in_intervals`: Used by advanced peak finders to merge noise events.

## 11. Directory Structure
All outputs are organized hierarchically by airport and model parameters to prevent data overlap.

```text
.
├── main.py (Main analysis pipeline)
├── main_plot.py (Standard 12-plot generator)
├── compare_plots.py (Model/Parameter comparison)
├── map_plot.py (Map generator for stations and airport)
├── plot_segmentation_performance.py (Segmentation trend tool)
├── convertfile.py (Raw RND to CSV converter)
├── run_vtbs_comparison.ps1 (Automation for Suvarnabhumi)
├── run_vtct_comparison.ps1 (Automation for Chiang Rai)
├── Merged_Converted_Flight_Log.xlsx (Flight data VTBS)
├── Merged_Converted_Flight_Log_VTCT.xlsx (Flight data VTCT)
├── iata-icao.csv (Airport code mapping)
├── raw_data/
│   ├── resources/ (Distance & elevation caching)
│   └── <airport>/ (e.g., vtbs, vtct)
│       └── <station>_noise_data.csv (Clean noise data)
├── src/ (Internal logic and models)
├── plot/ (New peak distribution reports)
│   └── <model>/<airport>/ (Sorted by setup)
└── result/
    ├── execution_times.json (Consolidated Timing & Accuracy Log)
    ├── comparison/ (Segmentation trends & multi-setup PDFs)
    │   ├── segmentation_performance_comparison.pdf
    │   └── 1_..., 2_... (Comparison reports)
    └── <setup_name>/ (e.g., dbscan_eps_150_min_samples_10_ma_legacy)
        └── <airport>/
            ├── Validated_Peaks_With_Flights.csv (Final matched results)
            └── plots/ (Standard station report PDFs)
```

---

# คู่มือการใช้งาน Aircraft Noise Calculator (ภาษาไทย)

คู่มือนี้แนะนำขั้นตอนการใช้งาน Script ต่างๆ ในโครงการสำหรับการประเมินเสียงอากาศยาน

## 0. การตั้งค่าเริ่มต้น
สร้าง virtual environment และติดตั้ง library ที่จำเป็น:
```bash
# สร้าง virtual environment
python -m venv venv

# เปิดใช้งาน
# Windows:
.\venv\Scripts\activate
# Mac / Ubuntu Linux:
source venv/bin/activate

# ติดตั้ง dependencies
pip install -r requirements.txt
```

## 1. การเตรียมตัว (venv)
เปิดใช้งาน virtual environment ก่อนเริ่มรันโค้ด:
```bash
# Windows
.\venv\Scripts\activate

# Mac / Ubuntu Linux
source venv/bin/activate
```

## 2. การแปลงไฟล์ข้อมูล (convertfile.py)
แปลงไฟล์ RND เป็น CSV เพื่อนำไปประมวลผลต่อ
```bash
python convertfile.py -ap vtbs
```
- สามารถใช้ `-ap` เพื่อระบุชื่อสนามบิน (ค่าเริ่มต้น: `vtbs`) ไฟล์ CSV จะถูกเก็บใน `raw_data/<airport>/`

## 3. การประมวลผลหลัก (main.py)
หาค่า Peak ของเสียงและจับคู่กับข้อมูลเที่ยวบิน (Flight Log)
```bash
python main.py -m dbscan -eps 150 -min_samples 10 -ma 121e
```
- **ตัวเลือกเพิ่มเติม:**
  - `-ma, --match-algorithm`: อัลกอริธึมจับคู่เที่ยวบิน (ค่าเริ่มต้น: `legacy`)
    - `legacy`: อัลกอริธึมเดิม ดึงข้อมูลสายการบินผ่าน API และดึงเที่ยวบิน 1-to-1 เบื้องต้น
    - `121e`: คัดแบบพิเศษ 1-ต่อ-1 (Exclusive) ให้เครื่อง 1 ลำจับคู่ได้ 1 คลื่นสูงสุดเท่านั้น (ให้สิทธิ์เสียงที่ดังกว่าจับคู่ก่อน)
    - `121`: คัดกรองเที่ยวบินที่ดีและตรงตามทิศรันเวย์ที่สุดต่อ 1 คลื่น (อิงส่วนต่าง Lag ต่ำสุด) เที่ยวบินซ้ำกันข้าม Peak ได้
    - `12m`: ดึงทุกเที่ยวบินที่บินอยู่ในช่วงเวลาการเกิดเสียงทั้งหมด
  - `-m, --model`: อัลกอริธึมสำหรับจัดกลุ่มสัญญาณ (`dbscan` หรือ `msa`) ค่าเริ่มต้น: `dbscan`
- ข้อมูลผลลัพธ์จะถูกเก็บแยกตามชุด parameter เเละอัลกอริธึมจับคู่ ในโฟลเดอร์ `result/<subfolder_name_ma_...>/`
- บันทึกเวลาเเละความเเม่นยำลงใน `result/execution_times.json`

## 4. การสร้างกราฟมาตรฐาน (main_plot.py)
สร้างรายงาน PDF ทั้งหมด 12 ประเภทจากการประมวลผลครั้งเดียว
```bash
python main_plot.py plot -m dbscan -eps 150 -min_samples 10
```
- รายงาน PDF จะถูกเก็บใน `result/<setup>/<airport>/plots/`

## 5. การเปรียบเทียบพารามิเตอร์และโมเดล (compare_plots.py)
เปรียบเทียบประสิทธิภาพระหว่างชุดพารามิเตอร์ต่างๆ หรือเปรียบเทียบข้ามรุ่นโมเดล
```bash
python compare_plots.py -m [model] [options]
```
- **ตัวเลือกเพิ่มเติม:**
  - `-m, --model`: ใส่ชื่อโมเดลเดี่ยว (เช่น `msa`) หรือรวมหลายโมเดลด้วยเครื่องหมาย `_` (เช่น `msa_dbscan`)
  - `-br, --bandwidth_range`: กำหนดช่วง Bandwidth ของ MSA (เช่น `-br 100,500`)
  - `-er, --eps_range`: กำหนดช่วง EPS ของ DBSCAN (เช่น `-er 150,200`)
  - `-ap, --airport`: ระบุชื่อสนามบิน (ค่าเริ่มต้น: `vtbs`)
  - `-se, --segment`: เปิดใช้งานการแบ่งข้อมูลเป็นส่วนๆ (Segmentation) เพื่อเพิ่มความเร็ว
  - `-K`: จำนวนส่วนที่ต้องการแบ่ง (ค่าเริ่มต้น: 100)
  - `--mode`: โหมดการประมวลผล: `p` หรือ `parallel` (เเยกเธรด - ค่าเริ่มต้น), `s` หรือ `sequential` (รันทีละสถานี)
- **ตัวอย่างการใช้งาน:**
  - เปรียบเทียบทั่วไป: `python compare_plots.py -m msa`
  - เปรียบเทียบข้ามโมเดล (DBSCAN และ MSA): `python compare_plots.py -m dbscan_msa`
  - เปรียบเทียบข้ามโมเดลในช่วงที่กำหนด: `python compare_plots.py -m msa_dbscan -br 100,300 -er 100,200`
- **การทำงาน:** สแกนโฟลเดอร์ใน `result/` ตามเงื่อนไขและสร้างกราฟเปรียบเทียบ
- **ผลลัพธ์:** ไฟล์รายงาน PDF ในโฟลเดอร์ `result/comparison/`

## 6. สคริปต์รันอัตโนมัติและการเปรียบเทียบ (Automated Scripts)
เพื่อความสะดวกในการรันหลายค่าพารามิเตอร์และเปรียบเทียบผลลัพธ์ ได้มีการจัดเตรียมสคริปต์ไว้ดังนี้:

### สำหรับ Windows (PowerShell)
รันสคริปต์เพื่อเเปลงไฟล์ข้อมูล ประมวลผล (พารามิเตอร์ 100-300) และสร้างรายงานเปรียบเทียบ:
- **สุวรรณภูมิ (VTBS):** `powershell -ExecutionPolicy Bypass -File .\run_vtbs_comparison.ps1`
- **เชียงราย (VTCT):** `powershell -ExecutionPolicy Bypass -File .\run_vtct_comparison.ps1`

### การเปรียบเทียบประสิทธิภาพการแบ่งข้อมูล (Segmentation)
เปรียบเทียบความเร็วและความแม่นยำระหว่างโหมดปกติและโหมด "Efficient Algorithm" (แบ่งข้อมูล):
- **Windows:** `powershell -ExecutionPolicy Bypass -File .\run_segmentation_comparison.ps1 <airport>`
- **Bash:** `./run_segmentation_comparison.sh <airport>`

### สำหรับ Linux / Mac / Git Bash (Bash)
ใช้สคริปต์เดียวที่รองรับทุกสนามบิน:
- **วิธีใช้:** `./run_comparison.sh <airport_code>` (เช่น `./run_comparison.sh vtct`)
- **หมายเหตุ:** สำหรับ Windows ต้องใช้ผ่านระบบ **Git Bash** หรือ **WSL** เท่านั้น

## 7. ชุดเครื่องมือ Matching เเละ Lag Analysis
ชุดเครื่องมือสำหรับค้นหาเเละวิเคราะห์ความต่างเวลา (Time Lag) ระหว่างเสียงเเละเที่ยวบิน

### การค้นหาตัวเลือกเที่ยวบิน (find_candidate.py)
ค้นหาทุกเที่ยวบินที่เป็นไปได้ในช่วงเวลาที่กำหนด (ค่าเริ่มต้น +/- 300 วินาที)
```bash
python find_candidate.py -p "result/<setup>/<airport>/Combined_Peak_Data.csv"
```
- **ผลลัพธ์:** ไฟล์ CSV รวมทุก Candidate ใน `result/candidate/`

### การวิเคราะห์ค่า Lag ทางสถิติ (analyze_candidate_lag.py)
หาค่า Lag มาตรฐานเเยกตามสถานี ประเภทการบิน เเละรุ่นเครื่องบิน ด้วย KDE เเละ DBSCAN
```bash
python analyze_candidate_lag.py -i "result/candidate/candidates_<airport>_....csv"
```
- **ผลลัพธ์:** กราฟ PDF รายสถานีเเละตารางสรุปเเบบเปรียบเทียบใน `result/candidate/`

### การจับคู่เเบบ 1-ต่อ-1 (match_1to1.py)
การจับคู่ที่เเม่นยำโดยเลือกเที่ยวบินที่ดีที่สุดเพียงลำเดียว พร้อมระบบ **Directional Priority** (ขาเข้า: Lag เป็นลบ / ขาออก: Lag เป็นบวก)
```bash
python match_1to1.py -p "result/<setup>/<airport>/Combined_Peak_Data.csv"
```
- **ผลลัพธ์:** ไฟล์จับคู่ 1-to-1 ใน `result/matching/`

### การวาดกราฟสรุปผล (plot_matching_results.py)
สร้างกราฟวิเคราะห์ผลลัพธ์การจับคู่ภาพรวม ทั้งการกระจายตัวของ Lag เเละความสัมพันธ์กับความดัง
```bash
python plot_matching_results.py -i "result/matching/matched_1to1_....csv"
```
- **ผลลัพธ์:** รายงาน PDF สรุปผลใน `result/matching/plots/`

## 8. การวิเคราะห์การกระจายตัวของ Peak (plot_peak.py)
วิเคราะห์การกระจายตัวทางสถิติของระยะเวลา (Duration) และระดับเสียง (Leq) ของทุกสถานี
```bash
python plot_peak.py [ตัวเลือก]
```
- **ตัวเลือก:**
  - `-i, --input`: ระบุพาธไฟล์ `Combined_Peak_Data.csv`
  - `--orient`: รูปแบบการวางกราฟ: `v` (แนวตั้ง - ค่าเริ่มต้น) หรือ `h` (แนวนอน)
  - `--exclude`: รายชื่อสถานีที่ต้องการยกเว้น (เช่น `--exclude silapakorn`)
  - `--raw`: สร้างกราฟจากข้อมูลดิบก่อนผ่านการตัด Outlier (ถ้ามีไฟล์ _Unfiltered.csv อยู่)
  - `--separate`: วาดและบันทึกกราฟแยกเป็นแต่ละสถานี แทนที่จะรวมเป็น Grid เดียวกัน
- **ความสามารถ:**
  - ระบุชื่อโมเดลและสนามบินจากพาธไฟล์โดยอัตโนมัติ
  - **Academic Styling:** จัดรูปแบบ 4 คอลัมน์สำหรับทั้ง 11 สถานี, Histogram แบบมีขอบดำ (ไม่มี KDE)
  - **Statistical Indicators:** แสดงค่าเฉลี่ย (Mean) ด้วยเส้นประหนาสีดำ และขอบเขต Outlier (Prediction Interval - PI) ด้วยเส้นจุดสีแดง
  - **ผลลัพธ์:** ไฟล์ PDF ในโฟลเดอร์ `plot/<model>/<airport>/`

## 9. การทำแผนที่พิกัดสถานี (map_plot.py)
สร้างแผนที่ PDF แสดงตำแหน่งของสถานีตรวจวัดระดับเสียงทั้งหมด และตำแหน่งของสนามบินสุวรรณภูมิ (BKK)
```bash
python map_plot.py
```
- **ข้อกำหนด:** ต้องมีการติดตั้งไลบรารี `contextily` และ `geopandas`
- **ความสามารถ:**
  - ดึงค่าพิกัดสถานีวิเคราะห์จากตาราง `NMpostion.xlsx`
  - ค้นหาพิกัดสนามบินจากฐานข้อมูล `iata-icao.csv`
  - สร้างแผนที่สัดส่วน 16:9 อัตโนมัติ โดยอิงจากขอบเขตข้อมูลทั้งหมด ด้วยฉากหลังภาษาอังกฤษ (CartoDB Voyager)
- **ผลลัพธ์:** ไฟล์ `bkk_stations_map.pdf` 

## 10. โครงสร้างซอร์สโค้ด (`src/scripts/`)
รายละเอียดหน้าที่การทำงานของ Script ต่างๆ ภายในระบบ

### ส่วนประมวลผลหลัก (Core Logic)
- **`aircraft_calculate.py`**: หัวใจหลักของการคำนวณเสียงอากาศยาน
  - `NoiseCalculation`: คลาสค้นหา Peak (`find_localpeak_alternative`)
  - `calculate_sound`: คำนวณค่าเทคนิคเสียง (Leq, SEL), ระยะเวลาตั้งตัดจบสัญญาณ และ Outliers (IQR/PI)
  - `calculate_station_peaks_worker`: ตัวจัดการการคำนวณแบบขนาน เเละตรวจสอบ Validation ตก 10 เดซิเบลขั้นสมบูรณ์
- **`data_processing.py`**: สคริปต์ประกอบและจัดการข้อมูลหลังคำนวณ
  - `process_combined_data`: ควบคุมการทำงานของโมดูลทั้งหมด (Ld, Ldn, Lden, สร้างตารางประเมินผล T/F/N)
  - `calculate_10db_validation_metrics`: ตรวจสอบ Precision/Recall จากกฎลด 10 dB
  - `calculate_overall_metrics`, `calculate_station_metrics`, `calculate_metrics_by_hour`: แกนกลางการคำนวณความแม่นยำรายวัน/รายชั่วโมง
  - `find_candidate_flights`: ระบบค้นหาเที่ยวบิน Candidate ระยะกว้าง
  - `run_unified_matching` & `match_1to1_exclusive`: ระบบสั่งการจับคู่เที่ยวบิน 1-to-1 และ 1-to-M โดยอิงจาก Prioritized Lag
- **`matchingFlight.py`**: ตรรกะจับคู่เที่ยวบินพื้นฐาน (เวลาทับซ้อน)
  - `find_flight_peak`: เปิดอวนดักกว้างๆ หาหลายเที่ยวบินที่ซ้อนทับกรอบเวลาเสียง
  - `match_peak`: ขั้นตอนคัดกรองเที่ยวบินภายในระยะหน่วง (Lag)

### โมเดลและการจัดกลุ่ม (`src/scripts/modelling/`)
- **`dbscan_model.py`**: `find_peaks` (การหาจุดยอดด้วยอัลกอริธึม DBSCAN ขจัด Noise)
- **`msa_model.py`**: `find_peaks_msa` (Mean Shift Algorithm ความเร็วสูงด้วยระบบ Bin-seeding และ Flatness Checker)
- **`k_means_model.py`**: `sound_clustering` (K-Means ด้วยระบบหาค่า K - Elbow method)
- **`validate.py`**: `validate_10db_down` (ตัวคำนวณกฎยืนยันตก 10 เดซิเบล เพื่อแยกว่าเป็นเครื่องบินจริงหรือไม่)

### ส่วนเสริมและยูทิลิตี้ (Helpers & Utilities)
- **`plot.py`**: คลังฟังก์ชันวาดกราฟิกทั้งหมด
  - พิมพ์รายงาน 12 แผ่น (`generate_plot1_daily_leq`, ถึง 12 ฯลฯ)
  - โมดูลสร้าง Dashboard ตารางคะแนน (`plot_accuracy_metrics`, `plot_detailed_metrics_table`)
  - ตัววาดเปรียบเทียบข้ามรุ่น (`compare_models_plot_grid`, `compare_stations_plot_grid_by_setup`)
  - พิมพ์กราฟสถิติกระจายตัว Peak ทั้งแบบเดี่ยวและแบบกลุ่ม (`plot_peak_distribution_grid`, `_individual`)
  - พิมพ์กราฟ Lag ของ Matching รายสถานี (`run_matching_plots`)
- **`preparation.py`**: การเตรียมและโหลดไฟล์ 
  - `load_config`, `get_param_from_folder`, `detect_metadata_from_path`: การสแกนตั้งค่าพารามิเตอร์จากชื่อ Directory
  - `load_flight_logs`, `load_peak_data`: ฟังก์ชันช่วยโหลด Data พร้อมเช็ค Error
  - `scan_folders`: สแกน Result ทั้งหมดในระบบอัตโนมัติ เพื่อดึงเข้า Compare Mode
- **`transform_data.py`**: แปลงพิกัด/ดึงชื่อ
  - `load_with_cache`: ระบบโหลดข้อมูล API เข้า Local SQLite3 เพื่อลดการดึง HTTP ซ้ำซ้อน
  - `parse_date`, `to_time`, `phasedecide`: Standardization ของวันที่และระยะห่างการบิน
  - `call_airline_name`, `call_airport_name`, `call_airplane_name` (แปลง Code ผ่านระบบฐานข้อมูลโลก)
- **`util.py`**: คณิตศาสตร์ทั่วไป
  - `calculate_log_average`, `SoundAddition`, `computeL_eq_t`: การคำนวณทางอะคูสติกส์-ลอการิทึม 
  - `get_operation`, `determine_operation`: พิสูจน์ว่าบิน Take-off / Landing ขึ้นอยู่กับเส้นทางการบินและท่าอากาศยานที่ดักฟัง
  - `merge_intervals`, `is_time_in_intervals`: ฟังก์ชันผสานช่วงเวลากรณีเสียงคาบเกี่ยวกัน

## 11. โครงสร้างโฟลเดอร์ (Directory Structure)
ข้อมูลผลลัพธ์จะถูกจัดเก็บอย่างเป็นระบบตามชื่อสนามบินและพารามิเตอร์ที่ใช้ เพื่อป้องกันข้อมูลทับซ้อนกัน

```text
.
├── main.py (ตัวประมวลผลหลัก)
├── main_plot.py (ตัวสร้างกราฟรายงาน 12 รูปเเบบ)
├── compare_plots.py (ตัวเปรียบเทียบพารามิเตอร์)
├── map_plot.py (ตัววาดแผนที่พิกัดสถานีเเละสนามบิน)
├── plot_segmentation_performance.py (ตัววิเคราะห์ค่า K)
├── run_... .ps1 (สคริปต์รันอัตโนมัติ)
├── Merged_Converted_Flight_Log... .xlsx (ตารางเที่ยวบิน)
├── raw_data/
│   ├── resources/ (เเคชข้อมูลระยะทาง)
│   └── <airport>/ (เช่น vtbs, vtct)
│       └── <station>_noise_data.csv (ข้อมูลเสียงมาตรฐาน)
└── result/
    ├── execution_times.json (บันทึกสถิติรวม)
    ├── comparison/ (กราฟเปรียบเทียบข้ามรุ่นเเละค่า K)
    │   ├── segmentation_performance_comparison.pdf
    │   └── 1_..., 2_... (รายงานเปรียบเทียบ)
    └── <setup_name_ma_...>/ (เเยกตามโหมดที่รัน เเละ Matching ปกติคือ ma_legacy)
        └── <airport>/
            ├── Validated_Peaks_With_Flights.csv (ผลลัพธ์สุดท้าย)
            └── plots/ (รายงาน PDF รายสถานี)
```
