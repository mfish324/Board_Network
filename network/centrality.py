"""
Centrality measures for board network analysis.

Calculates four centrality measures and composite N-Score based on
Larcker, So, and Wang (2013) research.
"""

import networkx as nx
import pandas as pd
import numpy as np
from typing import Dict, Optional
import warnings

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from config import EIGENVECTOR_MAX_ITER, EIGENVECTOR_TOLERANCE, NUM_QUINTILES
from network.network_builder import BoardNetwork


class CentralityCalculator:
    """
    Calculates centrality measures for companies in a board network.

    Centrality measures:
    1. Degree Centrality: Fraction of firms connected to this firm
    2. Eigenvector Centrality: Connections to well-connected nodes matter more
    3. Betweenness Centrality: Times node acts as bridge on shortest paths
    4. Closeness Centrality: Average distance to all other nodes
    5. N-Score: Average of four normalized measures
    """

    def __init__(self, network: BoardNetwork):
        """
        Initialize the centrality calculator.

        Args:
            network: BoardNetwork object
        """
        self.network = network

        # Ensure company network is built
        if self.network.company_network is None:
            self.network.project_to_company_network()

        self.company_network = self.network.company_network
        self.centrality_scores = {}

    def calculate_degree_centrality(self) -> Dict[str, float]:
        """
        Calculate degree centrality for all companies.

        Degree centrality = number of connections / (total nodes - 1)
        Interpretation: What fraction of other firms share directors with this firm?

        Returns:
            Dict mapping company to degree centrality score
        """
        return nx.degree_centrality(self.company_network)

    def calculate_eigenvector_centrality(self) -> Dict[str, float]:
        """
        Calculate eigenvector centrality for all companies.

        Eigenvector centrality: Connections to well-connected nodes count more.
        Interpretation: It's not just who you know, but who they know.

        Returns:
            Dict mapping company to eigenvector centrality score
        """
        try:
            return nx.eigenvector_centrality(
                self.company_network,
                max_iter=EIGENVECTOR_MAX_ITER,
                tol=EIGENVECTOR_TOLERANCE
            )
        except nx.PowerIterationFailedConvergence:
            warnings.warn(
                "Eigenvector centrality did not converge. Using numpy method."
            )
            return nx.eigenvector_centrality_numpy(self.company_network)

    def calculate_betweenness_centrality(self) -> Dict[str, float]:
        """
        Calculate betweenness centrality for all companies.

        Betweenness centrality: How often a node appears on shortest paths.
        Interpretation: Does this firm act as a bridge in the network?

        Returns:
            Dict mapping company to betweenness centrality score
        """
        return nx.betweenness_centrality(self.company_network)

    def calculate_closeness_centrality(self) -> Dict[str, float]:
        """
        Calculate closeness centrality for all companies.

        Closeness centrality: Average distance to all other nodes.
        Interpretation: How quickly can information reach this firm?

        Returns:
            Dict mapping company to closeness centrality score
        """
        # Handle disconnected components by calculating for each component
        if not nx.is_connected(self.company_network):
            # For disconnected graphs, calculate closeness within components
            closeness = {}
            for component in nx.connected_components(self.company_network):
                subgraph = self.company_network.subgraph(component)
                component_closeness = nx.closeness_centrality(subgraph)
                closeness.update(component_closeness)
            return closeness
        else:
            return nx.closeness_centrality(self.company_network)

    def calculate_all_centralities(self) -> pd.DataFrame:
        """
        Calculate all four centrality measures for all companies.

        Returns:
            DataFrame with centrality scores
        """
        # Calculate each centrality measure
        degree = self.calculate_degree_centrality()
        eigenvector = self.calculate_eigenvector_centrality()
        betweenness = self.calculate_betweenness_centrality()
        closeness = self.calculate_closeness_centrality()

        # Get all companies
        companies = list(self.network.companies)

        # Create DataFrame
        df = pd.DataFrame({
            'company_id': companies,
            'degree_centrality': [degree.get(c, 0) for c in companies],
            'eigenvector_centrality': [eigenvector.get(c, 0) for c in companies],
            'betweenness_centrality': [betweenness.get(c, 0) for c in companies],
            'closeness_centrality': [closeness.get(c, 0) for c in companies],
        })

        # Calculate normalized versions (0-1 scale within this sample)
        for col in ['degree_centrality', 'eigenvector_centrality',
                   'betweenness_centrality', 'closeness_centrality']:
            col_min = df[col].min()
            col_max = df[col].max()
            col_range = col_max - col_min

            if col_range > 0:
                df[f'{col}_norm'] = (df[col] - col_min) / col_range
            else:
                df[f'{col}_norm'] = 0.5  # All equal, assign middle value

        # Calculate N-Score (composite measure)
        df['n_score'] = (
            df['degree_centrality_norm'] +
            df['eigenvector_centrality_norm'] +
            df['betweenness_centrality_norm'] +
            df['closeness_centrality_norm']
        ) / 4

        # Assign quintiles based on N-Score (5 = most central)
        df['n_score_quintile'] = pd.qcut(
            df['n_score'],
            q=NUM_QUINTILES,
            labels=range(1, NUM_QUINTILES + 1),
            duplicates='drop'
        )

        # Add network statistics
        df['num_directors'] = df['company_id'].apply(
            lambda c: len(self.network.get_company_directors(c))
        )

        df['num_interlocks'] = df['company_id'].apply(
            lambda c: self.company_network.degree[c] if c in self.company_network else 0
        )

        # Sort by N-Score descending
        df = df.sort_values('n_score', ascending=False).reset_index(drop=True)

        return df

    def get_top_companies(self, n: int = 10, metric: str = 'n_score') -> pd.DataFrame:
        """
        Get top N most central companies.

        Args:
            n: Number of companies to return
            metric: Centrality metric to rank by

        Returns:
            DataFrame with top N companies
        """
        if not self.centrality_scores or len(self.centrality_scores) == 0:
            self.centrality_scores = self.calculate_all_centralities()

        df = self.centrality_scores.copy()
        return df.nlargest(n, metric)

    def get_companies_by_quintile(self, quintile: int) -> pd.DataFrame:
        """
        Get all companies in a specific N-Score quintile.

        Args:
            quintile: Quintile number (1-5, where 5 = most central)

        Returns:
            DataFrame with companies in the quintile
        """
        if not self.centrality_scores or len(self.centrality_scores) == 0:
            self.centrality_scores = self.calculate_all_centralities()

        df = self.centrality_scores.copy()
        return df[df['n_score_quintile'] == quintile].reset_index(drop=True)

    def export_centrality_scores(self, filepath: str):
        """
        Export centrality scores to CSV.

        Args:
            filepath: Path to output CSV file
        """
        if not self.centrality_scores or len(self.centrality_scores) == 0:
            self.centrality_scores = self.calculate_all_centralities()

        self.centrality_scores.to_csv(filepath, index=False)


def calculate_centrality(network: BoardNetwork) -> pd.DataFrame:
    """
    Convenience function to calculate all centrality measures.

    Args:
        network: BoardNetwork object

    Returns:
        DataFrame with centrality scores
    """
    calculator = CentralityCalculator(network)
    return calculator.calculate_all_centralities()


def compare_centrality_measures(network: BoardNetwork) -> pd.DataFrame:
    """
    Calculate correlation between different centrality measures.

    Args:
        network: BoardNetwork object

    Returns:
        DataFrame with correlation matrix
    """
    calculator = CentralityCalculator(network)
    df = calculator.calculate_all_centralities()

    # Select only the raw centrality columns
    centrality_cols = [
        'degree_centrality', 'eigenvector_centrality',
        'betweenness_centrality', 'closeness_centrality'
    ]

    correlation = df[centrality_cols].corr()
    return correlation
