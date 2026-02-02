#!/usr/bin/env python3
"""
Board Network Analyzer - Main CLI Interface

Analyzes corporate board networks and their relationship to stock performance.
Based on Larcker, So, and Wang (2013) research.
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

# Import modules
from data.sec_collector import SECCollector
from network.network_builder import build_board_network
from network.centrality import calculate_centrality
from strategy.backtester import BoardCentralityBacktester
from visualization.plots import (
    plot_network_interactive, plot_cumulative_returns,
    plot_drawdown, plot_top_companies, plot_correlation_heatmap
)
from config import OUTPUT_DIR


def collect_sec_data(args):
    """Collect board data from SEC EDGAR."""
    print("Collecting board data from SEC EDGAR...")
    print(f"Tickers: {args.tickers}")
    print(f"Year: {args.year}")

    # Parse tickers
    tickers = [t.strip().upper() for t in args.tickers.split(',')]

    # Create collector
    collector = SECCollector()

    # Collect data
    df = collector.collect_board_data(tickers, args.year, verbose=True)

    # Save to file
    output_file = OUTPUT_DIR / f"board_data_{args.year}.csv"
    df.to_csv(output_file, index=False)

    print(f"\nData saved to: {output_file}")
    print(f"Collected {len(df)} director-company relationships")

    return df


def analyze_network(args):
    """Analyze board network and calculate centrality."""
    print("Analyzing board network...")

    # Load data
    if args.csv:
        print(f"Loading data from: {args.csv}")
        df = pd.read_csv(args.csv)
    else:
        print("Error: Must provide --csv with board data")
        return

    # Build network
    print("Building network...")
    network = build_board_network(df)

    # Print network stats
    stats = network.get_network_stats()
    print("\nNetwork Statistics:")
    print(f"  Companies: {stats['num_companies']}")
    print(f"  Directors: {stats['num_directors']}")
    print(f"  Board interlocks: {stats['num_interlocks']}")
    print(f"  Avg directors per board: {stats['avg_directors_per_board']}")
    print(f"  Avg boards per director: {stats['avg_boards_per_director']}")
    print(f"  Network density: {stats['network_density']}")
    print(f"  Connected components: {stats['num_connected_components']}")

    # Calculate centrality
    print("\nCalculating centrality measures...")
    centrality_df = calculate_centrality(network)

    # Save centrality scores
    output_file = OUTPUT_DIR / "centrality_scores.csv"
    centrality_df.to_csv(output_file, index=False)
    print(f"Centrality scores saved to: {output_file}")

    # Show top companies
    print("\nTop 10 Most Central Companies:")
    print(centrality_df[['company_id', 'n_score', 'num_interlocks']].head(10).to_string(index=False))

    # Generate visualizations if requested
    if args.visualize:
        print("\nGenerating visualizations...")

        # Network plot
        network_file = OUTPUT_DIR / "network.html"
        plot_network_interactive(network, centrality_df, top_n=100, save_path=str(network_file))
        print(f"Network visualization saved to: {network_file}")

        # Top companies plot
        top_companies_file = OUTPUT_DIR / "top_companies.png"
        plot_top_companies(centrality_df, n=20, save_path=str(top_companies_file))
        print(f"Top companies plot saved to: {top_companies_file}")

        # Correlation heatmap
        corr_file = OUTPUT_DIR / "centrality_correlation.png"
        plot_correlation_heatmap(centrality_df, save_path=str(corr_file))
        print(f"Correlation heatmap saved to: {corr_file}")

    return network, centrality_df


def run_backtest(args):
    """Run backtest of centrality-based strategy."""
    print("Running backtest...")

    # Load centrality data
    if args.csv:
        print(f"Loading centrality data from: {args.csv}")
        centrality_df = pd.read_csv(args.csv)
    else:
        print("Error: Must provide --csv with centrality data")
        return

    # Ensure required columns exist
    required_cols = ['year', 'company_id', 'n_score_quintile']
    if not all(col in centrality_df.columns for col in required_cols):
        print(f"Error: CSV must contain columns: {required_cols}")
        return

    # Create backtester
    backtester = BoardCentralityBacktester(centrality_df)

    # Run backtest
    print(f"Backtesting from {args.start} to {args.end}...")
    returns_df = backtester.backtest(args.start, args.end)

    # Calculate metrics
    metrics = backtester.calculate_performance_metrics()

    # Print results
    print("\n" + "=" * 60)
    print("BACKTEST RESULTS")
    print("=" * 60)

    summary = backtester.get_performance_summary()
    print("\nPerformance Summary:")
    print(summary.to_string())

    print("\n" + "=" * 60)

    # Save results
    returns_file = OUTPUT_DIR / "backtest_returns.csv"
    returns_df.to_csv(returns_file)
    print(f"\nReturns saved to: {returns_file}")

    metrics_file = OUTPUT_DIR / "backtest_metrics.csv"
    summary.to_csv(metrics_file)
    print(f"Metrics saved to: {metrics_file}")

    # Generate visualizations if requested
    if args.visualize:
        print("\nGenerating visualizations...")

        # Cumulative returns
        cum_returns_file = OUTPUT_DIR / "cumulative_returns.png"
        plot_cumulative_returns(returns_df, save_path=str(cum_returns_file))
        print(f"Cumulative returns plot saved to: {cum_returns_file}")

        # Drawdown
        drawdown_file = OUTPUT_DIR / "drawdown.png"
        plot_drawdown(returns_df['long_short'], title='Long-Short Strategy Drawdown',
                     save_path=str(drawdown_file))
        print(f"Drawdown plot saved to: {drawdown_file}")

    return backtester


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description='Board Network Analyzer - Analyze corporate board networks and stock performance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Collect board data from SEC
  python main.py collect --tickers AAPL,MSFT,GOOGL --year 2024

  # Analyze network from CSV
  python main.py analyze --csv board_data.csv --visualize

  # Run backtest
  python main.py backtest --csv centrality_scores.csv --start 2015 --end 2024 --visualize

  # Full pipeline
  python main.py collect --tickers AAPL,MSFT,GOOGL --year 2024
  python main.py analyze --csv output/board_data_2024.csv --visualize
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Collect command
    collect_parser = subparsers.add_parser('collect', help='Collect board data from SEC EDGAR')
    collect_parser.add_argument('--tickers', required=True, help='Comma-separated list of tickers')
    collect_parser.add_argument('--year', type=int, required=True, help='Year to collect data for')

    # Analyze command
    analyze_parser = subparsers.add_parser('analyze', help='Analyze board network')
    analyze_parser.add_argument('--csv', required=True, help='CSV file with board data')
    analyze_parser.add_argument('--visualize', action='store_true', help='Generate visualizations')

    # Backtest command
    backtest_parser = subparsers.add_parser('backtest', help='Run backtest')
    backtest_parser.add_argument('--csv', required=True, help='CSV file with centrality data')
    backtest_parser.add_argument('--start', type=int, required=True, help='Start year')
    backtest_parser.add_argument('--end', type=int, required=True, help='End year')
    backtest_parser.add_argument('--visualize', action='store_true', help='Generate visualizations')

    args = parser.parse_args()

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Run command
    if args.command == 'collect':
        collect_sec_data(args)
    elif args.command == 'analyze':
        analyze_network(args)
    elif args.command == 'backtest':
        run_backtest(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
