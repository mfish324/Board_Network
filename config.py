"""
Configuration settings for Board Network Analyzer
"""
import os
from pathlib import Path

# Project paths
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data" / "cache"
OUTPUT_DIR = PROJECT_ROOT / "output"

# Create directories if they don't exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# SEC EDGAR settings
SEC_BASE_URL = "https://www.sec.gov"
SEC_ARCHIVE_URL = f"{SEC_BASE_URL}/Archives/edgar/data"
SEC_SUBMISSIONS_URL = "https://data.sec.gov/submissions"
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

# SEC rate limiting (max 10 requests per second)
SEC_RATE_LIMIT_DELAY = 0.11  # seconds between requests (slightly over 0.1 for safety)

# User agent for SEC requests (required by SEC)
SEC_USER_AGENT = {
    "User-Agent": "Board Network Analyzer research@example.com"
}

# Filing types
PROXY_FILING_TYPES = ["DEF 14A", "DEFA14A"]

# Director name patterns (for parsing proxy statements)
DIRECTOR_SECTION_PATTERNS = [
    r"election of directors",
    r"director nominees",
    r"board of directors",
    r"our directors",
    r"proposal 1",
]

# Name parsing
COMMON_TITLES = ["Mr.", "Mrs.", "Ms.", "Dr.", "Hon.", "Prof.", "Rev."]
COMMON_SUFFIXES = ["Jr.", "Sr.", "II", "III", "IV", "PhD", "MD", "Esq.", "CPA"]

# Centrality calculation settings
EIGENVECTOR_MAX_ITER = 1000
EIGENVECTOR_TOLERANCE = 1e-6

# Backtesting settings
REBALANCE_MONTH = 6  # June (after proxy season)
REBALANCE_DAY = 30
RISK_FREE_RATE = 0.02  # 2% annual
TRANSACTION_COST_BPS = 10  # 10 basis points per trade

# Quintile settings
NUM_QUINTILES = 5

# Stock data settings
BENCHMARK_TICKER = "SPY"  # S&P 500 ETF

# Visualization settings
FIGURE_SIZE = (12, 8)
DPI = 100

# Cache settings
CACHE_EXPIRY_DAYS = 30  # Days before re-fetching cached data
