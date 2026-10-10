#!/usr/bin/env python3
"""
Test director extraction from actual proxy filing.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.sec_collector import SECCollector
from config import OUTPUT_DIR

TEST_TICKER = 'AAPL'
YEAR = 2022

print(f"Testing director extraction for {TEST_TICKER} ({YEAR})")
print("=" * 60)

collector = SECCollector()
cik = collector.get_cik(TEST_TICKER)
filings = collector.find_proxy_filings(cik, YEAR)

# Find the main DEF 14A filing (not the amendment)
def_14a_filings = [f for f in filings if f['form'] == 'DEF 14A']

if def_14a_filings:
    filing = def_14a_filings[0]
    print(f"\nUsing filing: {filing['form']} from {filing['filing_date']}")

    # Download
    html = collector.download_filing(
        cik=filing['cik'],
        accession_number=filing['accession_number'],
        document=filing['primary_document']
    )

    print(f"Downloaded {len(html):,} characters")

    # Save a snippet for inspection
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    snippet_file = OUTPUT_DIR / "proxy_snippet.html"
    with open(snippet_file, 'w') as f:
        f.write(html[:50000])  # First 50KB
    print(f"Saved first 50KB to: {snippet_file}")

    # Try to extract directors
    print("\nAttempting to extract directors...")
    directors = collector.extract_directors(html)

    if directors:
        print(f"✓ Successfully extracted {len(directors)} directors:")
        for director in sorted(directors):
            print(f"  - {director}")
    else:
        print("✗ No directors extracted")
        print("\nSearching for key phrases in HTML...")

        # Look for director-related sections
        keywords = [
            'election of directors',
            'director nominees',
            'board of directors',
            'proposal 1',
            'Arthur D. Levinson',  # Known Apple director
            'Timothy D. Cook'       # Apple CEO
        ]

        for keyword in keywords:
            if keyword.lower() in html.lower():
                # Find context around the keyword
                idx = html.lower().find(keyword.lower())
                snippet = html[max(0, idx-200):min(len(html), idx+200)]
                print(f"\n  Found '{keyword}' at position {idx}")
                print(f"  Context: ...{snippet[:100]}...")
else:
    print("No DEF 14A filings found")
