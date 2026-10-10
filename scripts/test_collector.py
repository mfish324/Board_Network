#!/usr/bin/env python3
"""
Quick test of SEC collector with a few companies.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.sec_collector import SECCollector

# Test with 3 major companies
TEST_TICKERS = ['AAPL', 'MSFT', 'JPM']

print("Testing SEC data collector with 3 companies...")
print(f"Tickers: {', '.join(TEST_TICKERS)}")
print("Year: 2023")
print("-" * 60)

collector = SECCollector()
df = collector.collect_board_data(TEST_TICKERS, 2023, verbose=True)

print("\n" + "=" * 60)
print("RESULTS")
print("=" * 60)
print(f"Total rows: {len(df)}")
print(f"Companies found: {df['ticker'].nunique()}")
print(f"Unique directors: {df['director_name'].nunique()}")
print("\nSample data:")
print(df.head(10))
print("\nDirectors per company:")
print(df.groupby('ticker')['director_name'].count())
