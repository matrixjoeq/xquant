import os
from pathlib import Path
from typing import Dict, Any

# Project root directory
ROOT_DIR = Path(__file__).parent.parent

# Database configuration
DB_CONFIG = {
    'default': {
        'url': os.getenv('DATABASE_URL', 'sqlite:///data/market_data.db'),
        'echo': False
    }
}

# Data collection settings
DATA_CONFIG = {
    'daily_data': {
        'table_name': 'daily_prices',
        'columns': [
            'symbol',
            'date',
            'open',
            'high',
            'low',
            'close',
            'volume',
            'amount'
        ]
    },
    'fundamental_data': {
        'table_name': 'fundamental_data',
        'columns': [
            'symbol',
            'date',
            'pe_ratio',
            'pb_ratio',
            'dividend_yield',
            'market_cap'
        ]
    },
    'technical_indicators': {
        'table_name': 'technical_indicators',
        'columns': [
            'symbol',
            'date',
            'indicator_name',
            'indicator_value'
        ]
    }
}

# API configuration
API_CONFIG = {
    'tushare': {
        'token': os.getenv('TUSHARE_TOKEN', ''),
        'base_url': 'http://api.tushare.pro'
    }
}

# Logging configuration
LOG_CONFIG = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'standard': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        },
    },
    'handlers': {
        'default': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.StreamHandler',
        },
        'file': {
            'level': 'INFO',
            'formatter': 'standard',
            'class': 'logging.FileHandler',
            'filename': ROOT_DIR / 'logs' / 'data_collector.log',
            'mode': 'a',
        },
    },
    'loggers': {
        '': {
            'handlers': ['default', 'file'],
            'level': 'INFO',
            'propagate': True
        }
    }
}