import sqlite3
from typing import Dict, List, Optional
import pandas as pd
from pathlib import Path
import logging
from src.config_manager import ConfigManager


class DatabaseManager:
    def __init__(self, config_manager: ConfigManager):
        """Initialize the database manager.

        Args:
            config_manager: Configuration manager instance
        """
        self.config = config_manager
        self.logger = logging.getLogger(__name__)
        self._setup_database()

    def _drop_existing_tables(self) -> None:
        """Drop existing tables to ensure a clean database state."""
        self.conn.execute("DROP TABLE IF EXISTS daily_prices")
        self.conn.execute("DROP TABLE IF EXISTS technical_indicators")
        self.conn.commit()

    def _setup_database(self) -> None:
        """Set up the SQLite database connection and create tables if they don't exist."""
        db_path = Path(self.config.get_database_url().replace('sqlite:///', ''))
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = sqlite3.connect(db_path)
        self._drop_existing_tables()  # Drop existing tables before creating new ones
        self._create_tables()

    def _create_tables(self) -> None:
        """Create database tables based on the schema configuration."""
        # Create daily prices table
        schema = self.config.get_database_schema('daily_prices')
        if not schema:
            raise ValueError("Daily prices schema not found in configuration")

        columns = []
        for col, dtype in schema.dtypes.items():
            if dtype == 'INTEGER PRIMARY KEY AUTOINCREMENT':
                columns.append(f"{col} {dtype}")
            else:
                columns.append(f"{col} {dtype.replace('datetime64[ns]', 'TEXT')}")

        create_prices_table_sql = f"""
        CREATE TABLE IF NOT EXISTS daily_prices (
            {', '.join(columns)}
        )
        """

        # Create technical indicators table
        create_indicators_table_sql = """
        CREATE TABLE IF NOT EXISTS technical_indicators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            symbol TEXT NOT NULL,
            indicator_name TEXT NOT NULL,
            indicator_params TEXT NOT NULL,
            indicator_value REAL NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(date, symbol, indicator_name, indicator_params)
        )
        """

        self.conn.execute(create_prices_table_sql)
        self.conn.execute(create_indicators_table_sql)
        self.conn.commit()

    def store_price_data(self, df: pd.DataFrame) -> None:
        """Store price data in the database.

        Args:
            df: DataFrame containing price data
        """
        try:
            df.to_sql('daily_prices', self.conn, if_exists='append', index=False)
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Error storing price data: {str(e)}")
            self.conn.rollback()

    def store_indicator_data(self, df: pd.DataFrame, indicator_name: str, params: Dict) -> None:
        """Store technical indicator data in the database.

        Args:
            df: DataFrame containing indicator data
            indicator_name: Name of the indicator
            params: Parameters used to calculate the indicator
        """
        try:
            # Add metadata columns
            df['indicator_name'] = indicator_name
            df['indicator_params'] = str(params)
            df['created_at'] = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')

            # Store in database
            df.to_sql('technical_indicators', self.conn, if_exists='append', index=False)
            self.conn.commit()
        except Exception as e:
            self.logger.error(f"Error storing indicator data: {str(e)}")
            self.conn.rollback()

    def get_price_data(self, symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Get price data for a symbol within a date range.

        Args:
            symbol: Symbol to get data for
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format

        Returns:
            DataFrame containing price data
        """
        query = """
        SELECT * FROM daily_prices
        WHERE symbol = ?
        AND date BETWEEN ? AND ?
        ORDER BY date
        """
        return pd.read_sql_query(query, self.conn, params=(symbol, start_date, end_date))

    def get_indicator_data(self, symbol: str, indicator_name: str, params: Dict,
                          start_date: str, end_date: str) -> pd.DataFrame:
        """Get technical indicator data for a symbol.

        Args:
            symbol: Symbol to get data for
            indicator_name: Name of the indicator
            params: Parameters used to calculate the indicator
            start_date: Start date in YYYYMMDD format
            end_date: End date in YYYYMMDD format

        Returns:
            DataFrame containing indicator data
        """
        query = """
        SELECT * FROM technical_indicators
        WHERE symbol = ?
        AND indicator_name = ?
        AND indicator_params = ?
        AND date BETWEEN ? AND ?
        ORDER BY date
        """
        return pd.read_sql_query(query, self.conn,
                               params=(symbol, indicator_name, str(params), start_date, end_date))

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self, 'conn'):
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()