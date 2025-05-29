# Data Pipeline CLI Documentation

## Overview

The Data Pipeline CLI is a command-line interface for managing quantitative trading data. It provides commands for running the complete pipeline, updating specific ETFs, validating data, and checking pipeline status.

## Installation

1. **Python Requirements**:
   - Python 3.7 or higher
   - pip (Python package installer)

2. **Install Dependencies**:
   ```bash
   # Create and activate virtual environment (recommended)
   python3 -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On Linux/macOS
   source venv/bin/activate
   
   # Install required packages
   python3 -m pip install -r requirements.txt
   ```

3. **Verify Installation**:
   ```bash
   # Check Python version
   python3 --version
   
   # Check installed packages
   python3 -m pip list
   ```

## Basic Usage

The CLI is accessed through the `cli.py` script:

```bash
python3 src/cli.py <command> [options]
```

## Available Commands

### 1. Run Pipeline (`run`)

Runs the complete data pipeline for all configured ETFs.

```bash
python3 src/cli.py run [--config CONFIG] [--force]
```

Options:
- `--config`: Path to configuration file (default: src/config.json)
- `--force`: Force update even if data exists

Example:
```bash
# Run with default config
python3 src/cli.py run

# Run with custom config
python3 src/cli.py run --config path/to/config.json

# Force update all data
python3 src/cli.py run --force
```

### 2. Update ETF (`update`)

Updates data for a specific ETF.

```bash
python3 src/cli.py update --symbol SYMBOL [--config CONFIG]
```

Options:
- `--symbol`: ETF symbol to update (required)
- `--config`: Path to configuration file (default: src/config.json)

Example:
```bash
# Update CSI 300 ETF
python3 src/cli.py update --symbol 510300

# Update with custom config
python3 src/cli.py update --symbol 510300 --config path/to/config.json
```

### 3. Validate Data (`validate`)

Validates existing data for all ETFs or a specific ETF.

```bash
python3 src/cli.py validate [--symbol SYMBOL] [--config CONFIG]
```

Options:
- `--symbol`: Specific ETF symbol to validate (optional)
- `--config`: Path to configuration file (default: src/config.json)

Example:
```bash
# Validate all ETFs
python3 src/cli.py validate

# Validate specific ETF
python3 src/cli.py validate --symbol 510300
```

### 4. Check Status (`status`)

Shows the current status of the pipeline, including last update time, data points, and indicator calculations.

```bash
python3 src/cli.py status [--config CONFIG]
```

Options:
- `--config`: Path to configuration file (default: src/config.json)

Example:
```bash
# Check status with default config
python3 src/cli.py status

# Check status with custom config
python3 src/cli.py status --config path/to/config.json
```

## Output

### Logging

The CLI provides detailed logging:
- Console output for immediate feedback
- Log file at `logs/pipeline.log` for historical records

Log format:
```
YYYY-MM-DD HH:MM:SS - module - level - message
```

### Status Output

The status command shows:
- Last update time for each ETF
- Number of data points
- Indicator calculation status

Example:
```
Status for 510300:
  Last update: 2024-03-20
  Data points: 2500
  Indicators:
    MA: 2500 values
    RSI: 2500 values
    MACD: 2500 values
    BollingerBands: 2500 values
```

### Validation Output

The validate command shows:
- Missing data points
- Price anomalies
- Volume anomalies
- Data quality issues

Example:
```
Validation issues for 510300:
  - Missing values found: {'volume': 2}
  - Price anomalies found on dates: ['2024-03-15', '2024-03-18']
```

## Error Handling

The CLI provides clear error messages for common issues:
- Configuration file not found
- Invalid ETF symbol
- Database connection errors
- Data collection failures

## Platform Support

The CLI works on:
- Windows (Command Prompt and PowerShell)
- Linux
- macOS

## Best Practices

1. **Regular Updates**:
   ```bash
   # Daily update
   python3 src/cli.py run
   ```

2. **Data Validation**:
   ```bash
   # Validate after updates
   python3 src/cli.py validate
   ```

3. **Status Monitoring**:
   ```bash
   # Check pipeline health
   python3 src/cli.py status
   ```

4. **Configuration Management**:
   - Keep configuration files in version control
   - Use different configs for different environments
   - Document any configuration changes

## Troubleshooting

Common issues and solutions:

1. **Configuration Errors**:
   - Verify config file path
   - Check JSON syntax
   - Ensure all required fields are present

2. **Data Collection Issues**:
   - Check internet connection
   - Verify ETF symbols
   - Check API rate limits

3. **Database Errors**:
   - Verify database path
   - Check file permissions
   - Ensure sufficient disk space

4. **Logging Issues**:
   - Check log directory permissions
   - Verify log file path
   - Check disk space

## Support

For issues and feature requests:
1. Check the logs in `logs/pipeline.log`
2. Review the configuration
3. Check the documentation
4. Contact the development team 