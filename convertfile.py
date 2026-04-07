import os
import sys
import pandas as pd

# Ensure src module can be imported
current_dir = os.getcwd()
if current_dir not in sys.path:
    sys.path.append(current_dir)

from src.scripts.preparation import input_files

# Configuration for all sites
SITES = {
    "Romruedee-Romklao": {
        "rnd_dir": os.path.join("Aircraft-Noise", "Noise-Measurement-data", "Raw-data", "1-Romruedee-Romklao-12-20-Mar-2014", "AU1_0001"),
        "noise_csv": "raw_data/romruedee_noise_data.csv"
    },
    "Central-Village": {
        "rnd_dir": os.path.join("Aircraft-Noise", "Noise-Measurement-data", "Raw-data", "2-Central-Village-3-11-Apr-2014", "AU1_0002"),
        "noise_csv": "raw_data/central_village_noise_data.csv"
    },
    "Bangchalong-Canal": {
        "rnd_dir": os.path.join("Aircraft-Noise", "Noise-Measurement-data", "Raw-data", "3-Bangchalong-Canal-3-11-Apr-2014", "AU1_0001"),
        "noise_csv": "raw_data/bangchalong_canal_noise_data.csv"
    },
    "Bangchalong-Canal-SE-runway": {
        "rnd_dir": os.path.join("Aircraft-Noise", "Noise-Measurement-data", "Raw-data", "3-Bangchalong-Canal-SE-runway-Aug-2015", "R-Au1", "AU1_0002"),
        "noise_csv": "raw_data/bangchalong_canal_se_runway_noise_data.csv"
    },
    "ThanaPlace": {
        "rnd_dir": os.path.join("Aircraft-Noise", "Noise-Measurement-data", "Raw-data", "4-ThanaPlace-28-Apr-7-May-2014", "AU1_0002"),
        "noise_csv": "raw_data/thana_place_noise_data.csv"
    },
    "Romklao27": {
        "rnd_dir": os.path.join("Aircraft-Noise", "Noise-Measurement-data", "Raw-data", "5-Romklao27-28-Apr-7-May-2014", "AU1_0001"),
        "noise_csv": "raw_data/romklao27_noise_data.csv"
    },
    "Bangsaothong": {
        "rnd_dir": os.path.join("Aircraft-Noise", "Noise-Measurement-data", "Raw-data", "7-Bangsaothong-10-17-May-2014", "AU1_0002"),
        "noise_csv": "raw_data/bangsaothong_noise_data.csv"
    },
    "BangPla43": {
        "rnd_dir": os.path.join("Aircraft-Noise", "Noise-Measurement-data", "Raw-data", "6-BangPla43-10-17-May-2014", "AU1_0001"),
        "noise_csv": "raw_data/bang_pla43_noise_data.csv"
    },
    "HabitiaRamindra": {
        "rnd_dir": os.path.join("Aircraft-Noise", "Noise-Measurement-data", "Raw-data", "8-Habitia-Ramindra-20-26-May-2014", "AU1_0001"),
        "noise_csv": "raw_data/habitia_ramindra_noise_data.csv"
    },
    "Ladkrabang34": {
        "rnd_dir": os.path.join("Aircraft-Noise", "Noise-Measurement-data", "Raw-data", "9-Ladkrabang34-4-AOTs-NW-runway-Aug-2015", "R-Au1", "AU1_0001"),
        "noise_csv": "raw_data/ladkrabang34_noise_data.csv"
    },
    "Silapakorn": {
        "rnd_dir": os.path.join("Aircraft-Noise", "Noise-Measurement-data", "Raw-data", "10-Silapakorn-Uni-Control-site-2015", "AU1_0001"),
        "noise_csv": "raw_data/silapakorn_noise_data.csv"
    }
}

def process_vtct():
    airport = 'vtct'
    raw_data_dir = os.path.join('raw_data', airport)
    os.makedirs(raw_data_dir, exist_ok=True)
    
    # 1. Noise Conversion
    # File name in MahPahLuangAirport directory
    # User mentioned: MahPahLuangAirport\Leq0.5s-VTCT-Date20to25Mar2019.xlsx
    noise_excel = os.path.join('MahPahLuangAirport', 'Leq0.5s-VTCT-Date20to25Mar2019.xlsx')
    noise_csv_path = os.path.join(raw_data_dir, 'payao_noise_data.csv')
    
    if os.path.exists(noise_excel):
        if not os.path.exists(noise_csv_path):
            print(f"Converting VTCT noise data from: {noise_excel}")
            try:
                import re
                # Based on previous check, data starts at row 9 (skip 8)
                sheet_dict = pd.read_excel(noise_excel, sheet_name=None, skiprows=8)
                df_noise = pd.concat(sheet_dict.values(), ignore_index=True)
                
                # Fix non-standard timestamp format: '3/20/2019 12:00:00 AM:500' -> '3/20/2019 12:00:00.500 AM'
                if 'Period start' in df_noise.columns:
                    print("  Preprocessing timestamps for VTCT...")
                    def fix_timestamp(ts):
                        if isinstance(ts, str):
                            # Move ms part before AM/PM
                            return re.sub(r'(.*)\s+(AM|PM):(\d+)', r'\1.\3 \2', ts)
                        return ts
                    
                    df_noise['Period start'] = df_noise['Period start'].apply(fix_timestamp)
                
                # Standardize columns
                if 'Period start' in df_noise.columns and 'Leq' in df_noise.columns:
                    df_noise.to_csv(noise_csv_path, index=False, encoding='utf-8')
                    print(f"Saved VTCT noise data to: {noise_csv_path}")
                else:
                    print(f"Error: VTCT noise data columns mismatch. Found: {df_noise.columns.tolist()}")
            except Exception as e:
                print(f"Error converting VTCT noise: {e}")
        else:
            print(f"VTCT Noise CSV already exists: {noise_csv_path}")
    else:
        print(f"Warning: VTCT noise excel not found at {noise_excel}")
            
    # 2. Flight Log Conversion
    # User mentioned: MahPahLuangAirport\Billing-ท่าอากาศยานแม่ฟ้าหลวง เชียงราย.xlsx
    flight_excel = os.path.join('MahPahLuangAirport', 'Billing-ท่าอากาศยานแม่ฟ้าหลวง เชียงราย.xlsx')
    flight_output = f'Merged_Converted_Flight_Log_{airport.upper()}.xlsx'
    
    if os.path.exists(flight_excel):
        print(f"Converting VTCT flight log from: {flight_excel}")
        try:
            sheet_dict = pd.read_excel(flight_excel, sheet_name=None)
            df_flight = pd.concat(sheet_dict.values(), ignore_index=True)
            # Map columns to match Suvarnabhumi format
            # Raw: ['ID', 'TYPE', 'A/D', 'RUNWAY', 'DATE', 'TIME', 'TIME1', 'FROM', 'TO', 'LOCAL DATE', 'LOCAL DATE.1']
            mapping = {
                'ID': 'CALLSIGN',
                'TYPE': 'ACTYPE',
                'A/D': 'APPDEPFLAG',
                'RUNWAY': 'RWY',
                'FROM': 'POD',
                'TO': 'DEST',
                'LOCAL DATE.1': 'LOCAL TIME'
            }
            df_conv = df_flight.rename(columns=mapping)
            
            # APPDEPFLAG: DEP -> D, ARR -> A
            df_conv['APPDEPFLAG'] = df_conv['APPDEPFLAG'].map({'DEP': 'D', 'ARR': 'A'})
            
            # Handle LOCAL DATE (Buddhist Era 2562 -> 2019)
            if 'LOCAL DATE' in df_conv.columns:
                print("  Converting Buddhist Era dates to Common Era...")
                def transform_be_to_ce(dt_val):
                    if pd.isnull(dt_val): return dt_val
                    s_dt = str(dt_val)
                    # Extract 4-digit year (e.g. 2562)
                    import re
                    match = re.search(r'(\d{4})', s_dt)
                    if match:
                        year = int(match.group(1))
                        if year > 2400: # Threshold for BE
                            ce_year = year - 543
                            return s_dt.replace(str(year), str(ce_year), 1)
                    return dt_val
                
                df_conv['LOCAL DATE'] = df_conv['LOCAL DATE'].apply(transform_be_to_ce)
                df_conv['LOCAL DATE'] = pd.to_datetime(df_conv['LOCAL DATE'], errors='coerce')
                # Format as yyyy.mm.dd to match VTBS standard
                df_conv['LOCAL DATE'] = df_conv['LOCAL DATE'].dt.strftime('%Y.%m.%d')
            
            # Add missing REGISTRATION column if needed
            if 'REGISTRATION' not in df_conv.columns:
                df_conv['REGISTRATION'] = ''
                
            # Filter and order columns as per VTBS format
            std_cols = ['LOCAL DATE', 'LOCAL TIME', 'CALLSIGN', 'REGISTRATION', 'ACTYPE', 'POD', 'DEST', 'RWY', 'APPDEPFLAG']
            # Only keep columns that exist
            final_cols = [c for c in std_cols if c in df_conv.columns]
            df_final = df_conv[final_cols]
            
            df_final.to_excel(flight_output, index=False)
            print(f"Saved standardized VTCT flight log to: {flight_output}")
        except Exception as e:
            print(f"Error converting VTCT flight log: {e}")
    else:
        print(f"Warning: VTCT flight log excel not found at {flight_excel}")

def process_all(airport='vtbs'):
    if airport == 'vtct':
        process_vtct()
        return

    # Standard VTBS logic
    raw_data_dir = os.path.join('raw_data', airport)
    os.makedirs(raw_data_dir, exist_ok=True)
    os.makedirs('Processed-data', exist_ok=True)
    os.makedirs('logs', exist_ok=True)

    for station, config in SITES.items():
        print(f"\n>>> Processing Station: {station}")
        
        # Determine output path based on airport
        base_name = os.path.basename(config["noise_csv"])
        noise_csv_path = os.path.join(raw_data_dir, base_name)
        
        # Step 1: Convert RND to Noise CSV
        if not os.path.exists(noise_csv_path):
            rnd_dir = config['rnd_dir']
            print(f"Converting RND files from: {rnd_dir}")
            try:
                df_sound = input_files(os.path.abspath(rnd_dir))
                df_sound.to_csv(noise_csv_path, index=False, encoding='utf-8')
                print(f"Saved sound data to: {noise_csv_path}")
            except Exception as e:
                print(f"Error converting RND for {station}: {e}")
                continue
        else:
            print(f"Noise CSV already exists: {noise_csv_path}")

    print(f"\nConversion complete. All noise files for {airport} are ready in '{raw_data_dir}' directory.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Convert airport-specific noise and flight files to standard CSV format.")
    parser.add_argument('-ap', '--airport', type=str, default='vtbs', help="Airport code (e.g., vtbs, vtct)")
    args = parser.parse_args()
    
    process_all(airport=args.airport.lower())
