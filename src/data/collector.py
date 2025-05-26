from typing import List, Dict, Optional, Union
import logging
from datetime import datetime, timedelta

import akshare as ak
import tushare as ts
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from ..config import DATA_CONFIG, API_CONFIG

logger = logging.getLogger(__name__)

class DataCollector:
    """Data collector for fetching market data from TuShare and AKShare."""
    
    def __init__(self, db_url: str, tushare_token: Optional[str] = None):
        """
        Initialize the data collector.
        
        Args:
            db_url: SQLAlchemy database URL
            tushare_token: TuShare API token (optional)
        """
        self.engine = create_engine(db_url)
        if tushare_token:
            ts.set_token(tushare_token)
            self.pro = ts.pro_api()
        else:
            self.pro = None
            logger.warning("TuShare token not provided. Some data sources may be limited.")
    
    def collect_daily_data(self, 
                          symbols: List[str], 
                          start_date: Union[str, datetime],
                          end_date: Union[str, datetime]) -> pd.DataFrame:
        """
        Collect daily price data for given symbols.
        
        Args:
            symbols: List of stock symbols
            start_date: Start date for data collection
            end_date: End date for data collection
            
        Returns:
            DataFrame containing daily price data
        """
        all_data = []
        
        for symbol in symbols:
            try:
                # Try TuShare first if available
                if self.pro:
                    df = self.pro.daily(ts_code=symbol, 
                                      start_date=start_date,
                                      end_date=end_date)
                    if not df.empty:
                        df['symbol'] = symbol
                        all_data.append(df)
                        continue
                
                # Fallback to AKShare
                df = ak.stock_zh_a_hist(symbol=symbol,
                                      start_date=start_date,
                                      end_date=end_date,
                                      adjust="qfq")
                if not df.empty:
                    df['symbol'] = symbol
                    all_data.append(df)
                    
            except Exception as e:
                logger.error(f"Error collecting daily data for {symbol}: {str(e)}")
                continue
        
        if not all_data:
            return pd.DataFrame(columns=DATA_CONFIG['daily_data']['columns'])
        
        combined_data = pd.concat(all_data, ignore_index=True)
        return self._standardize_daily_data(combined_data)
    
    def collect_fundamental_data(self, 
                               symbols: List[str], 
                               date: Optional[Union[str, datetime]] = None) -> pd.DataFrame:
        """
        Collect fundamental data for given symbols.
        
        Args:
            symbols: List of stock symbols
            date: Specific date for fundamental data (optional)
            
        Returns:
            DataFrame containing fundamental data
        """
        all_data = []
        
        for symbol in symbols:
            try:
                # Try TuShare first if available
                if self.pro:
                    df = self.pro.daily_basic(ts_code=symbol, 
                                            trade_date=date)
                    if not df.empty:
                        df['symbol'] = symbol
                        all_data.append(df)
                        continue
                
                # Fallback to AKShare
                df = ak.stock_a_lg_indicator(symbol=symbol)
                if not df.empty:
                    df['symbol'] = symbol
                    all_data.append(df)
                    
            except Exception as e:
                logger.error(f"Error collecting fundamental data for {symbol}: {str(e)}")
                continue
        
        if not all_data:
            return pd.DataFrame(columns=DATA_CONFIG['fundamental_data']['columns'])
        
        combined_data = pd.concat(all_data, ignore_index=True)
        return self._standardize_fundamental_data(combined_data)
    
    def collect_technical_indicators(self, 
                                   symbols: List[str],
                                   indicators: List[str],
                                   start_date: Union[str, datetime],
                                   end_date: Union[str, datetime]) -> pd.DataFrame:
        """
        Calculate technical indicators for given symbols.
        
        Args:
            symbols: List of stock symbols
            indicators: List of technical indicators to calculate
            start_date: Start date for calculation
            end_date: End date for calculation
            
        Returns:
            DataFrame containing technical indicators
        """
        all_data = []
        
        for symbol in symbols:
            try:
                # Get daily data first
                daily_data = self.collect_daily_data([symbol], start_date, end_date)
                if daily_data.empty:
                    continue
                
                # Calculate indicators
                for indicator in indicators:
                    indicator_data = self._calculate_indicator(daily_data, indicator)
                    if not indicator_data.empty:
                        indicator_data['symbol'] = symbol
                        indicator_data['indicator_name'] = indicator
                        all_data.append(indicator_data)
                    
            except Exception as e:
                logger.error(f"Error calculating indicators for {symbol}: {str(e)}")
                continue
        
        if not all_data:
            return pd.DataFrame(columns=DATA_CONFIG['technical_indicators']['columns'])
        
        combined_data = pd.concat(all_data, ignore_index=True)
        return self._standardize_technical_data(combined_data)
    
    def store_data(self, 
                  data: pd.DataFrame, 
                  table_name: str,
                  if_exists: str = 'append') -> None:
        """
        Store data in the database.
        
        Args:
            data: DataFrame to store
            table_name: Name of the table to store data in
            if_exists: How to behave if the table already exists
        """
        if self.validate_data(data):
            data.to_sql(table_name, self.engine, if_exists=if_exists, index=False)
            logger.info(f"Stored {len(data)} rows in {table_name}")
        else:
            logger.error(f"Data validation failed for {table_name}")
    
    def validate_data(self, data: pd.DataFrame) -> bool:
        """
        Validate the collected data.
        
        Args:
            data: DataFrame to validate
            
        Returns:
            bool indicating if data is valid
        """
        if data.empty:
            logger.warning("Empty DataFrame received")
            return False
        
        # Check for required columns
        required_columns = set()
        for config in DATA_CONFIG.values():
            required_columns.update(config['columns'])
        
        missing_columns = required_columns - set(data.columns)
        if missing_columns:
            logger.error(f"Missing required columns: {missing_columns}")
            return False
        
        # Check for null values in critical columns
        critical_columns = ['symbol', 'date']
        if any(data[col].isnull().any() for col in critical_columns):
            logger.error("Null values found in critical columns")
            return False
        
        return True
    
    def _standardize_daily_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Standardize daily data format."""
        # Implementation will be added
        return data
    
    def _standardize_fundamental_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Standardize fundamental data format."""
        # Implementation will be added
        return data
    
    def _standardize_technical_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """Standardize technical indicator data format."""
        # Implementation will be added
        return data
    
    def _calculate_indicator(self, data: pd.DataFrame, indicator: str) -> pd.DataFrame:
        """Calculate a specific technical indicator."""
        # Implementation will be added
        return pd.DataFrame() 