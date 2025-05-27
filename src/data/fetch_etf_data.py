import logging
from datetime import datetime
import pandas as pd
from sqlalchemy import create_engine, text
from pathlib import Path

import akshare as ak

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fetch_etf_data(symbol: str, start_date: str, end_date: str) -> pd.DataFrame:
    """
    Fetch ETF data using AKShare.
    
    Args:
        symbol: ETF symbol
        start_date: Start date in YYYYMMDD format
        end_date: End date in YYYYMMDD format
        
    Returns:
        DataFrame containing ETF data
    """
    try:
        # Fetch ETF data
        df = ak.fund_etf_hist_em(symbol=symbol, start_date=start_date, end_date=end_date)
        
        # Rename columns to match database schema
        df = df.rename(columns={
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
        df['symbol'] = symbol
        
        # Convert date to datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Sort by date
        df = df.sort_values('date')
        
        return df
    
    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {str(e)}")
        return pd.DataFrame()

def main():
    # Database path
    db_path = Path("data/tushare/market_data.db")
    if not db_path.parent.exists():
        db_path.parent.mkdir(parents=True)
    
    # Create database engine
    engine = create_engine(f"sqlite:///{db_path}")
    
    # ETF symbols
    symbols = ['510300', '511010', '518880', '513100']
    
    # Date range
    start_date = '20131201'  # Updated to 2013/12/01
    end_date = '20250527'
    
    # Clear existing data for these symbols
    for symbol in symbols:
        with engine.connect() as conn:
            conn.execute(text(f"DELETE FROM daily_prices WHERE symbol = '{symbol}'"))
            conn.commit()
    
    # Fetch and store data for each ETF
    for symbol in symbols:
        logger.info(f"Fetching data for {symbol}")
        df = fetch_etf_data(symbol, start_date, end_date)
        
        if not df.empty:
            # Store in database
            df.to_sql('daily_prices', engine, if_exists='append', index=False)
            logger.info(f"Stored {len(df)} rows for {symbol}")
        else:
            logger.warning(f"No data fetched for {symbol}")

if __name__ == "__main__":
    main()