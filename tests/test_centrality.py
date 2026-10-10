"""
Tests for centrality calculation module.
"""

import pytest
import pandas as pd
import numpy as np

from network.network_builder import BoardNetwork
from network.centrality import CentralityCalculator, calculate_centrality


class TestCentralityCalculator:
    """Test cases for CentralityCalculator class."""

    @pytest.fixture
    def sample_network(self):
        """Create sample network for testing."""
        data = {
            'ticker': [
                'AAPL', 'AAPL', 'AAPL',
                'MSFT', 'MSFT', 'MSFT',
                'GOOGL', 'GOOGL',
                'JPM', 'JPM',
                'GS'
            ],
            'director_name': [
                'John Smith', 'Jane Doe', 'Bob Johnson',
                'Jane Doe', 'Alice Williams', 'Charlie Brown',
                'Bob Johnson', 'Alice Williams',
                'Eve Davis', 'Frank Miller',
                'George Wilson'
            ]
        }
        df = pd.DataFrame(data)

        network = BoardNetwork()
        network.build_from_dataframe(df)

        return network

    def test_initialization(self, sample_network):
        """Test calculator initialization."""
        calculator = CentralityCalculator(sample_network)

        assert calculator.network == sample_network
        assert calculator.company_network is not None

    def test_degree_centrality(self, sample_network):
        """Test degree centrality calculation."""
        calculator = CentralityCalculator(sample_network)
        degree = calculator.calculate_degree_centrality()

        assert isinstance(degree, dict)
        assert len(degree) == len(sample_network.companies)

        # All values should be between 0 and 1
        for value in degree.values():
            assert 0 <= value <= 1

    def test_eigenvector_centrality(self, sample_network):
        """Test eigenvector centrality calculation."""
        calculator = CentralityCalculator(sample_network)
        eigenvector = calculator.calculate_eigenvector_centrality()

        assert isinstance(eigenvector, dict)
        assert len(eigenvector) == len(sample_network.companies)

        # All values should be between 0 and 1
        for value in eigenvector.values():
            assert 0 <= value <= 1

    def test_betweenness_centrality(self, sample_network):
        """Test betweenness centrality calculation."""
        calculator = CentralityCalculator(sample_network)
        betweenness = calculator.calculate_betweenness_centrality()

        assert isinstance(betweenness, dict)
        assert len(betweenness) == len(sample_network.companies)

        # All values should be between 0 and 1
        for value in betweenness.values():
            assert 0 <= value <= 1

    def test_closeness_centrality(self, sample_network):
        """Test closeness centrality calculation."""
        calculator = CentralityCalculator(sample_network)
        closeness = calculator.calculate_closeness_centrality()

        assert isinstance(closeness, dict)
        assert len(closeness) == len(sample_network.companies)

        # All values should be between 0 and 1
        for value in closeness.values():
            assert 0 <= value <= 1

    def test_calculate_all_centralities(self, sample_network):
        """Test calculating all centrality measures."""
        calculator = CentralityCalculator(sample_network)
        df = calculator.calculate_all_centralities()

        # Check DataFrame structure
        assert isinstance(df, pd.DataFrame)
        assert 'company_id' in df.columns
        assert 'degree_centrality' in df.columns
        assert 'eigenvector_centrality' in df.columns
        assert 'betweenness_centrality' in df.columns
        assert 'closeness_centrality' in df.columns
        assert 'n_score' in df.columns
        assert 'n_score_quintile' in df.columns
        assert 'num_directors' in df.columns
        assert 'num_interlocks' in df.columns

        # Check all companies are included
        assert len(df) == len(sample_network.companies)

        # Check N-Score is average of normalized measures
        for _, row in df.iterrows():
            expected_n_score = (
                row['degree_centrality_norm'] +
                row['eigenvector_centrality_norm'] +
                row['betweenness_centrality_norm'] +
                row['closeness_centrality_norm']
            ) / 4

            assert np.isclose(row['n_score'], expected_n_score, rtol=0.01)

        # Check sorted by n_score
        assert df['n_score'].is_monotonic_decreasing

    def test_n_score_quintiles(self, sample_network):
        """Test N-Score quintile assignment."""
        calculator = CentralityCalculator(sample_network)
        df = calculator.calculate_all_centralities()

        # Check quintile values are in valid range
        quintiles = df['n_score_quintile'].dropna()
        for q in quintiles:
            assert 1 <= q <= 5

    def test_get_top_companies(self, sample_network):
        """Test getting top companies."""
        calculator = CentralityCalculator(sample_network)
        calculator.centrality_scores = calculator.calculate_all_centralities()

        top_3 = calculator.get_top_companies(n=3, metric='n_score')

        assert len(top_3) == 3
        # Should be sorted by n_score descending
        assert top_3.iloc[0]['n_score'] >= top_3.iloc[1]['n_score']

    def test_get_companies_by_quintile(self, sample_network):
        """Test getting companies by quintile."""
        calculator = CentralityCalculator(sample_network)
        calculator.centrality_scores = calculator.calculate_all_centralities()

        # Try to get quintile 5 (most central)
        q5 = calculator.get_companies_by_quintile(5)

        # Should have at least one company (if there are enough companies for quintiles)
        if len(sample_network.companies) >= 5:
            assert len(q5) >= 1
            # All should have quintile 5
            for _, row in q5.iterrows():
                assert row['n_score_quintile'] == 5

    def test_convenience_function(self, sample_network):
        """Test convenience function."""
        df = calculate_centrality(sample_network)

        assert isinstance(df, pd.DataFrame)
        assert 'n_score' in df.columns
        assert len(df) == len(sample_network.companies)

    def test_normalized_scores(self, sample_network):
        """Test that normalized scores are in [0, 1]."""
        calculator = CentralityCalculator(sample_network)
        df = calculator.calculate_all_centralities()

        norm_cols = [
            'degree_centrality_norm', 'eigenvector_centrality_norm',
            'betweenness_centrality_norm', 'closeness_centrality_norm'
        ]

        for col in norm_cols:
            assert df[col].min() >= 0
            assert df[col].max() <= 1

    def test_network_stats_columns(self, sample_network):
        """Test that network statistics are included."""
        calculator = CentralityCalculator(sample_network)
        df = calculator.calculate_all_centralities()

        # Check num_directors is correct
        for _, row in df.iterrows():
            company = row['company_id']
            directors = sample_network.get_company_directors(company)
            assert row['num_directors'] == len(directors)

    def test_single_node_network(self):
        """Test handling of single-node network."""
        data = {
            'ticker': ['AAPL'],
            'director_name': ['John Smith']
        }
        df = pd.DataFrame(data)

        network = BoardNetwork()
        network.build_from_dataframe(df)

        calculator = CentralityCalculator(network)
        result = calculator.calculate_all_centralities()

        # Should still work, but with limited centrality
        assert len(result) == 1
        assert result.iloc[0]['company_id'] == 'AAPL'
