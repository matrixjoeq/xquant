import logging
import logging.config
from datetime import datetime, timedelta
import os
from pathlib import Path

import akshare as ak
import pandas as pd
from sqlalchemy import create_engine

from src.config import LOG_CONFIG

# Configure logging
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)

def main():
    # Create database directory if it doesn't exist
    db_path = Path('data/tushare/market_data.db')
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Initialize database URL
    db_url = f"sqlite:///{db_path.absolute()}"
    engine = create_engine(db_url)

    # Set date range (10 years)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365*10)  # 10 years of data

    # Format dates for API
    start_date_str = start_date.strftime('%Y%m%d')
    end_date_str = end_date.strftime('%Y%m%d')

    # Fetch data for ETF 159696
    symbol = '159696'  # ETF symbol without exchange suffix
    logger.info(f"Fetching daily data for {symbol} from {start_date_str} to {end_date_str}")

    try:
        # Collect daily data using AKShare's ETF function
        daily_data = ak.fund_etf_hist_em(symbol=symbol, period="daily",
                                       start_date=start_date_str,
                                       end_date=end_date_str)

        if not daily_data.empty:
            # Rename columns to match our database schema
            daily_data = daily_data.rename(columns={
                '日期': 'date',
                '开盘': 'open',
                '收盘': 'close',
                '最高': 'high',
                '最低': 'low',
                '成交量': 'volume',
                '成交额': 'amount',
                '振幅': 'amplitude',
                '涨跌幅': 'pct_change',
                '涨跌额': 'change',
                '换手率': 'turnover'
            })

            # Add symbol column
            daily_data['symbol'] = symbol

            # Convert date column to datetime
            daily_data['date'] = pd.to_datetime(daily_data['date'])

            # Store data in database
            daily_data.to_sql('daily_prices', engine, if_exists='replace', index=False)
            logger.info(f"Successfully stored {len(daily_data)} records for {symbol}")

            # Print first few rows of data
            logger.info("\nFirst few records:")
            logger.info(daily_data.head().to_string())

            # Print last few rows of data
            logger.info("\nLast few records:")
            logger.info(daily_data.tail().to_string())
        else:
            logger.warning(f"No data found for {symbol}")

    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {str(e)}")

if __name__ == '__main__':
    main()