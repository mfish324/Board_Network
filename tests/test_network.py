"""
Tests for network builder module.
"""

import pytest
import pandas as pd
import networkx as nx
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from network.network_builder import BoardNetwork, build_board_network


class TestBoardNetwork:
    """Test cases for BoardNetwork class."""

    @pytest.fixture
    def sample_data(self):
        """Create sample board composition data."""
        data = {
            'ticker': ['AAPL', 'AAPL', 'AAPL', 'MSFT', 'MSFT', 'GOOGL', 'GOOGL', 'GOOGL'],
            'director_name': [
                'John Smith', 'Jane Doe', 'Bob Johnson',
                'Jane Doe', 'Alice Williams', 'Bob Johnson',
                'Alice Williams', 'Charlie Brown'
            ]
        }
        return pd.DataFrame(data)

    def test_initialization(self):
        """Test network initialization."""
        network = BoardNetwork()

        assert len(network.companies) == 0
        assert len(network.directors) == 0
        assert network.company_network is None

    def test_add_director(self):
        """Test adding directors."""
        network = BoardNetwork()
        network.add_director("John Smith")

        assert "John Smith" in network.directors
        assert network.bipartite_graph.has_node("John Smith")

    def test_add_company(self):
        """Test adding companies."""
        network = BoardNetwork()
        network.add_company("AAPL")

        assert "AAPL" in network.companies
        assert network.bipartite_graph.has_node("AAPL")

    def test_add_board_membership(self):
        """Test adding board memberships."""
        network = BoardNetwork()
        network.add_board_membership("John Smith", "AAPL")

        assert "AAPL" in network.companies
        assert "John Smith" in network.directors
        assert network.bipartite_graph.has_edge("John Smith", "AAPL")

    def test_build_from_dataframe(self, sample_data):
        """Test building network from DataFrame."""
        network = BoardNetwork()
        network.build_from_dataframe(sample_data)

        # Check companies
        assert len(network.companies) == 3
        assert "AAPL" in network.companies
        assert "MSFT" in network.companies
        assert "GOOGL" in network.companies

        # Check directors
        assert len(network.directors) == 5

    def test_project_to_company_network(self, sample_data):
        """Test projection to company network."""
        network = BoardNetwork()
        network.build_from_dataframe(sample_data)

        company_network = network.project_to_company_network()

        # All companies should be in network
        assert len(company_network.nodes()) == 3

        # Check for expected edges (shared directors)
        # AAPL and MSFT share Jane Doe
        assert company_network.has_edge("AAPL", "MSFT")

        # AAPL and GOOGL share Bob Johnson
        assert company_network.has_edge("AAPL", "GOOGL")

        # MSFT and GOOGL share Alice Williams
        assert company_network.has_edge("MSFT", "GOOGL")

    def test_shared_directors(self, sample_data):
        """Test getting shared directors."""
        network = BoardNetwork()
        network.build_from_dataframe(sample_data)

        # AAPL and MSFT share Jane Doe
        shared = network.get_shared_directors("AAPL", "MSFT")
        assert "Jane Doe" in shared

        # AAPL and GOOGL share Bob Johnson
        shared = network.get_shared_directors("AAPL", "GOOGL")
        assert "Bob Johnson" in shared

    def test_company_directors(self, sample_data):
        """Test getting company directors."""
        network = BoardNetwork()
        network.build_from_dataframe(sample_data)

        directors = network.get_company_directors("AAPL")
        assert len(directors) == 3
        assert "John Smith" in directors
        assert "Jane Doe" in directors
        assert "Bob Johnson" in directors

    def test_director_companies(self, sample_data):
        """Test getting director's companies."""
        network = BoardNetwork()
        network.build_from_dataframe(sample_data)

        companies = network.get_director_companies("Jane Doe")
        assert len(companies) == 2
        assert "AAPL" in companies
        assert "MSFT" in companies

    def test_network_stats(self, sample_data):
        """Test network statistics."""
        network = BoardNetwork()
        network.build_from_dataframe(sample_data)

        stats = network.get_network_stats()

        assert stats['num_companies'] == 3
        assert stats['num_directors'] == 5
        assert stats['num_interlocks'] == 3  # Three edges in company network
        assert stats['avg_directors_per_board'] > 0
        assert stats['avg_boards_per_director'] > 0

    def test_busy_directors(self, sample_data):
        """Test finding busy directors."""
        network = BoardNetwork()
        network.build_from_dataframe(sample_data)

        busy = network.get_busy_directors(min_boards=2)

        # Jane Doe, Bob Johnson, and Alice Williams serve on 2+ boards
        assert len(busy) == 3

        # Check they're sorted by number of boards
        assert busy[0][1] >= busy[1][1]

    def test_well_connected_companies(self, sample_data):
        """Test finding well-connected companies."""
        network = BoardNetwork()
        network.build_from_dataframe(sample_data)

        well_connected = network.get_well_connected_companies(min_interlocks=1)

        # All three companies have at least 1 interlock
        assert len(well_connected) == 3

    def test_to_edgelist(self, sample_data):
        """Test export to edge list."""
        network = BoardNetwork()
        network.build_from_dataframe(sample_data)

        edgelist = network.to_edgelist()

        assert isinstance(edgelist, pd.DataFrame)
        assert 'company1' in edgelist.columns
        assert 'company2' in edgelist.columns
        assert 'weight' in edgelist.columns
        assert len(edgelist) == 3  # Three edges

    def test_company_neighbors(self, sample_data):
        """Test getting company neighbors."""
        network = BoardNetwork()
        network.build_from_dataframe(sample_data)

        neighbors = network.get_company_neighbors("AAPL")

        assert "MSFT" in neighbors
        assert "GOOGL" in neighbors
        assert len(neighbors) == 2

    def test_edge_weights(self, sample_data):
        """Test edge weight calculation."""
        network = BoardNetwork()
        network.build_from_dataframe(sample_data)
        network.project_to_company_network()

        # Each pair shares exactly 1 director
        weight = network.company_network["AAPL"]["MSFT"]["weight"]
        assert weight == 1

    def test_empty_network(self):
        """Test handling of empty network."""
        network = BoardNetwork()
        stats = network.get_network_stats()

        assert stats['num_companies'] == 0
        assert stats['num_directors'] == 0

    def test_convenience_function(self, sample_data):
        """Test convenience function."""
        network = build_board_network(sample_data)

        assert len(network.companies) == 3
        assert len(network.directors) == 5
