# 高级动量轮动策略使用指南

## 策略概述

高级动量轮动策略（Advanced Momentum Rotation Strategy）是一个基于Backtrader框架的灵活量化交易策略，支持多种参数配置和风险管理功能。

### 主要特性

- ✅ **灵活的资产选择**：支持自定义轮动标的列表
- ✅ **可配置动量周期**：自定义动量测量回望期
- ✅ **多标的持有**：同时持有多个表现最佳的资产
- ✅ **智能头寸管理**：可配置总仓位和单个标的最大仓位
- ✅ **风险控制**：止损、移动止损、最小动量阈值
- ✅ **多种轮动频率**：日/周/月轮动
- ✅ **全面的性能分析**：详细的回测报告和图表

## 策略参数详解

### 核心策略参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `lookback_period` | int | 20 | 动量计算回望期（天数） |
| `top_n_holdings` | int | 3 | 同时持有的标的数量 |
| `position_size` | float | 0.95 | 总仓位比例（0.95 = 95%投资） |
| `rebalance_freq` | str | 'weekly' | 轮动频率：'daily', 'weekly', 'monthly' |
| `min_momentum_threshold` | float | 0.0 | 最小动量阈值 |

### 风险管理参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `max_position_size` | float | 0.4 | 单个标的最大仓位比例 |
| `stop_loss_pct` | float | -0.1 | 止损比例（-10%） |
| `trailing_stop_pct` | float | 0.05 | 移动止损比例（5%） |

### 交易参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `transaction_cost` | float | 0.001 | 交易成本（0.1%） |
| `min_cash_buffer` | float | 0.05 | 最小现金缓冲（5%） |

## 快速开始

### 1. 基本使用示例

```python
from src.strategy.advanced_momentum_rotation import AdvancedBacktestRunner

# 初始化回测运行器
runner = AdvancedBacktestRunner()

# 定义策略参数
strategy_params = {
    'lookback_period': 20,        # 20日动量
    'top_n_holdings': 3,          # 持有前3名
    'position_size': 0.95,        # 95%仓位
    'rebalance_freq': 'weekly',   # 周轮动
    'max_position_size': 0.4,     # 单个标的最大40%
    'transaction_cost': 0.001,    # 0.1%交易成本
}

# 定义标的池
symbols = ['510300', '518880', '513100', '511580', '161129']

# 运行回测
results = runner.run_backtest(
    symbols=symbols,
    start_date='2020-01-01',
    end_date='2024-12-31',
    strategy_params=strategy_params,
    initial_capital=1000000.0
)

# 生成性能报告
runner.generate_performance_report(results, "results/my_strategy")
```

### 2. 保守型策略配置

```python
# 保守型策略参数
conservative_params = {
    'lookback_period': 60,        # 更长的动量周期
    'top_n_holdings': 4,          # 更多分散化
    'position_size': 0.80,        # 较低仓位，保留更多现金
    'rebalance_freq': 'monthly',  # 月度轮动，减少交易成本
    'max_position_size': 0.25,    # 更小的单个仓位
    'stop_loss_pct': -0.05,       # 较紧的止损
    'trailing_stop_pct': 0.03,    # 较紧的移动止损
    'min_momentum_threshold': -0.05,  # 允许轻微负动量
}

# 保守型标的池（债券、黄金、防御性股票）
conservative_symbols = ['511580', '511130', '518880', '510300']
```

### 3. 激进型策略配置

```python
# 激进型策略参数
aggressive_params = {
    'lookback_period': 10,        # 短期动量
    'top_n_holdings': 2,          # 集中持有
    'position_size': 0.98,        # 高仓位
    'rebalance_freq': 'daily',    # 日轮动
    'max_position_size': 0.50,    # 允许更大单个仓位
    'stop_loss_pct': -0.15,       # 较宽止损
    'trailing_stop_pct': 0.08,    # 较宽移动止损
    'min_momentum_threshold': 0.01,  # 只选择正动量资产
    'transaction_cost': 0.002,    # 考虑频繁交易的更高成本
}

# 激进型标的池（商品、国际股票）
aggressive_symbols = ['159985', '159980', '161129', '162411', '513100']
```

## 参数优化

### 网格搜索优化

```python
def optimize_parameters():
    runner = AdvancedBacktestRunner()
    
    # 参数范围
    lookback_periods = [10, 20, 40, 60]
    top_n_values = [2, 3, 4]
    rebalance_frequencies = ['weekly', 'monthly']
    
    best_sharpe = -float('inf')
    best_params = None
    
    for lookback in lookback_periods:
        for top_n in top_n_values:
            for rebalance_freq in rebalance_frequencies:
                strategy_params = {
                    'lookback_period': lookback,
                    'top_n_holdings': top_n,
                    'rebalance_freq': rebalance_freq,
                    # ... 其他参数
                }
                
                results = runner.run_backtest(
                    symbols=['510300', '518880', '513100', '511580'],
                    start_date='2020-01-01',
                    end_date='2023-12-31',
                    strategy_params=strategy_params
                )
                
                sharpe_ratio = results['strategy_results']['sharpe_ratio']
                if sharpe_ratio > best_sharpe:
                    best_sharpe = sharpe_ratio
                    best_params = strategy_params
    
    return best_params
```

## 不同资产配置策略

### 1. 股票主导型

**适合场景**：牛市环境，追求高收益
**资产配置**：主要投资股票ETF
```python
equity_symbols = ['510300', '513100', '159561', '513520']
```

### 2. 债券主导型

**适合场景**：熊市环境，追求稳定收益
**资产配置**：主要投资债券ETF
```python
bond_symbols = ['511580', '511130', '511180', '511190']
```

### 3. 商品主导型

**适合场景**：通胀环境，对冲通胀风险
**资产配置**：主要投资商品期货ETF
```python
commodity_symbols = ['518880', '161226', '159985', '159980']
```

### 4. 均衡配置型

**适合场景**：不确定市场环境，追求风险平衡
**资产配置**：各类资产均衡配置
```python
balanced_symbols = ['510300', '518880', '513100', '511580', '161129']
```

## 性能分析

### 关键指标

- **总收益率**：策略期间总收益
- **年化收益率**：考虑复利的年化收益
- **夏普比率**：风险调整后收益
- **最大回撤**：最大亏损幅度
- **波动率**：收益波动程度
- **胜率**：盈利交易占比

### 生成报告

```python
# 运行回测后生成完整报告
runner.generate_performance_report(results, "results/strategy_analysis")
```

报告包含：
- 📊 投资组合价值变化图
- 📈 累计收益曲线
- 📉 回撤分析图
- 📄 详细性能指标报告

## 最佳实践

### 1. 参数设置建议

- **动量周期**：10-60天，较短周期更敏感，较长周期更稳定
- **持有数量**：2-5个，过少集中风险，过多分散效果
- **轮动频率**：周度平衡了敏感性和交易成本
- **仓位控制**：总仓位85-95%，单个仓位不超过40%

### 2. 风险管理

- 设置合理的止损水平（-5%到-15%）
- 使用移动止损锁定利润
- 设定最小动量阈值避免弱势资产
- 保持适当现金缓冲

### 3. 回测验证

- 使用足够长的历史数据（至少3年）
- 进行样本外验证
- 考虑不同市场环境（牛市、熊市、震荡市）
- 测试参数稳定性

## 注意事项

### 1. 数据质量
- 确保价格数据完整无缺失
- 使用复权价格进行准确计算
- 定期更新数据

### 2. 交易成本
- 考虑实际交易成本和滑点
- 频繁轮动会增加交易成本
- 选择低费率的交易平台

### 3. 市场环境
- 动量策略在趋势市场表现更好
- 震荡市场可能频繁止损
- 考虑宏观经济环境影响

### 4. 资金管理
- 不要使用全部资金
- 保持资金流动性
- 考虑资金规模对交易的影响

## 总结

高级动量轮动策略提供了一个灵活、强大的量化交易框架。通过合理的参数配置和风险管理，可以在不同市场环境下获得较好的风险调整收益。

关键成功要素：
1. 选择合适的资产池
2. 优化策略参数
3. 严格的风险控制
4. 持续的监控和调整

建议在实盘交易前进行充分的回测验证和模拟交易。 