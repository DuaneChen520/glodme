
# 黄金ETF华安（518880）日内做T系统配置文件

import os

# 基础配置
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
LOG_DIR = os.path.join(BASE_DIR, 'logs')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')

# 创建必要的目录
for dir_path in [DATA_DIR, LOG_DIR, OUTPUT_DIR]:
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)

# 标的配置
TICKER = '518880.SH'  # 黄金ETF华安
ASSET_NAME = '华安黄金ETF'

# 交易参数
INITIAL_CAPITAL = 100000.0  # 初始资金
TRADING_COST_RATE = 0.0003  # 交易佣金率（万分之三）
MIN_COST = 5.0  # 最低佣金5元
TICK_SIZE = 0.001  # 最小价格变动单位
SHARE_MULTIPLIER = 100  # 每手100份
MAX_POSITION_RATIO = 0.3  # 最大仓位比例

# 日内做T策略参数
STRATEGY_PARAMS = {
    'lookback_period': 20,  # 回看周期
    'std_threshold': 0.8,  # 标准差阈值
    'entry_threshold': 0.001,  # 入场阈值
    'exit_threshold': 0.0008,  # 出场阈值
    'max_position_ratio': 0.3,  # 最大仓位比例
    'stop_loss_ratio': 0.005,  # 止损比例
    'take_profit_ratio': 0.008,  # 止盈比例
}

# 时间配置
TRADING_DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
TRADING_SESSION_MORNING_START = '09:30:00'
TRADING_SESSION_MORNING_END = '11:30:00'
TRADING_SESSION_AFTERNOON_START = '13:00:00'
TRADING_SESSION_AFTERNOON_END = '15:00:00'

# 数据获取配置
DATA_SOURCE = 'akshare'  # 数据源选项: akshare, yfinance
UPDATE_INTERVAL = 60  # 数据更新间隔（秒）

# 日志配置
LOG_LEVEL = 'INFO'
LOG_FILE = os.path.join(LOG_DIR, 'trading_system.log')

