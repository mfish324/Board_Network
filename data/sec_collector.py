"""
SEC EDGAR data collector for board of directors information.

Collects board composition data from proxy statements (DEF 14A filings).
"""

import json
import re
import time
from pathlib import Path
from typing import List, Dict, Optional, Set
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import pandas as pd

from config import (
    SEC_BASE_URL, SEC_ARCHIVE_URL, SEC_SUBMISSIONS_URL,
    SEC_COMPANY_TICKERS_URL, SEC_RATE_LIMIT_DELAY, SEC_USER_AGENT,
    PROXY_FILING_TYPES, DATA_DIR
)
from network.name_standardizer import NameStandardizer


class SECCollector:
    """
    Collects board of directors data from SEC EDGAR filings.

    Features:
    - Maps tickers to CIK numbers
    - Finds proxy statement filings (DEF 14A)
    - Downloads and caches filings
    - Extracts director names from proxy statements
    - Handles SEC rate limiting (max 10 requests/second)
    """

    def __init__(self, cache_dir: Optional[Path] = None, user_agent: Optional[Dict] = None):
        """
        Initialize the SEC collector.

        Args:
            cache_dir: Directory for caching downloaded filings
            user_agent: Custom user agent dict (must include email per SEC policy)
        """
        self.cache_dir = cache_dir or DATA_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.user_agent = user_agent or SEC_USER_AGENT
        self.rate_limit_delay = SEC_RATE_LIMIT_DELAY
        self.last_request_time = 0

        self.name_standardizer = NameStandardizer()
        self.ticker_to_cik_map = None

    def _rate_limit(self):
        """Enforce SEC rate limiting (max 10 requests/second)."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = time.time()

    def _make_request(self, url: str) -> requests.Response:
        """
        Make a rate-limited request to SEC EDGAR.

        Args:
            url: URL to fetch

        Returns:
            Response object

        Raises:
            requests.RequestException: If request fails
        """
        self._rate_limit()
        response = requests.get(url, headers=self.user_agent, timeout=30)
        response.raise_for_status()
        return response

    def load_ticker_to_cik_map(self, force_refresh: bool = False) -> Dict[str, str]:
        """
        Load mapping of stock tickers to CIK numbers.

        Args:
            force_refresh: Force refresh from SEC (ignore cache)

        Returns:
            Dict mapping ticker symbols to CIK numbers (as strings)
        """
        cache_file = self.cache_dir / "ticker_to_cik.json"

        # Check cache
        if not force_refresh and cache_file.exists():
            with open(cache_file, 'r') as f:
                self.ticker_to_cik_map = json.load(f)
                return self.ticker_to_cik_map

        # Fetch from SEC
        response = self._make_request(SEC_COMPANY_TICKERS_URL)
        data = response.json()

        # Convert to ticker -> CIK mapping
        # SEC format: {0: {ticker: "AAPL", cik_str: 320193, title: "Apple Inc."}, ...}
        ticker_to_cik = {}
        for entry in data.values():
            ticker = entry['ticker'].upper()
            cik = str(entry['cik_str']).zfill(10)  # Pad CIK to 10 digits
            ticker_to_cik[ticker] = cik

        # Cache the mapping
        with open(cache_file, 'w') as f:
            json.dump(ticker_to_cik, f, indent=2)

        self.ticker_to_cik_map = ticker_to_cik
        return ticker_to_cik

    def get_cik(self, ticker: str) -> Optional[str]:
        """
        Get CIK number for a ticker symbol.

        Args:
            ticker: Stock ticker symbol

        Returns:
            10-digit CIK string or None if not found
        """
        if self.ticker_to_cik_map is None:
            self.load_ticker_to_cik_map()

        return self.ticker_to_cik_map.get(ticker.upper())

    def get_company_filings(self, cik: str) -> Dict:
        """
        Get all filings metadata for a company.

        Args:
            cik: 10-digit CIK number

        Returns:
            Dict with company filings metadata
        """
        url = f"{SEC_SUBMISSIONS_URL}/CIK{cik}.json"
        response = self._make_request(url)
        return response.json()

    def find_proxy_filings(self, cik: str, year: Optional[int] = None) -> List[Dict]:
        """
        Find proxy statement filings (DEF 14A) for a company.

        Args:
            cik: 10-digit CIK number
            year: Optional year to filter filings (e.g., 2024)

        Returns:
            List of filing dicts with keys: form, filing_date, accession_number, primary_document
        """
        filings_data = self.get_company_filings(cik)

        # Extract recent filings
        recent = filings_data.get('filings', {}).get('recent', {})
        forms = recent.get('form', [])
        filing_dates = recent.get('filingDate', [])
        accession_numbers = recent.get('accessionNumber', [])
        primary_documents = recent.get('primaryDocument', [])

        # Filter for proxy statements
        proxy_filings = []
        for i, form in enumerate(forms):
            if form in PROXY_FILING_TYPES:
                filing_date = filing_dates[i]

                # Filter by year if specified
                if year is not None:
                    filing_year = int(filing_date.split('-')[0])
                    if filing_year != year:
                        continue

                proxy_filings.append({
                    'form': form,
                    'filing_date': filing_date,
                    'accession_number': accession_numbers[i],
                    'primary_document': primary_documents[i],
                    'cik': cik
                })

        return proxy_filings

    def download_filing(self, cik: str, accession_number: str, document: str) -> str:
        """
        Download a filing document.

        Args:
            cik: CIK number
            accession_number: Filing accession number (with dashes)
            document: Primary document filename

        Returns:
            HTML content of the filing
        """
        # Check cache first
        cache_key = f"{cik}_{accession_number.replace('-', '')}_{document}"
        cache_file = self.cache_dir / f"{cache_key}.html"

        if cache_file.exists():
            return cache_file.read_text(encoding='utf-8', errors='ignore')

        # Download from SEC
        # Remove dashes from accession number for URL
        accession_no_dash = accession_number.replace('-', '')
        url = f"{SEC_ARCHIVE_URL}/{int(cik)}/{accession_no_dash}/{document}"

        response = self._make_request(url)
        content = response.text

        # Cache the content
        cache_file.write_text(content, encoding='utf-8')

        return content

    def extract_directors(self, html_content: str) -> Set[str]:
        """
        Extract director names from a proxy statement HTML.

        Args:
            html_content: HTML content of proxy statement

        Returns:
            Set of standardized director names
        """
        soup = BeautifulSoup(html_content, 'lxml')

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text
        text = soup.get_text()

        # Find director section
        directors = set()

        # Pattern 1: Look for comma-separated list after "Election of Directors:"
        # Example: "Election of Directors: James Bell, Tim Cook, Al Gore, and Sue Wagner"
        comma_list_pattern = re.compile(
            r'Election of Directors?:\s*([A-Z][^.]+?)(?:\s+and\s+|\s*$)',
            re.IGNORECASE | re.MULTILINE
        )

        comma_matches = comma_list_pattern.findall(text)
        for match in comma_matches:
            # Split by commas and 'and'
            names = re.split(r',\s*(?:and\s+)?|,?\s+and\s+', match)
            for name in names:
                name = name.strip()
                # Remove trailing text like "is independent" or descriptions
                name = re.sub(r'\s+(?:is|are|serve|serves|serving).*$', '', name, flags=re.IGNORECASE)
                # Only process if it looks like a name (2-4 words, capitalized)
                if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?(?:\s+[A-Z][a-z]+){1,2}$', name):
                    standardized = self.name_standardizer.standardize(name)
                    if standardized:
                        directors.add(standardized)

        # Pattern 2: Look for "Election of Directors", "Elect directors", or similar section
        director_section_pattern = re.compile(
            r'(?:elect(?:ion)?\s+(?:of|the)?\s*\d*\s*director|director nominees|board of directors|our directors|proposal 1.*director)',
            re.IGNORECASE
        )

        # Find section
        lines = text.split('\n')
        in_director_section = False
        section_lines = []

        for i, line in enumerate(lines):
            line = line.strip()

            # Check if we're entering director section
            if director_section_pattern.search(line):
                in_director_section = True

            # Check if we're leaving director section (common markers)
            if in_director_section and re.search(
                r'(?:executive compensation|audit committee|proposal 2|ratification|advisory vote)',
                line,
                re.IGNORECASE
            ):
                break

            if in_director_section:
                section_lines.append(line)

            # Limit section size to avoid false positives
            if len(section_lines) > 500:
                break

        # Extract names from section
        section_text = '\n'.join(section_lines)

        # Pattern 3: Name followed by age or year
        # Examples: "John Smith, 55" or "John Smith (55)" or "John Smith, age 55"
        name_age_pattern = re.compile(
            r'([A-Z][a-z]+(?:\s+[A-Z]\.?)?\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*[,\(]\s*(?:age\s*)?(\d{2})',
            re.MULTILINE
        )

        matches = name_age_pattern.findall(section_text)
        for name, age in matches:
            # Validate age is reasonable (30-95)
            if 30 <= int(age) <= 95:
                standardized = self.name_standardizer.standardize(name)
                if standardized:
                    directors.add(standardized)

        # Pattern 3b: Name followed by title
        # Examples: "John Smith, Chairman" or "John Smith Chief Executive Officer"
        name_title_pattern = re.compile(
            r'([A-Z][a-z]+(?:\s+[A-Z]\.?\s*)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s*[,\n]\s*(?:Chairman|Chief|Director|President|CEO|CFO|Independent)',
            re.MULTILINE | re.IGNORECASE
        )

        matches2 = name_title_pattern.findall(section_text)
        for name in matches2:
            standardized = self.name_standardizer.standardize(name)
            if standardized:
                directors.add(standardized)

        # Pattern 4: Look for names in tables (common in proxy statements)
        tables = soup.find_all('table')
        for table in tables[:10]:  # Check first 10 tables
            table_text = table.get_text()

            # Check if this looks like a director table
            if re.search(r'(?:director|name|age|independent)', table_text, re.IGNORECASE):
                # Extract potential names from table cells
                cells = table.find_all(['td', 'th'])
                for cell in cells:
                    cell_text = cell.get_text().strip()

                    # Look for names (2-3 words, each capitalized)
                    name_pattern = re.compile(r'^([A-Z][a-z]+(?:\s+[A-Z]\.?\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)$')
                    match = name_pattern.match(cell_text)
                    if match:
                        name = match.group(1)
                        standardized = self.name_standardizer.standardize(name)
                        if standardized:
                            directors.add(standardized)

        # Filter out common false positives
        false_positives = {
            'Annual Meeting', 'Board Of Directors', 'Chief Executive',
            'Executive Officer', 'Corporate Governance', 'Audit Committee',
            'Compensation Committee', 'Common Stock', 'Stock Exchange',
            'United States', 'New York', 'Table Of Contents'
        }

        directors = {d for d in directors if d not in false_positives}

        return directors

    def collect_board_data(self,
                          tickers: List[str],
                          year: int,
                          verbose: bool = True) -> pd.DataFrame:
        """
        Collect board of directors data for multiple companies.

        Args:
            tickers: List of stock ticker symbols
            year: Year to collect data for
            verbose: Show progress bar

        Returns:
            DataFrame with columns: ticker, company_name, director_name, year
        """
        results = []

        # Load ticker to CIK mapping
        self.load_ticker_to_cik_map()

        # Process each ticker
        iterator = tqdm(tickers, desc="Collecting board data") if verbose else tickers

        for ticker in iterator:
            try:
                # Get CIK
                cik = self.get_cik(ticker)
                if not cik:
                    if verbose:
                        print(f"Warning: Could not find CIK for {ticker}")
                    continue

                # Find proxy filings for the year
                filings = self.find_proxy_filings(cik, year)
                if not filings:
                    if verbose:
                        print(f"Warning: No proxy filings found for {ticker} in {year}")
                    continue

                # Prefer DEF 14A over amendments (DEFA14A)
                def_14a_filings = [f for f in filings if f['form'] == 'DEF 14A']
                filing = def_14a_filings[0] if def_14a_filings else filings[0]

                # Download filing
                html = self.download_filing(
                    cik=filing['cik'],
                    accession_number=filing['accession_number'],
                    document=filing['primary_document']
                )

                # Extract directors
                directors = self.extract_directors(html)

                # Add to results
                for director in directors:
                    results.append({
                        'year': year,
                        'ticker': ticker,
                        'director_name': director,
                    })

            except Exception as e:
                if verbose:
                    print(f"Error processing {ticker}: {e}")
                continue

        # Create DataFrame
        df = pd.DataFrame(results)

        return df


def collect_board_data_for_tickers(tickers: List[str],
                                   year: int,
                                   cache_dir: Optional[Path] = None) -> pd.DataFrame:
    """
    Convenience function to collect board data for a list of tickers.

    Args:
        tickers: List of stock ticker symbols
        year: Year to collect data for
        cache_dir: Optional cache directory

    Returns:
        DataFrame with board composition data
    """
    collector = SECCollector(cache_dir=cache_dir)
    return collector.collect_board_data(tickers, year)
