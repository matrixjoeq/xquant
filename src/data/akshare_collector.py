#!/usr/bin/env python3
import akshare as ak
import pandas as pd
import sqlite3
from typing import Dict, List, Optional
from datetime import datetime
import logging
from pathlib import Path
import time
import random
from fake_useragent import UserAgent
import requests
from config_manager import ConfigManager


class AkShareCollector:
    def __init__(self, config_manager: ConfigManager):
        """Initialize the AkShare data collector.

        Args:
            config_manager: Configuration manager instance
        """
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        self._setup_database()

        # Anti-crawler settings
        self.min_delay = 3  # Minimum delay between requests in seconds
        self.max_delay = 7  # Maximum delay between requests in seconds
        self.max_retries = 3  # Maximum number of retries for failed requests
        self.retry_delay = 10  # Delay between retries in seconds

        # Initialize fake user agent
        try:
            self.user_agent = UserAgent()
        except Exception as e:
            self.logger.warning(f"Failed to initialize UserAgent: {str(e)}")
            self.user_agent = None

    def _setup_database(self) -> None:
        """Set up the SQLite database connection and create tables if they don't exist."""
        db_path = Path(self.config.get_database_url().replace('sqlite:///', ''))
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self) -> None:
        """Create database tables based on the schema configuration."""
        schema = self.config.get_database_schema('daily_prices')
        if not schema:
            raise ValueError("Daily prices schema not found in configuration")

        columns = []
        for col, dtype in schema.dtypes.items():
            if dtype == 'INTEGER PRIMARY KEY AUTOINCREMENT':
                columns.append(f"{col} {dtype}")
            else:
                columns.append(f"{col} {dtype.replace('datetime64[ns]', 'TEXT')}")

        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS daily_prices (
            {', '.join(columns)}
        )
        """

        self.conn.execute(create_table_sql)
        self.conn.commit()

    def _random_delay(self) -> None:
        """Add a random delay between requests to avoid being blocked."""
        delay = random.uniform(self.min_delay, self.max_delay)
        self.logger.debug(f"Waiting for {delay:.2f} seconds...")
        time.sleep(delay)

    def _get_random_user_agent(self) -> str:
        """Get a random user agent string.

        Returns:
            str: Random user agent string
        """
        if self.user_agent:
            return self.user_agent.random
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"

    def _fetch_etf_data(self, symbol: str, price_type: str) -> Optional[pd.DataFrame]:
        """Fetch ETF data from AkShare with retry mechanism.

        Args:
            symbol: ETF symbol
            price_type: Type of price data to fetch

        Returns:
            DataFrame containing the ETF data or None if fetch fails
        """
        for attempt in range(self.max_retries):
            try:
                # Add random delay before each request
                self._random_delay()

                # Set random user agent for this request
                headers = {
                    'User-Agent': self._get_random_user_agent(),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Connection': 'keep-alive',
                }

                # Map price type to AkShare function parameter
                price_type_map = {
                    'non_restored': 'qfq',
                    'forward_restored': 'qfq',
                    'backward_restored': 'hfq'
                }

                # Set custom headers for AkShare session
                session = requests.Session()
                session.headers.update(headers)

                # Fetch data using East Money (with adjust parameter for different restorations)
                df = ak.fund_etf_hist_em(symbol=symbol, adjust=price_type_map[price_type])

                # Rename columns according to configuration
                df = df.rename(columns=self.config.get_column_mapping())

                # Add metadata columns
                df['symbol'] = symbol
                df['price_type'] = price_type

                return df

            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1}/{self.max_retries} failed for {symbol} ({price_type}): {str(e)}")
                if attempt < self.max_retries - 1:
                    self.logger.info(f"Retrying in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                else:
                    self.logger.error(f"All attempts failed for {symbol} ({price_type})")
                    return None

    def _validate_data(self, df: pd.DataFrame) -> bool:
        """Validate the fetched data against configuration rules.

        Args:
            df: DataFrame to validate

        Returns:
            bool: True if data is valid, False otherwise
        """
        # Check required columns
        required_cols = self.config.get_required_columns()
        if not all(col in df.columns for col in required_cols):
            self.logger.error(f"Missing required columns: {set(required_cols) - set(df.columns)}")
            return False

        # Check non-null columns
        non_null_cols = self.config.get_non_null_columns()
        if df[non_null_cols].isnull().any().any():
            self.logger.error("Found null values in non-null columns")
            return False

        return True

    def _store_data(self, df: pd.DataFrame) -> None:
        """Store the validated data in the database.

        Args:
            df: DataFrame to store
        """
        try:
            df.to_sql('daily_prices', self.conn, if_exists='append', index=False)
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Error storing data: {str(e)}")
            self.conn.rollback()

    def collect_data(self) -> pd.DataFrame:
        """Collect data for all configured ETFs and price types.
        
        Returns:
            DataFrame containing all collected data
        """
        etf_symbols = self.config.get_etf_symbols()
        price_types = self.config.get_price_types()
        date_range = self.config.get_date_range()
        all_data = []

        self.logger.info(f"Starting data collection for {len(etf_symbols)} ETFs")
        self.logger.info(f"Date range: {date_range.start_date} to {date_range.end_date}")

        for symbol in etf_symbols:
            etf_info = self.config.get_etf_info(symbol)
            self.logger.info(f"Processing {symbol} ({etf_info.name})")

            for price_type in price_types:
                self.logger.info(f"Fetching {price_type} data")

                # Fetch data
                df = self._fetch_etf_data(symbol, price_type)
                if df is None:
                    continue

                # Filter by date range
                df['date'] = pd.to_datetime(df['date'])
                mask = (df['date'] >= pd.to_datetime(date_range.start_date)) & \
                       (df['date'] <= pd.to_datetime(date_range.end_date))
                df = df[mask]

                # Validate data
                if not self._validate_data(df):
                    self.logger.error(f"Data validation failed for {symbol} ({price_type})")
                    continue

                # Store data
                self._store_data(df)
                self.logger.info(f"Successfully stored {len(df)} records for {symbol} ({price_type})")
                
                # Add to collected data
                all_data.append(df)

        self.logger.info("Data collection completed")
        
        # Combine all collected data
        if all_data:
            return pd.concat(all_data, ignore_index=True)
        else:
            return pd.DataFrame()  # Return empty DataFrame if no data was collected

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self, 'conn'):
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()