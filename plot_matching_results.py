import pandas as pd
import os
import argparse
from src.scripts.plot import run_matching_plots

def main():
    parser = argparse.ArgumentParser(description="Plot matching results (Modular).")
    parser.add_argument('-i', '--input_file', required=True, help="Path to matched output CSV (e.g. matched_1to1_<tag>.csv)")
    parser.add_argument('-o', '--output_dir', default=os.path.join('result', 'matching', 'plots'), help="Output directory")

    args = parser.parse_args()

    if not os.path.exists(args.input_file):
        print(f"Error: {args.input_file} not found.")
        return

    print(f"Loading results from {args.input_file}...")
    df = pd.read_csv(args.input_file)

    print("Generating plots...")
    run_matching_plots(df, args.output_dir)

    print(f"Done! Plots saved to {args.output_dir}")

if __name__ == "__main__":
    main()
