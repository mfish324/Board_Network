# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Board Network Analyzer is a Python tool that analyzes corporate board interlocks and their relationship to stock performance. Based on Larcker, So, and Wang (2013) research showing ~4.68% annual alpha from board centrality signals.

## Commands

### Install dependencies
```bash
pip install -r requirements.txt
pip install -e .  # optional, for development mode
```

### Run CLI commands
```bash
# Collect board data from SEC EDGAR
python main.py collect --tickers AAPL,MSFT,GOOGL --year 2024

# Analyze board network (requires board data CSV)
python main.py analyze --csv output/board_data_2024.csv --visualize

# Run backtest (requires centrality scores CSV with year column)
python main.py backtest --csv output/centrality_scores.csv --start 2015 --end 2024 --visualize
```

### Run tests
```bash
pytest tests/                           # all tests
pytest tests/test_name_standardizer.py  # single file
pytest tests/ --cov=. --cov-report=html # with coverage
```

## Architecture

### Data Flow Pipeline
1. **SEC Collection** (`data/sec_collector.py`): Fetches DEF 14A proxy filings from SEC EDGAR, extracts director names using regex patterns
2. **Name Standardization** (`network/name_standardizer.py`): Normalizes director names (expands nicknames, removes titles/suffixes)
3. **Network Building** (`network/network_builder.py`): Creates bipartite graph (directors-companies), projects to company-company network via shared directors
4. **Centrality Calculation** (`network/centrality.py`): Computes 4 NetworkX centrality measures + composite N-Score, assigns quintiles
5. **Backtesting** (`strategy/backtester.py`): Long Q5/Short Q1 strategy with annual June rebalancing using yfinance data

### Key Classes
- `SECCollector`: Rate-limited SEC EDGAR API client with filing cache
- `BoardNetwork`: Bipartite NetworkX graph with projection to company network
- `CentralityCalculator`: Computes degree, eigenvector, betweenness, closeness centrality
- `BoardCentralityBacktester`: Long-short strategy backtester with performance metrics
- `NameStandardizer`: Director name normalization with nickname expansion

### Configuration
Edit `config.py` for SEC settings, centrality parameters, backtesting rules (rebalance month, transaction costs, risk-free rate).

## Data Formats

### Board data CSV (input to analyze)
```
year,ticker,director_name
2024,AAPL,Timothy Cook
```

### Centrality scores CSV (output from analyze, input to backtest)
Requires columns: `year`, `company_id`, `n_score_quintile`

## SEC Rate Limiting

The SEC requires max 10 requests/second and a valid User-Agent with email. The collector handles rate limiting automatically via `SEC_RATE_LIMIT_DELAY` in config.
