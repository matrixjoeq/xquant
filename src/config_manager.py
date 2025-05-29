import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class Paths:
    root_dir: str
    data_dir: str
    akshare_dir: str
    reports_dir: str
    strategy_dir: str
    backtest_dir: str
    logs_dir: str


@dataclass
class Database:
    path: str
    url: str


@dataclass
class DateRange:
    start_date: str
    end_date: str


@dataclass
class PriceType:
    description: str


@dataclass
class AkShareConfig:
    name: str
    description: str
    price_types: Dict[str, PriceType]
    column_mapping: Dict[str, str]


@dataclass
class ETF:
    name: str
    description: str


@dataclass
class TradingUniverse:
    etfs: Dict[str, ETF]


@dataclass
class DatabaseSchema:
    columns: List[str]
    dtypes: Dict[str, str]
    constraints: List[str]


@dataclass
class ValidationRules:
    required_columns: List[str]
    non_null_columns: List[str]


class ConfigManager:
    def __init__(self, config_path: str = "src/config.json"):
        """Initialize the configuration manager.

        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self._initialize_components()

    def _load_config(self) -> Dict:
        """Load configuration from JSON file."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _initialize_components(self) -> None:
        """Initialize all configuration components."""
        self.paths = Paths(**self.config['paths'])
        self.database = Database(**self.config['database']['akshare'])
        self.date_range = DateRange(**self.config['date_range'])

        # Initialize AkShare configuration
        akshare_config = self.config['data_sources']['akshare']
        price_types = {
            name: PriceType(**config)
            for name, config in akshare_config['price_types'].items()
        }
        self.akshare = AkShareConfig(
            name=akshare_config['name'],
            description=akshare_config['description'],
            price_types=price_types,
            column_mapping=akshare_config['column_mapping']
        )

        # Initialize trading universe
        etfs = {
            symbol: ETF(**config)
            for symbol, config in self.config['trading_universe']['etfs'].items()
        }
        self.trading_universe = TradingUniverse(etfs=etfs)

        # Initialize database schemas
        self.database_schemas = {
            name: DatabaseSchema(**schema)
            for name, schema in self.config['database_schemas'].items()
        }

        # Initialize validation rules
        self.validation_rules = {
            name: ValidationRules(**rules)
            for name, rules in self.config['validation']['rules'].items()
        }
        self.price_types = self.config['validation']['price_types']

    def get_etf_symbols(self) -> List[str]:
        """Get list of ETF symbols from configuration."""
        return list(self.trading_universe.etfs.keys())

    def get_price_types(self) -> List[str]:
        """Get list of price types from configuration."""
        """Get list of available price types."""
        return list(self.akshare.price_types.keys())

    def get_column_mapping(self) -> Dict[str, str]:
        """Get the column mapping for AkShare data."""
        return self.akshare.column_mapping

    def get_required_columns(self) -> List[str]:
        """Get the list of required columns for daily prices."""
        return self.validation_rules['daily_prices'].required_columns

    def get_non_null_columns(self) -> List[str]:
        """Get the list of non-null columns for daily prices."""
        return self.validation_rules['daily_prices'].non_null_columns

    def get_database_schema(self, schema_name: str) -> Optional[DatabaseSchema]:
        """Get database schema by name."""
        return self.database_schemas.get(schema_name)

    def get_price_type_description(self, price_type: str) -> Optional[str]:
        """Get description for a specific price type."""
        return self.price_types.get(price_type)

    def get_etf_info(self, symbol: str) -> Optional[ETF]:
        """Get ETF information by symbol."""
        return self.trading_universe.etfs.get(symbol)

    def get_date_range(self) -> DateRange:
        """Get the configured date range."""
        return self.date_range

    def get_database_url(self) -> str:
        """Get the database URL."""
        return self.database.url

    def get_data_dir(self) -> str:
        """Get the data directory path."""
        return self.paths.data_dir

    def get_akshare_dir(self) -> str:
        """Get the AkShare data directory path."""
        return self.paths.akshare_dir

    def get_reports_dir(self) -> str:
        """Get the reports directory path."""
        return self.paths.reports_dir

    def get_technical_indicators(self) -> dict:
        """Get the technical indicators configuration from the config file."""
        return self.config.get('technical_indicators', {})