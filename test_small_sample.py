#!/usr/bin/env python3
"""
Quick test with 5 companies.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from data.sec_collector import SECCollector

# Test with 5 major companies
TEST_TICKERS = ['AAPL', 'MSFT', 'JPM', 'JNJ', 'WMT']

print("Testing SEC data collector with 5 companies...")
print(f"Tickers: {', '.join(TEST_TICKERS)}")
print("Year: 2022")
print("-" * 60)

collector = SECCollector()
df = collector.collect_board_data(TEST_TICKERS, 2022, verbose=True)

print("\n" + "=" * 60)
print("RESULTS")
print("=" * 60)
print(f"Total rows: {len(df)}")
if len(df) > 0:
    print(f"Companies found: {df['ticker'].nunique()}")
    print(f"Unique directors: {df['director_name'].nunique()}")
    print("\nSample data:")
    print(df.head(15))
    print("\nDirectors per company:")
    print(df.groupby('ticker')['director_name'].count())
else:
    print("No data collected - check warnings above")
