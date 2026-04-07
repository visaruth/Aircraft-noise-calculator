import os
import argparse
import time
from src.scripts.plot import setup_plot_dir, cleanup_temp_dir, generate_comparison_type_a, generate_comparison_type_b
from src.scripts.preparation import scan_folders, get_folder_label

def parse_range(range_str):
    if not range_str: return None
    try:
        parts = [float(x.strip()) for x in range_str.split(',')]
        if len(parts) == 2:
            return sorted(parts)
        return None
    except:
        return None

def main():
    parser = argparse.ArgumentParser(
        description="Aircraft Noise Comparison Tool (Modular) - Compare metrics across different parameters or models.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument('-m', '--model', type=str, required=True,
                       help="Model name (e.g., 'dbscan') or multiple models joined by underscore (e.g., 'msa_dbscan').")
    parser.add_argument('-br', '--bandwidth_range', type=str, 
                       help="Filter MSA by bandwidth range (e.g., '100,500')")
    parser.add_argument('-er', '--eps_range', type=str, 
                       help="Filter DBSCAN by EPS range (e.g., '100,200')")
    parser.add_argument('-ap', '--airport', type=str, default='vtbs', help="Airport code (default: vtbs)")
    parser.add_argument('--exclude', type=str, nargs='*', default=['silapakorn', 'habitia_ramindra'],
                       help="List of stations to exclude from the comparison")

    args = parser.parse_args()
    
    airport = args.airport.lower()
    model_list = args.model.split('_')
    bw_range = parse_range(args.bandwidth_range)
    ep_range = parse_range(args.eps_range)

    # Scan for output folders via modular preparation script
    folders = scan_folders(model_list, bandwidth_range=bw_range, eps_range=ep_range, airport=airport)
    if not folders:
        print(f"No output folders found for models: {model_list} matching your criteria.")
        return
        
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    model_tag = args.model
    output_root = os.path.join('result', 'comparison')
    compare_out_dir = setup_plot_dir(os.path.join(output_root, airport, f'compare_{model_tag}_{timestamp}'))
    temp_dir = os.path.join(output_root, 'temp_images_compare')
    
    print("====================================")
    print("Starting Model Comparison (Modular Mode)")
    print(f"Models selected: {model_list}")
    if bw_range: print(f"Bandwidth range: {bw_range}")
    if ep_range: print(f"EPS range: {ep_range}")
    print(f"Found {len(folders)} relevant folder(s):")
    for f in folders: print(f"  - {os.path.basename(f)} -> {get_folder_label(f)}")
    print(f"Output directory: {compare_out_dir}")
    print("====================================")
    
    # 1. Run comparison type A (By Parameter)
    generate_comparison_type_a(
        model_tag=model_tag, 
        folders=folders, 
        airport=airport, 
        exclude_stations=args.exclude, 
        output_dir=compare_out_dir, 
        temp_dir=temp_dir
    )
    
    # 2. Run comparison type B (By Station)
    generate_comparison_type_b(
        model_tag=model_tag, 
        folders=folders, 
        airport=airport, 
        exclude_stations=args.exclude, 
        output_dir=compare_out_dir, 
        temp_dir=temp_dir
    )
    
    cleanup_temp_dir(temp_dir)
    print(f"\nComparison complete. Results: {compare_out_dir}")

if __name__ == "__main__":
    main()
