#!/usr/bin/env python3
import sys
from pathlib import Path
import logging
import argparse
from src.data.pipeline import DataPipeline

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='ETF Data Pipeline CLI')
    parser.add_argument('command', choices=['run', 'validate', 'status'],
                      help='Command to execute')
    parser.add_argument('--symbol', help='Optional ETF symbol to process')
    args = parser.parse_args()
    
    try:
        pipeline = DataPipeline()
        
        if args.command == 'run':
            pipeline.update_data(args.symbol)
        elif args.command == 'validate':
            results = pipeline.validate_data(args.symbol)
            for symbol, issues in results.items():
                if issues:
                    logger.warning(f"Validation issues for {symbol}:")
                    for issue in issues:
                        logger.warning(f"  - {issue}")
                else:
                    logger.info(f"No validation issues for {symbol}")
        elif args.command == 'status':
            status = pipeline.get_status()
            for symbol, info in status.items():
                logger.info(f"\nStatus for {symbol}:")
                logger.info(f"  Last update: {info['last_update']}")
                logger.info(f"  Data points: {info['data_points']}")
                logger.info("  Indicators:")
                for indicator, count in info['indicators'].items():
                    logger.info(f"    - {indicator}: {count} values")
                    
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    # Add project root to Python path
    project_root = str(Path(__file__).parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    main()