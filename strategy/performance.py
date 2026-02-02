"""
Performance analysis utilities.

Additional performance metrics and analysis tools.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional


def calculate_rolling_sharpe(returns: pd.Series,
                             window: int = 252,
                             risk_free_rate: float = 0.02) -> pd.Series:
    """
    Calculate rolling Sharpe ratio.

    Args:
        returns: Series of returns
        window: Rolling window size (default 252 = 1 year of daily returns)
        risk_free_rate: Annual risk-free rate

    Returns:
        Series of rolling Sharpe ratios
    """
    # Annualized rolling return
    rolling_return = returns.rolling(window).mean() * 252

    # Annualized rolling volatility
    rolling_vol = returns.rolling(window).std() * np.sqrt(252)

    # Rolling Sharpe
    rolling_sharpe = (rolling_return - risk_free_rate) / rolling_vol

    return rolling_sharpe


def calculate_drawdown_series(returns: pd.Series) -> pd.Series:
    """
    Calculate drawdown series.

    Args:
        returns: Series of returns

    Returns:
        Series of drawdowns (as negative decimals)
    """
    cumulative = (1 + returns).cumprod()
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max

    return drawdown


def calculate_recovery_time(returns: pd.Series) -> int:
    """
    Calculate time to recover from maximum drawdown.

    Args:
        returns: Series of returns

    Returns:
        Number of periods to recover (0 if not recovered)
    """
    drawdown = calculate_drawdown_series(returns)
    max_dd_idx = drawdown.idxmin()

    # Find when drawdown returns to 0 after max drawdown
    after_max = drawdown.loc[max_dd_idx:]
    recovery = after_max[after_max >= 0]

    if len(recovery) > 0:
        recovery_idx = recovery.index[0]
        recovery_time = len(after_max.loc[:recovery_idx])
        return recovery_time
    else:
        return 0  # Not recovered


def calculate_sortino_ratio(returns: pd.Series,
                            risk_free_rate: float = 0.02,
                            periods_per_year: int = 252) -> float:
    """
    Calculate Sortino ratio (uses downside deviation instead of total volatility).

    Args:
        returns: Series of returns
        risk_free_rate: Annual risk-free rate
        periods_per_year: Number of periods per year

    Returns:
        Sortino ratio
    """
    # Annualized return
    ann_return = returns.mean() * periods_per_year

    # Downside deviation (only negative returns)
    downside_returns = returns[returns < 0]
    downside_std = downside_returns.std() * np.sqrt(periods_per_year)

    if downside_std > 0:
        sortino = (ann_return - risk_free_rate) / downside_std
    else:
        sortino = 0

    return sortino


def calculate_var(returns: pd.Series, confidence: float = 0.05) -> float:
    """
    Calculate Value at Risk (VaR).

    Args:
        returns: Series of returns
        confidence: Confidence level (default 0.05 = 95% VaR)

    Returns:
        VaR (as negative decimal)
    """
    return returns.quantile(confidence)


def calculate_cvar(returns: pd.Series, confidence: float = 0.05) -> float:
    """
    Calculate Conditional Value at Risk (CVaR / Expected Shortfall).

    Args:
        returns: Series of returns
        confidence: Confidence level

    Returns:
        CVaR (as negative decimal)
    """
    var = calculate_var(returns, confidence)
    cvar = returns[returns <= var].mean()
    return cvar


def calculate_ulcer_index(returns: pd.Series) -> float:
    """
    Calculate Ulcer Index (measure of downside volatility).

    Args:
        returns: Series of returns

    Returns:
        Ulcer Index
    """
    drawdown = calculate_drawdown_series(returns)
    ulcer = np.sqrt((drawdown ** 2).mean())
    return ulcer


def quintile_performance_comparison(backtest_results: pd.DataFrame,
                                   centrality_data: pd.DataFrame) -> pd.DataFrame:
    """
    Compare performance across all quintiles.

    Args:
        backtest_results: DataFrame with backtest returns
        centrality_data: DataFrame with centrality scores by quintile

    Returns:
        DataFrame with performance by quintile
    """
    # This would require running backtests for all quintiles
    # Placeholder for now
    pass


def calculate_monthly_returns(daily_returns: pd.Series) -> pd.Series:
    """
    Convert daily returns to monthly returns.

    Args:
        daily_returns: Series of daily returns

    Returns:
        Series of monthly returns
    """
    # Compound daily returns to get monthly
    monthly = (1 + daily_returns).resample('M').prod() - 1
    return monthly


def calculate_yearly_returns(daily_returns: pd.Series) -> pd.Series:
    """
    Convert daily returns to yearly returns.

    Args:
        daily_returns: Series of daily returns

    Returns:
        Series of yearly returns
    """
    # Compound daily returns to get yearly
    yearly = (1 + daily_returns).resample('Y').prod() - 1
    return yearly


def performance_attribution(portfolio_returns: pd.Series,
                           benchmark_returns: pd.Series) -> Dict:
    """
    Perform performance attribution vs benchmark.

    Args:
        portfolio_returns: Portfolio return series
        benchmark_returns: Benchmark return series

    Returns:
        Dict with attribution metrics
    """
    # Align series
    aligned = pd.DataFrame({
        'portfolio': portfolio_returns,
        'benchmark': benchmark_returns
    }).dropna()

    # Active return
    active_return = aligned['portfolio'] - aligned['benchmark']

    # Annualized metrics
    portfolio_ann = aligned['portfolio'].mean() * 252
    benchmark_ann = aligned['benchmark'].mean() * 252
    active_ann = active_return.mean() * 252

    # Tracking error
    tracking_error = active_return.std() * np.sqrt(252)

    # Information ratio
    if tracking_error > 0:
        information_ratio = active_ann / tracking_error
    else:
        information_ratio = 0

    # Beta
    covariance = np.cov(aligned['portfolio'], aligned['benchmark'])[0, 1]
    benchmark_var = aligned['benchmark'].var()
    beta = covariance / benchmark_var if benchmark_var > 0 else 1

    # Alpha (Jensen's alpha)
    risk_free_daily = 0.02 / 252
    alpha = (
        aligned['portfolio'].mean() - risk_free_daily -
        beta * (aligned['benchmark'].mean() - risk_free_daily)
    ) * 252

    return {
        'portfolio_return': portfolio_ann,
        'benchmark_return': benchmark_ann,
        'active_return': active_ann,
        'tracking_error': tracking_error,
        'information_ratio': information_ratio,
        'beta': beta,
        'alpha': alpha,
    }
