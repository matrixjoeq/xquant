import pandas as pd
import numpy as np
from pathlib import Path
import logging
import logging.config
from sqlalchemy import create_engine
from src.config import LOG_CONFIG

# Configure logging
logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)

class MACrossStrategy:
    def __init__(self, db_path: str, symbol: str, risk_per_trade: float = 0.02):
        """
        Initialize the MA Cross Strategy with RSI filter and ATR-based stops.

        Args:
            db_path: Path to the SQLite database
            symbol: ETF symbol
            risk_per_trade: Maximum risk per trade as a percentage of portfolio (default: 2%)
        """
        self.db_path = db_path
        self.symbol = symbol
        self.risk_per_trade = risk_per_trade
        self.data = None
        self.signals = None
        self.positions = None
        self.returns = None

    def calculate_rsi(self, data: pd.Series, periods: int = 14) -> pd.Series:
        """
        Calculate RSI (Relative Strength Index).

        Args:
            data: Price series
            periods: Number of periods for RSI calculation

        Returns:
            RSI series
        """
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    def calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, periods: int = 14) -> pd.Series:
        """
        Calculate Average True Range (ATR).

        Args:
            high: High price series
            low: Low price series
            close: Close price series
            periods: Number of periods for ATR calculation

        Returns:
            ATR series
        """
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=periods).mean()
        return atr

    def load_data(self):
        """Load and prepare data for analysis."""
        engine = create_engine(f"sqlite:///{self.db_path}")
        query = f"SELECT * FROM daily_prices WHERE symbol = '{self.symbol}' ORDER BY date"
        self.data = pd.read_sql(query, engine)

        if self.data.empty:
            raise ValueError(f"No data found for {self.symbol}")

        # Calculate moving averages
        self.data['MA5'] = self.data['close'].rolling(window=5).mean()
        self.data['MA10'] = self.data['close'].rolling(window=10).mean()
        self.data['MA20'] = self.data['close'].rolling(window=20).mean()

        # Calculate RSI
        self.data['RSI'] = self.calculate_rsi(self.data['close'], periods=14)

        # Calculate ATR
        self.data['ATR'] = self.calculate_atr(
            self.data['high'],
            self.data['low'],
            self.data['close'],
            periods=14
        )

        # Drop rows with NaN values (first 20 days due to MA20)
        self.data = self.data.dropna()

    def generate_signals(self):
        """Generate trading signals based on MA crossovers, RSI, and ATR-based stops."""
        # Initialize signals column
        self.data['signal'] = 0

        # Generate initial signals based on MA and RSI
        # Buy when MA5 > MA20 AND RSI > 60
        buy_condition = (self.data['MA5'] > self.data['MA20']) & (self.data['RSI'] > 60)
        # Sell when MA5 < MA20 AND RSI < 40
        sell_condition = (self.data['MA5'] < self.data['MA20']) & (self.data['RSI'] < 40)

        self.data.loc[buy_condition, 'signal'] = 1
        self.data.loc[sell_condition, 'signal'] = -1

        # Calculate positions
        self.data['position'] = self.data['signal'].diff()

        # Initialize stop-loss and trailing stop columns
        self.data['stop_loss'] = np.nan
        self.data['trailing_stop'] = np.nan
        self.data['highest_price'] = np.nan
        self.data['atr_multiplier'] = 1.0
        self.data['position_size'] = 0.0

        # Apply stop-loss and trailing stop logic
        current_position = 0
        entry_price = 0
        highest_price = 0
        portfolio_value = 100000  # Initial portfolio value

        for i in range(1, len(self.data)):
            if self.data['position'].iloc[i] == 1:  # New long position
                current_position = 1
                entry_price = self.data['close'].iloc[i]
                highest_price = entry_price
                current_atr = self.data['ATR'].iloc[i]

                # Calculate position size based on ATR
                risk_amount = portfolio_value * self.risk_per_trade
                stop_distance = current_atr  # 1 ATR stop-loss
                position_size = min(risk_amount / stop_distance, portfolio_value / entry_price)

                self.data.loc[self.data.index[i], 'stop_loss'] = entry_price - current_atr
                self.data.loc[self.data.index[i], 'highest_price'] = highest_price
                self.data.loc[self.data.index[i], 'atr_multiplier'] = 1.0
                self.data.loc[self.data.index[i], 'position_size'] = position_size

            elif self.data['position'].iloc[i] == -1:  # Exit position
                current_position = 0
                entry_price = 0
                highest_price = 0
                self.data.loc[self.data.index[i], 'position_size'] = 0

            elif current_position == 1:  # In position
                current_price = self.data['close'].iloc[i]
                current_atr = self.data['ATR'].iloc[i]

                # Update highest price
                if current_price > highest_price:
                    highest_price = current_price
                    # Adjust trailing stop based on profit
                    price_change = (highest_price - entry_price) / entry_price
                    if price_change >= 0.02:  # 2% profit
                        self.data.loc[self.data.index[i], 'atr_multiplier'] = 0.5
                    elif price_change >= 0.01:  # 1% profit
                        self.data.loc[self.data.index[i], 'atr_multiplier'] = 1.0

                # Update trailing stop
                self.data.loc[self.data.index[i], 'highest_price'] = highest_price
                self.data.loc[self.data.index[i], 'trailing_stop'] = (
                    highest_price - self.data['atr_multiplier'].iloc[i] * current_atr
                )
                self.data.loc[self.data.index[i], 'position_size'] = self.data['position_size'].iloc[i-1]

                # Check stop-loss
                if current_price <= self.data['stop_loss'].iloc[i-1]:
                    self.data.loc[self.data.index[i], 'signal'] = -1
                    current_position = 0
                    entry_price = 0
                    highest_price = 0
                    self.data.loc[self.data.index[i], 'position_size'] = 0

                # Check trailing stop
                elif current_price <= self.data['trailing_stop'].iloc[i-1]:
                    self.data.loc[self.data.index[i], 'signal'] = -1
                    current_position = 0
                    entry_price = 0
                    highest_price = 0
                    self.data.loc[self.data.index[i], 'position_size'] = 0

        # Update final positions based on signals
        self.data['position'] = self.data['signal'].shift(1).fillna(0)

    def backtest(self, initial_capital=100000):
        """
        Backtest the strategy.

        Args:
            initial_capital: Initial capital for backtesting
        """
        # Calculate returns
        self.data['returns'] = self.data['close'].pct_change()
        self.data['strategy_returns'] = self.data['position'] * self.data['returns'] * (self.data['position_size'] / initial_capital)

        # Calculate cumulative returns
        self.data['cumulative_returns'] = (1 + self.data['returns']).cumprod()
        self.data['strategy_cumulative_returns'] = (1 + self.data['strategy_returns']).cumprod()

        # Calculate portfolio value
        self.data['portfolio_value'] = initial_capital * self.data['strategy_cumulative_returns']

        # Calculate drawdown
        self.data['peak'] = self.data['portfolio_value'].cummax()
        self.data['drawdown'] = (self.data['portfolio_value'] - self.data['peak']) / self.data['peak']

    def calculate_metrics(self):
        """Calculate performance metrics."""
        # Calculate returns
        total_return = self.data['strategy_cumulative_returns'].iloc[-1] - 1

        # Convert date strings to datetime objects
        start_date = pd.to_datetime(self.data['date'].iloc[0])
        end_date = pd.to_datetime(self.data['date'].iloc[-1])
        n_years = (end_date - start_date).days / 365.25
        annual_return = (1 + total_return) ** (1 / n_years) - 1

        # Calculate drawdown
        max_drawdown = self.data['drawdown'].min()

        # Calculate Sharpe Ratio (assuming risk-free rate = 0)
        daily_returns = self.data['strategy_returns']
        sharpe_ratio = np.sqrt(252) * daily_returns.mean() / daily_returns.std()

        # Calculate win rate
        trades = self.data[self.data['position'] != 0]
        win_rate = len(trades[trades['strategy_returns'] > 0]) / len(trades) if len(trades) > 0 else 0

        # Calculate average RSI at entry and exit
        entry_rsi = self.data[self.data['position'] == 1]['RSI'].mean()
        exit_rsi = self.data[self.data['position'] == -1]['RSI'].mean()

        # Calculate stop-loss and trailing stop statistics
        stop_loss_hits = len(self.data[
            (self.data['signal'] == -1) &
            (self.data['close'] <= self.data['stop_loss'].shift(1))
        ])

        trailing_stop_hits = len(self.data[
            (self.data['signal'] == -1) &
            (self.data['close'] <= self.data['trailing_stop'].shift(1))
        ])

        # Calculate position sizing statistics
        avg_position_size = self.data['position_size'].mean()
        max_position_size = self.data['position_size'].max()

        metrics = {
            'Total Return': f'{total_return:.2%}',
            'Annual Return': f'{annual_return:.2%}',
            'Max Drawdown': f'{max_drawdown:.2%}',
            'Sharpe Ratio': f'{sharpe_ratio:.2f}',
            'Win Rate': f'{win_rate:.2%}',
            'Number of Trades': len(trades),
            'Average Entry RSI': f'{entry_rsi:.2f}',
            'Average Exit RSI': f'{exit_rsi:.2f}',
            'Stop-Loss Hits': stop_loss_hits,
            'Trailing Stop Hits': trailing_stop_hits,
            'Average Position Size': f'{avg_position_size:.2f}',
            'Max Position Size': f'{max_position_size:.2f}'
        }

        return metrics

    def run(self, initial_capital=100000):
        """Run the complete strategy."""
        self.load_data()
        self.generate_signals()
        self.backtest(initial_capital)
        return self.calculate_metrics()

def main():
    # Database path
    db_path = Path('data/tushare/market_data.db')
    if not db_path.exists():
        logger.error(f"Database file not found: {db_path}")
        return

    # Initialize and run strategy
    symbol = '159696'
    try:
        strategy = MACrossStrategy(db_path, symbol, risk_per_trade=0.02)  # 2% risk per trade
        metrics = strategy.run()

        # Print results
        logger.info("\nStrategy Performance Metrics:")
        for metric, value in metrics.items():
            logger.info(f"{metric}: {value}")

        # Save results to CSV
        output_path = Path('data/tushare/strategy_results.csv')
        strategy.data.to_csv(output_path)
        logger.info(f"\nDetailed results saved to {output_path}")

    except Exception as e:
        logger.error(f"Error running strategy: {str(e)}")

if __name__ == '__main__':
    main()