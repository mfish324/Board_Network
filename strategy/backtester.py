"""
Backtester for board centrality-based long-short strategy.

Tests the hypothesis that firms with central boards outperform
firms with peripheral boards (Larcker, So, Wang 2013).
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import warnings

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from config import (
    REBALANCE_MONTH, REBALANCE_DAY, RISK_FREE_RATE,
    TRANSACTION_COST_BPS
)
from strategy.stock_data import (
    StockDataFetcher, calculate_annualized_return,
    calculate_annualized_volatility, calculate_sharpe_ratio,
    calculate_max_drawdown
)


class BoardCentralityBacktester:
    """
    Backtests a long-short strategy based on board centrality.

    Strategy:
    - Long: Top quintile (most central boards)
    - Short: Bottom quintile (least central boards)
    - Rebalance: Annually in June (after proxy season)
    - Weighting: Equal weight within each leg
    """

    def __init__(self,
                 centrality_data: pd.DataFrame,
                 rebalance_month: int = REBALANCE_MONTH,
                 rebalance_day: int = REBALANCE_DAY,
                 transaction_cost_bps: float = TRANSACTION_COST_BPS):
        """
        Initialize the backtester.

        Args:
            centrality_data: DataFrame with columns: year, company_id, n_score_quintile
            rebalance_month: Month to rebalance (1-12)
            rebalance_day: Day of month to rebalance
            transaction_cost_bps: Transaction costs in basis points
        """
        self.centrality_data = centrality_data
        self.rebalance_month = rebalance_month
        self.rebalance_day = rebalance_day
        self.transaction_cost_bps = transaction_cost_bps / 10000  # Convert to decimal

        self.stock_fetcher = StockDataFetcher()
        self.performance = None
        self.holdings = []

    def get_rebalance_dates(self,
                           start_year: int,
                           end_year: int) -> List[datetime]:
        """
        Generate list of rebalance dates.

        Args:
            start_year: First year to rebalance
            end_year: Last year to rebalance

        Returns:
            List of rebalance dates
        """
        dates = []
        for year in range(start_year, end_year + 1):
            date = datetime(year, self.rebalance_month, self.rebalance_day)
            dates.append(date)
        return dates

    def get_portfolio_for_date(self,
                               rebalance_date: datetime,
                               quintile: int) -> List[str]:
        """
        Get portfolio constituents for a rebalance date and quintile.

        Args:
            rebalance_date: Rebalance date
            quintile: N-score quintile (1-5)

        Returns:
            List of ticker symbols
        """
        # Use centrality data from the previous year
        # (e.g., June 2020 rebalance uses 2019 proxy data)
        year = rebalance_date.year - 1

        # Filter centrality data
        data = self.centrality_data[
            (self.centrality_data['year'] == year) &
            (self.centrality_data['n_score_quintile'] == quintile)
        ]

        return data['company_id'].tolist()

    def calculate_portfolio_returns(self,
                                   tickers: List[str],
                                   start_date: datetime,
                                   end_date: datetime,
                                   position_type: str = 'long') -> pd.Series:
        """
        Calculate equal-weighted portfolio returns.

        Args:
            tickers: List of tickers in portfolio
            start_date: Start date
            end_date: End date
            position_type: 'long' or 'short'

        Returns:
            Series of daily portfolio returns
        """
        if not tickers:
            # Return zero returns if no tickers
            return pd.Series(0, index=pd.date_range(start_date, end_date))

        # Fetch returns
        try:
            prices = self.stock_fetcher.fetch_prices(tickers, start_date, end_date)

            if prices.empty:
                return pd.Series(0, index=pd.date_range(start_date, end_date))

            # Calculate returns
            returns = prices.pct_change()

            # Equal weight portfolio
            portfolio_returns = returns.mean(axis=1)

            # Invert for short positions
            if position_type == 'short':
                portfolio_returns = -portfolio_returns

            # Fill NaN with 0
            portfolio_returns = portfolio_returns.fillna(0)

            return portfolio_returns

        except Exception as e:
            warnings.warn(f"Error calculating portfolio returns: {e}")
            return pd.Series(0, index=pd.date_range(start_date, end_date))

    def backtest(self,
                start_year: int,
                end_year: int,
                long_quintile: int = 5,
                short_quintile: int = 1) -> pd.DataFrame:
        """
        Run the backtest.

        Args:
            start_year: First year to start trading
            end_year: Last year to end trading
            long_quintile: Quintile to go long (default 5 = most central)
            short_quintile: Quintile to go short (default 1 = least central)

        Returns:
            DataFrame with daily returns for long, short, and long-short portfolios
        """
        # Get rebalance dates
        rebalance_dates = self.get_rebalance_dates(start_year, end_year)

        # Initialize results
        all_returns = []

        # Iterate through rebalance periods
        for i, rebal_date in enumerate(rebalance_dates[:-1]):
            next_rebal_date = rebalance_dates[i + 1]

            # Get portfolios
            long_tickers = self.get_portfolio_for_date(rebal_date, long_quintile)
            short_tickers = self.get_portfolio_for_date(rebal_date, short_quintile)

            # Store holdings
            self.holdings.append({
                'date': rebal_date,
                'long_tickers': long_tickers,
                'short_tickers': short_tickers,
                'num_long': len(long_tickers),
                'num_short': len(short_tickers)
            })

            # Calculate returns for this period
            long_returns = self.calculate_portfolio_returns(
                long_tickers, rebal_date, next_rebal_date, 'long'
            )
            short_returns = self.calculate_portfolio_returns(
                short_tickers, rebal_date, next_rebal_date, 'short'
            )

            # Combine returns
            period_returns = pd.DataFrame({
                'long': long_returns,
                'short': short_returns,
            })

            # Long-short return (50% long, 50% short)
            period_returns['long_short'] = (
                0.5 * period_returns['long'] +
                0.5 * period_returns['short']
            )

            all_returns.append(period_returns)

        # Concatenate all periods
        returns_df = pd.concat(all_returns)

        # Apply transaction costs at rebalancing dates
        for rebal_date in rebalance_dates:
            if rebal_date in returns_df.index:
                # Subtract transaction costs from all positions
                returns_df.loc[rebal_date, 'long'] -= self.transaction_cost_bps
                returns_df.loc[rebal_date, 'short'] -= self.transaction_cost_bps
                returns_df.loc[rebal_date, 'long_short'] -= self.transaction_cost_bps

        # Fetch benchmark returns
        start_date = rebalance_dates[0]
        end_date = rebalance_dates[-1]
        benchmark_returns = self.stock_fetcher.fetch_benchmark(start_date, end_date)

        # Align benchmark with strategy returns
        returns_df['benchmark'] = benchmark_returns.reindex(returns_df.index).fillna(0)

        self.performance = returns_df
        return returns_df

    def calculate_performance_metrics(self) -> Dict:
        """
        Calculate performance metrics for the backtest.

        Returns:
            Dict with performance metrics
        """
        if self.performance is None:
            raise ValueError("Must run backtest first")

        metrics = {}

        for portfolio in ['long', 'short', 'long_short', 'benchmark']:
            returns = self.performance[portfolio].dropna()

            # Total return
            total_return = (1 + returns).prod() - 1

            # Annualized return
            ann_return = calculate_annualized_return(returns, periods_per_year=252)

            # Annualized volatility
            ann_vol = calculate_annualized_volatility(returns, periods_per_year=252)

            # Sharpe ratio
            sharpe = calculate_sharpe_ratio(returns, RISK_FREE_RATE, periods_per_year=252)

            # Max drawdown
            max_dd = calculate_max_drawdown(returns)

            # Calmar ratio (return / abs(max_drawdown))
            calmar = ann_return / abs(max_dd) if max_dd != 0 else 0

            # Win rate
            win_rate = (returns > 0).sum() / len(returns) if len(returns) > 0 else 0

            metrics[portfolio] = {
                'total_return': total_return,
                'annualized_return': ann_return,
                'annualized_volatility': ann_vol,
                'sharpe_ratio': sharpe,
                'max_drawdown': max_dd,
                'calmar_ratio': calmar,
                'win_rate': win_rate,
            }

        # Calculate alpha (excess return vs benchmark)
        ls_return = metrics['long_short']['annualized_return']
        bm_return = metrics['benchmark']['annualized_return']
        metrics['long_short']['alpha'] = ls_return - bm_return

        # Information ratio (alpha / tracking error)
        tracking_error = (
            self.performance['long_short'] - self.performance['benchmark']
        ).std() * np.sqrt(252)

        if tracking_error > 0:
            metrics['long_short']['information_ratio'] = (
                metrics['long_short']['alpha'] / tracking_error
            )
        else:
            metrics['long_short']['information_ratio'] = 0

        return metrics

    def get_performance_summary(self) -> pd.DataFrame:
        """
        Get a summary table of performance metrics.

        Returns:
            DataFrame with performance metrics for all portfolios
        """
        metrics = self.calculate_performance_metrics()

        # Convert to DataFrame
        df = pd.DataFrame(metrics).T

        # Format percentages
        pct_cols = ['total_return', 'annualized_return', 'annualized_volatility',
                   'max_drawdown', 'win_rate', 'alpha']

        for col in pct_cols:
            if col in df.columns:
                df[col] = df[col] * 100

        return df

    def get_cumulative_returns(self) -> pd.DataFrame:
        """
        Get cumulative returns for all portfolios.

        Returns:
            DataFrame with cumulative returns
        """
        if self.performance is None:
            raise ValueError("Must run backtest first")

        cum_returns = (1 + self.performance).cumprod() - 1
        return cum_returns


def run_backtest(centrality_data: pd.DataFrame,
                start_year: int,
                end_year: int) -> Tuple[pd.DataFrame, Dict]:
    """
    Convenience function to run a backtest.

    Args:
        centrality_data: DataFrame with centrality scores
        start_year: First year to start trading
        end_year: Last year to end trading

    Returns:
        Tuple of (returns DataFrame, metrics dict)
    """
    backtester = BoardCentralityBacktester(centrality_data)
    returns = backtester.backtest(start_year, end_year)
    metrics = backtester.calculate_performance_metrics()

    return returns, metrics
