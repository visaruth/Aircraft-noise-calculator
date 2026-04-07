import numpy as np
import pandas as pd
import os.path
import glob
import datetime as datetime

from src.scripts.transform_data import parse_date


def load_config(directory):
    file_name = [f for f in glob.glob(os.path.join(directory, "*.RNH"))]
    if not file_name:
        raise FileNotFoundError(f"No .RNH file found in directory: {directory}")
        
    with open(file_name[0], "r") as f:
        conf = f.read()
    
    t = {}
    lines = conf.split("\n")
    for i in lines:
        if i.strip() == "":
            continue
            
        # Handle different delimiters: comma (standard) or tab/whitespace (Ladkrabang34)
        if "," in i:
            temp = i.split(",", 1)
        else:
            # Fallback: split by tab or 2+ consecutive spaces
            import re
            temp = re.split(r'\t|\s{2,}', i.strip(), maxsplit=1)
            
        if len(temp) >= 2:
            t[temp[0].strip()] = temp[1].strip()
    return t


def files_dir_clean(file_names):
    conf = load_config(file_names)

    file_names = [f for f in glob.glob(os.path.join(file_names, "*.RND"))]
    open_files = [
        open(f, "r").read().replace(" ", "").replace(",", "").split("\n")
        for f in file_names
    ]

    data_concat = [x for lst in open_files for x in lst]
    data_cleaned = " ".join(data_concat).split()
    sound_lists = [float(data.replace("O", "0")) for data in data_cleaned]

    start = parse_date(conf["Start Time"])
    time = [
        start + datetime.timedelta(milliseconds=(100 * i))
        for i in range(len(sound_lists))
    ]
    df = pd.DataFrame({"Period start": time, "Leq": sound_lists})

    return df


def file_xlsx_clean(f_name, sheet_list):
    sound_files = [
        pd.read_excel(f_name, header=None, sheet_name=sn) for sn in sheet_list
    ]
    config_files = [dict(zip(sf[0:8][0], sf[0:8][1])) for sf in sound_files]
    sound_files = [
        pd.concat(
            [sf, pd.DataFrame({0: [config_files[i]["End"]], 1: [np.nan]})],
            ignore_index=True,
        )
        for i, sf in enumerate(sound_files)
    ]

    sound_list = [
        pd.DataFrame(sf[9:].values, columns=sf[8:9].values[0]) for sf in sound_files
    ]

    df = pd.concat(sound_list)
    df_clean = df[~(df["Period start"].str.contains("Overall"))].reset_index(drop=True)
    df_clean.fillna(method="ffill", inplace=True)

    return df_clean


def input_files(f_name):
    print("Checking file format...")
    
    # Robust cross-platform check for file type
    if os.path.isfile(f_name):
        ext = os.path.splitext(f_name)[1].lower()
        if ext == ".xlsx":
            xl = pd.ExcelFile(f_name)
            sheet_list = xl.sheet_names

            for c in ["Billing", "billing"]:
                if c in sheet_list:
                    sheet_list.remove(c)

            sound_lists = file_xlsx_clean(f_name, sheet_list)
            sound_lists["Period start"] = sound_lists["Period start"].apply(
                lambda a: parse_date(a)
            )
        elif ext == ".csv":
            # Optional: handle CSV directly if needed
            sound_lists = pd.read_csv(f_name)
        else:
            # If it's a file but not xlsx/csv, try dir cleanup parent folder
            sound_lists = files_dir_clean(os.path.dirname(f_name))
    else:
        # If it's a directory, perform directory-based RND cleanup
        sound_lists = files_dir_clean(f_name)

    return sound_lists

def load_flight_logs(excel_path):
    """
    Robustly loads flight logs from Excel, normalizing datetime columns.
    """
    if not os.path.exists(excel_path):
        print(f"Warning: Cannot find flight log at: {excel_path}")
        return pd.DataFrame()
    
    # Read all sheets in case the flight log is separated by days
    sheet_dict = pd.read_excel(excel_path, sheet_name=None)
    df_flight = pd.concat(sheet_dict.values(), ignore_index=True)
    if 'datetime' not in df_flight.columns:
        if 'LOCAL DATE' in df_flight.columns and 'LOCAL TIME' in df_flight.columns:
            df_flight['datetime_str'] = df_flight['LOCAL DATE'].astype(str).str.split().str[0] + " " + df_flight['LOCAL TIME'].astype(str).str.split().str[-1]
            df_flight['datetime'] = pd.to_datetime(df_flight['datetime_str'], errors='coerce', format='mixed')
        elif 'datetime_th' in df_flight.columns:
            df_flight = df_flight.rename(columns={'datetime_th': 'datetime'})
             
    if 'datetime' in df_flight.columns:
        df_flight['datetime'] = pd.to_datetime(df_flight['datetime'], errors='coerce')
        df_flight = df_flight.dropna(subset=['datetime'])
    return df_flight

def load_precomputed_metrics(input_dir):
    """
    Loads all metrics-related CSV files from a result subfolder.
    """
    import os
    import pandas as pd
    data = {}
    
    def try_read(filepath):
        if os.path.exists(filepath):
            try:
                return pd.read_csv(filepath)
            except Exception as e:
                print(f"Warning: Error reading {filepath}: {e}")
        else:
            print(f"Warning: Missing data file {filepath}")
        return None

    data['daily_leq'] = try_read(os.path.join(input_dir, 'daily_leq_metrics.csv'))
    data['validation'] = try_read(os.path.join(input_dir, 'Station_Flight_Validation.csv'))
    data['metrics'] = try_read(os.path.join(input_dir, 'all_stations_metrics_detailed.csv'))
    data['actype_counts'] = try_read(os.path.join(input_dir, 'ACTYPE_Counts_Per_Site.csv'))
    data['hourly_leq'] = try_read(os.path.join(input_dir, 'all_stations_hourly_leq.csv'))
    
    return data

def get_param_from_folder(folder_name):
    """
    Extracts model type and parameter value from folder name.
    """
    import re
    m_type, m_val = None, None
    if 'dbscan' in folder_name:
        match = re.search(r'eps_(\d+)', folder_name)
        m_val = int(match.group(1)) if match else None
        m_type = 'dbscan'
    elif 'msa' in folder_name:
        m_type = 'msa'
        if 'default' in folder_name:
            m_val = 'default'
        else:
            match = re.search(r'bandwidth_([\d_.]+)', folder_name)
            if match:
                val_str = match.group(1).replace('_', '.')
                try: m_val = float(val_str)
                except: m_val = match.group(1)
    
    if m_type and 'segmented' in folder_name.lower():
        k_match = re.search(r'K(\d+)', folder_name)
        k_val = k_match.group(1) if k_match else "X"
        m_type = f"{m_type}_seg_K{k_val}"
        
    return m_type, m_val

def get_folder_label(folder_path):
    """Returns a nice label for the comparison plots."""
    import os
    name = os.path.basename(folder_path)
    m_type, m_val = get_param_from_folder(name)
    if not m_type: return name
    
    clean_type = m_type.split('_')[0].upper()
    label = f"{clean_type}(val={m_val})"
    
    if 'seg' in m_type:
        k_val = m_type.split('K')[1] if 'K' in m_type else "?"
        label += f" [SEG K={k_val}]"
    return label

def scan_folders(model_list, bandwidth_range=None, eps_range=None, airport='vtbs'):
    """
    Scan output directory for subfolders matching criteria.
    """
    import os
    import glob
    if not os.path.exists('result'): return []
        
    setups = [s for s in glob.glob(os.path.join('result', '*')) if os.path.isdir(s)]
    selected = []
    
    for setup_path in setups:
        setup_name = os.path.basename(setup_path)
        if setup_name in ['comparison', 'raw_data', 'execution_times.json']: continue
        
        airport_dir = os.path.join(setup_path, airport)
        if not os.path.exists(airport_dir): continue
            
        m_type, m_val = get_param_from_folder(setup_name)
        if not m_type: continue
            
        # Model filter
        if m_type not in model_list: continue
            
        # Range filters
        if 'msa' in m_type and bandwidth_range:
            if isinstance(m_val, (int, float)):
                if not (bandwidth_range[0] <= m_val <= bandwidth_range[1]): continue
        if 'dbscan' in m_type and eps_range:
            if isinstance(m_val, int):
                if not (eps_range[0] <= m_val <= eps_range[1]): continue
                    
        selected.append(setup_path)
        
    return sorted(selected)

def detect_metadata_from_path(file_path):
    """
    Extracts model_name, airport_name, and k_value from a result file path.
    """
    import os
    import re
    
    abs_path = os.path.abspath(file_path)
    path_parts = abs_path.split(os.sep)
    
    model_name = None
    airport_name = 'vtbs' # Default
    k_value = ""
    
    if 'result' in path_parts:
        res_idx = path_parts.index('result')
        
        # 1. Detect Model (Folder immediately after 'result')
        if res_idx + 1 < len(path_parts):
            model_name = path_parts[res_idx + 1]
            
        # 2. Detect Airport (subfolder after model)
        if res_idx + 2 < len(path_parts):
            pot_airport = path_parts[res_idx + 2]
            # Airport codes are usually short (vtbs, vtct)
            if len(pot_airport) <= 5 and pot_airport != os.path.basename(file_path):
                airport_name = pot_airport
                
        # 3. Detect K-Value from model_name folder
        if model_name and '_K' in model_name:
            k_match = re.search(r'_K(\d+)', model_name)
            if k_match:
                k_value = f"K{k_match.group(1)}"
                
    # Fallback for model if not found from result structure
    if not model_name:
        path_lower = file_path.lower()
        if 'dbscan' in path_lower: model_name = 'dbscan'
        elif 'msa' in path_lower: model_name = 'msa'
        else: model_name = 'unknown'
        
    return model_name, airport_name, k_value
