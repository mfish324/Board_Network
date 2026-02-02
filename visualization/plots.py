"""
Visualization tools for board network analysis.

Creates plots for network structure, centrality, and performance.
"""

import matplotlib.pyplot as plt
import seaborn as sns
import networkx as nx
import pandas as pd
import numpy as np
from typing import Optional, List, Tuple
import plotly.graph_objects as go
import plotly.express as px

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from config import FIGURE_SIZE, DPI
from network.network_builder import BoardNetwork


# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = FIGURE_SIZE
plt.rcParams['figure.dpi'] = DPI


def plot_network(network: BoardNetwork,
                centrality_scores: Optional[pd.DataFrame] = None,
                layout: str = 'spring',
                node_size_metric: str = 'n_score',
                top_n: Optional[int] = 50,
                save_path: Optional[str] = None):
    """
    Plot the company network graph.

    Args:
        network: BoardNetwork object
        centrality_scores: DataFrame with centrality scores
        layout: Layout algorithm ('spring', 'circular', 'kamada_kawai')
        node_size_metric: Metric to size nodes by
        top_n: Only show top N most central companies
        save_path: Path to save figure
    """
    # Ensure company network is built
    if network.company_network is None:
        network.project_to_company_network()

    G = network.company_network

    # Filter to top N if specified
    if top_n is not None and centrality_scores is not None:
        top_companies = centrality_scores.nlargest(top_n, node_size_metric)['company_id'].tolist()
        G = G.subgraph(top_companies)

    # Calculate layout
    if layout == 'spring':
        pos = nx.spring_layout(G, k=0.5, iterations=50)
    elif layout == 'circular':
        pos = nx.circular_layout(G)
    elif layout == 'kamada_kawai':
        pos = nx.kamada_kawai_layout(G)
    else:
        pos = nx.spring_layout(G)

    # Node sizes based on centrality
    if centrality_scores is not None:
        score_dict = dict(zip(
            centrality_scores['company_id'],
            centrality_scores[node_size_metric]
        ))
        node_sizes = [score_dict.get(node, 0.1) * 2000 for node in G.nodes()]
    else:
        node_sizes = [100] * len(G.nodes())

    # Edge widths based on number of shared directors
    edge_widths = [G[u][v].get('weight', 1) * 0.5 for u, v in G.edges()]

    # Create plot
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)

    # Draw network
    nx.draw_networkx_nodes(
        G, pos, node_size=node_sizes,
        node_color='lightblue', alpha=0.7, ax=ax
    )

    nx.draw_networkx_edges(
        G, pos, width=edge_widths,
        alpha=0.3, ax=ax
    )

    nx.draw_networkx_labels(
        G, pos, font_size=8, ax=ax
    )

    ax.set_title('Board Interlock Network', fontsize=14, fontweight='bold')
    ax.axis('off')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=DPI, bbox_inches='tight')
    else:
        plt.show()


def plot_network_interactive(network: BoardNetwork,
                            centrality_scores: pd.DataFrame,
                            top_n: int = 100,
                            save_path: Optional[str] = None):
    """
    Create an interactive network plot using Plotly.

    Args:
        network: BoardNetwork object
        centrality_scores: DataFrame with centrality scores
        top_n: Number of top companies to show
        save_path: Path to save HTML file
    """
    # Ensure company network is built
    if network.company_network is None:
        network.project_to_company_network()

    # Filter to top N companies
    top_companies = centrality_scores.nlargest(top_n, 'n_score')['company_id'].tolist()
    G = network.company_network.subgraph(top_companies)

    # Calculate layout
    pos = nx.spring_layout(G, k=0.5, iterations=50)

    # Create edge trace
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 = pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.extend([x0, x1, None])
        edge_y.extend([y0, y1, None])

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines'
    )

    # Create node trace
    node_x = []
    node_y = []
    node_text = []
    node_size = []

    score_dict = dict(zip(
        centrality_scores['company_id'],
        centrality_scores['n_score']
    ))

    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

        # Hover text
        score = score_dict.get(node, 0)
        degree = G.degree[node]
        text = f"{node}<br>N-Score: {score:.3f}<br>Connections: {degree}"
        node_text.append(text)

        # Size
        node_size.append(score * 50)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers+text',
        hoverinfo='text',
        text=[node for node in G.nodes()],
        hovertext=node_text,
        textposition="top center",
        textfont=dict(size=8),
        marker=dict(
            size=node_size,
            color=[score_dict.get(node, 0) for node in G.nodes()],
            colorscale='Viridis',
            showscale=True,
            colorbar=dict(title="N-Score"),
            line=dict(width=2, color='white')
        )
    )

    # Create figure
    fig = go.Figure(data=[edge_trace, node_trace],
                   layout=go.Layout(
                       title='Board Interlock Network',
                       titlefont_size=16,
                       showlegend=False,
                       hovermode='closest',
                       margin=dict(b=0, l=0, r=0, t=40),
                       xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                       height=800
                   ))

    if save_path:
        fig.write_html(save_path)
    else:
        fig.show()


def plot_cumulative_returns(returns_df: pd.DataFrame,
                           save_path: Optional[str] = None):
    """
    Plot cumulative returns for all portfolios.

    Args:
        returns_df: DataFrame with returns for long, short, long_short, benchmark
        save_path: Path to save figure
    """
    # Calculate cumulative returns
    cum_returns = (1 + returns_df).cumprod()

    # Create plot
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)

    for col in ['long', 'short', 'long_short', 'benchmark']:
        if col in cum_returns.columns:
            ax.plot(cum_returns.index, cum_returns[col], label=col.replace('_', ' ').title(), linewidth=2)

    ax.set_title('Cumulative Returns', fontsize=14, fontweight='bold')
    ax.set_xlabel('Date')
    ax.set_ylabel('Cumulative Return')
    ax.legend(loc='best')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=DPI, bbox_inches='tight')
    else:
        plt.show()


def plot_drawdown(returns: pd.Series,
                 title: str = 'Drawdown',
                 save_path: Optional[str] = None):
    """
    Plot drawdown over time.

    Args:
        returns: Series of returns
        title: Plot title
        save_path: Path to save figure
    """
    # Calculate drawdown
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max

    # Create plot
    fig, ax = plt.subplots(figsize=FIGURE_SIZE)

    ax.fill_between(drawdown.index, drawdown * 100, 0, alpha=0.3, color='red')
    ax.plot(drawdown.index, drawdown * 100, color='red', linewidth=1)

    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlabel('Date')
    ax.set_ylabel('Drawdown (%)')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=DPI, bbox_inches='tight')
    else:
        plt.show()


def plot_quintile_performance(metrics_by_quintile: pd.DataFrame,
                              metric: str = 'annualized_return',
                              save_path: Optional[str] = None):
    """
    Plot performance by quintile.

    Args:
        metrics_by_quintile: DataFrame with metrics for each quintile
        metric: Metric to plot
        save_path: Path to save figure
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    quintiles = metrics_by_quintile.index
    values = metrics_by_quintile[metric]

    colors = ['red' if q == 1 else 'green' if q == 5 else 'gray' for q in quintiles]

    ax.bar(quintiles, values, color=colors, alpha=0.7)

    ax.set_title(f'{metric.replace("_", " ").title()} by N-Score Quintile',
                fontsize=14, fontweight='bold')
    ax.set_xlabel('N-Score Quintile (1=Least Central, 5=Most Central)')
    ax.set_ylabel(metric.replace('_', ' ').title())
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=DPI, bbox_inches='tight')
    else:
        plt.show()


def plot_rolling_sharpe(returns: pd.Series,
                       window: int = 252,
                       save_path: Optional[str] = None):
    """
    Plot rolling Sharpe ratio.

    Args:
        returns: Series of returns
        window: Rolling window size
        save_path: Path to save figure
    """
    from strategy.performance import calculate_rolling_sharpe

    rolling_sharpe = calculate_rolling_sharpe(returns, window)

    fig, ax = plt.subplots(figsize=FIGURE_SIZE)

    ax.plot(rolling_sharpe.index, rolling_sharpe, linewidth=2)
    ax.axhline(y=0, color='black', linestyle='--', alpha=0.3)

    ax.set_title(f'{window}-Day Rolling Sharpe Ratio', fontsize=14, fontweight='bold')
    ax.set_xlabel('Date')
    ax.set_ylabel('Sharpe Ratio')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=DPI, bbox_inches='tight')
    else:
        plt.show()


def plot_centrality_distribution(centrality_scores: pd.DataFrame,
                                 metric: str = 'n_score',
                                 save_path: Optional[str] = None):
    """
    Plot distribution of centrality scores.

    Args:
        centrality_scores: DataFrame with centrality scores
        metric: Centrality metric to plot
        save_path: Path to save figure
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.hist(centrality_scores[metric], bins=50, alpha=0.7, color='blue', edgecolor='black')

    ax.set_title(f'Distribution of {metric.replace("_", " ").title()}',
                fontsize=14, fontweight='bold')
    ax.set_xlabel(metric.replace('_', ' ').title())
    ax.set_ylabel('Frequency')
    ax.grid(True, alpha=0.3, axis='y')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=DPI, bbox_inches='tight')
    else:
        plt.show()


def plot_correlation_heatmap(centrality_scores: pd.DataFrame,
                            save_path: Optional[str] = None):
    """
    Plot correlation heatmap of centrality measures.

    Args:
        centrality_scores: DataFrame with centrality scores
        save_path: Path to save figure
    """
    # Select centrality columns
    centrality_cols = [
        'degree_centrality', 'eigenvector_centrality',
        'betweenness_centrality', 'closeness_centrality'
    ]

    corr = centrality_scores[centrality_cols].corr()

    fig, ax = plt.subplots(figsize=(8, 6))

    sns.heatmap(corr, annot=True, fmt='.3f', cmap='coolwarm',
               center=0, square=True, ax=ax,
               cbar_kws={'label': 'Correlation'})

    ax.set_title('Centrality Measures Correlation', fontsize=14, fontweight='bold')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=DPI, bbox_inches='tight')
    else:
        plt.show()


def plot_top_companies(centrality_scores: pd.DataFrame,
                      n: int = 20,
                      metric: str = 'n_score',
                      save_path: Optional[str] = None):
    """
    Plot top N most central companies.

    Args:
        centrality_scores: DataFrame with centrality scores
        n: Number of companies to show
        metric: Metric to rank by
        save_path: Path to save figure
    """
    top_n = centrality_scores.nlargest(n, metric)

    fig, ax = plt.subplots(figsize=(10, 8))

    ax.barh(range(n), top_n[metric], color='steelblue', alpha=0.7)
    ax.set_yticks(range(n))
    ax.set_yticklabels(top_n['company_id'])
    ax.invert_yaxis()

    ax.set_title(f'Top {n} Companies by {metric.replace("_", " ").title()}',
                fontsize=14, fontweight='bold')
    ax.set_xlabel(metric.replace('_', ' ').title())
    ax.grid(True, alpha=0.3, axis='x')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=DPI, bbox_inches='tight')
    else:
        plt.show()
