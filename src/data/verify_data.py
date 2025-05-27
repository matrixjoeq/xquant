import pandas as pd
from sqlalchemy import create_engine
from pathlib import Path

def verify_data():
    # Database path
    db_path = Path("data/tushare/market_data.db")
    engine = create_engine(f"sqlite:///{db_path}")
    
    # Query to get data for each ETF
    query = """
    SELECT symbol, 
           COUNT(*) as row_count,
           MIN(date) as start_date,
           MAX(date) as end_date
    FROM daily_prices
    GROUP BY symbol
    ORDER BY symbol
    """
    
    # Execute query
    df = pd.read_sql(query, engine)
    print("\nData Summary:")
    print(df.to_string(index=False))
    
    # Get sample data for each ETF
    print("\nSample Data (first 3 rows for each ETF):")
    for symbol in df['symbol']:
        sample_query = f"""
        SELECT *
        FROM daily_prices
        WHERE symbol = '{symbol}'
        ORDER BY date
        LIMIT 3
        """
        sample_df = pd.read_sql(sample_query, engine)
        print(f"\n{symbol}:")
        print(sample_df.to_string(index=False))

if __name__ == "__main__":
    verify_data() 