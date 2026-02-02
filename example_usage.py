#!/usr/bin/env python3
"""
Example usage of Board Network Analyzer

This script demonstrates the main functionality of the tool.
"""

import pandas as pd
from pathlib import Path

# Import modules
from data.sec_collector import SECCollector
from network.network_builder import build_board_network
from network.centrality import calculate_centrality
from strategy.backtester import BoardCentralityBacktester
from visualization.plots import (
    plot_network_interactive,
    plot_top_companies,
    plot_correlation_heatmap
)
from config import OUTPUT_DIR


def example_1_collect_data():
    """Example 1: Collect board data from SEC EDGAR."""
    print("=" * 60)
    print("Example 1: Collecting Board Data from SEC EDGAR")
    print("=" * 60)

    # Define tickers to analyze
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'JPM', 'GS']
    year = 2024

    print(f"\nCollecting data for: {', '.join(tickers)}")
    print(f"Year: {year}\n")

    # Create collector
    collector = SECCollector()

    # Collect board data
    # NOTE: This will make real requests to SEC EDGAR
    # Set verbose=False to reduce output
    df = collector.collect_board_data(tickers, year, verbose=True)

    # Save to CSV
    output_file = OUTPUT_DIR / f"board_data_{year}.csv"
    df.to_csv(output_file, index=False)

    print(f"\nCollected {len(df)} director-company relationships")
    print(f"Data saved to: {output_file}")

    return df


def example_2_analyze_network(df):
    """Example 2: Build network and calculate centrality."""
    print("\n" + "=" * 60)
    print("Example 2: Analyzing Board Network")
    print("=" * 60)

    # Build network
    print("\nBuilding board interlock network...")
    network = build_board_network(df)

    # Print network statistics
    stats = network.get_network_stats()
    print("\nNetwork Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # Find busy directors
    busy_directors = network.get_busy_directors(min_boards=2)
    print(f"\nDirectors serving on 2+ boards: {len(busy_directors)}")
    if busy_directors:
        print("Top 5 busy directors:")
        for director, num_boards in busy_directors[:5]:
            print(f"  {director}: {num_boards} boards")

    # Calculate centrality
    print("\nCalculating centrality measures...")
    centrality_df = calculate_centrality(network)

    # Save results
    output_file = OUTPUT_DIR / "centrality_scores.csv"
    centrality_df.to_csv(output_file, index=False)
    print(f"Centrality scores saved to: {output_file}")

    # Show top 10 most central companies
    print("\nTop 10 Most Central Companies:")
    top_10 = centrality_df[['company_id', 'n_score', 'n_score_quintile', 'num_interlocks']].head(10)
    print(top_10.to_string(index=False))

    return network, centrality_df


def example_3_visualize(network, centrality_df):
    """Example 3: Generate visualizations."""
    print("\n" + "=" * 60)
    print("Example 3: Generating Visualizations")
    print("=" * 60)

    # Interactive network plot
    print("\nCreating interactive network visualization...")
    network_file = OUTPUT_DIR / "network.html"
    plot_network_interactive(network, centrality_df, top_n=50, save_path=str(network_file))
    print(f"Saved to: {network_file}")

    # Top companies bar chart
    print("\nCreating top companies chart...")
    top_companies_file = OUTPUT_DIR / "top_companies.png"
    plot_top_companies(centrality_df, n=15, save_path=str(top_companies_file))
    print(f"Saved to: {top_companies_file}")

    # Centrality correlation heatmap
    print("\nCreating centrality correlation heatmap...")
    corr_file = OUTPUT_DIR / "centrality_correlation.png"
    plot_correlation_heatmap(centrality_df, save_path=str(corr_file))
    print(f"Saved to: {corr_file}")


def example_4_load_from_csv():
    """Example 4: Load existing data from CSV."""
    print("\n" + "=" * 60)
    print("Example 4: Loading Data from CSV")
    print("=" * 60)

    # Create sample data
    sample_data = {
        'year': [2024] * 12,
        'ticker': ['AAPL', 'AAPL', 'AAPL', 'MSFT', 'MSFT', 'MSFT',
                  'GOOGL', 'GOOGL', 'GOOGL', 'JPM', 'JPM', 'GS'],
        'director_name': [
            'John Smith', 'Jane Doe', 'Bob Johnson',
            'Jane Doe', 'Alice Williams', 'Charlie Brown',
            'Bob Johnson', 'Alice Williams', 'David Lee',
            'Eve Davis', 'Frank Miller', 'George Wilson'
        ]
    }

    df = pd.DataFrame(sample_data)

    # Save to CSV
    csv_file = OUTPUT_DIR / "sample_board_data.csv"
    df.to_csv(csv_file, index=False)
    print(f"\nCreated sample data: {csv_file}")

    # Load from CSV
    loaded_df = pd.read_csv(csv_file)
    print(f"Loaded {len(loaded_df)} rows")

    # Build network
    network = build_board_network(loaded_df)
    stats = network.get_network_stats()
    print(f"\nNetwork has {stats['num_companies']} companies and {stats['num_directors']} directors")

    return loaded_df


def example_5_python_api():
    """Example 5: Using the Python API directly."""
    print("\n" + "=" * 60)
    print("Example 5: Using Python API")
    print("=" * 60)

    # Create sample board data
    data = {
        'ticker': ['AAPL', 'AAPL', 'MSFT', 'MSFT', 'GOOGL', 'GOOGL'],
        'director_name': ['John Smith', 'Jane Doe', 'Jane Doe',
                         'Bob Johnson', 'Bob Johnson', 'Alice Williams']
    }
    df = pd.DataFrame(data)

    # Build network
    from network import BoardNetwork
    network = BoardNetwork()
    network.build_from_dataframe(df, company_col='ticker', director_col='director_name')

    # Get specific information
    print("\nAPPL directors:")
    aapl_directors = network.get_company_directors('AAPL')
    for director in aapl_directors:
        print(f"  - {director}")

    print("\nJane Doe serves on:")
    jane_companies = network.get_director_companies('Jane Doe')
    for company in jane_companies:
        print(f"  - {company}")

    print("\nAPPL and MSFT share:")
    shared = network.get_shared_directors('AAPL', 'MSFT')
    for director in shared:
        print(f"  - {director}")


def main():
    """Run all examples."""
    print("\n")
    print("╔" + "═" * 58 + "╗")
    print("║" + " " * 10 + "Board Network Analyzer - Examples" + " " * 15 + "║")
    print("╚" + "═" * 58 + "╝")

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Example 5: Quick Python API demo (doesn't require SEC data)
    example_5_python_api()

    # Example 4: Load from CSV
    df = example_4_load_from_csv()

    # If you want to run SEC collection (commented out by default):
    # df = example_1_collect_data()

    # Example 2: Analyze network
    network, centrality_df = example_2_analyze_network(df)

    # Example 3: Visualizations
    example_3_visualize(network, centrality_df)

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
    print(f"\nCheck the '{OUTPUT_DIR}' directory for outputs.")


if __name__ == '__main__':
    main()
