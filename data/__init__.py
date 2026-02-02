"""Data collection module for board network analyzer."""

from .sec_collector import SECCollector, collect_board_data_for_tickers

__all__ = [
    'SECCollector',
    'collect_board_data_for_tickers',
]
