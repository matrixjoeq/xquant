import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine, text
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MomentumRotationStrategy:
    def __init__(self, db_path: str, symbols: list, initial_capital: float = 100000.0):
        """
        Initialize the momentum rotation strategy.
        
        Args:
            db_path: Path to the SQLite database
            symbols: List of ETF symbols to trade
            initial_capital: Initial capital for backtesting
        """
        self.db_path = db_path
        self.symbols = symbols
        self.initial_capital = initial_capital
        self.engine = create_engine(f"sqlite:///{db_path}")
        
        # Strategy parameters
        self.three_week_weight = 4  # Weight for 3-week momentum
        self.four_week_weight = 3   # Weight for 4-week momentum
        
    def load_data(self) -> pd.DataFrame:
        """Load and prepare data for all symbols."""
        query = f"""
        SELECT *
        FROM daily_prices
        WHERE symbol IN {tuple(self.symbols)}
        ORDER BY date
        """
        df = pd.read_sql(query, self.engine)
        df['date'] = pd.to_datetime(df['date'])
        return df
    
    def calculate_momentum(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate weighted momentum for each ETF.
        
        Args:
            df: DataFrame with price data
            
        Returns:
            DataFrame with momentum calculations
        """
        # Create a copy to avoid modifying the original
        df = df.copy()
        
        # Calculate returns for 3-week and 4-week periods
        df['return_3w'] = df.groupby('symbol')['close'].pct_change(15)  # 15 trading days ≈ 3 weeks
        df['return_4w'] = df.groupby('symbol')['close'].pct_change(20)  # 20 trading days ≈ 4 weeks
        
        # Calculate weighted momentum
        df['weighted_momentum'] = (
            self.three_week_weight * df['return_3w'].fillna(0) + 
            self.four_week_weight * df['return_4w'].fillna(0)
        ) / (self.three_week_weight + self.four_week_weight)
        
        return df
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate trading signals based on momentum.
        
        Args:
            df: DataFrame with momentum calculations
            
        Returns:
            DataFrame with trading signals
        """
        # Create a copy to avoid modifying the original
        df = df.copy()
        
        # Add day of week (0 = Monday, 4 = Friday)
        df['day_of_week'] = df['date'].dt.dayofweek
        
        # Initialize signal column
        df['signal'] = 0
        
        # Get unique dates
        dates = df['date'].unique()
        
        # For each Friday (or last trading day of the week)
        for date in dates:
            # Get data for this date
            date_data = df[df['date'] == date]
            
            # Skip if not Friday (or last trading day)
            if date_data['day_of_week'].iloc[0] != 4:
                continue
            
            # Find ETF with highest momentum (excluding NaN values)
            valid_momentum = date_data[date_data['weighted_momentum'].notna()]
            if not valid_momentum.empty:
                best_etf = valid_momentum.loc[valid_momentum['weighted_momentum'].idxmax()]
                
                # Generate buy signal for the best ETF
                df.loc[(df['date'] == date) & (df['symbol'] == best_etf['symbol']), 'signal'] = 1
        
        return df
    
    def backtest(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Backtest the strategy with robust weekly rotation: on each Friday, if the selected ETF is not the one currently held, sell the current holding and buy the new one. Only buy/sell if valid price and cash/holdings exist. Always carry forward portfolio value and cash. Never lose cash/holdings unless a valid trade occurs.
        """
        df = df.copy()
        df['position'] = 0
        df['cash'] = self.initial_capital
        df['holdings'] = 0.0
        df['portfolio_value'] = self.initial_capital
        
        current_position = None  # symbol
        current_shares = 0.0
        cash = self.initial_capital
        
        # Sort by date and symbol for consistent processing
        df = df.sort_values(['date', 'symbol']).reset_index(drop=True)
        
        # Debug logging
        logger.info(f"Starting backtest with initial capital: ${self.initial_capital:,.2f}")
        
        for date in sorted(df['date'].unique()):
            day_data = df[df['date'] == date]
            is_friday = day_data['day_of_week'].iloc[0] == 4
            signal_row = day_data[day_data['signal'] == 1]
            selected_symbol = signal_row['symbol'].iloc[0] if not signal_row.empty else None
            
            # Debug logging for current state
            logger.info(f"\nDate: {date}")
            logger.info(f"Current position: {current_position}, Shares: {current_shares:.2f}, Cash: ${cash:,.2f}")
            
            # On Friday, check if we need to rotate
            if is_friday and selected_symbol is not None:
                logger.info(f"Friday - Selected ETF: {selected_symbol}")
                
                # Only trade if the new ETF is different from the current holding
                if current_position != selected_symbol:
                    logger.info(f"Need to rotate from {current_position} to {selected_symbol}")
                    
                    # Try to sell current holding if any
                    if current_position is not None and current_shares > 0:
                        sell_row = day_data[day_data['symbol'] == current_position]
                        if not sell_row.empty and not np.isnan(sell_row['close'].iloc[0]):
                            sell_price = sell_row['close'].iloc[0]
                            cash = current_shares * sell_price * 0.99  # 1% transaction cost
                            logger.info(f"Sold {current_position} at ${sell_price:.2f}, Cash after sale: ${cash:,.2f}")
                            current_shares = 0.0
                        else:
                            logger.info(f"Could not sell {current_position} - invalid price")
                            continue  # Skip the trade if we can't sell
                    
                    # Try to buy new ETF only if we have cash
                    if cash > 0:
                        buy_row = day_data[day_data['symbol'] == selected_symbol]
                        if not buy_row.empty and not np.isnan(buy_row['close'].iloc[0]):
                            buy_price = buy_row['close'].iloc[0]
                            current_shares = (cash * 0.99) / buy_price  # 1% transaction cost
                            logger.info(f"Bought {selected_symbol} at ${buy_price:.2f}, Shares: {current_shares:.2f}")
                            cash = 0.0
                            current_position = selected_symbol
                        else:
                            logger.info(f"Could not buy {selected_symbol} - invalid price")
                            continue  # Skip the trade if we can't buy
                    else:
                        logger.info("No cash available for buying")
                        continue  # Skip the trade if no cash
                else:
                    logger.info(f"Already holding {selected_symbol} - no trade needed")
            
            # On all days, update holdings and portfolio value
            for idx, row in day_data.iterrows():
                if current_position is not None and row['symbol'] == current_position and current_shares > 0:
                    price = row['close']
                    if not np.isnan(price):
                        holdings = current_shares * price
                        df.at[idx, 'position'] = 1
                        df.at[idx, 'holdings'] = holdings
                        df.at[idx, 'cash'] = cash
                        df.at[idx, 'portfolio_value'] = holdings + cash
                        logger.info(f"Updated holdings for {current_position}: ${holdings:,.2f}, Portfolio value: ${holdings + cash:,.2f}")
                else:
                    df.at[idx, 'position'] = 0
                    df.at[idx, 'holdings'] = 0.0
                    df.at[idx, 'cash'] = cash
                    df.at[idx, 'portfolio_value'] = cash
                    logger.info(f"No holdings, Portfolio value: ${cash:,.2f}")
        
        # Final debug logging
        logger.info(f"\nBacktest completed:")
        logger.info(f"Final position: {current_position}")
        logger.info(f"Final shares: {current_shares:.2f}")
        logger.info(f"Final cash: ${cash:,.2f}")
        if current_position is not None and current_shares > 0:
            last_price = df[df['symbol'] == current_position]['close'].iloc[-1]
            final_holdings = current_shares * last_price
            logger.info(f"Final holdings: ${final_holdings:,.2f}")
            logger.info(f"Final portfolio value: ${final_holdings + cash:,.2f}")
        
        return df
    
    def calculate_metrics(self, df: pd.DataFrame) -> dict:
        """
        Calculate performance metrics.
        
        Args:
            df: DataFrame with backtest results
            
        Returns:
            Dictionary with performance metrics
        """
        # Get unique dates and portfolio values
        dates = df['date'].unique()
        portfolio_values = df.groupby('date')['portfolio_value'].first()
        
        # Calculate returns
        returns = portfolio_values.pct_change()
        
        # Calculate metrics
        total_return = (portfolio_values.iloc[-1] / portfolio_values.iloc[0]) - 1
        annual_return = (1 + total_return) ** (252 / len(dates)) - 1
        volatility = returns.std() * np.sqrt(252)
        sharpe_ratio = annual_return / volatility if volatility != 0 else 0
        max_drawdown = (portfolio_values / portfolio_values.cummax() - 1).min()
        
        # Calculate win rate
        trades = df[df['signal'] == 1]
        if len(trades) > 0:
            win_rate = len(trades[trades['pct_change'] > 0]) / len(trades)
        else:
            win_rate = 0
        
        return {
            'Total Return': f'{total_return:.2%}',
            'Annual Return': f'{annual_return:.2%}',
            'Volatility': f'{volatility:.2%}',
            'Sharpe Ratio': f'{sharpe_ratio:.2f}',
            'Max Drawdown': f'{max_drawdown:.2%}',
            'Win Rate': f'{win_rate:.2%}',
            'Number of Trades': f'{len(trades)}',
            'Final Portfolio Value': f'${portfolio_values.iloc[-1]:,.2f}'
        }
    
    def run(self) -> dict:
        """Run the complete strategy."""
        # Load data
        df = self.load_data()
        
        # Calculate momentum
        df = self.calculate_momentum(df)
        
        # Generate signals
        df = self.generate_signals(df)
        
        # Run backtest
        df = self.backtest(df)
        
        # Calculate metrics
        metrics = self.calculate_metrics(df)
        
        return metrics

def main():
    # Database path
    db_path = Path("data/tushare/market_data.db")
    
    # ETF symbols
    symbols = ['510300', '511010', '518880', '513100']
    
    # Initialize and run strategy
    strategy = MomentumRotationStrategy(db_path, symbols)
    metrics = strategy.run()
    
    # Print results
    print("\nStrategy Performance Metrics:")
    for metric, value in metrics.items():
        print(f"{metric}: {value}")

if __name__ == "__main__":
    main() 