"""
Board network builder using NetworkX.

Constructs bipartite director-company networks and projects to
company-company networks based on shared directors.
"""

import networkx as nx
from networkx.algorithms import bipartite
import pandas as pd
from typing import Dict, Set, List, Tuple, Optional


class BoardNetwork:
    """
    Represents a board interlock network.

    The network has two representations:
    1. Bipartite graph: Directors <-> Companies
    2. Projected graph: Company <-> Company (edge = shared director)
    """

    def __init__(self):
        """Initialize an empty board network."""
        self.bipartite_graph = nx.Graph()
        self.company_network = None
        self.companies = set()
        self.directors = set()
        self.company_to_directors = {}
        self.director_to_companies = {}

    def add_director(self, director: str):
        """
        Add a director to the network.

        Args:
            director: Director name
        """
        self.directors.add(director)
        self.bipartite_graph.add_node(director, bipartite=1)

    def add_company(self, company: str):
        """
        Add a company to the network.

        Args:
            company: Company identifier (typically ticker)
        """
        self.companies.add(company)
        self.bipartite_graph.add_node(company, bipartite=0)

    def add_board_membership(self, director: str, company: str):
        """
        Add a board membership (director serves on company's board).

        Args:
            director: Director name
            company: Company identifier
        """
        # Add nodes if not already present
        if company not in self.companies:
            self.add_company(company)
        if director not in self.directors:
            self.add_director(director)

        # Add edge in bipartite graph
        self.bipartite_graph.add_edge(director, company)

        # Update mappings
        if company not in self.company_to_directors:
            self.company_to_directors[company] = set()
        self.company_to_directors[company].add(director)

        if director not in self.director_to_companies:
            self.director_to_companies[director] = set()
        self.director_to_companies[director].add(company)

    def build_from_dataframe(self, df: pd.DataFrame,
                            company_col: str = 'ticker',
                            director_col: str = 'director_name'):
        """
        Build the network from a DataFrame.

        Args:
            df: DataFrame with board composition data
            company_col: Column name for company identifier
            director_col: Column name for director name
        """
        for _, row in df.iterrows():
            company = row[company_col]
            director = row[director_col]
            self.add_board_membership(director, company)

    def project_to_company_network(self, weighted: bool = True) -> nx.Graph:
        """
        Project the bipartite graph to a company-company network.

        Companies are connected if they share at least one director.
        Edge weight = number of shared directors.

        Args:
            weighted: Include edge weights (number of shared directors)

        Returns:
            NetworkX graph of company-company connections
        """
        if weighted:
            # Create weighted projection
            self.company_network = bipartite.weighted_projected_graph(
                self.bipartite_graph,
                self.companies
            )
        else:
            # Create unweighted projection
            self.company_network = bipartite.projected_graph(
                self.bipartite_graph,
                self.companies
            )

        return self.company_network

    def get_shared_directors(self, company1: str, company2: str) -> Set[str]:
        """
        Get directors shared between two companies.

        Args:
            company1: First company identifier
            company2: Second company identifier

        Returns:
            Set of shared director names
        """
        if company1 not in self.company_to_directors:
            return set()
        if company2 not in self.company_to_directors:
            return set()

        return self.company_to_directors[company1] & self.company_to_directors[company2]

    def get_company_directors(self, company: str) -> Set[str]:
        """
        Get all directors for a company.

        Args:
            company: Company identifier

        Returns:
            Set of director names
        """
        return self.company_to_directors.get(company, set())

    def get_director_companies(self, director: str) -> Set[str]:
        """
        Get all companies a director serves on.

        Args:
            director: Director name

        Returns:
            Set of company identifiers
        """
        return self.director_to_companies.get(director, set())

    def get_network_stats(self) -> Dict:
        """
        Get statistics about the network.

        Returns:
            Dict with network statistics
        """
        # Ensure company network is built
        if self.company_network is None:
            self.project_to_company_network()

        # Count interlocks
        total_interlocks = 0
        for company in self.companies:
            neighbors = list(self.company_network.neighbors(company))
            total_interlocks += len(neighbors)
        total_interlocks //= 2  # Each edge counted twice

        # Calculate average directors per board
        avg_directors = sum(
            len(directors) for directors in self.company_to_directors.values()
        ) / len(self.companies) if self.companies else 0

        # Calculate average boards per director
        avg_boards = sum(
            len(companies) for companies in self.director_to_companies.values()
        ) / len(self.directors) if self.directors else 0

        # Network density
        density = nx.density(self.company_network)

        # Connected components
        num_components = nx.number_connected_components(self.company_network)

        return {
            'num_companies': len(self.companies),
            'num_directors': len(self.directors),
            'num_interlocks': total_interlocks,
            'avg_directors_per_board': round(avg_directors, 2),
            'avg_boards_per_director': round(avg_boards, 2),
            'network_density': round(density, 4),
            'num_connected_components': num_components,
        }

    def get_busy_directors(self, min_boards: int = 3) -> List[Tuple[str, int]]:
        """
        Get directors serving on multiple boards.

        Args:
            min_boards: Minimum number of boards to be considered "busy"

        Returns:
            List of (director, num_boards) tuples, sorted by num_boards descending
        """
        busy = [
            (director, len(companies))
            for director, companies in self.director_to_companies.items()
            if len(companies) >= min_boards
        ]
        return sorted(busy, key=lambda x: x[1], reverse=True)

    def get_well_connected_companies(self, min_interlocks: int = 5) -> List[Tuple[str, int]]:
        """
        Get companies with many board interlocks.

        Args:
            min_interlocks: Minimum number of interlocks

        Returns:
            List of (company, num_interlocks) tuples, sorted by num_interlocks descending
        """
        if self.company_network is None:
            self.project_to_company_network()

        well_connected = [
            (company, self.company_network.degree[company])
            for company in self.companies
            if self.company_network.degree[company] >= min_interlocks
        ]
        return sorted(well_connected, key=lambda x: x[1], reverse=True)

    def to_edgelist(self) -> pd.DataFrame:
        """
        Export company network as edge list.

        Returns:
            DataFrame with columns: company1, company2, weight (num shared directors)
        """
        if self.company_network is None:
            self.project_to_company_network()

        edges = []
        for u, v, data in self.company_network.edges(data=True):
            edges.append({
                'company1': u,
                'company2': v,
                'weight': data.get('weight', 1)
            })

        return pd.DataFrame(edges)

    def get_company_neighbors(self, company: str) -> Dict[str, int]:
        """
        Get companies connected to a given company.

        Args:
            company: Company identifier

        Returns:
            Dict mapping neighbor companies to number of shared directors
        """
        if self.company_network is None:
            self.project_to_company_network()

        if company not in self.company_network:
            return {}

        neighbors = {}
        for neighbor in self.company_network.neighbors(company):
            weight = self.company_network[company][neighbor].get('weight', 1)
            neighbors[neighbor] = weight

        return neighbors


def build_board_network(df: pd.DataFrame,
                       company_col: str = 'ticker',
                       director_col: str = 'director_name') -> BoardNetwork:
    """
    Convenience function to build a board network from a DataFrame.

    Args:
        df: DataFrame with board composition data
        company_col: Column name for company identifier
        director_col: Column name for director name

    Returns:
        BoardNetwork object
    """
    network = BoardNetwork()
    network.build_from_dataframe(df, company_col, director_col)
    return network
