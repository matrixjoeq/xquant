import os
from datetime import datetime, timedelta
import logging.config

from src.data.collector import DataCollector
from src.config import DB_CONFIG, LOG_CONFIG

# Configure logging
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)

def main():
    # Initialize data collector
    collector = DataCollector(
        db_url=DB_CONFIG['default']['url'],
        tushare_token=os.getenv('TUSHARE_TOKEN')
    )
    
    # Example symbols (Shanghai A-shares)
    symbols = ['600000.SH', '600036.SH', '601318.SH']
    
    # Set date range (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    try:
        # Collect daily data
        logger.info("Collecting daily data...")
        daily_data = collector.collect_daily_data(
            symbols=symbols,
            start_date=start_date.strftime('%Y%m%d'),
            end_date=end_date.strftime('%Y%m%d')
        )
        
        if not daily_data.empty:
            collector.store_data(
                data=daily_data,
                table_name='daily_prices'
            )
        
        # Collect fundamental data
        logger.info("Collecting fundamental data...")
        fundamental_data = collector.collect_fundamental_data(
            symbols=symbols
        )
        
        if not fundamental_data.empty:
            collector.store_data(
                data=fundamental_data,
                table_name='fundamental_data'
            )
        
        # Collect technical indicators
        logger.info("Collecting technical indicators...")
        indicators = ['MA', 'RSI', 'MACD']
        technical_data = collector.collect_technical_indicators(
            symbols=symbols,
            indicators=indicators,
            start_date=start_date.strftime('%Y%m%d'),
            end_date=end_date.strftime('%Y%m%d')
        )
        
        if not technical_data.empty:
            collector.store_data(
                data=technical_data,
                table_name='technical_indicators'
            )
            
    except Exception as e:
        logger.error(f"Error in data collection: {str(e)}")
        raise

if __name__ == '__main__':
    main() 