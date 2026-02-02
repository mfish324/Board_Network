#!/usr/bin/env python3
"""
Collect board of directors data for S&P 100 companies.
"""

import sys
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from data.sec_collector import SECCollector
from config import OUTPUT_DIR

# S&P 100 tickers (as of 2024)
SP100_TICKERS = [
    'AAPL', 'ABBV', 'ABT', 'ACN', 'ADBE', 'AIG', 'AMD', 'AMGN', 'AMT', 'AMZN',
    'AVGO', 'AXP', 'BA', 'BAC', 'BK', 'BKNG', 'BLK', 'BMY', 'BRK.B', 'C',
    'CAT', 'CHTR', 'CL', 'CMCSA', 'COF', 'COP', 'COST', 'CRM', 'CSCO', 'CVS',
    'CVX', 'DD', 'DHR', 'DIS', 'DOW', 'DUK', 'EMR', 'EXC', 'F', 'FDX',
    'GD', 'GE', 'GILD', 'GM', 'GOOG', 'GOOGL', 'GS', 'HD', 'HON', 'IBM',
    'INTC', 'INTU', 'ISRG', 'JNJ', 'JPM', 'KO', 'LIN', 'LLY', 'LMT', 'LOW',
    'MA', 'MCD', 'MDLZ', 'MDT', 'MET', 'META', 'MMM', 'MO', 'MRK', 'MS',
    'MSFT', 'NEE', 'NFLX', 'NKE', 'NVDA', 'ORCL', 'PEP', 'PFE', 'PG', 'PM',
    'PYPL', 'QCOM', 'RTX', 'SBUX', 'SCHW', 'SO', 'SPG', 'T', 'TGT', 'TMO',
    'TSLA', 'TXN', 'UNH', 'UNP', 'UPS', 'USB', 'V', 'VZ', 'WFC', 'WMT'
]

def main():
    print("=" * 70)
    print("S&P 100 Board of Directors Data Collection")
    print("=" * 70)
    print(f"\nTotal companies: {len(SP100_TICKERS)}")
    print(f"Year: 2023 (most recent complete year)")
    print(f"\nNOTE: This will make {len(SP100_TICKERS)} requests to SEC EDGAR")
    print(f"Estimated time: ~{len(SP100_TICKERS) * 0.2:.0f} minutes (rate limited)")
    print("=" * 70)

    # Ask for confirmation
    response = input("\nProceed with data collection? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Collection cancelled.")
        return

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize collector
    collector = SECCollector()

    # Collect data for 2023
    year = 2023
    print(f"\nCollecting board data for {year}...")
    print("This will take a while due to SEC rate limiting (max 10 requests/sec)")
    print("-" * 70)

    # Collect the data
    df = collector.collect_board_data(SP100_TICKERS, year, verbose=True)

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = OUTPUT_DIR / f"sp100_board_data_{year}_{timestamp}.csv"
    df.to_csv(output_file, index=False)

    # Print summary
    print("\n" + "=" * 70)
    print("COLLECTION COMPLETE")
    print("=" * 70)
    print(f"Total rows collected: {len(df)}")
    print(f"Unique companies: {df['ticker'].nunique()}")
    print(f"Unique directors: {df['director_name'].nunique()}")
    print(f"Output file: {output_file}")
    print("\nNext steps:")
    print("1. Analyze the network:")
    print(f"   python main.py analyze --csv {output_file} --visualize")
    print("\n2. View top companies by centrality:")
    print(f"   cat output/centrality_scores.csv | head -20")
    print("=" * 70)


if __name__ == '__main__':
    main()
