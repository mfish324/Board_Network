#!/usr/bin/env python3
"""
Debug SEC collector to see what's happening.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.sec_collector import SECCollector

# Test with one company
TEST_TICKER = 'AAPL'
YEAR = 2022  # Try 2022 instead

print(f"Testing SEC collector with {TEST_TICKER} for year {YEAR}")
print("=" * 60)

collector = SECCollector()

# Step 1: Load ticker map
print("\n1. Loading ticker to CIK mapping...")
ticker_map = collector.load_ticker_to_cik_map()
print(f"   Total tickers in map: {len(ticker_map)}")

# Step 2: Get CIK for Apple
cik = collector.get_cik(TEST_TICKER)
print(f"\n2. CIK for {TEST_TICKER}: {cik}")

if cik:
    # Step 3: Find proxy filings
    print(f"\n3. Looking for proxy filings for CIK {cik} in {YEAR}...")
    filings = collector.find_proxy_filings(cik, YEAR)
    print(f"   Found {len(filings)} proxy filings")

    if filings:
        for i, filing in enumerate(filings):
            print(f"   Filing {i+1}:")
            print(f"      Type: {filing['form']}")
            print(f"      Date: {filing['filing_date']}")
            print(f"      Accession: {filing['accession_number']}")

        # Step 4: Download one filing
        print(f"\n4. Downloading first proxy filing...")
        filing = filings[0]
        html = collector.download_filing(
            cik=filing['cik'],
            accession_number=filing['accession_number'],
            document=filing['primary_document']
        )
        print(f"   Downloaded {len(html)} characters of HTML")

        # Step 5: Extract directors
        print(f"\n5. Extracting director names...")
        directors = collector.extract_directors(html)
        print(f"   Found {len(directors)} directors:")
        for director in sorted(directors):
            print(f"      - {director}")
    else:
        print("   No filings found. Trying without year filter...")
        filings_all = collector.find_proxy_filings(cik)
        print(f"   Total proxy filings (all years): {len(filings_all)}")
        if filings_all:
            print("   Recent filings:")
            for filing in filings_all[:5]:
                print(f"      {filing['filing_date']}: {filing['form']}")
else:
    print(f"Could not find CIK for {TEST_TICKER}")
