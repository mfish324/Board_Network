#!/usr/bin/env python3
"""
Debug MSFT extraction.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from data.sec_collector import SECCollector
from config import OUTPUT_DIR

TEST_TICKER = 'MSFT'
YEAR = 2022

print(f"Testing director extraction for {TEST_TICKER} ({YEAR})")
print("=" * 60)

collector = SECCollector()
cik = collector.get_cik(TEST_TICKER)
print(f"CIK: {cik}")

filings = collector.find_proxy_filings(cik, YEAR)
print(f"\nFound {len(filings)} filings:")
for f in filings:
    print(f"  {f['form']} - {f['filing_date']}")

if filings:
    # Prefer DEF 14A
    def_14a = [f for f in filings if f['form'] == 'DEF 14A']
    filing = def_14a[0] if def_14a else filings[0]
    
    print(f"\nUsing: {filing['form']} from {filing['filing_date']}")
    
    html = collector.download_filing(
        cik=filing['cik'],
        accession_number=filing['accession_number'],
        document=filing['primary_document']
    )
    
    print(f"Downloaded {len(html):,} characters")
    
    # Save snippet
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    snippet_file = OUTPUT_DIR / f"{TEST_TICKER}_proxy_snippet.html"
    with open(snippet_file, 'w') as f:
        f.write(html[:50000])
    print(f"Saved snippet to: {snippet_file}")
    
    # Extract directors
    directors = collector.extract_directors(html)
    print(f"\nExtracted {len(directors)} directors:")
    for d in sorted(directors):
        print(f"  - {d}")
    
    # Search for "Election of Directors" in text
    if len(directors) == 0:
        print("\nSearching for 'Election of Directors' pattern...")
        import re
        matches = re.findall(r'[Ee]lection of [Dd]irectors?[:\s]+([^\n]{0,200})', html[:100000])
        for i, match in enumerate(matches[:3]):
            print(f"  Match {i+1}: ...{match[:100]}...")
