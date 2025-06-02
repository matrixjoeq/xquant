#!/usr/bin/env python3
import sys
import os
from pathlib import Path
import logging
import argparse
import backtrader as bt

src_root = str(Path(__file__).parent)
sys.path.insert(0, src_root)

from data.pipeline import DataPipeline
from strategy.momentum_rotation import BacktestRunner

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_data_pipeline(args):
    """Run data pipeline operations."""
    pipeline = DataPipeline()

    if args.data_command == 'run':
        pipeline.update_data(args.symbol)
    elif args.data_command == 'validate':
        results = pipeline.validate_data(args.symbol)
        for symbol, issues in results.items():
            if issues:
                logger.warning(f"Validation issues for {symbol}:")
                for issue in issues:
                    logger.warning(f"  - {issue}")
            else:
                logger.info(f"No validation issues for {symbol}")
    elif args.data_command == 'status':
        status = pipeline.get_status()
        for symbol, info in status.items():
            logger.info(f"\nStatus for {symbol}:")
            logger.info(f"  Last update: {info['last_update']}")
            logger.info(f"  Data points: {info['data_points']}")
            logger.info("  Indicators:")
            for indicator, count in info['indicators'].items():
                logger.info(f"    - {indicator}: {count} values")

def run_strategy(args):
    """Run strategy operations."""
    runner = BacktestRunner()

    try:
        if args.strategy_command == 'optimize':
            logger.info("Starting parameter optimization...")
            best_params, train_results = runner.optimize_parameters(
                train_start=args.train_start,
                train_end=args.train_end,
                lookback_range=args.lookback_range,
                top_n_range=args.top_n_range
            )

            # Validate strategy
            logger.info("Starting strategy validation...")
            val_results = runner.validate_strategy(
                best_params,
                val_start=args.val_start,
                val_end=args.val_end
            )

            # Generate report
            logger.info("Generating strategy report...")
            runner.generate_report(train_results, val_results, best_params)

            logger.info("Strategy analysis completed successfully!")

        elif args.strategy_command == 'validate':
            # Load best parameters from file
            import json
            with open('best_parameters.json', 'r') as f:
                best_params = json.load(f)

            # Run validation
            logger.info("Running strategy validation...")
            val_results = runner.validate_strategy(
                best_params,
                val_start=args.val_start,
                val_end=args.val_end
            )

            # Generate report
            logger.info("Generating validation report...")
            runner.generate_report(None, val_results, best_params)

            logger.info("Validation completed successfully!")

    except Exception as e:
        logger.error(f"Strategy failed: {str(e)}")
        raise
    finally:
        runner._close_db()

def main():
    parser = argparse.ArgumentParser(description='ETF Trading System CLI')
    subparsers = parser.add_subparsers(dest='mode', help='Operation mode')

    # Data pipeline subparser
    data_parser = subparsers.add_parser('data', help='Data pipeline operations')
    data_parser.add_argument('data_command', choices=['run', 'validate', 'status'],
                           help='Data pipeline command to execute')
    data_parser.add_argument('--symbol', help='Optional ETF symbol to process')

    # Strategy subparser
    strategy_parser = subparsers.add_parser('strategy', help='Strategy operations')
    strategy_parser.add_argument('strategy_command', choices=['optimize', 'validate'],
                               help='Strategy command to execute')
    strategy_parser.add_argument('--train-start', default='2013-01-01',
                               help='Training period start date (YYYY-MM-DD)')
    strategy_parser.add_argument('--train-end', default='2022-12-31',
                               help='Training period end date (YYYY-MM-DD)')
    strategy_parser.add_argument('--val-start', default='2023-01-01',
                               help='Validation period start date (YYYY-MM-DD)')
    strategy_parser.add_argument('--val-end', default='2025-05-31',
                               help='Validation period end date (YYYY-MM-DD)')
    strategy_parser.add_argument('--lookback-range', nargs='+', type=int,
                               default=[5, 10, 20, 60, 120],
                               help='Lookback periods to test')
    strategy_parser.add_argument('--holding-range', nargs='+', type=int,
                               default=[5, 10, 20, 60],
                               help='Holding periods to test')
    strategy_parser.add_argument('--top-n-range', nargs='+', type=int,
                               default=[1, 2],
                               help='Top N values to test')

    args = parser.parse_args()

    try:
        if args.mode == 'data':
            run_data_pipeline(args)
        elif args.mode == 'strategy':
            run_strategy(args)
        else:
            parser.print_help()
            sys.exit(1)

    except Exception as e:
        logger.error(f"Operation failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()