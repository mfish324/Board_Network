"""
SEC EDGAR data collector for board of directors information.

Collects board composition data from proxy statements (DEF 14A filings).
"""

import json
import re
from collections import Counter
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

INLINE_TAGS = ['span', 'b', 'i', 'u', 'em', 'strong', 'a', 'font', 'sup', 'sub']

DIRECTOR_SINCE_RE = re.compile(
    r'\b(?:director|board\s+member|trustee)\s*:?\s*since\b', re.IGNORECASE)
ELECTION_LIST_RE = re.compile(
    r'Election of Directors?:\s*([A-Z][^.:]{10,400}?)(?=\s+FOR\b|\s{2,}|[.:]|$)')
AGE_SUFFIX_RE = re.compile(r'\s*[,|]\s*(?:age\s*)?\d{2}\s*$', re.IGNORECASE)
LEADING_JUNK_RE = re.compile(r'^[^A-Za-zÀ-ſ]+')
ANCHOR_WINDOW = 12  # lines either side of a "Director since" marker

NAME_TOKEN_RE = re.compile(
    r"^(?:[A-Z]\.|[A-Z][A-Za-zÀ-ſ'’\-]*[a-zß-ſ]\.?)$")
NAME_PARTICLES = {'de', 'del', 'la', 'van', 'von', 'der', 'den', 'bin', 'al',
                  'ter', 'du', 'di', 'da', 'le'}
CREDENTIALS = {'dvm', 'dmd', 'cfa', 'llb', 'mbbs', 'kbe', 'rn', 'frcp', 'phd', 'md', 'mph', 'mba', 'jd', 'cpa', 'cbe', 'obe', 'jr',
               'sr', 'ii', 'iii', 'iv', 'dds', 'esq', 'frs', 'dphil', 'msc',
               'ma', 'ms', 'ba', 'bs', 'dba', 'usn', 'ret', 'usaf'}
NAME_STOPWORDS = {
    'board', 'committee', 'committees', 'director', 'directors', 'independent',
    'chair', 'chairman', 'chairperson', 'lead', 'company', 'corporation',
    'inc', 'corp', 'proxy', 'statement', 'meeting', 'annual', 'compensation',
    'audit', 'governance', 'corporate', 'executive', 'officer', 'officers',
    'skills', 'experience', 'biography', 'background', 'career', 'highlights',
    'age', 'since', 'table', 'contents', 'nominee', 'nominees', 'shareholder',
    'shareholders', 'stockholder', 'stockholders', 'proposal', 'vote',
    'election', 'elected', 'overview', 'summary', 'information', 'principal',
    'occupation', 'primary', 'public', 'other', 'current', 'key',
    'qualifications', 'expertise', 'finance', 'financial', 'risk', 'strategy',
    'leadership', 'international', 'technology', 'operations', 'business',
    'industry', 'sustainability', 'responsibility', 'nominating', 'human',
    'capital', 'management', 'member', 'members', 'president', 'chief', 'vice',
    'senior', 'general', 'counsel', 'secretary', 'treasurer', 'united',
    'states', 'new', 'york', 'of', 'the', 'and', 'for', 'to', 'in', 'on', 'at',
    'by', 'our', 'we', 'ltd', 'llc', 'plc', 'group', 'holdings', 'partners',
    'university', 'college', 'school', 'institute', 'foundation', 'council',
    'bank', 'trust', 'fund', 'securities', 'exchange', 'commission', 'form',
    'item', 'part', 'page', 'notice', 'internal', 'revenue', 'service',
    'retired', 'former', 'emeritus', 'non', 'employee', 'tenure', 'attendance',
    'gender', 'diversity', 'ethnic', 'race', 'name', 'title', 'year', 'years',
    'fees', 'total', 'stock', 'awards', 'option', 'options', 'cash',
    'level', 'high', 'petroleum', 'recent', 'past', 'special', 'consumer',
    'health', 'pharmaceutical', 'chemical', 'engineering', 'energy',
    'investments', 'strategic', 'planning', 'sachs', 'goldman', 'lockheed', 'thermo', 'fisher', 'scientific', 'palo', 'alto',
    # organizations / places / headings that appear in nominee bios
    'collective', 'street', 'airlines', 'affiliation', 'affiliations',
    'networks', 'southern', 'northern', 'eastern', 'western', 'california',
    'selected', 'directorships', 'advisers', 'advisors', 'institution',
    'laboratories', 'systems', 'technologies', 'pharmaceuticals',
    'communications', 'industries', 'enterprises', 'international',
    'associates', 'ventures', 'resources', 'services', 'solutions',
    'department', 'ministry', 'american', 'national', 'global', 'world',
    'society', 'association', 'center', 'centre', 'hospital', 'museum',
    'professor', 'dean', 'partner', 'founder', 'co', 'inc.', 'corp.',
}


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

        # Match directors on first + last name only: filings disagree about
        # middle initials ("Timothy P. Flynn" vs "Tim Flynn"), which would
        # otherwise hide real interlocks and duplicate people within a board.
        self.name_standardizer = NameStandardizer(normalize_middle=False)
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
        filings_block = filings_data.get('filings', {})

        # The "recent" block only holds the latest ~1000 filings; high-volume
        # filers (e.g. JPM) push older proxies into paginated archive files.
        blocks = [filings_block.get('recent', {})]
        for archive in filings_block.get('files', []):
            if year is not None:
                first = str(archive.get('filingFrom', ''))[:4]
                last = str(archive.get('filingTo', ''))[:4]
                if first.isdigit() and last.isdigit() and not (
                        int(first) <= year <= int(last)):
                    continue
            url = f"{SEC_SUBMISSIONS_URL}/{archive['name']}"
            blocks.append(self._make_request(url).json())

        proxy_filings = []
        for block in blocks:
            forms = block.get('form', [])
            filing_dates = block.get('filingDate', [])
            accession_numbers = block.get('accessionNumber', [])
            primary_documents = block.get('primaryDocument', [])

            for i, form in enumerate(forms):
                if form not in PROXY_FILING_TYPES:
                    continue
                filing_date = filing_dates[i]

                if year is not None and int(filing_date.split('-')[0]) != year:
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
        raw = response.content
        try:
            content = raw.decode('utf-8')
        except UnicodeDecodeError:
            content = raw.decode('cp1252', errors='replace')

        # Cache the content
        cache_file.write_text(content, encoding='utf-8')

        return content

    def extract_directors(self, html_content: str) -> Set[str]:
        """
        Extract director names from a proxy statement HTML.

        Director nominee cards in proxy statements share one signal: a
        "Director since <year>" marker next to the nominee's name. The layout
        varies (name before or after the marker), so every standalone
        name-like line within a few lines of a marker is taken as a director.
        A comma-separated "Election of Directors: A, B and C" list (Apple
        style) is also recognised.

        Args:
            html_content: HTML content of proxy statement

        Returns:
            Set of standardized director names
        """
        # An XML declaration makes lxml's HTML parser warn on XHTML filings
        html_content = re.sub(r'^\s*<\?xml[^>]*\?>', '', html_content)
        soup = BeautifulSoup(html_content, 'lxml')
        for tag in soup(["script", "style"]):
            tag.decompose()
        for tag in soup.find_all(INLINE_TAGS):
            tag.unwrap()
        soup.smooth()

        text = soup.get_text('\n')
        text = re.sub(r'[\xa0\u2000-\u200b\u202f\u3000]+', ' ', text)
        # Strip leading bullets/symbols so "• Herb Allen" reads as a name
        lines = [LEADING_JUNK_RE.sub('', ln).strip() for ln in text.split('\n')]
        lines = [ln for ln in lines if ln]

        raw_names = set()
        list_names = set()

        # Signal 1: nominee cards anchored on "Director since"
        anchors = [i for i, ln in enumerate(lines)
                   if len(ln) < 120 and DIRECTOR_SINCE_RE.search(ln)]
        name_at = {i: self._line_to_name(ln) for i, ln in enumerate(lines)}
        for i in anchors:
            lo = max(0, i - ANCHOR_WINDOW)
            hi = min(len(lines), i + ANCHOR_WINDOW + 1)
            for j in range(lo, hi):
                if name_at.get(j):
                    raw_names.add(name_at[j])

        # Signal 2: "Election of Directors: A, B, and C"
        joined = ' '.join(lines)
        for match in ELECTION_LIST_RE.findall(joined):
            match = re.split(r'\s+FOR\b', match)[0]
            for name in re.split(r',\s*(?:and\s+)?|\s+and\s+', match):
                name = self._line_to_name(name.strip())
                if name:
                    list_names.add(name)

        # A real director is mentioned repeatedly (card, bio, committee and
        # compensation tables); one-off name-like strings are usually
        # organizations or places from a nominee's bio. Match on surname
        # because bios say "Dr. Beckerle".
        def _mentions(name: str) -> int:
            surname = re.escape(name.split()[-1].strip('.'))
            return len(re.findall(r'\b' + surname + r'\b', joined))
        raw_names = {n for n in raw_names if _mentions(n) >= 3}

        # Directors also show up as standalone lines in committee and
        # compensation tables; organizations in bios mostly appear inside
        # sentences, so require at least two standalone-line mentions.
        # A name sitting right next to a marker is the card heading itself
        # and is accepted on a single mention.
        standalone = Counter(v for v in name_at.values() if v)
        near_anchor = {
            name_at[j]
            for i in anchors
            for j in range(max(0, i - 3), min(len(lines), i + 4))
            if name_at.get(j)
        }
        raw_names = {n for n in raw_names
                     if standalone[n] >= 2 or n in near_anchor}

        # Drop "D. Adamczyk" when "Darius Adamczyk" was also found
        full_names = {n for n in raw_names if not re.match(r'^[A-Z]\.\s', n)
                      or len(n.split()) > 2}
        raw_names = {
            n for n in raw_names
            if n in full_names or not any(
                f.split()[-1] == n.split()[-1] and f.split()[0].startswith(n[0])
                for f in full_names)
        }

        directors = set()
        for name in raw_names | list_names:
            standardized = self.name_standardizer.standardize(name)
            if standardized:
                directors.add(standardized)
        return directors

    @staticmethod
    def _line_to_name(line: str) -> Optional[str]:
        """Return the person name a line consists of, or None."""
        if len(line) > 70 or len(line) < 5:
            return None
        # "David Solomon, 61" / "John B. Frank | 66": drop the trailing age
        line = re.sub(AGE_SUFFIX_RE, '', line)
        # "ARI BOUSBIB": cards sometimes set the name in capitals
        if line.isupper():
            line = line.title()
        # Drop trailing credentials: "Susan Desmond-Hellmann, M.D., M.P.H."
        head, *rest = [p.strip() for p in line.split(',')]
        if rest and not all(
                re.sub(r'[.\s]', '', r).lower() in CREDENTIALS for r in rest):
            return None
        tokens = head.split()
        # Peel a trailing label off the name: an ALLCAPS word, a role word,
        # or a possessive ("Intel's Chief Executive Officer").
        for k in range(2, min(len(tokens), 5) + 1):
            if k < len(tokens):
                nxt = tokens[k]
                if ((nxt.isupper() and len(nxt) >= 4)
                        or nxt.lower().strip('.') in NAME_STOPWORDS
                        or re.search(r"['’]s$", nxt)):
                    if all(NAME_TOKEN_RE.match(t) or t.strip('.').lower() in NAME_PARTICLES
                           for t in tokens[:k]):
                        tokens = tokens[:k]
                        break
        if not 2 <= len(tokens) <= 5:
            return None
        for k, tok in enumerate(tokens):
            bare = tok.strip('.').lower()
            if bare in NAME_STOPWORDS or any(c.isdigit() for c in tok):
                return None
            if k > 0 and bare in NAME_PARTICLES:
                continue
            if not NAME_TOKEN_RE.match(tok):
                return None
        # Last token must be a real word, not an initial
        if len(tokens[-1].strip('.')) < 2:
            return None
        return ' '.join(tokens)

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

                # Only the definitive proxy carries the nominee cards. DEFA14A
                # is supplemental material (press releases, vote reminders)
                # and yields junk names, so never fall back to it.
                def_14a_filings = [f for f in filings if f['form'] == 'DEF 14A']
                if not def_14a_filings:
                    if verbose:
                        forms = sorted({f['form'] for f in filings})
                        print(f"Warning: No DEF 14A for {ticker} in {year} "
                              f"(found only: {', '.join(forms)})")
                    continue
                filing = def_14a_filings[0]

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
