import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union
import logging
from .database_manager import DatabaseManager


class IndicatorCalculator:
    def __init__(self, db_manager: DatabaseManager):
        """Initialize the indicator calculator.
        
        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.logger = logging.getLogger(__name__)
        
    def calculate_ma(self, symbol: str, period: int, start_date: str, end_date: str) -> pd.DataFrame:
        """Calculate Moving Average.
        
        Args:
            symbol: Symbol to calculate for
            period: MA period
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            
        Returns:
            DataFrame containing MA values
        """
        # Get price data
        df = self.db.get_price_data(symbol, start_date, end_date)
        if df.empty:
            return pd.DataFrame()
            
        # Calculate MA
        df['ma'] = df['close'].rolling(window=period).mean()
        
        # Prepare result
        result = df[['date', 'symbol', 'ma']].copy()
        result = result.rename(columns={'ma': 'indicator_value'})
        
        # Store in database
        params = {'period': period}
        self.db.store_indicator_data(result, 'MA', params)
        
        return result
        
    def calculate_rsi(self, symbol: str, period: int, start_date: str, end_date: str) -> pd.DataFrame:
        """Calculate Relative Strength Index.
        
        Args:
            symbol: Symbol to calculate for
            period: RSI period
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            
        Returns:
            DataFrame containing RSI values
        """
        # Get price data
        df = self.db.get_price_data(symbol, start_date, end_date)
        if df.empty:
            return pd.DataFrame()
            
        # Calculate price changes
        delta = df['close'].diff()
        
        # Calculate gains and losses
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # Calculate RS and RSI
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Prepare result
        result = df[['date', 'symbol', 'rsi']].copy()
        result = result.rename(columns={'rsi': 'indicator_value'})
        
        # Store in database
        params = {'period': period}
        self.db.store_indicator_data(result, 'RSI', params)
        
        return result
        
    def calculate_macd(self, symbol: str, fast_period: int, slow_period: int, 
                      signal_period: int, start_date: str, end_date: str) -> pd.DataFrame:
        """Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            symbol: Symbol to calculate for
            fast_period: Fast EMA period
            slow_period: Slow EMA period
            signal_period: Signal line period
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            
        Returns:
            DataFrame containing MACD values
        """
        # Get price data
        df = self.db.get_price_data(symbol, start_date, end_date)
        if df.empty:
            return pd.DataFrame()
            
        # Calculate EMAs
        exp1 = df['close'].ewm(span=fast_period, adjust=False).mean()
        exp2 = df['close'].ewm(span=slow_period, adjust=False).mean()
        
        # Calculate MACD line and signal line
        macd = exp1 - exp2
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        
        # Calculate histogram
        df['macd'] = macd
        df['signal'] = signal
        df['histogram'] = macd - signal
        
        # Store MACD line
        macd_result = df[['date', 'symbol', 'macd']].copy()
        macd_result = macd_result.rename(columns={'macd': 'indicator_value'})
        params = {
            'fast_period': fast_period,
            'slow_period': slow_period,
            'signal_period': signal_period,
            'type': 'macd_line'
        }
        self.db.store_indicator_data(macd_result, 'MACD', params)
        
        # Store signal line
        signal_result = df[['date', 'symbol', 'signal']].copy()
        signal_result = signal_result.rename(columns={'signal': 'indicator_value'})
        params['type'] = 'signal_line'
        self.db.store_indicator_data(signal_result, 'MACD', params)
        
        # Store histogram
        hist_result = df[['date', 'symbol', 'histogram']].copy()
        hist_result = hist_result.rename(columns={'histogram': 'indicator_value'})
        params['type'] = 'histogram'
        self.db.store_indicator_data(hist_result, 'MACD', params)
        
        return df[['date', 'symbol', 'macd', 'signal', 'histogram']]
        
    def calculate_bollinger_bands(self, symbol: str, period: int, num_std: float,
                                start_date: str, end_date: str) -> pd.DataFrame:
        """Calculate Bollinger Bands.
        
        Args:
            symbol: Symbol to calculate for
            period: MA period
            num_std: Number of standard deviations
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
            
        Returns:
            DataFrame containing Bollinger Bands values
        """
        # Get price data
        df = self.db.get_price_data(symbol, start_date, end_date)
        if df.empty:
            return pd.DataFrame()
            
        # Calculate middle band (SMA)
        df['middle_band'] = df['close'].rolling(window=period).mean()
        
        # Calculate standard deviation
        std = df['close'].rolling(window=period).std()
        
        # Calculate upper and lower bands
        df['upper_band'] = df['middle_band'] + (std * num_std)
        df['lower_band'] = df['middle_band'] - (std * num_std)
        
        # Store middle band
        middle_result = df[['date', 'symbol', 'middle_band']].copy()
        middle_result = middle_result.rename(columns={'middle_band': 'indicator_value'})
        params = {
            'period': period,
            'num_std': num_std,
            'type': 'middle_band'
        }
        self.db.store_indicator_data(middle_result, 'BollingerBands', params)
        
        # Store upper band
        upper_result = df[['date', 'symbol', 'upper_band']].copy()
        upper_result = upper_result.rename(columns={'upper_band': 'indicator_value'})
        params['type'] = 'upper_band'
        self.db.store_indicator_data(upper_result, 'BollingerBands', params)
        
        # Store lower band
        lower_result = df[['date', 'symbol', 'lower_band']].copy()
        lower_result = lower_result.rename(columns={'lower_band': 'indicator_value'})
        params['type'] = 'lower_band'
        self.db.store_indicator_data(lower_result, 'BollingerBands', params)
        
        return df[['date', 'symbol', 'middle_band', 'upper_band', 'lower_band']] 