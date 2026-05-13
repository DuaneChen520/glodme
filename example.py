
"""
黄金ETF日内做T系统 - 示例脚本

本示例展示如何使用系统的核心功能进行回测和策略分析
"""

import pandas as pd
import numpy as np
from datetime import datetime
import matplotlib.pyplot as plt

from config import TICKER, ASSET_NAME
from data_fetcher import DataFetcher
from strategy import IntradayT0Strategy
from risk_manager import RiskManager


def example_backtest():
    """示例：运行策略回测"""
    print("=" * 60)
    print("示例1：运行策略回测")
    print("=" * 60)
    
    # 初始化组件
    data_fetcher = DataFetcher()
    strategy = IntradayT0Strategy()
    risk_manager = RiskManager()
    
    # 获取历史数据
    print("\n1. 获取历史数据...")
    df = data_fetcher.fetch_historical_data()
    print(f"   获取到 {len(df)} 条数据")
    print(f"   时间范围: {df.index[0]} 到 {df.index[-1]}")
    
    # 生成日内模拟数据（用于回测）
    print("\n2. 生成日内数据...")
    intraday_df = data_fetcher.fetch_intraday_data()
    print(f"   日内数据点: {len(intraday_df)}")
    
    # 运行回测
    print("\n3. 运行策略回测...")
    results_df = strategy.backtest(intraday_df)
    print("   回测完成！")
    
    # 显示策略表现
    print("\n4. 策略表现分析:")
    metrics = strategy.get_performance_metrics()
    for key, value in metrics.items():
        print(f"   {key}: {value}")
    
    # 显示风险指标
    print("\n5. 风险指标:")
    if not intraday_df.empty:
        current_price = intraday_df['price'].iloc[-1]
        risk_metrics = risk_manager.get_risk_metrics(current_price)
        for key, value in risk_metrics.items():
            print(f"   {key}: {value}")
    
    return results_df


def example_real_time_simulation():
    """示例：模拟实时交易"""
    print("\n" + "=" * 60)
    print("示例2：模拟实时交易流程")
    print("=" * 60)
    
    data_fetcher = DataFetcher()
    strategy = IntradayT0Strategy()
    
    # 获取日内数据
    df = data_fetcher.fetch_intraday_data()
    if df.empty:
        print("   无法获取数据，跳过此示例")
        return
    
    # 模拟实时数据流
    print("\n模拟实时交易信号:")
    print("-" * 40)
    
    df = strategy.calculate_indicators(df)
    
    for i in range(len(df)):
        row = df.iloc[i]
        time_str = row.name.strftime("%H:%M:%S") if hasattr(row.name, 'strftime') else str(row.name)
        price = row['price']
        
        # 生成信号（简化版）
        signal = 0
        if 'dev_from_ma20' in row:
            if row['dev_from_ma20'] < -0.002:
                signal = 1
            elif row['dev_from_ma20'] > 0.002:
                signal = -1
        
        if signal != 0:
            signal_str = "买入" if signal == 1 else "卖出"
            print(f"   [{time_str}] 价格: {price:.3f} | 信号: {signal_str}")
    
    print("-" * 40)
    print("模拟完成！")


def example_parameter_optimization():
    """示例：参数优化（简单演示）"""
    print("\n" + "=" * 60)
    print("示例3：参数优化演示")
    print("=" * 60)
    
    data_fetcher = DataFetcher()
    df = data_fetcher.fetch_intraday_data()
    if df.empty:
        print("   无法获取数据，跳过此示例")
        return
    
    print("\n测试不同的布林带倍数参数:")
    print("-" * 40)
    
    std_values = [0.5, 0.8, 1.0, 1.2, 1.5]
    results = []
    
    for std in std_values:
        strategy = IntradayT0Strategy()
        strategy.params['std_threshold'] = std
        strategy.backtest(df)
        metrics = strategy.get_performance_metrics()
        results.append({
            'std_threshold': std,
            'total_trades': metrics.get('total_trades', 0),
            'total_pnl': metrics.get('total_pnl', 0),
            'win_rate': metrics.get('win_rate', 0)
        })
        print(f"   std={std}: 交易次数={metrics.get('total_trades', 0)}, "
              f"盈亏={metrics.get('total_pnl', 0):.2f}, "
              f"胜率={metrics.get('win_rate', 0):.2%}")
    
    print("-" * 40)
    return results


def main():
    """主函数 - 运行所有示例"""
    print("\n" + "=" * 60)
    print("华安黄金ETF(518880) 日内做T系统")
    print("功能示例演示")
    print("=" * 60)
    
    try:
        # 示例1：回测
        results_df = example_backtest()
        
        # 示例2：模拟实时交易
        example_real_time_simulation()
        
        # 示例3：参数优化
        example_parameter_optimization()
        
        print("\n" + "=" * 60)
        print("所有示例运行完成！")
        print("\n提示：")
        print("- 要运行Web界面，请执行: streamlit run app.py")
        print("- 更多使用说明，请查看项目文档")
        print("=" * 60 + "\n")
        
    except Exception as e:
        print(f"\n运行出错: {e}")
        print("但不影响系统功能，这只是一个演示脚本")


if __name__ == "__main__":
    main()

