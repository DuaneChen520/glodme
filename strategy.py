
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import Optional, Dict, List, Tuple

from config import STRATEGY_PARAMS, SHARE_MULTIPLIER
from data_fetcher import DataFetcher

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IntradayT0Strategy:
    """日内做T策略核心类"""

    def __init__(self, params: Optional[Dict] = None):
        """
        初始化策略

        Args:
            params: 策略参数字典，如不提供则使用默认配置
        """
        self.params = params if params else STRATEGY_PARAMS.copy()
        self.data_fetcher = DataFetcher()
        self.position = 0  # 当前持仓（正为多头，负为空头，0为空仓）
        self.entry_price = 0.0  # 入场价格
        self.trade_history = []
        self.pnl_history = []
        self.price_history = []

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算技术指标

        Args:
            df: 包含价格数据的DataFrame

        Returns:
            添加了技术指标的DataFrame
        """
        df = df.copy()

        # 移动平均线
        df['MA_short'] = df['price'].rolling(window=5).mean()
        df['MA_mid'] = df['price'].rolling(window=10).mean()
        df['MA_long'] = df['price'].rolling(window=20).mean()

        # 布林带
        df['MA20'] = df['price'].rolling(window=20).mean()
        df['std20'] = df['price'].rolling(window=20).std()
        df['upper_band'] = df['MA20'] + df['std20'] * self.params['std_threshold']
        df['lower_band'] = df['MA20'] - df['std20'] * self.params['std_threshold']

        # RSI
        delta = df['price'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # MACD
        df['EMA12'] = df['price'].ewm(span=12, adjust=False).mean()
        df['EMA26'] = df['price'].ewm(span=26, adjust=False).mean()
        df['MACD'] = df['EMA12'] - df['EMA26']
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['Histogram'] = df['MACD'] - df['Signal']

        # 价格偏离度
        df['dev_from_ma20'] = (df['price'] - df['MA20']) / df['MA20']

        return df

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号

        Args:
            df: 包含价格和技术指标的DataFrame

        Returns:
            添加了交易信号的DataFrame
        """
        df = self.calculate_indicators(df)
        df['signal'] = 0  # 0: 无信号, 1: 买入, -1: 卖出

        for i in range(1, len(df)):
            price = df['price'].iloc[i]
            upper = df['upper_band'].iloc[i]
            lower = df['lower_band'].iloc[i]
            rsi = df['RSI'].iloc[i]
            ma_short = df['MA_short'].iloc[i]
            ma_mid = df['MA_mid'].iloc[i]

            # 做多信号：价格跌破下轨 + RSI超卖 + 短期均线上穿中期均线
            if (price < lower and 
                rsi < 30 and 
                ma_short > ma_mid and 
                df['MA_short'].iloc[i-1] <= df['MA_mid'].iloc[i-1]):
                df['signal'].iloc[i] = 1

            # 做空信号：价格突破上轨 + RSI超买 + 短期均线下穿中期均线
            elif (price > upper and 
                  rsi > 70 and 
                  ma_short < ma_mid and 
                  df['MA_short'].iloc[i-1] >= df['MA_mid'].iloc[i-1]):
                df['signal'].iloc[i] = -1

            # 基于价格偏离度的信号
            dev = df['dev_from_ma20'].iloc[i]
            if dev < -self.params['entry_threshold'] and rsi < 35:
                df['signal'].iloc[i] = 1
            elif dev > self.params['entry_threshold'] and rsi > 65:
                df['signal'].iloc[i] = -1

        return df

    def check_exit_conditions(
        self,
        current_price: float,
        entry_price: float,
        position: int
    ) -> Tuple[bool, str]:
        """
        检查出场条件

        Args:
            current_price: 当前价格
            entry_price: 入场价格
            position: 当前持仓

        Returns:
            (是否出场, 原因)
        """
        if position == 0:
            return False, "无持仓"

        # 计算盈亏
        pnl_pct = (current_price - entry_price) / entry_price if position > 0 else (entry_price - current_price) / entry_price

        # 止盈
        if pnl_pct >= self.params['take_profit_ratio']:
            return True, f"止盈：盈利{pnl_pct:.2%}"

        # 止损
        if pnl_pct <= -self.params['stop_loss_ratio']:
            return True, f"止损：亏损{pnl_pct:.2%}"

        return False, ""

    def execute_trade(
        self,
        price: float,
        timestamp: datetime,
        signal: int
    ) -> Dict:
        """
        执行交易逻辑

        Args:
            price: 当前价格
            timestamp: 时间戳
            signal: 交易信号

        Returns:
            交易记录字典
        """
        trade = {
            'timestamp': timestamp,
            'price': price,
            'action': '',
            'size': 0,
            'pnl': 0.0
        }

        # 检查是否需要先平仓
        if self.position != 0:
            should_exit, reason = self.check_exit_conditions(price, self.entry_price, self.position)
            if should_exit:
                # 平仓
                trade['action'] = 'close'
                trade['size'] = -self.position
                if self.position > 0:
                    trade['pnl'] = (price - self.entry_price) * abs(self.position)
                else:
                    trade['pnl'] = (self.entry_price - price) * abs(self.position)
                self.trade_history.append(trade.copy())
                self.pnl_history.append(trade['pnl'])
                self.position = 0
                logger.info(f"{reason} | 平仓于 {price:.3f} | 盈亏: {trade['pnl']:.2f}")

        # 根据信号开仓
        if self.position == 0 and signal != 0:
            # 计算仓位大小（简化处理）
            size = 1000  # 每次交易1000份
            size = (size // SHARE_MULTIPLIER) * SHARE_MULTIPLIER  # 按手取整

            if signal == 1:
                trade['action'] = 'buy'
                trade['size'] = size
                self.position = size
                self.entry_price = price
                logger.info(f"买入 {size} 份于 {price:.3f}")
            elif signal == -1:
                trade['action'] = 'sell'
                trade['size'] = -size
                self.position = -size
                self.entry_price = price
                logger.info(f"卖出 {size} 份于 {price:.3f}")

            self.trade_history.append(trade.copy())

        return trade

    def backtest(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        策略回测

        Args:
            df: 包含价格数据的DataFrame

        Returns:
            回测结果DataFrame
        """
        df = self.generate_signals(df)
        self.position = 0
        self.entry_price = 0.0
        self.trade_history = []
        self.pnl_history = []

        for idx, row in df.iterrows():
            signal = row['signal']
            price = row['price']
            self.execute_trade(price, idx, signal)

        # 如果回测结束仍有持仓，强制平仓
        if self.position != 0:
            last_price = df['price'].iloc[-1]
            self.execute_trade(last_price, df.index[-1], 0)

        return df

    def get_real_time_signal(self, current_data: pd.DataFrame) -> int:
        """
        获取实时交易信号

        Args:
            current_data: 包含当前和历史数据的DataFrame

        Returns:
            交易信号 (1: 买入, -1: 卖出, 0: 无)
        """
        df = self.generate_signals(current_data)
        return df['signal'].iloc[-1] if len(df) > 0 else 0

    def update_price_history(self, price: float, timestamp: datetime):
        """
        更新价格历史

        Args:
            price: 当前价格
            timestamp: 时间戳
        """
        self.price_history.append({
            'timestamp': timestamp,
            'price': price
        })
        if len(self.price_history) > 1000:
            self.price_history = self.price_history[-1000:]

    def get_performance_metrics(self) -> Dict:
        """
        获取策略表现指标

        Returns:
            包含表现指标的字典
        """
        if not self.trade_history:
            return {}

        trades = [t for t in self.trade_history if t['action'] == 'close']
        if not trades:
            return {}

        pnls = [t['pnl'] for t in trades]
        win_trades = [p for p in pnls if p > 0]
        loss_trades = [p for p in pnls if p <= 0]

        total_pnl = sum(pnls)
        win_rate = len(win_trades) / len(trades) if trades else 0
        avg_win = np.mean(win_trades) if win_trades else 0
        avg_loss = np.mean(loss_trades) if loss_trades else 0
        profit_factor = abs(sum(win_trades) / sum(loss_trades)) if loss_trades and sum(loss_trades) != 0 else float('inf')

        return {
            'total_trades': len(trades),
            'total_pnl': total_pnl,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'largest_win': max(pnls) if pnls else 0,
            'largest_loss': min(pnls) if pnls else 0,
        }

    def reset(self):
        """重置策略状态"""
        self.position = 0
        self.entry_price = 0.0
        self.trade_history = []
        self.pnl_history = []
        self.price_history = []

