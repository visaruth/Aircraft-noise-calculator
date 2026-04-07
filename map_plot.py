import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import contextily as cx
from shapely.geometry import Point

def create_map():
    print("Loading data...")
    # Load station data
    try:
        df_stations = pd.read_excel('NMpostion.xlsx')
    except Exception as e:
        print(f"Error reading NMpostion.xlsx: {e}")
        return

    # Column names based on user snippet
    lat_col = 'Decimal (Y): lattitude (°N) '
    lon_col = 'Decimal (X): longitude (°E)'
    place_col = 'Place'
    
    if lat_col not in df_stations.columns or lon_col not in df_stations.columns:
        print(f"Error: Could not find latitude/longitude columns in NMpostion.xlsx.")
        print(f"Available columns: {df_stations.columns.tolist()}")
        return

    # Load airport data
    try:
        df_airports = pd.read_csv('iata-icao.csv', encoding='utf-8', on_bad_lines='skip')
        bkk_data = df_airports[df_airports['iata'] == 'BKK'].iloc[0]
        bkk_lat = float(bkk_data['latitude'])
        bkk_lon = float(bkk_data['longitude'])
    except Exception as e:
        print(f"Error reading iata-icao.csv: {e}")
        return

    print(f"Found BKK coordinates: Lat {bkk_lat}, Lon {bkk_lon}")

    # Create GeoDataFrames (EPSG:4326 is WGS84 for Lat/Lon)
    geometry_stations = [Point(xy) for xy in zip(df_stations[lon_col], df_stations[lat_col])]
    gdf_stations = gpd.GeoDataFrame(df_stations, geometry=geometry_stations, crs="EPSG:4326")

    gdf_airport = gpd.GeoDataFrame({'Place': ['Suvarnabhumi Airport (BKK)']}, 
                                   geometry=[Point(bkk_lon, bkk_lat)], 
                                   crs="EPSG:4326")

    # Combine to calculate bounds easily
    gdf_all = pd.concat([gdf_stations, gdf_airport], ignore_index=True)

    # Convert to Web Mercator (EPSG:3857) for Contextily basemaps
    print("Converting CRS and preparing plot...")
    gdf_stations = gdf_stations.to_crs(epsg=3857)
    gdf_airport = gdf_airport.to_crs(epsg=3857)
    gdf_all = gdf_all.to_crs(epsg=3857)

    # Calculate bounds
    minx, miny, maxx, maxy = gdf_all.total_bounds
    
    # Add 10% padding to the bounding box initially
    x_padding = (maxx - minx) * 0.1
    y_padding = (maxy - miny) * 0.1
    
    final_minx, final_maxx = minx - x_padding, maxx + x_padding
    final_miny, final_maxy = miny - y_padding, maxy + y_padding
    
    # Force 16:9 rectangle aspect ratio by expanding the shorter dimension
    x_range = final_maxx - final_minx
    y_range = final_maxy - final_miny
    
    target_aspect = 16.0 / 9.0
    current_aspect = x_range / y_range
    
    if current_aspect < target_aspect:
        # Too tall, need to expand X
        needed_x = y_range * target_aspect
        diff = (needed_x - x_range) / 2
        final_minx -= diff
        final_maxx += diff
    else:
        # Too wide, need to expand Y
        needed_y = x_range / target_aspect
        diff = (needed_y - y_range) / 2
        final_miny -= diff
        final_maxy += diff
        
    fig_width = 16
    fig_height = 9
    
    # Plotting
    fig, ax = plt.subplots(figsize=(fig_width, fig_height))

    # Plot stations
    gdf_stations.plot(ax=ax, color='red', marker='o', markersize=50, label='Noise Stations')

    # Annotate stations
    for x, y, label in zip(gdf_stations.geometry.x, gdf_stations.geometry.y, gdf_stations[place_col]):
        ax.annotate(label, xy=(x, y), xytext=(5, 5), textcoords="offset points", 
                    fontsize=9, ha='left', va='bottom', 
                    bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="gray", alpha=0.8))

    # Plot airport
    gdf_airport.plot(ax=ax, color='blue', marker='*', markersize=300, label='BKK Airport')
    
    # Annotate airport
    ax.annotate('Suvarnabhumi Airport', 
                xy=(gdf_airport.geometry.x.iloc[0], gdf_airport.geometry.y.iloc[0]), 
                xytext=(10, -10), textcoords="offset points", 
                fontsize=11, fontweight='bold', color='blue', 
                ha='left', va='top',
                bbox=dict(boxstyle="round,pad=0.3", fc="yellow", ec="blue", alpha=0.8))

    ax.set_xlim(final_minx, final_maxx)
    ax.set_ylim(final_miny, final_maxy)

    # Add CartoDB Voyager basemap (mostly English labels globally)
    print("Adding English basemap (CartoDB Voyager)...")
    cx.add_basemap(ax, source=cx.providers.CartoDB.Voyager)

    ax.set_title('Noise Stations and Suvarnabhumi Airport (BKK)', fontsize=16)
    ax.set_axis_off()  # Hide axis coordinates as they are in EPSG 3857

    plt.legend(loc='upper right')
    plt.tight_layout()

    # Save to PDF
    output_pdf = 'bkk_stations_map.pdf'
    plt.savefig(output_pdf, format='pdf', dpi=300, bbox_inches='tight')
    print(f"Successfully saved map to {output_pdf}")

if __name__ == '__main__':
    create_map()
