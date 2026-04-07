import os
import pandas as pd
import datetime
import requests
import io

# Setup resource directory for caching external data
RESOURCE_DIR = os.path.join('raw_data', 'resources')
os.makedirs(RESOURCE_DIR, exist_ok=True)

def load_with_cache(url, cache_filename, type_name):
    """Loads data from cache if available, otherwise downloads with timeout."""
    cache_path = os.path.join(RESOURCE_DIR, cache_filename)
    
    # Try loading from local cache first
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
        try:
            return pd.read_csv(cache_path)
        except Exception as e:
            print(f"Warning: Failed to read cache {cache_filename}: {e}")
            
    # Download if not in cache or reading failed
    print(f"Attempting to download {type_name} data from {url}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    try:
        # Use a strict 5-second timeout to avoid blocking during parallel imports
        response = requests.get(url, headers=headers, timeout=5)
        response.raise_for_status()
        
        # Parse HTML tables
        dfs = pd.read_html(io.StringIO(response.text))
        df = dfs[0] if dfs else pd.DataFrame()
            
        # Save to local cache for future use
        if not df.empty:
            df.to_csv(cache_path, index=False)
            print(f"  Successfully cached {type_name} data to {cache_path}")
        return df
    except Exception as e:
        print(f"Warning: Failed to fetch {type_name} data from web: {e}")
        # Handle fallback if no cache exists
        if os.path.exists(cache_path):
            print(f"  Falling back to existing (possibly legacy) cache at {cache_path}")
            return pd.read_csv(cache_path)
        
        # Minimal empty data-frames for failure cases to prevent crashes
        if type_name == 'airline':
            return pd.DataFrame(columns=["ICAO", "Airline"])
        elif type_name == 'airplane':
            return pd.DataFrame(columns=["ICAO Code", "WTC"])
        return pd.DataFrame()

# --- Initialize lookup data (Lazy-loaded globals for module compatibility) ---

# 1. Airline Codes (Wikipedia)
airline_data = load_with_cache(
    "https://en.wikipedia.org/wiki/List_of_airline_codes", 
    "airline_codes.csv", 
    "airline"
)
callsign_name = airline_data.dropna(subset=["ICAO"]) if not airline_data.empty and "ICAO" in airline_data.columns else pd.DataFrame(columns=["ICAO", "Airline"])
airline_dict = dict(zip(callsign_name["ICAO"], callsign_name["Airline"]))

# 2. Airplane Types (AVCodes)
airplane_data = load_with_cache(
    "https://www.avcodes.co.uk/acrtypes.asp", 
    "airplane_types.csv", 
    "airplane"
)
airplane_name = airplane_data.dropna(subset=["ICAO Code"]) if not airplane_data.empty and "ICAO Code" in airplane_data.columns else pd.DataFrame(columns=["ICAO Code", "WTC"])
airplane_dict = dict(zip(airplane_name["ICAO Code"], airplane_name["WTC"]))

# 3. Airport Names (Local CSV)
try:
    airport_names = pd.read_csv("./iata-icao.csv")
    airport_names = airport_names.dropna(subset=["icao"])
    airport_dict = dict(zip(airport_names["icao"], airport_names["airport"]))
except Exception as e:
    print(f"Warning: Failed to load local iata-icao.csv: {e}")
    airport_names = pd.DataFrame(columns=["icao", "airport"])
    airport_dict = {}


def parse_date(dt):
    date_format = [
        "%m/%d/%Y %I:%M:%S %p:%f",
        "%Y/%m/%d %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y-%m-%d",
        "%m-%d-%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
        "%Y-%m-%d %H:%M:%S",
        "%m-%d-%Y %H:%M:%S",
        "%d-%m-%Y %H:%M:%S",
    ]

    for date_f in date_format:
        try:
            dateObject = datetime.datetime.strptime(dt, date_f)
            return dateObject
        except:
            continue
    return None


def to_time(t):
    t_dt = pd.to_datetime(t)
    return t_dt.time()


def to_date(dt):
    try:
        dt = pd.to_datetime(dt)
        return dt
    except:
        dateObject = datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S")
        dt_str = dateObject.date()
        return datetime.date(dt_str.year - 543, dt_str.month, dt_str.day)


def phasedecide(date):
    dt = date.time()
    if (dt.hour >= 7) & (dt.hour < 19):
        return 1
    elif (dt.hour >= 19) & (dt.hour < 22):
        return 2
    else:
        return 3


def call_airline_name(call):
    c_name = "".join(i for i in call if not i.isdigit())
    if c_name in airline_dict:
        return airline_dict[c_name]
    else:
        return c_name


def call_airport_name(name):
    if name in airport_dict:
        return airport_dict[name]
    else:
        return name


def call_airplane_name(name):
    if name in airplane_dict:
        return airplane_dict[name]
    else:
        return "Unknown"
