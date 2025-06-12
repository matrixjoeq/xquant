#!/usr/bin/env python3
"""
演示：20日动量轮动策略
====================

策略配置：
- 基于20日动量
- 在创业板、纳指、黄金和30年国债之间轮动
- 只持有动量排名第一的标的
- 回测区间：2022/01/01-2024/12/31
"""

import sys
import os
from pathlib import Path
import logging

# Add src to path for imports
src_path = str(Path(__file__).parent / "src")
sys.path.insert(0, src_path)

from strategy.advanced_momentum_rotation import AdvancedBacktestRunner


def demo_momentum_rotation_strategy():
    """演示20日动量轮动策略"""
    
    print("=" * 80)
    print("20日动量轮动策略演示")
    print("=" * 80)
    print("策略配置：")
    print("- 动量周期：20日")
    print("- 轮动标的：创业板、纳指、黄金、30年国债")
    print("- 持有数量：仅持有排名第一的标的")
    print("- 回测区间：2022/01/01 - 2024/12/31")
    print("=" * 80)
    
    # 初始化回测运行器
    runner = AdvancedBacktestRunner()
    
    # 首先检查数据库中可用的ETF
    print("\n📊 检查数据库中可用的ETF...")
    available_symbols = runner.get_available_symbols()
    print(f"数据库中可用的ETF: {available_symbols}")
    
    # 定义目标ETF映射（根据实际可用数据调整）
    target_etfs = {
        '510300': '沪深300ETF (代表A股市场)',
        '513100': '纳斯达克100ETF', 
        '518880': '黄金ETF',
        '511130': '博时上证30年期国债指数ETF'
    }
    
    # 直接使用目标ETF（已确认在数据库中存在）
    symbols = ['510300', '513100', '518880', '511130']
    print(f"\n🎯 目标ETF配置：")
    for symbol in symbols:
        name = target_etfs.get(symbol, symbol)
        print(f"✅ {symbol} - {name}")
    
    print(f"📊 共选择 {len(symbols)} 个ETF进行轮动")
    
    # 策略参数配置
    strategy_params = {
        # 核心参数
        'lookback_period': 20,          # 20日动量
        'top_n_holdings': 1,            # 只持有排名第一的标的
        'position_size': 0.95,          # 95%仓位投资
        'rebalance_freq': 'weekly',     # 每周轮动检查
        
        # 仓位管理
        'max_position_size': 1.0,       # 允许单个标的占100%仓位
        'min_cash_buffer': 0.05,        # 5%现金缓冲
        
        # 风险管理
        'stop_loss_pct': -0.08,         # 8%止损
        'trailing_stop_pct': 0.05,      # 5%移动止损
        'min_momentum_threshold': -0.05, # 允许轻微负动量
        
        # 交易成本
        'transaction_cost': 0.001,      # 0.1%交易成本
    }
    
    print(f"\n📋 策略参数：")
    for key, value in strategy_params.items():
        if key == 'target_symbols':
            continue
        print(f"  {key}: {value}")
    
    print(f"\n🚀 开始回测...")
    
    try:
        # 运行回测
        results = runner.run_backtest(
            symbols=symbols,
            start_date='2022-01-01',
            end_date='2024-12-31',
            strategy_params=strategy_params,
            initial_capital=1000000.0
        )
        
        # 显示基本结果
        print(f"\n📈 回测结果摘要：")
        print("=" * 50)
        print(f"初始资金: ${results['initial_capital']:,.2f}")
        print(f"最终价值: ${results['final_value']:,.2f}")
        print(f"总收益率: {results['total_return']:.2%}")
        
        strategy_results = results['strategy_results']
        print(f"年化收益率: {strategy_results['annualized_return']:.2%}")
        print(f"夏普比率: {strategy_results['sharpe_ratio']:.2f}")
        print(f"最大回撤: {strategy_results['max_drawdown']:.2%}")
        print(f"波动率: {strategy_results['volatility']:.2%}")
        
        # 分析器结果
        analyzers = results['analyzers']
        if 'trades' in analyzers and analyzers['trades']:
            trades = analyzers['trades']
            total_trades = trades.get('total', {}).get('total', 0)
            won_trades = trades.get('won', {}).get('total', 0)
            lost_trades = trades.get('lost', {}).get('total', 0)
            
            print(f"\n📊 交易分析：")
            print(f"总交易次数: {total_trades}")
            print(f"盈利交易: {won_trades}")
            print(f"亏损交易: {lost_trades}")
            if total_trades > 0:
                win_rate = won_trades / total_trades
                print(f"胜率: {win_rate:.2%}")
        
        # 显示最终持仓
        if 'final_positions' in strategy_results:
            print(f"\n💼 最终持仓：")
            final_positions = strategy_results['final_positions']
            if final_positions:
                for symbol, weight in final_positions.items():
                    etf_name = target_etfs.get(symbol, symbol)
                    print(f"  {symbol} ({etf_name}): {weight:.2%}")
            else:
                print("  持有现金")
        
        # 显示轮动历史的最后几次
        if 'rebalance_history' in strategy_results and strategy_results['rebalance_history']:
            rebalance_history = strategy_results['rebalance_history']
            print(f"\n🔄 最近轮动记录（最后5次）：")
            for rebalance in rebalance_history[-5:]:
                date = rebalance['date']
                selected = rebalance['selected_assets']
                momentum_scores = rebalance['momentum_scores']
                
                print(f"  {date}:")
                if selected:
                    top_asset = selected[0]
                    momentum = momentum_scores.get(top_asset, 0)
                    etf_name = target_etfs.get(top_asset, top_asset)
                    print(f"    选择: {top_asset} ({etf_name}) - 动量: {momentum:.2%}")
                else:
                    print(f"    选择: 持有现金")
        
        # 生成详细报告
        print(f"\n📊 生成详细报告...")
        output_dir = "demo_results"
        os.makedirs(output_dir, exist_ok=True)
        
        runner.generate_performance_report(results, output_dir)
        
        print(f"✅ 详细报告已生成到 '{output_dir}/' 目录")
        print(f"   - 性能图表: {output_dir}/portfolio_performance.png")
        print(f"   - 回撤分析: {output_dir}/drawdown_analysis.png") 
        print(f"   - 文字报告: {output_dir}/performance_report.txt")
        
        # 策略评价
        print(f"\n🎯 策略评价：")
        annual_return = strategy_results['annualized_return']
        max_drawdown = strategy_results['max_drawdown']
        sharpe_ratio = strategy_results['sharpe_ratio']
        
        if annual_return > 0.05:  # 5%
            print(f"✅ 年化收益率 {annual_return:.2%} 表现良好")
        else:
            print(f"⚠️  年化收益率 {annual_return:.2%} 表现一般")
            
        if max_drawdown > -0.15:  # -15%
            print(f"✅ 最大回撤 {max_drawdown:.2%} 控制较好")
        else:
            print(f"⚠️  最大回撤 {max_drawdown:.2%} 风险较高")
            
        if sharpe_ratio > 1.0:
            print(f"✅ 夏普比率 {sharpe_ratio:.2f} 风险调整收益优秀")
        elif sharpe_ratio > 0.5:
            print(f"✅ 夏普比率 {sharpe_ratio:.2f} 风险调整收益良好")
        else:
            print(f"⚠️  夏普比率 {sharpe_ratio:.2f} 风险调整收益一般")
        
        print(f"\n💡 策略建议：")
        print(f"1. 该策略适合趋势明显的市场环境")
        print(f"2. 在震荡市场中可能频繁换手")
        print(f"3. 建议结合宏观环境调整参数")
        print(f"4. 实盘前建议进行更长时间的回测验证")
        
    except Exception as e:
        print(f"❌ 回测执行失败: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        runner._close_db()
    
    print(f"\n" + "=" * 80)
    print("演示完成！")
    print("=" * 80)


if __name__ == "__main__":
    # 设置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 运行演示
    demo_momentum_rotation_strategy() 