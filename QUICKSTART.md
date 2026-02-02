# Quick Start Guide

Get started with Board Network Analyzer in 5 minutes.

## Installation

```bash
cd board_network
pip install -r requirements.txt
```

## Option 1: Run Example Script (Recommended for First-Time Users)

```bash
python example_usage.py
```

This will:
- Create sample board data
- Build a network
- Calculate centrality measures
- Generate visualizations

Check the `output/` directory for results.

## Option 2: Collect Real Data from SEC

### Step 1: Collect Board Data

```bash
python main.py collect --tickers AAPL,MSFT,GOOGL,JPM,GS --year 2024
```

**Note**: This makes real requests to SEC EDGAR and may take a few minutes.

Output: `output/board_data_2024.csv`

### Step 2: Analyze Network

```bash
python main.py analyze --csv output/board_data_2024.csv --visualize
```

Output:
- `output/centrality_scores.csv` - Centrality rankings
- `output/network.html` - Interactive network graph
- `output/top_companies.png` - Bar chart
- `output/centrality_correlation.png` - Heatmap

### Step 3: View Results

Open `output/network.html` in your browser to explore the interactive network!

Top companies by centrality are in `centrality_scores.csv`.

## Option 3: Use Your Own Data

Create a CSV file with this format:

```csv
year,ticker,director_name
2024,AAPL,Timothy Cook
2024,AAPL,Arthur Levinson
2024,MSFT,Satya Nadella
2024,MSFT,William Gates
```

Then run:

```bash
python main.py analyze --csv your_data.csv --visualize
```

## Understanding the Output

### Centrality Scores CSV

| Column | Description |
|--------|-------------|
| company_id | Stock ticker |
| n_score | Composite centrality score (0-1) |
| n_score_quintile | Quintile ranking (1=least central, 5=most central) |
| degree_centrality | Fraction of other firms connected to this firm |
| eigenvector_centrality | Connections to well-connected firms |
| betweenness_centrality | How often firm acts as bridge |
| closeness_centrality | Average distance to all other firms |
| num_directors | Number of directors on board |
| num_interlocks | Number of other firms sharing directors |

### Key Metrics

- **N-Score Quintile 5**: Most central boards (recommended long positions)
- **N-Score Quintile 1**: Least central boards (recommended short positions)
- **Expected Alpha**: ~4.68% annually from long Q5, short Q1 strategy

## Next Steps

1. **Backtest Strategy**: See if the centrality effect holds in your data
   ```bash
   python main.py backtest --csv output/centrality_scores.csv --start 2020 --end 2024 --visualize
   ```

2. **Explore Code**: Check `example_usage.py` for Python API usage

3. **Read Research**: See README.md references section

4. **Customize**: Edit `config.py` to adjust parameters

## Troubleshooting

### "Could not find CIK for ticker"
- Ticker may not be in SEC database
- Try different tickers or check ticker symbol

### "No proxy filings found"
- Company may not have filed proxy in that year
- Try different year

### Rate limit errors from SEC
- Tool automatically handles rate limiting
- If errors persist, increase `SEC_RATE_LIMIT_DELAY` in config.py

### Empty visualizations
- Need at least 5-10 companies for meaningful network
- Try collecting more tickers

## Support

- Read full documentation: `README.md`
- Run tests: `pytest tests/`
- Check examples: `example_usage.py`

## Research Citation

If using for academic research, please cite:

Larcker, D. F., So, E. C., & Wang, C. C. (2013). Boardroom centrality and firm performance. *Journal of Accounting and Economics*, 55(2-3), 225-250.
