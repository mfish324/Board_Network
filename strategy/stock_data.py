"""
Stock data fetcher using yfinance.

Fetches historical stock prices and calculates returns for backtesting.
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import List, Optional, Union
from datetime import datetime, timedelta
import warnings

from config import BENCHMARK_TICKER


class StockDataFetcher:
    """
    Fetches and manages stock price data for backtesting.

    Features:
    - Downloads adjusted close prices from Yahoo Finance
    - Calculates daily/monthly returns
    - Handles missing data and delistings
    - Fetches benchmark data for comparison
    """

    def __init__(self):
        """Initialize the stock data fetcher."""
        self.price_data = None
        self.returns_data = None
        self.benchmark_data = None

    def fetch_prices(self,
                    tickers: List[str],
                    start_date: Union[str, datetime],
                    end_date: Union[str, datetime],
                    auto_adjust: bool = True) -> pd.DataFrame:
        """
        Fetch historical adjusted close prices for multiple tickers.

        Args:
            tickers: List of stock ticker symbols
            start_date: Start date (YYYY-MM-DD or datetime)
            end_date: End date (YYYY-MM-DD or datetime)
            auto_adjust: Use adjusted prices (accounts for splits, dividends)

        Returns:
            DataFrame with dates as index and tickers as columns
        """
        # Convert dates to strings if needed
        if isinstance(start_date, datetime):
            start_date = start_date.strftime('%Y-%m-%d')
        if isinstance(end_date, datetime):
            end_date = end_date.strftime('%Y-%m-%d')

        # Download data
        try:
            data = yf.download(
                tickers,
                start=start_date,
                end=end_date,
                auto_adjust=auto_adjust,
                progress=False,
                show_errors=False
            )

            # Extract adjusted close prices
            if len(tickers) == 1:
                # yfinance returns Series for single ticker
                prices = data['Close'].to_frame()
                prices.columns = [tickers[0]]
            else:
                # Multiple tickers
                if 'Adj Close' in data.columns:
                    prices = data['Adj Close']
                elif 'Close' in data.columns.get_level_values(0):
                    prices = data['Close']
                else:
                    prices = data

            self.price_data = prices
            return prices

        except Exception as e:
            warnings.warn(f"Error fetching price data: {e}")
            return pd.DataFrame()

    def calculate_returns(self,
                         prices: Optional[pd.DataFrame] = None,
                         frequency: str = 'daily') -> pd.DataFrame:
        """
        Calculate returns from price data.

        Args:
            prices: Price DataFrame (uses stored data if None)
            frequency: 'daily' or 'monthly'

        Returns:
            DataFrame of returns
        """
        if prices is None:
            prices = self.price_data

        if prices is None or prices.empty:
            raise ValueError("No price data available")

        # Resample if monthly
        if frequency == 'monthly':
            prices = prices.resample('M').last()

        # Calculate returns
        returns = prices.pct_change()

        self.returns_data = returns
        return returns

    def fetch_benchmark(self,
                       start_date: Union[str, datetime],
                       end_date: Union[str, datetime],
                       ticker: str = BENCHMARK_TICKER) -> pd.DataFrame:
        """
        Fetch benchmark returns (default: SPY).

        Args:
            start_date: Start date
            end_date: End date
            ticker: Benchmark ticker symbol

        Returns:
            DataFrame with benchmark returns
        """
        # Convert dates to strings if needed
        if isinstance(start_date, datetime):
            start_date = start_date.strftime('%Y-%m-%d')
        if isinstance(end_date, datetime):
            end_date = end_date.strftime('%Y-%m-%d')

        # Fetch benchmark data
        benchmark = yf.download(
            ticker,
            start=start_date,
            end=end_date,
            auto_adjust=True,
            progress=False,
            show_errors=False
        )

        if benchmark.empty:
            warnings.warn(f"Could not fetch benchmark data for {ticker}")
            return pd.DataFrame()

        # Extract close price and calculate returns
        if 'Close' in benchmark.columns:
            benchmark_prices = benchmark['Close']
        else:
            benchmark_prices = benchmark

        benchmark_returns = benchmark_prices.pct_change()
        benchmark_returns.name = ticker

        self.benchmark_data = benchmark_returns
        return benchmark_returns

    def get_valid_tickers(self,
                         tickers: List[str],
                         start_date: Union[str, datetime],
                         end_date: Union[str, datetime],
                         min_data_points: int = 100) -> List[str]:
        """
        Filter tickers to only include those with sufficient data.

        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date
            min_data_points: Minimum number of valid price points

        Returns:
            List of valid ticker symbols
        """
        prices = self.fetch_prices(tickers, start_date, end_date)

        if prices.empty:
            return []

        # Check data availability for each ticker
        valid_tickers = []
        for ticker in tickers:
            if ticker in prices.columns:
                non_null_count = prices[ticker].notna().sum()
                if non_null_count >= min_data_points:
                    valid_tickers.append(ticker)

        return valid_tickers

    def forward_fill_prices(self,
                          prices: Optional[pd.DataFrame] = None,
                          limit: int = 5) -> pd.DataFrame:
        """
        Forward fill missing prices (e.g., non-trading days).

        Args:
            prices: Price DataFrame (uses stored data if None)
            limit: Maximum number of consecutive NaNs to fill

        Returns:
            DataFrame with filled prices
        """
        if prices is None:
            prices = self.price_data

        if prices is None or prices.empty:
            raise ValueError("No price data available")

        filled = prices.fillna(method='ffill', limit=limit)
        return filled

    def get_returns_for_period(self,
                              tickers: List[str],
                              start_date: Union[str, datetime],
                              end_date: Union[str, datetime],
                              frequency: str = 'daily') -> pd.DataFrame:
        """
        Convenience method to fetch prices and calculate returns.

        Args:
            tickers: List of ticker symbols
            start_date: Start date
            end_date: End date
            frequency: 'daily' or 'monthly'

        Returns:
            DataFrame of returns
        """
        prices = self.fetch_prices(tickers, start_date, end_date)
        returns = self.calculate_returns(prices, frequency)
        return returns


def fetch_stock_returns(tickers: List[str],
                       start_date: Union[str, datetime],
                       end_date: Union[str, datetime],
                       frequency: str = 'daily') -> pd.DataFrame:
    """
    Convenience function to fetch stock returns.

    Args:
        tickers: List of ticker symbols
        start_date: Start date
        end_date: End date
        frequency: 'daily' or 'monthly'

    Returns:
        DataFrame of returns
    """
    fetcher = StockDataFetcher()
    return fetcher.get_returns_for_period(tickers, start_date, end_date, frequency)


def calculate_cumulative_returns(returns: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate cumulative returns from periodic returns.

    Args:
        returns: DataFrame of periodic returns

    Returns:
        DataFrame of cumulative returns
    """
    return (1 + returns).cumprod() - 1


def calculate_annualized_return(returns: pd.Series,
                               periods_per_year: int = 252) -> float:
    """
    Calculate annualized return from periodic returns.

    Args:
        returns: Series of periodic returns
        periods_per_year: Number of periods per year (252 for daily, 12 for monthly)

    Returns:
        Annualized return
    """
    total_return = (1 + returns).prod() - 1
    num_periods = len(returns)
    years = num_periods / periods_per_year

    if years > 0:
        annualized = (1 + total_return) ** (1 / years) - 1
    else:
        annualized = 0

    return annualized


def calculate_annualized_volatility(returns: pd.Series,
                                   periods_per_year: int = 252) -> float:
    """
    Calculate annualized volatility from periodic returns.

    Args:
        returns: Series of periodic returns
        periods_per_year: Number of periods per year

    Returns:
        Annualized volatility
    """
    return returns.std() * np.sqrt(periods_per_year)


def calculate_sharpe_ratio(returns: pd.Series,
                          risk_free_rate: float = 0.02,
                          periods_per_year: int = 252) -> float:
    """
    Calculate Sharpe ratio.

    Args:
        returns: Series of periodic returns
        risk_free_rate: Annual risk-free rate
        periods_per_year: Number of periods per year

    Returns:
        Sharpe ratio
    """
    ann_return = calculate_annualized_return(returns, periods_per_year)
    ann_vol = calculate_annualized_volatility(returns, periods_per_year)

    if ann_vol > 0:
        sharpe = (ann_return - risk_free_rate) / ann_vol
    else:
        sharpe = 0

    return sharpe


def calculate_max_drawdown(returns: pd.Series) -> float:
    """
    Calculate maximum drawdown.

    Args:
        returns: Series of periodic returns

    Returns:
        Maximum drawdown (as negative decimal, e.g., -0.25 for 25% drawdown)
    """
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max
    max_dd = drawdown.min()

    return max_dd
