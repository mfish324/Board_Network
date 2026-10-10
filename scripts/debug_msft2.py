#!/usr/bin/env python3
import sys, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from data.sec_collector import SECCollector
from bs4 import BeautifulSoup

collector = SECCollector()
cik = collector.get_cik('MSFT')
filings = collector.find_proxy_filings(cik, 2022)
def_14a = [f for f in filings if f['form'] == 'DEF 14A']
filing = def_14a[0]

html = collector.download_filing(
    cik=filing['cik'],
    accession_number=filing['accession_number'],
    document=filing['primary_document']
)

soup = BeautifulSoup(html, 'lxml')
for script in soup(["script", "style"]):
    script.decompose()
text = soup.get_text()

# Test pattern
pattern = re.compile(
    r'(?:elect(?:ion)?\s+(?:of|the)?\s*\d*\s*director|director nominees)',
    re.IGNORECASE
)

print("Searching for director section pattern...")
matches = pattern.findall(text)
print(f"Found {len(matches)} matches:")
for i, match in enumerate(matches[:10]):
    print(f"  {i+1}. '{match}'")

# Find section
print("\nLooking for section context...")
lines = text.split('\n')
for i, line in enumerate(lines):
    if pattern.search(line):
        print(f"\nLine {i}: {line[:100]}")
        # Show next few lines
        for j in range(1, 20):
            if i+j < len(lines):
                print(f"  +{j}: {lines[i+j][:80]}")
        break
