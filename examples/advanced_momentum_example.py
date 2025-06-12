#!/usr/bin/env python3
"""
Advanced Momentum Rotation Strategy - Usage Examples
====================================================

This file demonstrates how to use the Advanced Momentum Rotation Strategy
with various parameter configurations and asset universes.
"""

import sys
import os
from pathlib import Path
import logging

# Add src to path for imports
src_path = str(Path(__file__).parent.parent / "src")
sys.path.insert(0, src_path)

from strategy.advanced_momentum_rotation import AdvancedBacktestRunner


def example_1_basic_usage():
    """Example 1: Basic usage with default parameters."""
    print("\n" + "="*60)
    print("Example 1: Basic Momentum Rotation Strategy")
    print("="*60)
    
    runner = AdvancedBacktestRunner()
    
    # Basic strategy parameters
    strategy_params = {
        'lookback_period': 20,        # 20-day momentum
        'top_n_holdings': 3,          # Hold top 3 assets
        'position_size': 0.95,        # 95% invested
        'rebalance_freq': 'weekly',   # Weekly rebalancing
        'max_position_size': 0.4,     # Max 40% per position
        'transaction_cost': 0.001,    # 0.1% transaction cost
    }
    
    # Basic asset universe (equity-focused)
    symbols = ['510300', '518880', '513100', '159561', '513520']
    
    try:
        results = runner.run_backtest(
            symbols=symbols,
            start_date='2020-01-01',
            end_date='2024-12-31',
            strategy_params=strategy_params,
            initial_capital=1000000.0
        )
        
        print(f"Final Portfolio Value: ${results['final_value']:,.2f}")
        print(f"Total Return: {results['total_return']:.2%}")
        print(f"Sharpe Ratio: {results['strategy_results']['sharpe_ratio']:.2f}")
        
        # Generate detailed report
        runner.generate_performance_report(results, "results/example_1")
        
    except Exception as e:
        print(f"Example 1 failed: {e}")
    finally:
        runner._close_db()


def example_2_conservative_strategy():
    """Example 2: Conservative strategy with bonds and defensive assets."""
    print("\n" + "="*60)
    print("Example 2: Conservative Multi-Asset Strategy")
    print("="*60)
    
    runner = AdvancedBacktestRunner()
    
    # Conservative strategy parameters
    strategy_params = {
        'lookback_period': 60,        # Longer momentum period
        'top_n_holdings': 4,          # Hold top 4 assets
        'position_size': 0.80,        # 80% invested (20% cash buffer)
        'rebalance_freq': 'monthly',  # Monthly rebalancing
        'max_position_size': 0.25,    # Max 25% per position
        'stop_loss_pct': -0.05,       # 5% stop loss
        'trailing_stop_pct': 0.03,    # 3% trailing stop
        'transaction_cost': 0.001,
        'min_momentum_threshold': -0.05,  # Allow negative momentum up to -5%
    }
    
    # Conservative asset universe (bonds, gold, defensive equities)
    symbols = ['511580', '511130', '518880', '161226', '510300']
    
    try:
        results = runner.run_backtest(
            symbols=symbols,
            start_date='2020-01-01',
            end_date='2024-12-31',
            strategy_params=strategy_params,
            initial_capital=1000000.0
        )
        
        print(f"Final Portfolio Value: ${results['final_value']:,.2f}")
        print(f"Total Return: {results['total_return']:.2%}")
        print(f"Max Drawdown: {results['strategy_results']['max_drawdown']:.2%}")
        print(f"Volatility: {results['strategy_results']['volatility']:.2%}")
        
        runner.generate_performance_report(results, "results/example_2")
        
    except Exception as e:
        print(f"Example 2 failed: {e}")
    finally:
        runner._close_db()


def example_3_aggressive_strategy():
    """Example 3: Aggressive strategy with commodities and international exposure."""
    print("\n" + "="*60)
    print("Example 3: Aggressive Global Multi-Asset Strategy")
    print("="*60)
    
    runner = AdvancedBacktestRunner()
    
    # Aggressive strategy parameters
    strategy_params = {
        'lookback_period': 10,        # Short momentum period
        'top_n_holdings': 2,          # Concentrated holdings
        'position_size': 0.98,        # 98% invested
        'rebalance_freq': 'daily',    # Daily rebalancing
        'max_position_size': 0.50,    # Max 50% per position
        'stop_loss_pct': -0.15,       # 15% stop loss
        'trailing_stop_pct': 0.08,    # 8% trailing stop
        'transaction_cost': 0.002,    # Higher transaction cost for frequent trading
        'min_momentum_threshold': 0.01,  # Only positive momentum assets
    }
    
    # Aggressive asset universe (commodities, international equities)
    symbols = ['159985', '159980', '161129', '162411', '513100']
    
    try:
        results = runner.run_backtest(
            symbols=symbols,
            start_date='2020-01-01',
            end_date='2024-12-31',
            strategy_params=strategy_params,
            initial_capital=1000000.0
        )
        
        print(f"Final Portfolio Value: ${results['final_value']:,.2f}")
        print(f"Total Return: {results['total_return']:.2%}")
        print(f"Sharpe Ratio: {results['strategy_results']['sharpe_ratio']:.2f}")
        print(f"Max Drawdown: {results['strategy_results']['max_drawdown']:.2%}")
        
        runner.generate_performance_report(results, "results/example_3")
        
    except Exception as e:
        print(f"Example 3 failed: {e}")
    finally:
        runner._close_db()


def example_4_parameter_optimization():
    """Example 4: Parameter optimization across different configurations."""
    print("\n" + "="*60)
    print("Example 4: Parameter Optimization")
    print("="*60)
    
    runner = AdvancedBacktestRunner()
    
    # Asset universe for optimization
    symbols = ['510300', '518880', '513100', '511580', '159985']
    
    # Parameter ranges to test
    lookback_periods = [10, 20, 40, 60]
    top_n_values = [2, 3, 4]
    rebalance_frequencies = ['weekly', 'monthly']
    
    best_result = None
    best_sharpe = -float('inf')
    
    print("Testing parameter combinations...")
    
    for lookback in lookback_periods:
        for top_n in top_n_values:
            for rebalance_freq in rebalance_frequencies:
                
                strategy_params = {
                    'lookback_period': lookback,
                    'top_n_holdings': top_n,
                    'position_size': 0.90,
                    'rebalance_freq': rebalance_freq,
                    'max_position_size': 0.35,
                    'transaction_cost': 0.001,
                }
                
                try:
                    results = runner.run_backtest(
                        symbols=symbols,
                        start_date='2020-01-01',
                        end_date='2023-12-31',  # Shorter period for optimization
                        strategy_params=strategy_params,
                        initial_capital=1000000.0
                    )
                    
                    sharpe_ratio = results['strategy_results']['sharpe_ratio']
                    total_return = results['total_return']
                    max_drawdown = results['strategy_results']['max_drawdown']
                    
                    print(f"Lookback: {lookback:2d}, Top N: {top_n}, Freq: {rebalance_freq:7s} "
                          f"| Sharpe: {sharpe_ratio:5.2f}, Return: {total_return:6.2%}, "
                          f"Drawdown: {max_drawdown:6.2%}")
                    
                    if sharpe_ratio > best_sharpe:
                        best_sharpe = sharpe_ratio
                        best_result = {
                            'params': strategy_params.copy(),
                            'results': results
                        }
                
                except Exception as e:
                    print(f"Failed for lookback={lookback}, top_n={top_n}, freq={rebalance_freq}: {e}")
    
    if best_result:
        print(f"\nBest Parameters (Sharpe Ratio: {best_sharpe:.2f}):")
        for key, value in best_result['params'].items():
            print(f"  {key}: {value}")
        
        # Generate report for best parameters
        runner.generate_performance_report(best_result['results'], "results/example_4_best")
    
    runner._close_db()


def example_5_custom_asset_universe():
    """Example 5: Custom asset universe selection."""
    print("\n" + "="*60)
    print("Example 5: Custom Asset Universe Analysis")
    print("="*60)
    
    runner = AdvancedBacktestRunner()
    
    # Get all available symbols
    available_symbols = runner.get_available_symbols()
    print(f"Available symbols in database: {available_symbols}")
    
    # Define different asset universes for comparison
    asset_universes = {
        'Equity_Heavy': ['510300', '513100', '159561', '513520'],
        'Bond_Heavy': ['511580', '511130', '511180', '511190'],
        'Commodity_Heavy': ['518880', '161226', '159985', '159980'],
        'Balanced': ['510300', '518880', '513100', '511580', '161129'],
        'All_Assets': ['510300', '518880', '513100', '511580', '159985', 
                       '161226', '159561', '161129']
    }
    
    # Standard strategy parameters
    strategy_params = {
        'lookback_period': 20,
        'top_n_holdings': 3,
        'position_size': 0.90,
        'rebalance_freq': 'weekly',
        'max_position_size': 0.35,
        'transaction_cost': 0.001,
    }
    
    results_comparison = {}
    
    for universe_name, symbols in asset_universes.items():
        # Filter symbols that exist in database
        available_symbols_in_universe = [s for s in symbols if s in available_symbols]
        
        if len(available_symbols_in_universe) < 2:
            print(f"Skipping {universe_name}: insufficient symbols")
            continue
        
        print(f"\nTesting {universe_name}: {available_symbols_in_universe}")
        
        try:
            results = runner.run_backtest(
                symbols=available_symbols_in_universe,
                start_date='2020-01-01',
                end_date='2024-12-31',
                strategy_params=strategy_params,
                initial_capital=1000000.0
            )
            
            results_comparison[universe_name] = {
                'total_return': results['total_return'],
                'sharpe_ratio': results['strategy_results']['sharpe_ratio'],
                'max_drawdown': results['strategy_results']['max_drawdown'],
                'volatility': results['strategy_results']['volatility']
            }
            
            print(f"  Total Return: {results['total_return']:.2%}")
            print(f"  Sharpe Ratio: {results['strategy_results']['sharpe_ratio']:.2f}")
            print(f"  Max Drawdown: {results['strategy_results']['max_drawdown']:.2%}")
            
        except Exception as e:
            print(f"  Failed: {e}")
    
    # Summary comparison
    if results_comparison:
        print(f"\n{'Universe':<15} {'Return':<8} {'Sharpe':<7} {'Drawdown':<9} {'Volatility':<10}")
        print("-" * 60)
        
        for universe, metrics in results_comparison.items():
            print(f"{universe:<15} {metrics['total_return']:>7.2%} "
                  f"{metrics['sharpe_ratio']:>6.2f} {metrics['max_drawdown']:>8.2%} "
                  f"{metrics['volatility']:>9.2%}")
    
    runner._close_db()


def main():
    """Run all examples."""
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Advanced Momentum Rotation Strategy - Examples")
    print("=" * 50)
    
    # Create results directory
    os.makedirs("results", exist_ok=True)
    
    # Run examples
    try:
        example_1_basic_usage()
        example_2_conservative_strategy()
        example_3_aggressive_strategy()
        example_4_parameter_optimization()
        example_5_custom_asset_universe()
        
        print("\n" + "="*60)
        print("All examples completed successfully!")
        print("Check the 'results/' directory for detailed reports and charts.")
        print("="*60)
        
    except Exception as e:
        print(f"Examples failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main() 