
import pandas as pd
import numpy as np
from datetime import datetime
import logging
from typing import Optional, Dict, List, Tuple

from config import (
    INITIAL_CAPITAL, TRADING_COST_RATE, MIN_COST, 
    MAX_POSITION_RATIO, STRATEGY_PARAMS
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RiskManager:
    """风险管理类"""

    def __init__(self, initial_capital: float = INITIAL_CAPITAL):
        """
        初始化风险管理

        Args:
            initial_capital: 初始资金
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.position = 0  # 当前持仓数量
        self.position_value = 0.0  # 持仓市值
        self.avg_entry_price = 0.0  # 平均入场价格
        self.trade_history = []
        self.daily_pnl = []
        self.max_drawdown = 0.0
        self.peak_capital = initial_capital
        self.max_position_ratio = STRATEGY_PARAMS['max_position_ratio']

    def calculate_trading_cost(self, size: int, price: float) -> float:
        """
        计算交易成本

        Args:
            size: 交易数量
            price: 交易价格

        Returns:
            交易成本
        """
        value = abs(size) * price
        cost = value * TRADING_COST_RATE
        return max(cost, MIN_COST)

    def check_position_limit(self, new_position: int, price: float) -> Tuple[bool, int]:
        """
        检查持仓限制

        Args:
            new_position: 目标持仓
            price: 当前价格

        Returns:
            (是否允许, 调整后的持仓)
        """
        max_position_value = self.current_capital * self.max_position_ratio
        new_position_value = abs(new_position) * price

        if new_position_value <= max_position_value:
            return True, new_position

        # 超过限制，调整持仓
        adjusted_size = int(max_position_value / price)
        if new_position > 0:
            return False, adjusted_size
        else:
            return False, -adjusted_size

    def check_daily_loss_limit(self, current_price: float) -> bool:
        """
        检查每日亏损限制

        Args:
            current_price: 当前价格

        Returns:
            True表示可以继续交易，False表示触发止损
        """
        today = datetime.now().date()
        today_trades = [t for t in self.trade_history if t['timestamp'].date() == today]

        if not today_trades:
            return True

        # 计算今日盈亏
        today_pnl = sum(t['pnl'] for t in today_trades)

        # 加上当前持仓的浮动盈亏
        if self.position != 0:
            unrealized_pnl = (current_price - self.avg_entry_price) * self.position
            total_pnl = today_pnl + unrealized_pnl
        else:
            total_pnl = today_pnl

        # 每日亏损限制设为初始资金的2%
        daily_loss_limit = self.initial_capital * 0.02
        if total_pnl <= -daily_loss_limit:
            logger.warning(f"触发每日亏损限制！今日亏损: {total_pnl:.2f}")
            return False

        return True

    def execute_trade(
        self,
        action: str,
        size: int,
        price: float,
        timestamp: datetime
    ) -> Dict:
        """
        执行交易并更新风控状态

        Args:
            action: 'buy' 或 'sell'
            size: 交易数量（正数）
            price: 交易价格
            timestamp: 时间戳

        Returns:
            交易记录
        """
        trade = {
            'timestamp': timestamp,
            'action': action,
            'size': size,
            'price': price,
            'cost': 0.0,
            'pnl': 0.0
        }

        # 计算交易成本
        trade['cost'] = self.calculate_trading_cost(size, price)

        # 更新资金
        if action == 'buy':
            self.current_capital -= size * price + trade['cost']
            # 更新持仓
            old_position = self.position
            old_value = old_position * self.avg_entry_price
            new_value = size * price
            self.position = old_position + size
            if self.position != 0:
                self.avg_entry_price = (old_value + new_value) / self.position
            else:
                self.avg_entry_price = 0.0
        elif action == 'sell':
            # 计算盈亏
            if self.position > 0:
                trade['pnl'] = (price - self.avg_entry_price) * size - trade['cost']
            else:
                trade['pnl'] = (self.avg_entry_price - price) * size - trade['cost']

            self.current_capital += size * price - trade['cost']
            # 更新持仓
            self.position -= size
            if self.position == 0:
                self.avg_entry_price = 0.0

        # 更新持仓市值
        self.position_value = abs(self.position) * price

        # 记录交易
        self.trade_history.append(trade)

        # 更新峰值和最大回撤
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown

        logger.info(
            f"{action.upper()} {size} @ {price:.3f} | "
            f"成本: {trade['cost']:.2f} | "
            f"盈亏: {trade['pnl']:.2f} | "
            f"资金: {self.current_capital:.2f} | "
            f"持仓: {self.position}"
        )

        return trade

    def calculate_position_pnl(self, current_price: float) -> float:
        """
        计算当前持仓的浮动盈亏

        Args:
            current_price: 当前价格

        Returns:
            浮动盈亏
        """
        if self.position == 0:
            return 0.0
        return (current_price - self.avg_entry_price) * self.position

    def get_risk_metrics(self, current_price: float) -> Dict:
        """
        获取风险指标

        Args:
            current_price: 当前价格

        Returns:
            风险指标字典
        """
        unrealized_pnl = self.calculate_position_pnl(current_price)
        total_pnl = self.current_capital - self.initial_capital + unrealized_pnl
        return_pct = total_pnl / self.initial_capital

        position_ratio = self.position_value / self.current_capital if self.current_capital > 0 else 0

        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'total_pnl': total_pnl,
            'return_pct': return_pct,
            'unrealized_pnl': unrealized_pnl,
            'position': self.position,
            'position_value': self.position_value,
            'position_ratio': position_ratio,
            'avg_entry_price': self.avg_entry_price,
            'max_drawdown': self.max_drawdown,
            'peak_capital': self.peak_capital,
            'num_trades': len(self.trade_history)
        }

    def should_stop_trading(self, current_price: float) -> bool:
        """
        判断是否应该停止交易

        Args:
            current_price: 当前价格

        Returns:
            True表示应该停止
        """
        # 检查总资金回撤
        total_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital
        if total_drawdown >= 0.10:  # 10%总回撤
            logger.warning(f"触发总资金回撤限制！回撤: {total_drawdown:.2%}")
            return True

        # 检查每日亏损
        if not self.check_daily_loss_limit(current_price):
            return True

        return False

    def reset(self):
        """重置风控状态"""
        self.current_capital = self.initial_capital
        self.position = 0
        self.position_value = 0.0
        self.avg_entry_price = 0.0
        self.trade_history = []
        self.max_drawdown = 0.0
        self.peak_capital = self.initial_capital


class PortfolioManager:
    """投资组合管理"""

    def __init__(self, initial_capital: float = INITIAL_CAPITAL):
        self.risk_manager = RiskManager(initial_capital)
        self.assets = {}  # 资产持仓信息

    def add_asset(self, symbol: str, name: str = ""):
        """添加资产"""
        self.assets[symbol] = {
            'name': name,
            'position': 0,
            'avg_price': 0.0,
            'market_value': 0.0
        }

    def update_market_value(self, symbol: str, price: float):
        """更新市值"""
        if symbol in self.assets:
            self.assets[symbol]['market_value'] = self.assets[symbol]['position'] * price

    def get_portfolio_summary(self, prices: Dict[str, float]) -> Dict:
        """获取组合摘要"""
        total_value = self.risk_manager.current_capital
        for symbol, data in self.assets.items():
            price = prices.get(symbol, data['avg_price'])
            total_value += data['position'] * price

        return {
            'total_value': total_value,
            'cash': self.risk_manager.current_capital,
            'assets': self.assets
        }

