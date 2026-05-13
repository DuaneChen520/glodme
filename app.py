
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time

from config import TICKER, ASSET_NAME
from data_fetcher import DataFetcher
from strategy import IntradayT0Strategy
from risk_manager import RiskManager

# 页面配置
st.set_page_config(
    page_title="黄金ETF日内做T系统",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 初始化数据
if 'data_fetcher' not in st.session_state:
    st.session_state.data_fetcher = DataFetcher()
if 'strategy' not in st.session_state:
    st.session_state.strategy = IntradayT0Strategy()
if 'risk_manager' not in st.session_state:
    st.session_state.risk_manager = RiskManager()
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'intraday_data' not in st.session_state:
    st.session_state.intraday_data = pd.DataFrame()


st.title("📊 华安黄金ETF(518880) 日内做T系统")
st.markdown("---")

# 侧边栏配置
with st.sidebar:
    st.header("⚙️ 系统配置")
    
    # 策略参数
    st.subheader("策略参数")
    lookback_period = st.slider("回看周期", 5, 50, 20)
    std_threshold = st.slider("布林带倍数", 0.5, 2.0, 0.8, 0.1)
    entry_threshold = st.slider("入场阈值", 0.001, 0.01, 0.001, 0.001)
    exit_threshold = st.slider("出场阈值", 0.0005, 0.005, 0.0008, 0.0001)
    stop_loss = st.slider("止损比例", 0.001, 0.02, 0.005, 0.001)
    take_profit = st.slider("止盈比例", 0.002, 0.03, 0.008, 0.001)
    
    # 更新策略参数
    new_params = {
        'lookback_period': lookback_period,
        'std_threshold': std_threshold,
        'entry_threshold': entry_threshold,
        'exit_threshold': exit_threshold,
        'stop_loss_ratio': stop_loss,
        'take_profit_ratio': take_profit,
        'max_position_ratio': 0.3
    }
    
    if st.button("更新策略参数"):
        st.session_state.strategy.params = new_params
        st.success("参数已更新！")
    
    st.markdown("---")
    
    # 回测功能
    st.subheader("📊 回测功能")
    backtest_date = st.date_input("回测日期", datetime.now() - timedelta(days=1))
    
    if st.button("运行回测"):
        with st.spinner("正在运行回测..."):
            # 获取日内数据
            date_str = backtest_date.strftime("%Y-%m-%d")
            df = st.session_state.data_fetcher.fetch_intraday_data(date_str)
            
            if not df.empty:
                # 运行回测
                st.session_state.strategy.reset()
                results_df = st.session_state.strategy.backtest(df)
                st.session_state.intraday_data = results_df
                st.success("回测完成！")
            else:
                st.error("获取数据失败，请检查日期或网络")
    
    st.markdown("---")
    
    # 控制按钮
    st.subheader("🎛️ 交易控制")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("▶️ 启动", type="primary"):
            st.session_state.is_running = True
            st.success("系统已启动！")
    
    with col2:
        if st.button("⏹️ 停止"):
            st.session_state.is_running = False
            st.warning("系统已停止")


# 主界面
tab1, tab2, tab3, tab4 = st.tabs(["📈 实时监控", "📊 策略分析", "💰 风险管理", "📋 交易记录"])

# Tab 1: 实时监控
with tab1:
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.subheader("价格走势图")
        
        # 获取实时数据
        if st.session_state.intraday_data.empty:
            # 生成示例数据
            df = st.session_state.data_fetcher.fetch_intraday_data()
            st.session_state.intraday_data = st.session_state.strategy.generate_signals(df)
        
        df = st.session_state.intraday_data
        
        if not df.empty:
            # 创建价格图表
            fig = go.Figure()
            
            # 价格线
            fig.add_trace(go.Scatter(
                x=df.index,
                y=df['price'],
                name='价格',
                line=dict(color='#1f77b4', width=2)
            ))
            
            # 布林带
            if 'MA20' in df.columns:
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df['upper_band'],
                    name='上轨',
                    line=dict(color='#ff7f0e', width=1, dash='dash'),
                    opacity=0.7
                ))
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df['MA20'],
                    name='中轨',
                    line=dict(color='#2ca02c', width=1, dash='dash'),
                    opacity=0.7
                ))
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df['lower_band'],
                    name='下轨',
                    line=dict(color='#ff7f0e', width=1, dash='dash'),
                    opacity=0.7
                ))
            
            # 买卖信号标记
            buy_signals = df[df['signal'] == 1]
            sell_signals = df[df['signal'] == -1]
            
            if not buy_signals.empty:
                fig.add_trace(go.Scatter(
                    x=buy_signals.index,
                    y=buy_signals['price'],
                    mode='markers',
                    name='买入信号',
                    marker=dict(symbol='triangle-up', size=10, color='#2ca02c')
                ))
            
            if not sell_signals.empty:
                fig.add_trace(go.Scatter(
                    x=sell_signals.index,
                    y=sell_signals['price'],
                    mode='markers',
                    name='卖出信号',
                    marker=dict(symbol='triangle-down', size=10, color='#d62728')
                ))
            
            fig.update_layout(
                title='价格与技术指标',
                xaxis_title='时间',
                yaxis_title='价格',
                hovermode='x unified',
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("实时状态")
        
        # 最新价格
        if not df.empty:
            latest_price = df['price'].iloc[-1]
            prev_price = df['price'].iloc[-2] if len(df) > 1 else latest_price
            price_change = latest_price - prev_price
            change_pct = (price_change / prev_price) * 100 if prev_price != 0 else 0
            
            st.metric(
                label="最新价格",
                value=f"{latest_price:.3f}",
                delta=f"{change_pct:+.2f}%",
                delta_color="normal"
            )
            
            # 状态指标
            st.markdown("### 系统状态")
            status_color = "green" if st.session_state.is_running else "red"
            st.markdown(f"**运行状态**: <span style='color:{status_color}'>{'运行中' if st.session_state.is_running else '已停止'}</span>", 
                       unsafe_allow_html=True)
            
            # 当前持仓
            position = st.session_state.strategy.position
            st.metric(
                label="当前持仓",
                value=f"{position} 份",
                delta=None
            )
            
            if position != 0:
                entry_price = st.session_state.strategy.entry_price
                unrealized_pnl = (latest_price - entry_price) * position if position > 0 else (entry_price - latest_price) * abs(position)
                st.metric(
                    label="浮动盈亏",
                    value=f"{unrealized_pnl:.2f}",
                    delta=f"{unrealized_pnl / (abs(position) * entry_price) * 100:+.2f}%" if position != 0 else None
                )

# Tab 2: 策略分析
with tab2:
    st.subheader("策略表现")
    
    col1, col2, col3, col4 = st.columns(4)
    
    metrics = st.session_state.strategy.get_performance_metrics()
    
    with col1:
        st.metric("总交易次数", metrics.get('total_trades', 0))
    with col2:
        st.metric("总盈亏", f"{metrics.get('total_pnl', 0):.2f}")
    with col3:
        st.metric("胜率", f"{metrics.get('win_rate', 0):.2%}")
    with col4:
        st.metric("盈亏比", f"{metrics.get('profit_factor', 0):.2f}")
    
    st.markdown("---")
    
    # 技术指标图表
    if not df.empty and 'RSI' in df.columns:
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            row_heights=[0.6, 0.4]
        )
        
        # 价格图
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['price'],
            name='价格',
            line=dict(color='#1f77b4')
        ), row=1, col=1)
        
        # RSI图
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['RSI'],
            name='RSI',
            line=dict(color='#9467bd')
        ), row=2, col=1)
        
        # RSI超买超卖线
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)
        
        fig.update_layout(
            height=600,
            title_text="价格与RSI指标"
        )
        
        st.plotly_chart(fig, use_container_width=True)

# Tab 3: 风险管理
with tab3:
    st.subheader("风险指标")
    
    # 获取当前价格
    current_price = df['price'].iloc[-1] if not df.empty else 4.5
    
    risk_metrics = st.session_state.risk_manager.get_risk_metrics(current_price)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("初始资金", f"{risk_metrics.get('initial_capital', 0):.2f}")
        st.metric("当前资金", f"{risk_metrics.get('current_capital', 0):.2f}")
        st.metric("总盈亏", f"{risk_metrics.get('total_pnl', 0):.2f}")
        st.metric("收益率", f"{risk_metrics.get('return_pct', 0):.2%}")
    
    with col2:
        st.metric("持仓市值", f"{risk_metrics.get('position_value', 0):.2f}")
        st.metric("持仓比例", f"{risk_metrics.get('position_ratio', 0):.2%}")
        st.metric("最大回撤", f"{risk_metrics.get('max_drawdown', 0):.2%}")
        st.metric("交易次数", risk_metrics.get('num_trades', 0))
    
    st.markdown("---")
    
    # 资金曲线
    if st.session_state.risk_manager.trade_history:
        trades = st.session_state.risk_manager.trade_history
        capital_history = [st.session_state.risk_manager.initial_capital]
        
        for trade in trades:
            if trade['action'] == 'buy':
                capital_history.append(capital_history[-1] - trade['size'] * trade['price'] - trade['cost'])
            else:
                capital_history.append(capital_history[-1] + trade['size'] * trade['price'] - trade['cost'])
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=list(range(len(capital_history))),
            y=capital_history,
            name='资金曲线',
            line=dict(color='#1f77b4', width=2),
            fill='tozeroy',
            fillcolor='rgba(31, 119, 180, 0.1)'
        ))
        fig.update_layout(
            title='资金曲线',
            xaxis_title='交易次数',
            yaxis_title='资金',
            height=400
        )
        st.plotly_chart(fig, use_container_width=True)

# Tab 4: 交易记录
with tab4:
    st.subheader("交易历史")
    
    if st.session_state.strategy.trade_history:
        trade_df = pd.DataFrame(st.session_state.strategy.trade_history)
        trade_df = trade_df.sort_values('timestamp', ascending=False)
        
        st.dataframe(
            trade_df.style.format({
                'price': '{:.3f}',
                'pnl': '{:.2f}',
                'cost': '{:.2f}'
            }),
            use_container_width=True
        )
        
        # 下载按钮
        csv = trade_df.to_csv(index=False)
        st.download_button(
            label="📥 下载交易记录",
            data=csv,
            file_name=f"trades_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("暂无交易记录")

# 底部说明
st.markdown("---")
st.markdown("""
### 📖 使用说明
1. **系统配置**: 在左侧边栏调整策略参数
2. **回测分析**: 选择历史日期进行策略回测
3. **实时监控**: 查看价格走势和实时信号
4. **风险管理**: 监控资金曲线和风险指标

⚠️ **免责声明**: 本系统仅供学习和研究使用，不构成投资建议。投资有风险，交易需谨慎。
""")

# 自动刷新（如果运行中）
if st.session_state.is_running:
    time.sleep(5)
    st.rerun()

