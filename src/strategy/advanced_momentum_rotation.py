#!/usr/bin/env python3
"""
Advanced Momentum Rotation Strategy
===================================

A flexible momentum rotation strategy that supports:
- Configurable asset universe
- Adjustable momentum lookback period
- Multiple holdings (top N assets)
- Flexible position sizing
- Risk management controls
"""

import pandas as pd
import numpy as np
import sqlite3
from typing import List, Dict, Tuple, Optional
import logging
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import seaborn as sns
import backtrader as bt
import backtrader.analyzers as btanalyzers
from collections import defaultdict


class AdvancedMomentumRotationStrategy(bt.Strategy):
    """Advanced Momentum Rotation Strategy with flexible parameters."""
    
    params = (
        # Core strategy parameters
        ('lookback_period', 20),        # Momentum calculation period
        ('top_n_holdings', 3),          # Number of top assets to hold
        ('position_size', 0.95),        # Total position size (0.95 = 95% invested)
        ('rebalance_freq', 'weekly'),   # Rebalancing frequency: 'daily', 'weekly', 'monthly'
        ('min_momentum_threshold', 0.0), # Minimum momentum to consider buying
        
        # Risk management parameters
        ('max_position_size', 0.4),     # Maximum single position size
        ('stop_loss_pct', -0.1),        # Stop loss percentage (-10%)
        ('trailing_stop_pct', 0.05),    # Trailing stop percentage (5%)
        
        # Trading parameters
        ('transaction_cost', 0.001),    # Transaction cost (0.1%)
        ('min_cash_buffer', 0.05),      # Minimum cash buffer (5%)
        
        # Asset universe (will be set dynamically)
        ('target_symbols', []),         # List of symbols to rotate among
    )
    
    def __init__(self):
        """Initialize the strategy."""
        self.logger = logging.getLogger(__name__)
        
        # Strategy state
        self.current_positions = {}  # {symbol: position_size}
        self.momentum_scores = {}    # {symbol: momentum_score}
        self.last_rebalance_date = None
        self.pending_orders = []
        self.stop_losses = {}        # {symbol: stop_loss_price}
        self.trailing_stops = {}     # {symbol: trailing_stop_price}
        
        # Performance tracking
        self.portfolio_values = []
        self.trade_history = []
        self.rebalance_history = []
        
        # Validate parameters
        self._validate_parameters()
        
        self.logger.info(f"Strategy initialized with parameters:")
        self.logger.info(f"  - Lookback period: {self.params.lookback_period}")
        self.logger.info(f"  - Top N holdings: {self.params.top_n_holdings}")
        self.logger.info(f"  - Position size: {self.params.position_size:.2%}")
        self.logger.info(f"  - Rebalance frequency: {self.params.rebalance_freq}")
        self.logger.info(f"  - Target symbols: {len(self.params.target_symbols)} assets")
    
    def _validate_parameters(self):
        """Validate strategy parameters."""
        if self.params.top_n_holdings <= 0:
            raise ValueError("top_n_holdings must be positive")
        
        if not (0 < self.params.position_size <= 1):
            raise ValueError("position_size must be between 0 and 1")
        
        if not (0 < self.params.max_position_size <= 1):
            raise ValueError("max_position_size must be between 0 and 1")
        
        if self.params.rebalance_freq not in ['daily', 'weekly', 'monthly']:
            raise ValueError("rebalance_freq must be 'daily', 'weekly', or 'monthly'")
        
        if self.params.lookback_period <= 0:
            raise ValueError("lookback_period must be positive")
    
    def next(self):
        """Main strategy logic called on each bar."""
        current_date = self.data0.datetime.date(0)
        
        # Track portfolio value
        self.portfolio_values.append({
            'date': current_date,
            'value': self.broker.getvalue(),
            'cash': self.broker.getcash()
        })
        
        # Check for pending orders
        if self.pending_orders:
            return
        
        # Check stop losses and trailing stops
        self._check_risk_controls()
        
        # Check if it's time to rebalance
        if self._should_rebalance(current_date):
            self._execute_rebalance()
    
    def _should_rebalance(self, current_date) -> bool:
        """Determine if rebalancing should occur."""
        if self.last_rebalance_date is None:
            return True
        
        days_since_rebalance = (current_date - self.last_rebalance_date).days
        
        if self.params.rebalance_freq == 'daily':
            return days_since_rebalance >= 1
        elif self.params.rebalance_freq == 'weekly':
            return days_since_rebalance >= 7
        elif self.params.rebalance_freq == 'monthly':
            return days_since_rebalance >= 30
        
        return False
    
    def _calculate_momentum_scores(self) -> Dict[str, float]:
        """Calculate momentum scores for all assets."""
        momentum_scores = {}
        
        for data in self.datas:
            symbol = data._name
            
            # Skip if symbol not in target list
            if self.params.target_symbols and symbol not in self.params.target_symbols:
                continue
            
            # Check if we have enough data
            if len(data) < self.params.lookback_period:
                continue
            
            # Calculate momentum (total return over lookback period)
            try:
                current_price = data.close[0]
                past_price = data.close[-self.params.lookback_period]
                momentum = (current_price / past_price) - 1.0
                
                # Apply minimum threshold
                if momentum >= self.params.min_momentum_threshold:
                    momentum_scores[symbol] = momentum
                    
            except (IndexError, ZeroDivisionError):
                continue
        
        return momentum_scores
    
    def _select_top_assets(self, momentum_scores: Dict[str, float]) -> List[str]:
        """Select top N assets based on momentum scores."""
        if not momentum_scores:
            return []
        
        # Sort by momentum score (descending)
        sorted_assets = sorted(momentum_scores.items(), key=lambda x: x[1], reverse=True)
        
        # Select top N
        top_assets = [asset for asset, score in sorted_assets[:self.params.top_n_holdings]]
        
        return top_assets
    
    def _calculate_target_positions(self, selected_assets: List[str]) -> Dict[str, float]:
        """Calculate target position sizes for selected assets."""
        if not selected_assets:
            return {}
        
        # Calculate equal weight for each asset
        total_position_size = self.params.position_size
        n_assets = len(selected_assets)
        equal_weight = total_position_size / n_assets
        
        # Apply maximum position size constraint
        position_size = min(equal_weight, self.params.max_position_size)
        
        # Create target positions
        target_positions = {}
        for asset in selected_assets:
            target_positions[asset] = position_size
        
        return target_positions
    
    def _execute_rebalance(self):
        """Execute portfolio rebalancing."""
        current_date = self.data0.datetime.date(0)
        
        # Calculate momentum scores
        momentum_scores = self._calculate_momentum_scores()
        self.momentum_scores = momentum_scores
        
        # Select top assets
        selected_assets = self._select_top_assets(momentum_scores)
        
        # Calculate target positions
        target_positions = self._calculate_target_positions(selected_assets)
        
        # Execute trades to reach target positions
        self._execute_trades(target_positions)
        
        # Update state
        self.last_rebalance_date = current_date
        self.current_positions = target_positions.copy()
        
        # Log rebalancing
        self.rebalance_history.append({
            'date': current_date,
            'selected_assets': selected_assets,
            'momentum_scores': momentum_scores.copy(),
            'target_positions': target_positions.copy()
        })
        
        self.logger.info(f"Rebalanced on {current_date}")
        self.logger.info(f"Selected assets: {selected_assets}")
        self.logger.info(f"Momentum scores: {momentum_scores}")
    
    def _execute_trades(self, target_positions: Dict[str, float]):
        """Execute trades to reach target positions."""
        portfolio_value = self.broker.getvalue()
        
        # Get current positions
        current_positions = {}
        for data in self.datas:
            symbol = data._name
            position = self.getposition(data)
            if position.size != 0:
                current_positions[symbol] = position.size * data.close[0] / portfolio_value
        
        # Calculate trades needed
        trades_to_execute = []
        
        # Close positions not in target
        for symbol, current_weight in current_positions.items():
            if symbol not in target_positions:
                # Sell entire position
                data = self.getdatabyname(symbol)
                position = self.getposition(data)
                if position.size > 0:
                    trades_to_execute.append(('sell', symbol, position.size))
        
        # Adjust positions for target assets
        for symbol, target_weight in target_positions.items():
            current_weight = current_positions.get(symbol, 0.0)
            weight_diff = target_weight - current_weight
            
            if abs(weight_diff) > 0.01:  # Only trade if difference > 1%
                data = self.getdatabyname(symbol)
                current_price = data.close[0]
                
                # Calculate shares to trade
                target_value = target_weight * portfolio_value
                current_value = current_weight * portfolio_value
                trade_value = target_value - current_value
                shares_to_trade = int(trade_value / current_price)
                
                if shares_to_trade > 0:
                    trades_to_execute.append(('buy', symbol, shares_to_trade))
                elif shares_to_trade < 0:
                    trades_to_execute.append(('sell', symbol, abs(shares_to_trade)))
        
        # Execute trades
        for trade_type, symbol, shares in trades_to_execute:
            data = self.getdatabyname(symbol)
            
            if trade_type == 'buy':
                order = self.buy(data=data, size=shares)
                self.logger.info(f"BUY {shares} shares of {symbol}")
            else:
                order = self.sell(data=data, size=shares)
                self.logger.info(f"SELL {shares} shares of {symbol}")
            
            if order:
                self.pending_orders.append(order)
                self.trade_history.append({
                    'date': self.data0.datetime.date(0),
                    'symbol': symbol,
                    'action': trade_type,
                    'shares': shares,
                    'price': data.close[0]
                })
    
    def _check_risk_controls(self):
        """Check and execute risk control measures."""
        for data in self.datas:
            symbol = data._name
            position = self.getposition(data)
            
            if position.size > 0:
                current_price = data.close[0]
                entry_price = position.price
                
                # Calculate return
                current_return = (current_price / entry_price) - 1.0
                
                # Check stop loss
                if current_return <= self.params.stop_loss_pct:
                    order = self.sell(data=data, size=position.size)
                    if order:
                        self.pending_orders.append(order)
                        self.logger.info(f"STOP LOSS triggered for {symbol} at {current_return:.2%}")
                
                # Update trailing stop
                if symbol not in self.trailing_stops:
                    self.trailing_stops[symbol] = current_price
                else:
                    # Update trailing stop if price moved favorably
                    if current_price > self.trailing_stops[symbol]:
                        self.trailing_stops[symbol] = current_price
                    
                    # Check trailing stop
                    trailing_return = (current_price / self.trailing_stops[symbol]) - 1.0
                    if trailing_return <= -self.params.trailing_stop_pct:
                        order = self.sell(data=data, size=position.size)
                        if order:
                            self.pending_orders.append(order)
                            self.logger.info(f"TRAILING STOP triggered for {symbol}")
    
    def notify_order(self, order):
        """Handle order notifications."""
        if order.status in [order.Submitted, order.Accepted]:
            return
        
        if order.status in [order.Completed]:
            if order.isbuy():
                self.logger.info(f'BUY EXECUTED: {order.data._name} @ {order.executed.price:.2f}')
            else:
                self.logger.info(f'SELL EXECUTED: {order.data._name} @ {order.executed.price:.2f}')
        
        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.logger.warning(f'ORDER FAILED: {order.data._name} - Status: {order.status}')
        
        # Remove from pending orders
        if order in self.pending_orders:
            self.pending_orders.remove(order)
    
    def stop(self):
        """Called when strategy execution is complete."""
        # Calculate final performance metrics
        if self.portfolio_values:
            df_portfolio = pd.DataFrame(self.portfolio_values)
            df_portfolio.set_index('date', inplace=True)
            
            # Calculate returns
            df_portfolio['returns'] = df_portfolio['value'].pct_change()
            
            # Calculate metrics
            total_return = (df_portfolio['value'].iloc[-1] / df_portfolio['value'].iloc[0]) - 1
            annualized_return = (1 + total_return) ** (252 / len(df_portfolio)) - 1
            volatility = df_portfolio['returns'].std() * np.sqrt(252)
            sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
            
            # Calculate maximum drawdown
            cumulative_returns = (1 + df_portfolio['returns']).cumprod()
            running_max = cumulative_returns.expanding().max()
            drawdown = (cumulative_returns / running_max) - 1
            max_drawdown = drawdown.min()
            
            # Store results
            self.results = {
                'total_return': total_return,
                'annualized_return': annualized_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'portfolio_values': df_portfolio,
                'trade_history': self.trade_history,
                'rebalance_history': self.rebalance_history,
                'final_positions': self.current_positions
            }
            
            self.logger.info(f"Strategy completed:")
            self.logger.info(f"  Total Return: {total_return:.2%}")
            self.logger.info(f"  Annualized Return: {annualized_return:.2%}")
            self.logger.info(f"  Volatility: {volatility:.2%}")
            self.logger.info(f"  Sharpe Ratio: {sharpe_ratio:.2f}")
            self.logger.info(f"  Max Drawdown: {max_drawdown:.2%}")


class AdvancedBacktestRunner:
    """Advanced backtest runner for the momentum rotation strategy."""
    
    def __init__(self, db_path: str = "data/akshare/market_data.db"):
        """Initialize the backtest runner."""
        self.logger = logging.getLogger(__name__)
        self.db_path = db_path
        self.conn = None
    
    def _connect_db(self):
        """Connect to the database."""
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path)
    
    def _close_db(self):
        """Close database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols in the database."""
        self._connect_db()
        query = "SELECT DISTINCT symbol FROM daily_prices ORDER BY symbol"
        df = pd.read_sql_query(query, self.conn)
        return df['symbol'].tolist()
    
    def get_price_data(self, 
                      symbols: List[str], 
                      start_date: str, 
                      end_date: str,
                      price_type: str = 'non_restored') -> Dict[str, pd.DataFrame]:
        """Get price data for specified symbols."""
        self._connect_db()
        price_data = {}
        
        for symbol in symbols:
            query = f"""
            SELECT date, open, high, low, close, volume
            FROM daily_prices
            WHERE symbol = '{symbol}'
            AND price_type = '{price_type}'
            AND date BETWEEN '{start_date}' AND '{end_date}'
            ORDER BY date
            """
            
            try:
                df = pd.read_sql_query(query, self.conn)
                if not df.empty:
                    df['date'] = pd.to_datetime(df['date'])
                    df.set_index('date', inplace=True)
                    price_data[symbol] = df
                    self.logger.info(f"Loaded {len(df)} records for {symbol}")
                else:
                    self.logger.warning(f"No data found for {symbol}")
            except Exception as e:
                self.logger.error(f"Error loading data for {symbol}: {e}")
        
        return price_data
    
    def run_backtest(self,
                    symbols: List[str],
                    start_date: str,
                    end_date: str,
                    strategy_params: Dict,
                    initial_capital: float = 1000000.0) -> Dict:
        """Run backtest with specified parameters."""
        
        # Get price data
        price_data = self.get_price_data(symbols, start_date, end_date)
        
        if not price_data:
            raise ValueError("No price data available for the specified symbols and date range")
        
        # Create cerebro engine
        cerebro = bt.Cerebro()
        
        # Add strategy with parameters
        strategy_params['target_symbols'] = symbols
        cerebro.addstrategy(AdvancedMomentumRotationStrategy, **strategy_params)
        
        # Add data feeds
        for symbol, data in price_data.items():
            feed = bt.feeds.PandasData(
                dataname=data,
                name=symbol,
                datetime=None,
                open='open',
                high='high',
                low='low',
                close='close',
                volume='volume',
                openinterest=-1
            )
            cerebro.adddata(feed)
        
        # Set broker parameters
        cerebro.broker.setcash(initial_capital)
        cerebro.broker.setcommission(
            commission=strategy_params.get('transaction_cost', 0.001)
        )
        
        # Add analyzers
        cerebro.addanalyzer(btanalyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(btanalyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(btanalyzers.Returns, _name='returns')
        cerebro.addanalyzer(btanalyzers.TradeAnalyzer, _name='trades')
        
        # Run backtest
        self.logger.info(f"Running backtest from {start_date} to {end_date}")
        self.logger.info(f"Symbols: {symbols}")
        self.logger.info(f"Strategy parameters: {strategy_params}")
        
        results = cerebro.run()
        strategy = results[0]
        
        # Extract results
        final_value = cerebro.broker.getvalue()
        
        backtest_results = {
            'initial_capital': initial_capital,
            'final_value': final_value,
            'total_return': (final_value / initial_capital) - 1,
            'strategy_results': strategy.results,
            'analyzers': {
                'sharpe': results[0].analyzers.sharpe.get_analysis(),
                'drawdown': results[0].analyzers.drawdown.get_analysis(),
                'returns': results[0].analyzers.returns.get_analysis(),
                'trades': results[0].analyzers.trades.get_analysis()
            }
        }
        
        return backtest_results
    
    def generate_performance_report(self, results: Dict, output_dir: str = "results"):
        """Generate comprehensive performance report."""
        import os
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Extract data
        strategy_results = results['strategy_results']
        portfolio_df = strategy_results['portfolio_values']
        
        # Generate plots
        self._plot_portfolio_performance(portfolio_df, output_dir)
        self._plot_drawdown(portfolio_df, output_dir)
        
        # Generate text report
        self._generate_text_report(results, output_dir)
        
        self.logger.info(f"Performance report generated in {output_dir}/")
    
    def _plot_portfolio_performance(self, portfolio_df: pd.DataFrame, output_dir: str):
        """Plot portfolio performance."""
        plt.figure(figsize=(12, 8))
        
        plt.subplot(2, 1, 1)
        plt.plot(portfolio_df.index, portfolio_df['value'])
        plt.title('Portfolio Value Over Time')
        plt.ylabel('Portfolio Value')
        plt.grid(True)
        
        plt.subplot(2, 1, 2)
        plt.plot(portfolio_df.index, portfolio_df['returns'].cumsum())
        plt.title('Cumulative Returns')
        plt.ylabel('Cumulative Returns')
        plt.xlabel('Date')
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/portfolio_performance.png", dpi=300, bbox_inches='tight')
        plt.show()
    
    def _plot_drawdown(self, portfolio_df: pd.DataFrame, output_dir: str):
        """Plot drawdown analysis."""
        returns = portfolio_df['returns']
        cumulative_returns = (1 + returns).cumprod()
        running_max = cumulative_returns.expanding().max()
        drawdown = (cumulative_returns / running_max) - 1
        
        plt.figure(figsize=(12, 6))
        plt.fill_between(drawdown.index, drawdown, 0, alpha=0.3, color='red')
        plt.plot(drawdown.index, drawdown, color='red', linewidth=1)
        plt.title('Drawdown Analysis')
        plt.ylabel('Drawdown')
        plt.xlabel('Date')
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/drawdown_analysis.png", dpi=300, bbox_inches='tight')
        plt.show()
    
    def _generate_text_report(self, results: Dict, output_dir: str):
        """Generate text performance report."""
        strategy_results = results['strategy_results']
        analyzers = results['analyzers']
        
        report = f"""
Advanced Momentum Rotation Strategy - Performance Report
========================================================

1. Overall Performance
---------------------
Initial Capital: ${results['initial_capital']:,.2f}
Final Value: ${results['final_value']:,.2f}
Total Return: {results['total_return']:.2%}
Annualized Return: {strategy_results['annualized_return']:.2%}
Volatility: {strategy_results['volatility']:.2%}
Sharpe Ratio: {strategy_results['sharpe_ratio']:.2f}
Maximum Drawdown: {strategy_results['max_drawdown']:.2%}

2. Trade Analysis
----------------
Total Trades: {analyzers['trades'].get('total', {}).get('total', 0)}
Winning Trades: {analyzers['trades'].get('won', {}).get('total', 0)}
Losing Trades: {analyzers['trades'].get('lost', {}).get('total', 0)}
Win Rate: {analyzers['trades'].get('won', {}).get('total', 0) / max(analyzers['trades'].get('total', {}).get('total', 1), 1):.2%}

3. Drawdown Analysis
-------------------
Maximum Drawdown: {analyzers['drawdown'].get('max', {}).get('drawdown', 0):.2%}
Drawdown Duration: {analyzers['drawdown'].get('max', {}).get('len', 0)} days

4. Final Positions
-----------------
"""
        
        if 'final_positions' in strategy_results:
            for symbol, weight in strategy_results['final_positions'].items():
                report += f"{symbol}: {weight:.2%}\n"
        
        # Save report
        with open(f"{output_dir}/performance_report.txt", 'w') as f:
            f.write(report)


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    runner = AdvancedBacktestRunner()
    
    # Strategy parameters
    strategy_params = {
        'lookback_period': 20,
        'top_n_holdings': 3,
        'position_size': 0.95,
        'rebalance_freq': 'weekly',
        'max_position_size': 0.4,
        'stop_loss_pct': -0.1,
        'trailing_stop_pct': 0.05,
        'transaction_cost': 0.001,
        'min_momentum_threshold': 0.0
    }
    
    # Asset universe
    symbols = ['510300', '518880', '513100', '511580', '511130']
    
    try:
        results = runner.run_backtest(
            symbols=symbols,
            start_date='2020-01-01',
            end_date='2024-12-31',
            strategy_params=strategy_params,
            initial_capital=1000000.0
        )
        
        runner.generate_performance_report(results)
        
    except Exception as e:
        logging.error(f"Backtest failed: {e}")
    finally:
        runner._close_db() 