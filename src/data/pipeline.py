#!/usr/bin/env python3
import logging
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime
import json
from data.akshare_collector import AkShareCollector
from data.database_manager import DatabaseManager
from data.indicator_calculator import IndicatorCalculator
from config_manager import ConfigManager


class DataPipeline:
    def __init__(self, config_path: str = "src/config.json"):
        """Initialize the data pipeline.
        
        Args:
            config_path: Path to the configuration file
        """
        self.logger = logging.getLogger(__name__)
        self.config_manager = ConfigManager(config_path)
        self.db_manager = DatabaseManager(self.config_manager)
        self.collector = AkShareCollector(self.config_manager)
        self.calculator = IndicatorCalculator(self.db_manager)
        
    def update_data(self, symbol: Optional[str] = None) -> None:
        """Update data according to configuration.
        
        Args:
            symbol: Optional symbol to update. If None, updates all ETFs.
        """
        try:
            # Get date range from config
            date_range = self.config_manager.get_date_range()
            
            # Get ETFs to update
            etf_symbols = self.config_manager.get_etf_symbols()
            if symbol:
                if symbol not in etf_symbols:
                    raise ValueError(f"Symbol {symbol} not found in configuration")
                etf_symbols = [symbol]
            
            # Update data for each ETF
            for symbol in etf_symbols:
                self.logger.info(f"Updating data for {symbol}")
                
                # Collect price data
                price_data = self.collector.collect_data()
                
                if not price_data.empty:
                    # Store price data
                    self.db_manager.store_price_data(price_data)
                    
                    # Calculate and store indicators
                    self._calculate_indicators(symbol, date_range.start_date, date_range.end_date)
                else:
                    self.logger.warning(f"No price data collected for {symbol}")
                    
        except Exception as e:
            self.logger.error(f"Error updating data: {str(e)}")
            raise
        finally:
            self.db_manager.close()
            
    def _calculate_indicators(self, symbol: str, start_date: str, end_date: str) -> None:
        """Calculate technical indicators for a symbol.
        
        Args:
            symbol: Symbol to calculate indicators for
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format
        """
        try:
            # Get indicator parameters from config
            indicators = self.config_manager.get_technical_indicators()
            
            # Calculate each indicator
            if 'ma' in indicators:
                for period in indicators['ma']['periods']:
                    self.calculator.calculate_ma(symbol, period, start_date, end_date)
                    
            if 'rsi' in indicators:
                for period in indicators['rsi']['periods']:
                    self.calculator.calculate_rsi(symbol, period, start_date, end_date)
                    
            if 'macd' in indicators:
                params = indicators['macd']
                self.calculator.calculate_macd(
                    symbol,
                    params['fast_period'],
                    params['slow_period'],
                    params['signal_period'],
                    start_date,
                    end_date
                )
                
            if 'bollinger_bands' in indicators:
                params = indicators['bollinger_bands']
                self.calculator.calculate_bollinger_bands(
                    symbol,
                    params['period'],
                    params['num_std'],
                    start_date,
                    end_date
                )
                
        except Exception as e:
            self.logger.error(f"Error calculating indicators for {symbol}: {str(e)}")
            raise
            
    def validate_data(self, symbol: Optional[str] = None) -> Dict[str, List[str]]:
        """Validate the collected data.
        
        Args:
            symbol: Optional symbol to validate. If None, validates all ETFs.
            
        Returns:
            Dictionary containing validation results
        """
        validation_results = {}
        
        try:
            # Get validation rules from config
            rules = self.config_manager.get_validation_rules()
            
            # Get ETFs to validate
            etf_symbols = self.config_manager.get_etf_symbols()
            if symbol:
                if symbol not in etf_symbols:
                    raise ValueError(f"Symbol {symbol} not found in configuration")
                etf_symbols = [symbol]
            
            for symbol in etf_symbols:
                validation_results[symbol] = []
                
                # Get price data
                date_range = self.config_manager.get_date_range()
                price_data = self.db_manager.get_price_data(
                    symbol,
                    date_range.start_date,
                    date_range.end_date
                )
                
                if price_data.empty:
                    validation_results[symbol].append("No price data available")
                    continue
                    
                # Check for missing values
                missing_values = price_data.isnull().sum()
                if missing_values.any():
                    validation_results[symbol].append(
                        f"Missing values found: {missing_values[missing_values > 0].to_dict()}"
                    )
                    
                # Check for price anomalies
                if 'price_anomaly_threshold' in rules:
                    threshold = rules['price_anomaly_threshold']
                    price_changes = price_data['close'].pct_change().abs()
                    anomalies = price_changes[price_changes > threshold]
                    if not anomalies.empty:
                        validation_results[symbol].append(
                            f"Price anomalies found on dates: {anomalies.index.tolist()}"
                        )
                        
                # Check for volume anomalies
                if 'volume_anomaly_threshold' in rules:
                    threshold = rules['volume_anomaly_threshold']
                    volume_changes = price_data['volume'].pct_change().abs()
                    anomalies = volume_changes[volume_changes > threshold]
                    if not anomalies.empty:
                        validation_results[symbol].append(
                            f"Volume anomalies found on dates: {anomalies.index.tolist()}"
                        )
                        
        except Exception as e:
            self.logger.error(f"Error validating data: {str(e)}")
            raise
            
        return validation_results
        
    def get_status(self) -> Dict[str, Dict]:
        """Get the status of the pipeline.
        
        Returns:
            Dictionary containing status information for each ETF
        """
        status = {}
        
        try:
            for symbol in self.config_manager.get_etf_symbols():
                status[symbol] = {
                    'last_update': None,
                    'data_points': 0,
                    'indicators': {}
                }
                
                # Get latest price data
                date_range = self.config_manager.get_date_range()
                price_data = self.db_manager.get_price_data(
                    symbol,
                    date_range.start_date,
                    date_range.end_date
                )
                
                if not price_data.empty:
                    status[symbol]['last_update'] = price_data['date'].max()
                    status[symbol]['data_points'] = len(price_data)
                    
                    # Get indicator status
                    indicators = self.config_manager.get_technical_indicators()
                    for indicator_name in indicators:
                        indicator_data = self.db_manager.get_indicator_data(
                            symbol,
                            indicator_name,
                            {},
                            date_range.start_date,
                            date_range.end_date
                        )
                        status[symbol]['indicators'][indicator_name] = len(indicator_data)
                        
        except Exception as e:
            self.logger.error(f"Error getting status: {str(e)}")
            raise
            
        return status 