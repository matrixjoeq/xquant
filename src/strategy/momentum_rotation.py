#!/usr/bin/env python3
import pandas as pd
import numpy as np
from pathlib import Path
import sqlite3
from typing import List, Dict, Tuple
import logging
from datetime import datetime
import matplotlib.pyplot as plt
import backtrader as bt
import backtrader.analyzers as btanalyzers
from chinese_calendar import is_workday

class MomentumRotationStrategy(bt.Strategy):
    """Momentum rotation strategy using Backtrader."""

    params = (
        ('lookback_period', 15),
        ('top_n', 1),
    )

    def __init__(self):
        """Initialize the strategy."""
        self.logger = logging.getLogger(__name__)
        self.order = None
        self.current_holding = None
        self.days_in_position = 0
        self.last_trading_day = None

    def next(self):
        if self.order:
            return

        # Check if it's the last trading day of the week
        current_date = self.data0.datetime.date(0)
        if self.is_last_trading_day_of_week(current_date):
            self.last_trading_day = True
        else:
            self.last_trading_day = False

        if not self.last_trading_day:
            return

        # Calculate momentum for each asset
        momentums = {}
        for data in self.datas:
            if len(data) > self.params.lookback_period:
                returns = (data.close[0] / data.close[-self.params.lookback_period]) - 1
                momentums[data._name] = returns

        # Find the top asset
        top_asset = max(momentums, key=momentums.get)

        # Check if the current holding is the top asset
        if self.current_holding != top_asset:
            # Sell current holding if it exists
            if self.current_holding:
                self.order = self.sell(data=self.getdatabyname(self.current_holding))
            # Buy the new top asset
            self.order = self.buy(data=self.getdatabyname(top_asset))
            self.current_holding = top_asset
            self.days_in_position = 0
        else:
            # Check price change for the current holding
            current_data = self.getdatabyname(self.current_holding)
            price_change = (current_data.close[0] / current_data.close[-1]) - 1
            if price_change < -0.05:  # Example threshold for selling
                self.order = self.sell(data=current_data)
                self.current_holding = None
                self.days_in_position = 0
            else:
                self.days_in_position += 1

    def is_last_trading_day_of_week(self, date):
        # Check if the current day is a trading day
        if date.weekday() < 5:  # Monday to Friday
            # Check if it's the last trading day of the week
            next_day = date + pd.Timedelta(days=1)
            while next_day.weekday() < 5:
                if self.is_trading_day(next_day):
                    return False
                next_day += pd.Timedelta(days=1)
            return True
        return False

    def is_trading_day(self, date):
        return is_workday(date)  # Using chinese_calendar to check if it's a trading day

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY {order.data._name} @ {order.executed.price:.2f}')
            else:
                self.log(f'SELL {order.data._name} @ {order.executed.price:.2f}')

        self.order = None

    def stop(self):
        """Called when the strategy is done."""
        # Calculate performance metrics
        returns = pd.Series(self.broker.getvalue()).pct_change()

        # Calculate metrics
        total_return = (self.broker.getvalue()[-1] / self.broker.getvalue()[0]) - 1
        annualized_return = (1 + total_return) ** (252/len(returns)) - 1
        sharpe_ratio = np.sqrt(252) * returns.mean() / returns.std()
        max_drawdown = (pd.Series(self.broker.getvalue()) / pd.Series(self.broker.getvalue()).cummax() - 1).min()
        volatility = returns.std() * np.sqrt(252)

        # Store results
        self.results = {
            'total_return': total_return,
            'annualized_return': annualized_return,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown,
            'volatility': volatility,
            'portfolio_value': self.broker.getvalue(),
            'position_history': self.current_holding,
            'dates': self.data0.datetime.date(0)
        }

    def log(self, txt, dt=None):
        dt = dt or self.data0.datetime.date(0)
        self.logger.info(f'{dt}: {txt}')

class BacktestRunner:
    """Class to run backtests using Backtrader."""

    def __init__(self, db_path: str = "data/akshare/market_data.db"):
        """Initialize the backtest runner.

        Args:
            db_path: Path to the SQLite database containing market data
        """
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self.symbols = ['510300', '513100', '511010', '518880']
        self.conn = None

    def _connect_db(self):
        """Connect to the SQLite database."""
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path)

    def _close_db(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None

    def get_price_data(self, start_date: str, end_date: str) -> Dict[str, pd.DataFrame]:
        """Get price data for all symbols.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format

        Returns:
            Dictionary mapping symbols to their price data
        """
        self._connect_db()
        price_data = {}

        for symbol in self.symbols:
            query = f"""
            SELECT date, open, high, low, close, volume
            FROM daily_prices
            WHERE symbol = '{symbol}'
            AND date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY date
            """
            self.logger.info(f"Executing query for {symbol}: {query}")
            try:
                df = pd.read_sql_query(query, self.conn)
                if df.empty:
                    self.logger.warning(f"No data returned for {symbol} between {start_date} and {end_date}")
                else:
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                    price_data[symbol] = df
                    self.logger.info(f"Fetched data for {symbol}: shape {df.shape}")
            except Exception as e:
                self.logger.error(f"Error fetching data for {symbol}: {e}")

        return price_data

    def run_backtest(self,
                    start_date: str,
                    end_date: str,
                    lookback_period: int,
                    top_n: int) -> Dict:
        """Run a backtest with the given parameters.

        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            lookback_period: Number of periods to look back for momentum
            top_n: Number of top performing assets to hold

        Returns:
            Dictionary containing backtest results
        """
        # Get price data
        price_data = self.get_price_data(start_date, end_date)

        # Create cerebro engine
        cerebro = bt.Cerebro()

        # Add strategy
        cerebro.addstrategy(MomentumRotationStrategy,
                           lookback_period=lookback_period,
                           top_n=top_n)

        # Add data feeds
        for symbol, data in price_data.items():
            self.logger.info(f"Adding data feed for {symbol}: shape {data.shape}")
            feed = bt.feeds.PandasData(
                dataname=data,
                name=symbol,
                datetime=None,  # Use index as datetime
                open='open',
                high='high',
                low='low',
                close='close',
                volume='volume',
                openinterest=-1
            )
            cerebro.adddata(feed)

        # Set initial capital
        cerebro.broker.setcash(1000000.0)

        # Add analyzers
        cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(btanalyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(btanalyzers.Returns, _name='returns')

        # Run backtest
        results = cerebro.run()
        strategy = results[0]

        # Get results
        backtest_results = {
            'total_return': strategy.results['total_return'],
            'annualized_return': strategy.results['annualized_return'],
            'sharpe_ratio': strategy.results['sharpe_ratio'],
            'max_drawdown': strategy.results['max_drawdown'],
            'volatility': strategy.results['volatility'],
            'portfolio_value': strategy.results['portfolio_value'],
            'positions': strategy.results['position_history'],
            'dates': strategy.results['dates']
        }

        # Plot results
        plt.figure(figsize=(12, 6))
        plt.plot(strategy.results['dates'], strategy.results['portfolio_value'])
        plt.title('Strategy Performance')
        plt.xlabel('Date')
        plt.ylabel('Portfolio Value')
        plt.grid(True)
        plt.savefig('backtest_performance.png')
        plt.close()

        return backtest_results

    def optimize_parameters(self,
                          train_start: str = '2013-01-01',
                          train_end: str = '2022-12-31',
                          lookback_range: List[int] = [5, 10, 20, 60, 120],
                          top_n_range: List[int] = [1, 2]) -> Tuple[Dict, pd.DataFrame]:
        """Optimize strategy parameters using training data.

        Args:
            train_start: Start date for training
            train_end: End date for training
            lookback_range: List of lookback periods to test
            top_n_range: List of top N values to test

        Returns:
            Tuple of (best parameters dictionary, results DataFrame)
        """
        self.logger.info("Starting parameter optimization...")

        best_sharpe = -np.inf
        best_params = None
        results = []

        for lookback in lookback_range:
            for top_n in top_n_range:
                self.logger.info(f"Testing parameters: lookback={lookback}, top_n={top_n}")

                # Run backtest
                backtest_results = self.run_backtest(
                    train_start,
                    train_end,
                    lookback,
                    top_n
                )

                # Store results
                result = {
                    'lookback_period': lookback,
                    'top_n': top_n,
                    'sharpe_ratio': backtest_results['sharpe_ratio'],
                    'total_return': backtest_results['total_return'],
                    'annualized_return': backtest_results['annualized_return'],
                    'max_drawdown': backtest_results['max_drawdown'],
                    'volatility': backtest_results['volatility']
                }
                results.append(result)

                # Update best parameters
                if backtest_results['sharpe_ratio'] > best_sharpe:
                    best_sharpe = backtest_results['sharpe_ratio']
                    best_params = {
                        'lookback_period': lookback,
                        'top_n': top_n,
                        'metrics': backtest_results
                    }

        # Convert results to DataFrame
        results_df = pd.DataFrame(results)

        # Save optimization results
        results_df.to_csv('strategy_optimization_results.csv')

        return best_params, results_df

    def validate_strategy(self,
                         best_params: Dict,
                         val_start: str = '2023-01-01',
                         val_end: str = '2025-05-31') -> Dict:
        """Validate strategy performance on validation data.

        Args:
            best_params: Best parameters from optimization
            val_start: Start date for validation
            val_end: End date for validation

        Returns:
            Dictionary containing validation results
        """
        self.logger.info("Starting strategy validation...")

        results = self.run_backtest(
            val_start,
            val_end,
            best_params['lookback_period'],
            best_params['top_n']
        )

        return results

    def generate_report(self,
                       train_results: pd.DataFrame,
                       val_results: Dict,
                       best_params: Dict) -> None:
        """Generate detailed strategy report.

        Args:
            train_results: Training optimization results
            val_results: Validation results
            best_params: Best parameters from optimization
        """
        report = f"""
Momentum Rotation Strategy Report
================================

1. Parameter Optimization Results
--------------------------------
Best Parameters:
- Lookback Period: {best_params['lookback_period']} days
- Top N Assets: {best_params['top_n']}

Training Performance Metrics:
- Sharpe Ratio: {best_params['metrics']['sharpe_ratio']:.4f}
- Total Return: {best_params['metrics']['total_return']:.2%}
- Annualized Return: {best_params['metrics']['annualized_return']:.2%}
- Maximum Drawdown: {best_params['metrics']['max_drawdown']:.2%}
- Volatility: {best_params['metrics']['volatility']:.2%}

2. Validation Results
--------------------
Validation Period: 2023-01-01 to 2025-05-31

Performance Metrics:
- Sharpe Ratio: {val_results['sharpe_ratio']:.4f}
- Total Return: {val_results['total_return']:.2%}
- Annualized Return: {val_results['annualized_return']:.2%}
- Maximum Drawdown: {val_results['max_drawdown']:.2%}
- Volatility: {val_results['volatility']:.2%}

3. Parameter Sensitivity Analysis
-------------------------------
{train_results.to_string()}

4. Performance Charts
-------------------
- Training optimization results saved to: strategy_optimization_results.csv
- Validation performance chart saved to: backtest_performance.png
"""

        with open('strategy_report.txt', 'w') as f:
            f.write(report)

        self.logger.info("Strategy report generated: strategy_report.txt")